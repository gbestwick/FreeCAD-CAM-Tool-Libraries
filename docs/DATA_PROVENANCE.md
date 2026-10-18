# Data provenance and public-release status

**Public data distribution is not cleared.** User-supplied files are retained locally, unchanged. The original-code MIT license does not cover `.fctb` data, CSV catalogs, legacy macros, source READMEs, or historical library backups. No permission was inferred from the fact that a catalog is publicly readable.

Inspection date: 2026-10-18. No license or redistribution grant was present in any of the three supplied packages. No standalone FreeCAD-exported tool samples were provided, despite source READMEs referring to such samples. Six `.fctl` backup files were present: five contain empty or three-tool library states; the sixth references one historical tool UUID absent from the supplied definitions. These are historical membership records, not complete tool exports or a manifest to install.

| Dataset | Supplied evidence | Verification status | Release action |
|---|---|---|---|
| 118 imperial jobber drills | README, Drill_Index.csv, deterministic UUID definitions | CSV transcription consistent; flute/overall lengths described as generic estimates; original authorship and data rights unknown | Establish original author/data license and dimension basis |
| 36 PCB micro drills | README, Tool_Index.csv, references to Kechtek MC/Amony UPX/YAMAMOTO | CSV consistent; reference ranges mixed with generic sizes; assumed angle and placeholder lengths explicitly identified | Obtain provenance/permission; do not claim manufacturer-specific physical accuracy |
| 15 Harvey thread mills | README, Harvey_Imperial_Tool_Index.csv with per-part URLs, Thread_Size_Lookup.csv | CSV consistent; NeckLength proxy and sample Crest not manufacturer-verified geometry | Obtain redistribution permission or reviewed independent-data basis before release |
| 121 metric drills | Copied unchanged from installed FreeCAD 1.1.3 library; exact membership snapshot, SHA-256 hashes, derived index | 1.0–13.0 mm by 0.1 mm; 118°, 2 flutes, HSS; names reference DIN338 but original dimensions/source/license unverified | Establish author/data rights and dimension basis; geometry provisional |
| 68 DESKAR metric end mills | 2023 catalog printed p115 / PDF p64 left; reviewed nominal dimension CSV, source PDF hash and generator | 34 geometry variants, explicitly offered in both flute counts; generic native solid remains provisional | Establish data redistribution basis before public release |
| 30 imperial end mills | No verified files/source | Absent | Supply verified definitions and provenance; do not substitute metric sizes |

## Source references checked

- Supplied Harvey part URLs remain in the original CSV. The current [Harvey/ATA terms of use](https://www.atatools.com/terms-of-use), revised September 23, 2026, explicitly cover harveytool.com and describe limited personal/non-commercial downloading. They do **not establish permission for this open-source dataset redistribution**. This is a release-review finding, not a legal conclusion about individual factual dimensions.
- [Kechtek](https://www.kechtek.com/) identifies its PCB tooling products. The supplied [MC micro drill reference](https://www.kechtek.com/product/pcb-cutting-tools/pcb-drills/pcb-micro-drill.html) is an attribution lead; no explicit open-data license was established during this review.
- Supplied [Amony UPX reference](https://www.hmntool.com/upx-1-8-inch-shank-micro-drills.html) and [YAMAMOTO reference](https://ysk-drills.com/en/pcb/) identify data/representative-angle leads, not redistribution grants. This development pass did not independently remeasure cutters or verify each source-page specification.

The presence of source URLs, factual values, attribution, or a generic visualization does not by itself clear the assembled dataset or reproduced catalog material. Before a public release, record the actual license or permission, its scope, grantor, date, and retained notices. Alternatively, replace uncertain data only with independently established, appropriately licensed definitions and record their provenance. Preserve a clear history and do not silently change catalog values.

## Inventory records

`source-inventory.json` lists all curated tool source paths, target paths, hashes, and a complete inventory of the original package artifacts. Its recovered-collection record identifies the metric source library UUID, membership snapshot hash, import date, and limitations. Recovered tool records use native asset-relative source paths instead of depending on private machine paths. Original folders remain untouched. `docs/source-catalogs/` contains reference copies of the supplied catalogs, legacy macros, and notes, also pending rights review. Neither those copies nor the original folders should be bundled into a public release without review.

`python -m freecad_cam_libraries.audit --release` checks completeness and requires `source.redistribution = cleared`, `source.license`, and `source.permission_evidence`. It intentionally fails now. Passing that mechanical check would not replace human review of the evidence or actual native integration testing.

No manufacturer contact was made and no permission request was sent. No repository was published or external data redistributed by this task.

## Recovered installed metric library

At the user's request, 121 definitions were copied read-only from the FreeCAD 1.1.3 Flatpak library labeled `Jobber Metric Drills`, UUID `2400f95a-837b-4b8f-be69-239007f417e4`. Stored tool bytes, UUIDs, names and geometry were preserved. The source library and files were checked for changes during the snapshot. No current FreeCAD tool or library was modified. `docs/source-catalogs/metric-installed/Jobber_Metric_Drills.fctl` preserves membership/numbering as evidence; the new collection follows the installer's numbering policy. The derived CSV is not an independent manufacturer catalog. This recovery brought the inventory to 290 before the subsequent DESKAR additions.

## DREANIQUE end mills under review

At the user's request, research has begun on DREANIQUE manufacturer-specific end mills. The complete manufacturer PDF could not be retrieved for visual inspection; ambiguous indexed text is not used for generation. Two P4E dimensioned drawing examples are recorded with image-source URLs and hashes under `docs/source-catalogs/dreanique/`, along with the access limitations. They are generation checks outside the production inventory. Manufacturer-image/data redistribution clearance remains unresolved; no source photographs or complete catalog have been bundled.

## DESKAR metric endmills

A readable LIFENG / DESKAR 2023 catalog was obtained from the regional brand site. Printed p115 supplies 34 nominal dimension variants in both two- and four-flute versions. All 68 generated definitions are enabled in the manifest. The [source review](source-catalogs/deskar/README.md) records exact source URL/hash, table locator, transcription scope, reproducible generation, geometry limitations and unresolved data rights. No complete PDF or page images are bundled. Original 290 source definitions remain byte-for-byte unchanged. Current totals: 358 available, 388 expected, 30 imperial endmills missing.
