"""FreeCAD CAM boundary for 1.1.x and the 27.1.x development family.

Only public asset-manager/model/serializer methods are used. No internal files
or database tables are edited. Importing this module works outside FreeCAD.
"""
from .manifest import read_json, SUPPORTED_VERSIONS


def check_version(version):
    try:
        major, minor = int(version[0]), int(version[1])
    except (ValueError, TypeError, IndexError) as exc:
        raise RuntimeError(f"Unrecognized FreeCAD version: {version}") from exc
    family = f"{major}.{minor}.x"
    if family not in SUPPORTED_VERSIONS:
        raise RuntimeError(f"Requires FreeCAD 1.1.x or 27.1.x development; found {'.'.join(map(str, version[:3]))}")
    return family


class FreeCADAdapter:
    def __init__(self):
        import FreeCAD
        check_version(FreeCAD.Version())
        # Import package to register serializers before using cam_assets.
        from Path.Tool import Library, ToolBit, cam_assets
        from Path.Tool.assets import AssetUri, DummyAssetSerializer
        from Path.Tool.shape import ToolBitShape
        from Path.Tool.toolbit.serializers import FCTBSerializer
        self.assets, self.Library = cam_assets, Library
        self.AssetUri, self.serializer = AssetUri, FCTBSerializer
        self.Shape, self.shape_serializer = ToolBitShape, DummyAssetSerializer
        for name in ("list_assets", "get_raw", "get", "exists", "add_raw", "add", "delete"):
            if not callable(getattr(cam_assets, name, None)):
                raise RuntimeError(f"FreeCAD CAM API missing {name}")
        # setup() deliberately omitted: it seeds/migrates user assets, even
        # during a preview. Normal CAM startup may already have called it.

    def snapshot(self):
        tools, libraries = {}, []
        for store in ("builtin", "local"):
            for uri in self.assets.list_assets("toolbit", store=store):
                tools[uri.asset_id] = read_json(self.assets.get_raw(uri, store=store))
        for uri in self.assets.list_assets("toolbitlibrary", store="local"):
            raw = self.assets.get_raw(uri, store="local")
            data = read_json(raw)
            libraries.append({"id": uri.asset_id, "label": data.get("label", uri.asset_id),
                              "data": data, "raw": raw})
        return tools, libraries

    def tool_data(self, ident):
        uri = f"toolbit://{ident}"
        for store in ("local", "builtin"):
            if self.assets.exists(uri, store=store):
                return read_json(self.assets.get_raw(uri, store=store))
        return None

    def prepare(self, tool):
        # ToolBitShape contains native Base.Quantity values that cannot be
        # pickled/deep-copied. Rehydrate independent shapes via their public
        # native importer instead of mutating cached assets or Python copying.
        dependencies = {}
        for uri in self.serializer.extract_dependencies(tool.raw):
            raw = self.assets.get_raw(uri, store=("local", "builtin"))
            dependencies[uri] = self.Shape.from_bytes(
                raw, uri.asset_id, dependencies=None, serializer=self.shape_serializer
            )
        return self.serializer.deserialize(tool.raw, tool.id, dependencies)

    def register(self, tool, prepared):
        if self.tool_data(tool.id) is not None:
            raise RuntimeError("Tool appeared after preview; rerun to inspect it")
        # add_raw is the documented API behind add_file. Preserve exact source
        # bytes: do not serialize native defaults back into contributed data.
        self.assets.add_raw("toolbit", tool.id, tool.raw, store="local")
        self.assets.get(f"toolbit://{tool.id}")  # Full dependency/shape load.

    def library_raw(self, ident):
        uri = f"toolbitlibrary://{ident}"
        if not self.assets.exists(uri, store="local"):
            return None
        return self.assets.get_raw(uri, store="local")

    def save_library(self, ident, data, expected_raw):
        if self.library_raw(ident) != expected_raw:
            raise RuntimeError("Destination changed since preview; rerun before installing")
        # Rebuild an independent model; do not mutate a cached user library.
        deps = {}
        for row in data["tools"]:
            uri = self.AssetUri(f"toolbit://{row['path'][:-5]}")
            # A library serializes UUID references and numbers only. A shallow
            # ToolBit load preserves those without reopening every shape on
            # every per-tool save; registration already verified new geometry.
            deps[uri] = self.assets.get(uri, depth=0)
        library = self.Library.from_dict(data, ident, deps)
        self.assets.add(library, store="local")
        saved = self.library_raw(ident)
        if read_json(saved) != data:
            raise RuntimeError("Saved library differs from expected library; inspect recovery journal")
        return saved

    def remove_test_asset(self, asset_type, ident):
        self.assets.delete(f"{asset_type}://{ident}", store="local")
