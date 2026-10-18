# Contributing collections

Use Python 3.10+ for development. The installer itself runs in FreeCAD 1.1.x with its bundled Python and Qt. No external runtime dependencies are allowed.

## Add data without changing importer code

1. Obtain the original source definitions or verified measurements and permission to redistribute the dataset. Do not infer missing dimensions to satisfy validation. Record source URLs, author, catalog revision/date, units, field-level verification, and the applicable license or written permission.
2. Add `libraries/<category>/<collection>/`. Supported categories are drills, endmills, and threadmills. Put exactly one canonical UUID-named `.fctb` file per tool in the directory. Keep IDs stable after publication; retain an upstream supplied UUID where appropriate. Do not include duplicate aggregate folders or asset backups.
3. Add a row to `libraries/manifest.json`, retaining `schema_version: 1`. Existing supported shapes require no Python changes. Choose a stable lower-case hyphenated ID. IDs determine managed library UUIDs; changing an ID creates a different library. Choose a unique human-readable name with the real point angle/flute count; renaming an existing managed destination is intentionally not automatic.
4. Supply every metadata field shown below. Set `status: missing` until the count is complete; set `available` only when files actually exist and pass validation. Mark geometry as `verified`, `generic`, or `provisional` with specific limitations. `unavailable` is used for absent source data. A collection's measurement units describe its catalog, not necessarily the units used to serialize each FreeCAD quantity.
5. Run core tests and the audit. Test in FreeCAD using a disposable/backed-up profile, then check appearance, dimensions, existing library numbering, repeated execution, and restart persistence. Attach the actual version and results. Mock tests do not replace this step.
6. Add sources, permission evidence, and any catalog under the collection or `docs/source-catalogs/`. Update the inventory, README, counts/tests, and provenance ledger. Include geometry caveats in the manifest so users see them in the GUI. Do not label data as cleared based on attribution alone.

Example manifest entry (illustrative; it does not supply this missing collection):

```json
{
  "id": "endmills-metric-2f",
  "name": "Metric Flat Endmills - 2 Flute",
  "category": "endmills",
  "directory": "endmills/metric-2f",
  "expected_count": 25,
  "source": {
    "attribution": "Original author and manufacturer/catalog revision",
    "redistribution": "unverified",
    "urls": ["https://example.com/source"]
  },
  "units": "metric",
  "geometry": {
    "description": "Flat end mills, 2 flutes",
    "accuracy": "unavailable",
    "notes": "Definitions have not yet been supplied."
  },
  "compatible_versions": ["1.1.x"],
  "status": "missing"
}
```

Once permissions are established, `source.redistribution` may become `cleared` **with** `source.license` and `source.permission_evidence` identifying the actual license/permission record. The release audit requires all three, but strings alone are not proof: maintainers must review the underlying evidence. Do not apply the code's MIT license to third-party data without permission.

Paths use relative forward slashes and must stay inside `libraries/`. Absolute paths, Windows drive paths, backslashes, `..`, symlink escapes, and repeated collection directories are refused. Source code never needs machine-specific asset paths.

## Shape requirements

See [API research](docs/FREECAD_API.md) for native schemas versus stricter project requirements. `.fctb` version 2, canonical UUID, matching filename, explicit name, parameter object, and matching shape/shape-type are required. Property values may be in `parameter` or `attribute`, but contradictory values are rejected. Existing drill files retain CuttingEdgeHeight as metadata; do not invent that value when a source lacks it—establish the measurement or leave the proposed collection unavailable.

Use `drill.fcstd`, `endmill.fcstd`, or **`thread-mill.fcstd`**. Keep the thread mill's **`cuttingAngle`** capitalization. Existing source material values HSS/Carbide and positive integer Flutes are checked. Unknown materials, units, expressions, and new shapes require research and focused validator changes, rather than automatic conversion or defaults.

Synthetic tools in tests and IntegrationTest.FCMacro must never be promoted into production catalogs. Provisional geometry can be included only with explicit field-level notes and a clear statement that it is unsuitable for collision checking.

## Code changes

Keep FreeCAD imports in the compatibility boundary and GUI/entry points. Use injected adapter mocks for core logic tests and meaningful failure/recovery cases. Add native integration coverage when changing API calls. Preserve exact source geometry and existing user numbers. Do not implement automatic destructive uninstall, UUID replacement, silent equivalence merging, or storage-file editing.
