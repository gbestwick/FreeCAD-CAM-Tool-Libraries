# FreeCAD CAM Tool Library Manager

A manifest-driven installer for FreeCAD CAM tool collections. Run one macro, select multiple collections, preview the changes, and install without creating libraries manually. Uses FreeCAD's Python environment and Qt bindings; no pip installation or external Python packages are needed.

**Status: development build targeting FreeCAD 1.1.x.** Core tests pass outside FreeCAD. Native three-shape registration/save/reload/cleanup and a 358-tool install/repeat/new-process reload have passed in **FreeCAD 1.1.3 Flatpak on Linux** using an isolated test profile. The user also reported a successful three-shape GUI integration macro run. The installer dialog, GUI restart visibility, Windows, native Linux, and macOS remain unverified. The supplied data has unresolved redistribution permissions; this checkout is not cleared for public data distribution. See [data provenance](docs/DATA_PROVENANCE.md) and [release checklist](docs/RELEASE_CHECKLIST.md).

## Use

1. Clone or download and extract the **complete repository** to a writable, accessible location. Keep `InstallLibraries.FCMacro`, `src/`, and `libraries/` together. Do not copy just the macro into your macro directory.
2. Back up your FreeCAD CAM assets as described below. Open FreeCAD 1.1.x.
3. Choose **Macro → Macros → Execute**, navigating to `InstallLibraries.FCMacro` in this extraction. If your FreeCAD build requires CAM to be loaded, select the CAM workbench first.
4. Select collections individually or use **Select All Available**. Missing collections are disabled. Read the geometry notes in the preview area.
5. Click **Preview Selected Libraries** to check duplicates and proposed tool numbers. **Dry-run** is checked by default and creates no installer assets or backups. FreeCAD's normal CAM startup may separately initialize or migrate assets.
6. To install, uncheck **Dry-run**, then click **Install Selected Libraries**. Watch progress, the scrolling log, and the final summary. The recovery directory contains exact original libraries and the report.
7. Close and reopen CAM's Tool Bit Library manager to refresh. Restart FreeCAD and confirm the tools remain available before relying on this development build.

No network access is needed during installation. The installer finds its bundled data relative to the macro and accommodates an extraction wrapper folder. If location detection fails, run the macro from the complete repository folder. Multiple ambiguous extractions are not guessed.

**Flatpak:** place the extraction somewhere the FreeCAD sandbox can read, such as an accessible Documents folder. Allow access using your normal Flatpak permissions if needed. Backups are placed inside FreeCAD's own user-data directory. The installer uses FreeCAD's configured local asset store rather than guessing host paths. Native API checks pass in this Linux Flatpak installation; interactive GUI operation remains pending verification.

## Included collections

| Collection | Expected | Present | Geometry / status |
|---|---:|---:|---|
| Jobber Fractional Drills - 118deg | 32 | 32 | Generic jobber lengths |
| Jobber Numbered Drills - 118deg | 60 | 60 | Generic jobber lengths |
| Jobber Letter Drills - 118deg | 26 | 26 | Generic jobber lengths |
| Jobber Metric Drills - 118deg | 121 | 121 | Recovered installed data; provisional |
| PCB Micro Drills - **118deg Assumed** - Carbide | 36 | 36 | Provisional; see below |
| DESKAR Metric Flat Endmills - HRC50 - 2 Flute | 34 | 34 | Catalog nominal dimensions; provisional solid |
| DESKAR Metric Flat Endmills - HRC50 - 4 Flute | 34 | 34 | Catalog nominal dimensions; provisional solid |
| Imperial Flat Endmills - 2 Flute | 15 | 0 | Missing; disabled |
| Imperial Flat Endmills - 4 Flute | 15 | 0 | Missing; disabled |
| Harvey Imperial Threadmills - 60deg | 15 | 15 | Provisional |
| **Total** | **388** | **358** | **30 imperial endmill definitions missing** |

DESKAR replaces the unavailable DREANIQUE catalog as the active metric endmill source. Its readable 2023 catalog provides 34 dimension variants in each flute count, replacing the initial estimate of 25; the expected inventory is consequently 388 rather than 370. See the [reviewed source and regeneration instructions](docs/source-catalogs/deskar/README.md). Imperial collections remain disabled pending verified specifications. Earlier DREANIQUE research is retained separately, outside the production inventory.

The planned PCB 135° collection was **not** supplied. Every supplied PCB definition specifies an assumed 118° point. The manifest names the actual supplied data; no angles were changed to meet the proposed collection name.

The original jobber `All_ToolBits` directory duplicates its Fractional, Number, and Letter subfolders. Only the separate sets are curated into `libraries/`. The 169 originally supplied tools and 121 recovered metric tools retain their exact source bytes and UUIDs; [source-inventory.json](docs/source-inventory.json) records their SHA-256 hashes and original paths. The 68 new DESKAR definitions have a reviewed dimension CSV, deterministic generator and per-file provenance records in the same inventory. Original folders are retained for local reference. The metric collection was recovered read-only from the installed FreeCAD library; its source membership snapshot and derived index are in [metric source records](docs/source-catalogs/metric-installed/README.md). [Source catalogs](docs/source-catalogs/) preserve the supplied notes and CSV files, including historical labels that do not always match corrected field names.

## Preservation and duplicates

Existing tool definitions are never overwritten. Existing library numbers are retained; new tools receive numbers after the highest current number. File order is deterministic. A matching library name is reused if unambiguous; managed libraries use deterministic IDs. Renamed managed libraries, ambiguous names, broken dependencies, and nonstandard library metadata are reported and left unchanged.

The UUID is the primary identity. A matching UUID with a changed definition or display name is a conflict. Equivalent definitions with different UUIDs are skipped by default, without merging or relinking. Equivalence compares all properties, normalizes supported length/angle units, and ignores display names. It is conservative: differences in defaults, metadata, or unknown units may need manual review.

One known equivalent pair is **letter E and fractional 1/4-inch**. Selecting all supplied collections with the default policy imports **357 tools** and reports one conflict. Check **Keep different UUIDs as separate tools when definitions are equivalent** to explicitly retain all **358** distinct catalog entries. This policy creates separate assets; it never merges or overwrites definitions. Repeating either policy preserves numbers and adds no duplicate memberships.

Tools already registered globally with the same unchanged UUID can be linked to a missing destination library without rewriting the tool. Invalid individual files are reported while independent valid tools continue. Incomplete collection counts block that collection to avoid silently installing an incomplete download.

## Geometry limitations

Validation checks structure and basic dimensional relationships, not machining suitability or manufacturer accuracy. **None of the supplied collections is verified for collision checking.**

- Imperial jobber overall and flute lengths are generic estimates. The 121 metric drills were recovered from the user's installed library: their names reference DIN338, but the original length source and verification are unknown.
- PCB drills do not model a stepped 3.175 mm shank. The tip angle is assumed. Reference flute lengths come from mixed Kechtek MC and Amony UPX ranges; 3.10 and 3.175 mm entries use placeholder lengths.
- Harvey `NeckLength` uses maximum threading depth as a provisional geometric proxy; these are different specifications. `Crest = 0.10 mm` comes from a FreeCAD sample rather than a verified cutter dimension. The generic shape does not reproduce the exact tooth profile.
- DESKAR endmill dimensions are catalog nominal transcriptions; the generic solid omits helix, relief, tolerances and detailed transitions. HRC50 identifies the catalog workpiece application, not cutter hardness.
- Chipload values in these files are not cutting recommendations. Verify dimensions, holder clearance, feeds, speeds, and the physical cutter separately.

FreeCAD's drill schema lacks `CuttingEdgeHeight`; the supplied field is retained and checked as collection metadata, without claiming that the standard solid models its flute boundary. End mills and thread mills have their own schemas. Thread mills require **`thread-mill.fcstd`**, not `threadmill.fcstd`.

Names describe family, size system/series, and point/cutting angle or flute count. Use `Jobber … Drills - 118deg`, `… Flat Endmills - 2 Flute`, and `… Threadmills - 60deg`; include assumptions explicitly.

## Backups, recovery, and removal

Before your first test, close FreeCAD and copy its **configured CAM asset directory** to a separate safe location. With FreeCAD open, its Python console can display that location:

```python
from Path import Preferences
print(Preferences.getAssetPath())
```

Restart after making the offline copy. Do not edit library assets concurrently with installation.

Before changing a destination, the installer saves its exact original library bytes. Backups and write-ahead journals are placed under:

```text
<FreeCAD user data>/FreeCADCAMLibraries/backups/<unique-run-id>/
```

The final report displays the actual path. Saves occur per tool using FreeCAD APIs. There is **no atomic bulk transaction**: failure may leave saved earlier tools or a registered tool that is not linked to a library. A normal rerun can reuse an unchanged orphan UUID and finish linking it. A failure during a library save stops that collection. Read [recovery instructions](docs/RECOVERY.md) before restoring anything; backups describe the state before the first change of that run.

To remove tools, use FreeCAD's CAM Tool Bit Library manager to remove the unwanted library memberships or an entire collection library. Libraries may contain user-added tools: inspect before deleting them. Removing a library does not necessarily delete shared registered tool assets. Do not delete global tools still used by other libraries or jobs. There is intentionally no blanket destructive uninstall button. Restore from an offline backup if needed.

## Development and contributions

Run with Python 3.10+ and the standard library:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m freecad_cam_libraries.audit
PYTHONPATH=src python3 -m freecad_cam_libraries.audit --release
```

In Windows PowerShell, set `$env:PYTHONPATH = 'src'` and use `python` instead of `python3`. The release audit intentionally fails until missing data and redistribution evidence are resolved. No dependency installation is needed for these tests. A CI workflow is provided for Windows, Linux, and macOS; it has not been run remotely here.

See [architecture](docs/ARCHITECTURE.md), [API research](docs/FREECAD_API.md), and [CONTRIBUTING.md](CONTRIBUTING.md). Existing supported tool shapes can be added through the manifest without importer changes. New shapes require researched validators and adapter integration checks.

Run `IntegrationTest.FCMacro` in FreeCAD 1.1.x for a temporary three-shape API smoke test. It reports registration, save/reload, numbering, and cleanup to Report view. These synthetic tools are test assets only. It does not test GUI restart visibility or the installer dialog; follow [TESTING.md](docs/TESTING.md) for the full manual protocol.

For bug reports, include FreeCAD's complete version/build, operating system and packaging (especially Flatpak), collection IDs, whether dry-run was used, the log, and relevant journal/report errors. Reproduce with a temporary or backed-up CAM profile. Remove private paths or user tool data before sharing. Report reproducible problems in [GitHub Issues](https://github.com/gbestwick/FreeCAD-CAM-Tool-Libraries/issues).

## Screenshots

- [Screenshot placeholder: grouped collection selection, counts, and geometry notes.]
- [Screenshot placeholder: dry-run duplicate report and explicit distinct-UUID option.]
- [Screenshot placeholder: successful installation and tools visible after FreeCAD restart.]

## License and attribution

Original installer code is [MIT licensed](LICENSE). This does not license the supplied manufacturer-derived tool files, CSVs, legacy macros, or source documentation. Attribution alone does not establish redistribution rights. Current source data remains pending provenance/permission review; do not publish this data-bearing checkout as an open-source release until cleared. FreeCAD is a separate project; this installer does not bundle its source or claim endorsement.
