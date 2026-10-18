# FreeCAD 1.1 Imperial Jobber Drills — corrected format

118 HSS drills: 32 fractional (1/64–1/2 in), 60 numbered (#1–#60), 26 lettered (A–Z).

## Import

Use the **existing working** `Import_Drills_FreeCAD_1_1.FCMacro` (a copy is included).
Create an empty FreeCAD CAM tool library and select **All_ToolBits** to import the entire collection. Or select **Fractional**, **Number**, or **Letter** to import those sizes into separate libraries. Do not select the parent directory: the macro searches recursively and would see duplicates from the All_ToolBits folder.

Choose the three-tool TEST run first, inspect the tools in FreeCAD, then run ALL. Importing into an existing library is supported; UUIDs are stable across this replacement archive but differ from any previously imported old-format tools.

## What changed

Each tool now has a deterministic UUID `id` matching its .fctb filename, a FreeCAD 1.1 `shape-type`, and the correct typed parameter fields matching the working metric drills and the user-exported Z drill. Source drill diameters, flute lengths, overall lengths, and names have been preserved from the original imperial archive.

## Caveats

Lengths are generic jobber drill dimensions, not checked against your physical tool inventory. The original library definitions were not run through FreeCAD on Linux in this environment; the corrected files have been structurally validated here.
