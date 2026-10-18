# FreeCAD 1.1 API research

Inspected upstream release tag **1.1.0**, commit **34a9716668b1ddeb55b914f1c5be644826bdbbbf**, on 2026-10-18. The checkout was placed outside this project for reference. Initial research used source inspection. A subsequent check located FreeCAD 1.1.3 through Flatpak; native tests now pass in an isolated profile (see TESTING.md). Supporting the 1.1.x family is a target guarded by runtime version and capability checks; individual patch builds remain unverified.

The supplied legacy macros match the essential asset registration pattern, but require users to create/select libraries manually and do not compare existing definitions or handle all failure cases. They are references, not compatibility proof.

## Verified source entry points

All links below are pinned to the inspected release tag:

- [Path.Tool package registration and exports](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/__init__.py): public `Library`, `ToolBit`, and `cam_assets`; FCTL/FCTB serializers registered on import. `Path.Tool.ToolBit` is a class exported by this package, not the historical uppercase module layout.
- [CamAssetManager](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/camassets.py): local/builtin stores, local-first `get`, configured paths via Path.Preferences, `setup()` calls initialization and migration helpers. `cam_assets` is also exported from `Path.Tool`.
- [AssetManager](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/assets/manager.py): `list_assets(asset_type, store=...)`, `get_raw(uri, store=...)`, `get(uri, store=..., depth=None)`, `exists`, `add_raw`, `add_file`, `add`, `delete`. `add_file` delegates to `add_raw` and uses filename stem unless an ID is supplied. Both add methods can overwrite an existing asset; callers must guard UUIDs. Writes invalidate related cache entries. Full `get` resolves dependencies and can perform main-thread Qt work.
- [Library model](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/library/models/library.py): `Library(label, id=None)`, `from_dict(data, id, dependencies)`, `add_bit(bit, bit_no=None)`, `get_bits`, `get_bit_no_from_bit`, `get_next_bit_no`, `remove_bit`, `to_dict`. Native automatic numbering appends after the highest current number. Explicitly colliding numbers can renumber other bits: the installer prevents those collisions first.
- [FCTLSerializer](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/library/serializers/fctl.py): library payload uses version 1, label, and tool entries `{nr, path}`; IDs come from the asset URI/filename. Saving a Library serializes this native representation.
- [FCTBSerializer](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/toolbit/serializers/fctb.py): `extract_dependencies(data)` returns shape URIs; `deserialize(data, id, dependencies)` supplies a canonical ID and builds from the resolved shape. `deep_deserialize` preserves the source `id` when present. The installer requires an explicit canonical UUID and matching filename instead of relying on fallback ID creation.
- [ToolBit model](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/toolbit/models/base.py): `from_dict`, `from_shape`, and `to_dict`; parameters and attributes both apply to the shape/object, with a documented ambiguity in their separation. Material supports HSS/Carbide. Native serialization can add defaults; the installer registers exact source bytes through the supported raw API instead of changing supplied definitions.

## Shapes and validation policy

| Shape reference | FreeCAD schema fields |
|---|---|
| `drill.fcstd` / Drill | Diameter, Flutes, Length, TipAngle |
| `endmill.fcstd` / Endmill | CuttingEdgeHeight, Diameter, Flutes, Length, ShankDiameter |
| `thread-mill.fcstd` / ThreadMill | Crest, Diameter, Flutes, Length, NeckDiameter, NeckLength, ShankDiameter, **cuttingAngle** |

Source: [drill schema](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/shape/models/drill.py), [endmill schema](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/shape/models/endmill.py), [threadmill schema](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Path/Tool/shape/models/threadmill.py).

Lengths are App::PropertyLength, angles App::PropertyAngle, and Flutes App::PropertyInteger. The case of `cuttingAngle` is significant. The thread shape class accepts multiple aliases, but the actual bundled shape file and supplied definitions use **thread-mill.fcstd**; the installer requires that filename.

Upstream [drill](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Tools/Bit/5mm_Drill.fctb), [endmill](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Tools/Bit/5mm_Endmill.fctb), and [thread cutter](https://github.com/FreeCAD/FreeCAD/blob/1.1.0/src/Mod/CAM/Tools/Bit/5mm-thread-cutter.fctb) examples omit some fields and UUIDs that the project requires for curated collections. FreeCAD permits defaults; project quality requirements are deliberately stricter and must not be presented as FreeCAD format requirements.

Specifically, this project requires UUID/filename consistency, explicit Flutes, and Material for drills/end mills; it also requires supplied drill CuttingEdgeHeight as catalog metadata. Thread mills require explicit cuttingAngle and crest geometry. It does not require unrelated endmill fields on drills. Zero Crest and Chipload are accepted; positive sizes, angles below 180°, and elementary length/neck relationships are checked. Supported units are mm, cm, m, um/µm, in, and deg/°; bare lengths use FreeCAD mm base units. Unsupported expressions/units require review rather than guessed conversion.

## Safety and persistence

The inspected CAM asset APIs do not expose a bulk transaction that combines independent tool registrations and library saves. FreeCAD document transactions are not a transaction over these file-backed CAM stores. The implementation makes no atomic-install claim.

The adapter uses native `Library.from_dict` plus `cam_assets.add` for library saves and native FCTBSerializer deserialization before registering exact tool bytes with `add_raw`. It does not edit underlying store paths or databases. Saving writes persistent assets, and a new FreeCADCmd process now verifies persistence on 1.1.3 Linux Flatpak. GUI restart visibility is still pending.

Changes since 1.1.0 or vendor-specific builds must be verified inside FreeCAD using IntegrationTest.FCMacro and the full manual protocol. Mock tests establish project logic, not native compatibility.

## Native regression: Base.Quantity copying

The first user-run smoke test failed in Python `copy.deepcopy` because a shape contains unpickleable `Base.Quantity` objects. The adapter now retrieves native shape bytes through `get_raw` with local/builtin fallback and reconstructs an independent `ToolBitShape.from_bytes(data, id, dependencies=None, serializer=DummyAssetSerializer)`. This public shape importer avoids Python pickling and cached-shape mutation. Icons are unnecessary for this preparation step; normal registered-tool loading still resolves native dependencies.

Library saves load dependency ToolBits with `get(uri, depth=0)`: library serialization needs only UUID references and tool numbers. Newly registered tools have already undergone a full load. This avoids repeatedly reopening every existing shape on each save; the separate new-process reload check resolves all dependencies fully.
