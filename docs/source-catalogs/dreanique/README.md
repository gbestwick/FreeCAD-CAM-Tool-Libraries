# DREANIQUE end mill source review

Status on 2026-10-18: source research and offline generation pipeline prepared;
full production collections remain disabled. No dimensions were inferred or
substituted to meet the original 25/25/15/15 proposed inventory.

## Sources and access limitations

The manufacturer-hosted 2024 catalog is indexed at:

https://www.dreanique.com/Content/upload/pdf/2022689233/DREANIQUE-CATALOG2024.pdf

The available web fetcher returned a missing/unavailable resource; direct
requests encountered a Cloudflare challenge. No readable PDF was retrieved,
so its tables could not be visually inspected. The current manufacturer
store at https://dreanique.com/collections lists a small selection of
woodworking tools, not a complete accessible catalog for the planned
metric two- and four-flute metal-cutting sets.

Indexed catalog text is an attribution/research lead, not approved generation
input. In particular:

- T2E extraction has inconsistent headers and repeated numerical columns.
  It is unclear whether the source page itself or its extraction is wrong.
- AU2E indexed rows include part-number/diameter disagreements: the D1.5 row
  is rendered with diameter 2, and the D2.5 row with diameter 3. These have
  not been silently corrected or used to generate tools.
- No complete documented imperial two-/four-flute series has been verified.
  Inch-sized shanks alone do not establish imperial cutting diameters.

A readable copy of the catalog, or original manufacturer dimensional drawings
for the intended series, is required to finish the production collections.
This review does not establish current stock, authenticity of marketplace
purchases, physical cutter measurements, or redistribution permissions.

## Two confirmed drawing examples

The original P4E listing is identified as AliExpress item `32920849210`.
Its manufacturer-series dimensioned product images are mirrored on a reseller
page at https://sendboxsac.com/producto/p4e-fresado-cnc-ranura-y-caras/ .
The drawings themselves, rather than the reseller's general description,
were read visually. Their explicit dimensions agree with the same two
indexed manufacturer-catalog rows.

| Part | Cutting diameter mm | Cutting length mm | Shank diameter mm | Overall length mm | Flutes |
|---|---:|---:|---:|---:|---:|
| P4E-D1.0-H4 | 1.0 | 3 | 4 | 50 | 4 |
| P4E-D2.0-H4 | 2.0 | 6 | 4 | 50 | 4 |

Direct drawing sources:

- https://sendboxsac.com/wp-content/uploads/2026/01/Tungsten-carbide-end-mill-4-flutes-3.jpg
- https://sendboxsac.com/wp-content/uploads/2026/01/Tungsten-carbide-end-mill-4-flutes-2.jpg

`endmills-reviewed.csv` records only these two reviewed examples, their source
URLs, and SHA-256 hashes of the retrieved images. The source photographs are
retained locally under the ignored `.test-runs/dreanique-research/` directory,
not bundled for redistribution. The factual transcription CSV remains
pending data provenance/permission review under the same policy as other
manufacturer-derived project data; the original-code MIT license does not
license the source images.

These examples are not included in `libraries/` or the manifest. They are
source/generation checks, not a claim of a complete collection. Their FreeCAD
solids use the generic endmill shape and do not reproduce the real transition,
helix, relief, or exact tooth geometry; physical collision suitability is not
established. No feed, speed, chipload, coating, or other unverified property
was added to their definitions.

## Offline generator

Run with a reviewed source table and an explicitly chosen output directory:

```bash
python3 tools/generate_dreanique_endmills.py docs/source-catalogs/dreanique/endmills-reviewed.csv .test-runs/dreanique-preview
python3 tools/generate_dreanique_endmills.py docs/source-catalogs/dreanique/endmills-reviewed.csv .test-runs/dreanique-preview --check
```

The generator uses only the Python standard library. It requires every size,
material, flute count, visual-review status, source URL, source locator, and
source hash explicitly. It accepts only the currently reviewed flat P4E
family and its four-flute identity; other families require source review
before extending the generator's family map. No data or API change is needed
in the installer to add another completed supported-shape collection.

UUIDs are deterministic from manufacturer and part number, independent of
mutable geometry. The generator preflights the entire output, refuses to
replace changed definitions or mix in unrelated tool files, and supports
read-only deterministic checks. It never writes FreeCAD's asset store or
changes manifest availability. Generated source definitions should undergo
normal validation, provenance review, and native tests before being moved
into an enabled collection.

## Validation performed

The reviewed examples were generated outside the production library tree and
validated against the project's endmill schema. In an isolated FreeCAD 1.1.3
Flatpak profile, both registered successfully, entered a temporary collection,
saved and reloaded with the source dimensions intact, and were skipped on
repeat installation. The user's normal CAM storage was not used. The full
standard-library suite, including eight generator safeguard tests, passes
65 tests. These results test serialization and installation behavior; they
do not verify the remainder of the manufacturer's catalog.
