"""Strict manifest loading and portable, contained collection paths."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import json
import re


SUPPORTED_VERSIONS = ("1.1.x", "27.1.x")


class ManifestError(ValueError):
    pass


def read_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


@dataclass(frozen=True)
class Collection:
    id: str
    name: str
    category: str
    directory: Path
    expected_count: int
    source: dict
    units: str
    geometry: dict
    compatible_versions: tuple
    status: str
    legacy_names: tuple = ()

    def files(self):
        if not self.directory.is_dir():
            return []
        files = sorted(self.directory.rglob("*.fctb"))
        for path in files:
            if not path.resolve().is_relative_to(self.directory.resolve()):
                raise ManifestError(f"Tool symlink escapes collection: {path}")
        return files

    def availability(self):
        count = len(self.files())
        return self.status == "available" and count == self.expected_count, count


def load_manifest(path):
    path = Path(path).resolve()
    root = path.parent
    data = read_json(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ManifestError("Expected manifest schema_version 1")
    if not isinstance(data.get("collections"), list):
        raise ManifestError("collections must be a list")
    result, ids, names, directories = [], set(), set(), set()
    for row in data["collections"]:
        if not isinstance(row, dict):
            raise ManifestError("Collection must be an object")
        required = ("id", "name", "category", "directory", "expected_count", "source",
                    "units", "geometry", "compatible_versions", "status")
        if any(key not in row for key in required):
            raise ManifestError(f"Missing collection fields: {row}")
        cid, name, directory = row["id"], row["name"], row["directory"]
        if not isinstance(cid, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", cid):
            raise ManifestError(f"Invalid collection id: {cid}")
        if not isinstance(name, str) or not name.strip() or name in names or cid in ids:
            raise ManifestError(f"Empty or duplicate collection name/id: {cid}")
        if not isinstance(directory, str) or not directory or "\\" in directory or ":" in directory:
            raise ManifestError("Use a relative POSIX directory path")
        rel = PurePosixPath(directory)
        target = (root / directory).resolve()
        if rel.is_absolute() or ".." in rel.parts or not target.is_relative_to(root) or target == root:
            raise ManifestError(f"Directory escapes libraries: {directory}")
        if target in directories:
            raise ManifestError(f"Duplicate collection directory: {directory}")
        if row["category"] not in ("drills", "endmills", "threadmills"):
            raise ManifestError("Unsupported category")
        if type(row["expected_count"]) is not int or row["expected_count"] <= 0:
            raise ManifestError("expected_count must be a positive integer")
        if row["units"] not in ("metric", "imperial"):
            raise ManifestError("units must be metric or imperial")
        if row["status"] not in ("available", "missing"):
            raise ManifestError("status must be available or missing")
        versions = row["compatible_versions"]
        if not isinstance(versions, list) or not versions or any(v not in SUPPORTED_VERSIONS for v in versions):
            raise ManifestError("compatible_versions must contain supported families: 1.1.x, 27.1.x")
        legacy_names = row.get("legacy_names", [])
        if (not isinstance(legacy_names, list)
                or any(not isinstance(n, str) or not n.strip() or n == name or n in names for n in legacy_names)
                or len(set(legacy_names)) != len(legacy_names)):
            raise ManifestError("legacy_names must be distinct, nonempty historical names without collection collisions")
        source, geometry = row["source"], row["geometry"]
        if not isinstance(source, dict) or any(not isinstance(source.get(k), str) or not source[k]
                                               for k in ("attribution", "redistribution")):
            raise ManifestError("source needs attribution and redistribution status")
        if not isinstance(geometry, dict) or any(not isinstance(geometry.get(k), str) or not geometry[k]
                                                 for k in ("description", "accuracy", "notes")):
            raise ManifestError("geometry needs description, accuracy, and notes")
        if geometry["accuracy"] not in ("verified", "generic", "provisional", "unavailable"):
            raise ManifestError("Unknown geometry accuracy")
        ids.add(cid); names.add(name); names.update(legacy_names); directories.add(target)
        result.append(Collection(cid, name, row["category"], target, row["expected_count"],
                                 source, row["units"], geometry, tuple(versions), row["status"], tuple(legacy_names)))
    return result
