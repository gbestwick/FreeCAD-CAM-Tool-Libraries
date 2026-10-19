# Numbered jobber drill extension: #61–#80

Added 2026-10-19 to complete the existing numbered collection from **#80 through #1**, 80 tools total. The original #1–#60 definitions are unchanged, including their UUIDs and generic length estimates. This extension does not claim that the entire combined collection is Precision Twist Drill tooling.

## Reviewed source

Precision Twist Drill / Dormer Pramet, **General Purpose Jobber Length Drills, R10 Fractional / R18 Wire Gauge**, one-page dimension sheet, left-hand table. A manufacturer-branded document is hosted on the distributor content service [Syndigo](https://content.syndigo.com/asset/4adecacb-7597-4e5c-b752-4a3a510fa3ff/original.pdf); it is not an original manufacturer-domain URL. Downloaded, rendered and visually reviewed on 2026-10-19.

PDF SHA-256: `3ed61c4a21a56f2e6f88b5961c6aa3b509f6d3ee11fa3b25378be6317c6ddbb2`.

`reviewed.csv` records each R18 part number, wire number, diameter, flute length and overall length in inches, plus source URL/hash/locator. The sheet explicitly specifies HSS, 118° conventional point, steam oxide finish. The 20 rows run from **#80 (0.0135 in / 0.3429 mm)** to **#61 (0.0390 in / 0.9906 mm)**. All three dimensions were read from the table, not inferred from neighboring sizes. Mixed fractions are written as `1 5/8`, avoiding the catalog's potentially ambiguous `1.5/8` typography. Exact conversion uses 25.4 mm per inch.

These are nominal transcriptions, not measured physical cutters. Generic FreeCAD drill geometry does not reproduce the full flute, web or cutting-edge details. The combined collection remains unsuitable for collision checking. Tool names identify the PTD R18 source only for the new 20 definitions. No speeds, feeds or chiploads were invented.

## Reproduce

```bash
python3 tools/generate_numbered_extension.py docs/source-catalogs/numbered-extension/reviewed.csv libraries/drills/numbered-118 --check
```

Omit `--check` to create missing outputs. The generator requires the complete reviewed #61–#80 set and preflights all generated files before writing. Existing #1–#60 files coexist unchanged; customized output files are never overwritten. UUIDs are deterministic per PTD R18 part number. The installer preserves existing registered definitions and reports any UUID conflicts.

The complete PDF and rendered page image stay in ignored `.test-runs/numbered-research/`; they are not bundled. Redistribution rights for the generated data remain unverified and are not granted by the original-code MIT license.

## Range names and existing installations

The numbered collection keeps its stable ID `jobber-numbered-118`. Its new name explicitly gives **#80–#1 (0.0135–0.2280 in)**. The former name is recorded in the manifest's `legacy_names`, as are previous names of the other available collections. The installer recognizes these exact historical labels and preserves them in existing libraries, appending missing tools after the highest existing tool number. New libraries use the range-bearing name.

It does not rename user libraries. Custom names outside the documented historical labels still cause a preservation conflict for a managed UUID. Multiple destinations matching a current or historical name are ambiguous and left unchanged. Renaming an existing library is optional and should be done by its owner in FreeCAD; the installer can also recognize the current range-bearing name on later runs.
