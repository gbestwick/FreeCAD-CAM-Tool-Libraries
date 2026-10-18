# DESKAR metric flat endmills — reviewed source

The active metric endmill collections use the LIFENG / DESKAR **2023 English catalog**, printed **page 115**, the **left half of PDF page 64**. The regional DESKAR brand site provides a readable [catalog PDF](https://deskar.su/upload/iblock/63f/oj1o4nyuedcg1ecg21djfjzc6ry65l0b/deskar_katalog_en.pdf). Downloaded and visually inspected on 2026-10-18. Its cover identifies LIFENG / DESKAR and the manufacturer's websites; the regional host is a mirror, not the original manufacturer domain.

Downloaded PDF SHA-256:

```text
8f21d828433ce2549eafc18f648025108b0a804ba8ddfa992352ceae183d8d48
```

The heading explicitly identifies **two- and four-flute carbide flat endmills**. The 34 table rows specify cutting diameter **D1**, shank diameter **D2**, flute length **L1**, and full length **L**. Both flute options apply to this table, giving **34 tools per collection, 68 total**. Diameters span 1–20 mm; overall lengths span 50–200 mm. Multiple rows share cutting diameter but differ in shank, flute length or overall length. These variants are retained separately.

`endmills-reviewed.csv` contains the visually transcribed nominal dimensions, source hash, URL and per-row locator. The catalog MODEL column is a dimension string in **D1*D2*L1*L** order, not a unique manufacturer ordering SKU. The generator checks that string against the four independently recorded columns. This consistency check does not replace visual review. The source table's display-column order differs: D1, L1, L, D2.

The catalog's **HRC50** wording describes its workpiece application range, not cutter hardness or a verified material capability. It distinguishes this page from the different HRC60 family on printed page 116. No values from page 116, ball-nose pages, or other families were mixed into these collections. No helix angle, feeds, speeds, chipload or seller SKU was inferred. The source mentions a coating; it is not encoded as an additional unverified native property.

## Reproduce

From the project root, with standard-library Python:

```bash
python3 tools/generate_deskar_endmills.py docs/source-catalogs/deskar/endmills-reviewed.csv libraries/endmills --check
```

Omit `--check` only to create missing deterministic files. The generator preflights both collections and refuses customized definitions, stale tool files, and symlink collection/tool outputs. It never accesses the installed FreeCAD store. UUIDs identify the reviewed catalog family, model reference and flute option. Changes to source identity require explicit review; no existing installed asset is overwritten by the installer.

The earlier proposed 25 metric tools per flute count was a planning estimate. These real 34-row collections replace those two empty manifest slots, increasing the expected total from 370 to **388**, with **358 available**. The **30 imperial endmills remain missing and disabled**: metric sizes are not renamed as fractional cutters. A readable, verified imperial source is still needed.

## Accuracy and rights

These are transcribed catalog nominal dimensions, not measured cutters or detailed manufacturer solids. FreeCAD's generic `endmill.fcstd` omits helix, relief, tolerances and detailed transitions. Geometry remains marked provisional and is not established as suitable for collision checking. Match all four dimensions and flute count to the purchased cutter, rather than relying only on a marketplace brand label.

Redistribution rights for the assembled data remain **unverified**. The complete catalog and page images are retained only in the ignored local research directory, not bundled with the dataset. Attribution and a readable catalog do not establish an open-data license. The repository's original-code MIT license does not license this data.

DREANIQUE research is retained separately for traceability; its two reviewed examples remain excluded from the production inventory. No DREANIQUE geometry was relabeled as DESKAR.
