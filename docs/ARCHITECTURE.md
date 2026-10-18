# Architecture and implementation plan

The initial inventory found three supplied packages, three legacy macros, four CSV catalogs, three source READMEs, six historical `.fctl` backups, and 287 `.fctb` files representing 169 unique UUIDs. The extra 118 files are exact copies in the jobber All_ToolBits folder. No end mills, metric drills, standalone user exports, or preexisting manifest were supplied. Source-package descriptions reference user exports, but those exports themselves are absent.

The implementation order was source/API inspection, manifest and validators, the adapter and core engine, curated unchanged data, tests, GUI, and documentation. The design keeps FreeCAD and Qt imports out of the core.

| Module | Responsibility |
|---|---|
| `manifest.py` | Schema/version checks, source discovery, path containment, collection metadata |
| `validation.py` | UUID/filename and shape-specific checks, limited quantity parsing, conservative equivalence |
| `library_manager.py` | Stable collection-to-library UUIDs, unambiguous destination resolution, append-only numbering |
| `tool_manager.py` | Identity/equivalence classification; no implicit merging |
| `compatibility.py` | All native FreeCAD API calls, serializer preparation, registration, native library save |
| `installer.py` | Shared preview/install decisions, write-ahead recovery journal, per-tool save, reports |
| `gui.py` | Grouped collection selection, preview/dry-run, explicit duplicate policy, progress/log/results |
| `audit.py` | Independent data validation and stricter public-release readiness checks |

The macro locates the repository and launches the GUI. The source checkout, rather than a pip package, is the distribution unit: the Python package alone does not contain the collections or entry-point macro. `pyproject.toml` supports Python tooling but installing it is unnecessary.

## Engine sequence

1. Snapshot local and builtin tool JSON, with local tools taking precedence. Snapshot local libraries and their exact bytes. An unreadable inventory fails closed before writes.
2. Validate selected complete collections, every source tool, and cross-selection UUID uniqueness.
3. Resolve each target by deterministic managed UUID or exact library label. Refuse renamed managed IDs, ambiguous labels, unsupported library metadata, repeated numbers/memberships, and unresolved references.
4. Classify each tool by UUID, complete definition, and normalized equivalence. Preserve modified same-UUID assets. Default to skipping different-UUID equivalents; only an explicit `distinct` policy registers them separately.
5. For missing memberships, append at max existing number + 1. Dry-run ends with the plan without native deserialization or disk writes.
6. For a real change, prepare a native tool through FCTBSerializer with resolved shape dependencies. Rehydrate an independent shape from native FCStd bytes before deserialization, which can modify its parameter state. Native Base.Quantity objects cannot be deep-copied.
7. Create the external recovery directory, flush a journal, and back up exact original library bytes. Record intended registration before registering unchanged source bytes through the asset API.
8. Recheck tool identity and destination bytes, create an independent native Library model, and save through `cam_assets.add`. Verify resulting library JSON. Record committed membership and continue.
9. Save the report. If a library save fails, stop that collection. Earlier successful saves persist; independent collections may proceed. Disk/journal OS errors stop further installation.

There is no internal asset-file editing, source-geometry rewriting, automatic merge, library rename, or destructive rollback. A registered but unlinked tool is recoverable on rerun. A save that raises after writing may have an uncertain outcome; the write-ahead journal and native read-back must be inspected. See RECOVERY.md.

## Deliberate limits

- Source count mismatches block the whole collection; malformed tools in a count-complete collection are isolated and reported.
- Equivalence is conservative, not a geometric solid comparison. All property names/values and extra metadata must match after supported unit normalization; display names are ignored only for different-UUID equivalence. Default-added properties may produce a conflict.
- Unrecognized library fields are refused rather than dropped by native serialization.
- No global transactional lock exists. Read-before-write checks reduce accidental overwrites but cannot eliminate an external concurrent writer between the check and save. Do not modify CAM assets during installation.
- GUI work stays on the main thread because native asset construction requires it. Progress/log repaint between tools; a single slow native operation can temporarily block interaction. No cancellation is offered mid-save.
- Normal CAM initialization may seed/migrate assets. The installer does not call `setup()` in preview or installation, avoiding hidden initialization changes attributable to the installer.
- Addon Manager packaging, fully automatic uninstallation, manufacturer-data clearance, missing definitions, and remaining GUI/platform verification remain future work. Native adapter and full inventory checks have passed on FreeCAD 1.1.3 Linux Flatpak; see TESTING.md.

## Installed metric data recovery

The initial 169-tool inventory has been extended by recovering 121 referenced definitions from the installed Jobber Metric Drills library. Source files were copied read-only with byte/hash preservation, the manifest's existing metric entry was enabled, and source membership/numbering was captured separately as provenance. This recovery brought the inventory to 290 tools across six collections before endmill generation. No importer code change was needed. Original installed assets were not modified.

## Reviewed manufacturer endmill generation

DESKAR 2023 catalog printed page 115 supplies 34 metric dimension variants in both two- and four-flute options. An offline standard-library generator reads the reviewed source CSV and creates 68 deterministic native definitions; the runtime importer is unchanged. Two formerly empty metric slots are now brand-specific collections. The planning count changes from 370 to 388 expected; 358 tools are available in eight collections, with 30 imperial endmills still missing. Original source bytes remain unchanged; generated tool hashes and source records extend the inventory.
