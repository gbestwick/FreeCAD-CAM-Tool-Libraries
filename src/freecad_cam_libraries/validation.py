"""FreeCAD 1.1 schemas plus explicit collection-quality requirements.

No values are filled in or changed. Bare lengths are FreeCAD base units (mm).
The deliberately limited unit parser accepts mm, cm, m, um, in and degrees.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import json
import re
import uuid
from .manifest import read_json


SCHEMAS = {
    "drill.fcstd": ("Drill", ("Diameter", "Length", "CuttingEdgeHeight", "TipAngle", "Flutes", "Material")),
    "endmill.fcstd": ("Endmill", ("Diameter", "Length", "CuttingEdgeHeight", "ShankDiameter", "Flutes", "Material")),
    "thread-mill.fcstd": ("ThreadMill", ("Diameter", "Length", "NeckDiameter", "NeckLength", "ShankDiameter", "Crest", "cuttingAngle", "Flutes")),
}
LENGTHS = {"Diameter", "Length", "CuttingEdgeHeight", "ShankDiameter", "NeckDiameter", "NeckLength", "Crest", "Chipload"}
ANGLES = {"TipAngle", "cuttingAngle"}
UNITS = {"": Decimal(1), "mm": Decimal(1), "cm": Decimal(10), "m": Decimal(1000),
         "um": Decimal("0.001"), "µm": Decimal("0.001"), "in": Decimal("25.4")}


class ValidationError(ValueError):
    pass


def quantity(value, angle=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValidationError(f"Invalid quantity: {value!r}")
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([^\d\s]*)\s*", str(value))
    if not match:
        raise ValidationError(f"Unsupported quantity: {value!r}")
    number, unit = match.groups()
    factors = {"": Decimal(1), "°": Decimal(1), "deg": Decimal(1)} if angle else UNITS
    if unit not in factors:
        raise ValidationError(f"Unsupported {'angle' if angle else 'length'} unit: {unit}")
    try:
        result = Decimal(number) * factors[unit]
    except InvalidOperation as exc:
        raise ValidationError(f"Invalid quantity {value}") from exc
    if not result.is_finite():
        raise ValidationError("Quantity must be finite")
    return result


def properties(data):
    params, attrs = data.get("parameter", {}), data.get("attribute", {})
    if not isinstance(params, dict) or not isinstance(attrs, dict):
        raise ValidationError("parameter and attribute must be objects")
    for key in params.keys() & attrs.keys():
        if params[key] != attrs[key]:
            raise ValidationError(f"Conflicting parameter/attribute: {key}")
    return dict(params, **attrs)


def fingerprint(data, include_name=False):
    """Conservative equivalence: all properties/extra metadata must agree.

    Normalize known units and parameter/attribute placement, ignore UUID and
    display name for equivalence. Unknown values remain exact, never inferred.
    """
    props = properties(data)
    for key, value in props.items():
        if key in LENGTHS or key in ANGLES:
            props[key] = str(quantity(value, key in ANGLES).normalize())
    rest = {k: v for k, v in data.items() if k not in
            ("id", "name", "parameter", "attribute", "shape-type")}
    if include_name:
        rest["name"] = data.get("name")
    rest["properties"] = props
    return hashlib.sha256(json.dumps(rest, sort_keys=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Tool:
    path: Path
    data: dict
    raw: bytes
    warnings: tuple = ()

    @property
    def id(self):
        return self.data["id"]


def validate_tool(path, category=None):
    path = Path(path)
    raw = path.read_bytes()
    try:
        data = read_json(raw)
        if not isinstance(data, dict):
            raise ValidationError("Tool must be an object")
        ident = data.get("id")
        if not isinstance(ident, str) or str(uuid.UUID(ident)) != ident or path.stem != ident:
            raise ValidationError("Canonical UUID must match filename")
        if data.get("version") != 2 or type(data.get("version")) is not int:
            raise ValidationError("Only fctb version 2 is supported")
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            raise ValidationError("Missing tool name")
        shape = data.get("shape")
        if shape not in SCHEMAS:
            raise ValidationError(f"Unsupported shape: {shape!r}; thread mills require thread-mill.fcstd")
        shape_type, required = SCHEMAS[shape]
        if data.get("shape-type") != shape_type:
            raise ValidationError(f"shape-type must be {shape_type}")
        if category and {"drill.fcstd": "drills", "endmill.fcstd": "endmills", "thread-mill.fcstd": "threadmills"}[shape] != category:
            raise ValidationError("Shape does not match collection category")
        if not isinstance(data.get("parameter"), dict):
            raise ValidationError("Missing parameter object")
        props = properties(data)
        for key in required:
            if key not in props:
                raise ValidationError(f"Missing {shape_type} property: {key}")
        values = {}
        for key, value in props.items():
            if key in LENGTHS or key in ANGLES:
                values[key] = quantity(value, key in ANGLES)
                if values[key] < 0 or (values[key] == 0 and key not in ("Crest", "Chipload")):
                    raise ValidationError(f"{key} must be positive (Crest/Chipload may be zero)")
                if key in ANGLES and not 0 < values[key] < 180:
                    raise ValidationError(f"{key} must be between 0 and 180 degrees")
        flutes = props["Flutes"]
        if type(flutes) is not int or flutes <= 0:
            raise ValidationError("Flutes must be a positive integer")
        if "Material" in props and props["Material"] not in ("HSS", "Carbide"):
            raise ValidationError("Material must be HSS or Carbide; unknown materials require review")
        for key in ("CuttingEdgeHeight", "NeckLength"):
            if key in values and values[key] > values["Length"]:
                raise ValidationError(f"{key} exceeds Length")
        if "NeckDiameter" in values and values["NeckDiameter"] > values["Diameter"]:
            raise ValidationError("NeckDiameter exceeds cutting Diameter")
        warnings = ()
        if shape == "drill.fcstd":
            warnings = ("Standard drill geometry does not model a stepped shank; CuttingEdgeHeight is collection metadata beyond the drill schema.",)
        return Tool(path, data, raw, warnings)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValidationError(f"{path.name}: {exc}") from exc
