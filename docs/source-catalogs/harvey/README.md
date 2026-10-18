# Corrected FreeCAD 1.1.3 Harvey imperial internal thread mill library

**Correction:** Files match the actual exported `MySampleThreadMill.fctb` structure: `shape: thread-mill.fcstd`, `shape-type: ThreadMill`, with the FreeCAD fields `Crest`, `NeckDiameter`, `NeckLength`, and `cuttingAngle`. The old archive used an incorrect shape filename and incompatible parameters. The included importer accepts the corrected thread-mill shape.

**Caution about modeled geometry:** `NeckDiameter` comes from the Harvey catalog data. `NeckLength` has been set to the manufacturer's **maximum threading depth as a provisional geometric proxy**, because an actual neck-length dimension was not established in the dataset. **They are not equivalent specifications.** `Crest = 0.10 mm` is taken from the supplied FreeCAD sample, not a verified Harvey specification, and may require editing per cutter. In addition, this FreeCAD shape is generic and does not represent the exact cutter's tooth profile or coating. For verified machining dimensions and the original manufacturer links, see `Harvey_Imperial_Tool_Index.csv`. Do not use these provisional solids for collision-sensitive toolpaths.

## Install

1. **Use only the files in this corrected ZIP.** Extract the archive. Do not mix them with the old definitions.
2. In FreeCAD's CAM Tool Bit Library, make/select a separate empty library.
3. Run **`Import_Threadmills_FreeCAD_1_1.FCMacro`** from this archive (not the old `Import_Drills_FreeCAD_1_1.FCMacro`).
4. Select the `ToolBits` folder, choose the new library, and run the three-tool test first. Inspect the geometry and verify all three appear in the library before importing the remainder.
5. If any earlier attempted import left registered but unlinked tool assets, their UUIDs may be present in local storage; use a new library and report any such error before proceeding. The new files keep the existing UUIDs.

There are 15 tools. `Thread_Size_Lookup.csv` and `Harvey_Imperial_Tool_Index.csv` are provided unchanged from the original collection. Confirm catalog compatibility, thread class and pilot hole before machining.
