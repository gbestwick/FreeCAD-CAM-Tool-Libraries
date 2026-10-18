# FreeCAD 1.1 PCB micro drills — 3.175 mm shank

36 individual UUID-named `drill.fcstd` v2 files. Sizes: 0.10–0.50 mm by 0.05; 0.60–3.10 mm by 0.10; plus 3.175 mm.

## Import
1. Create an empty library in FreeCAD CAM, e.g. `PCB Micro Drills - 1-8 shank`.
2. Run `Import_Drills_FreeCAD_1_1.FCMacro` inside FreeCAD 1.1.
3. Choose `ToolBits`, select the library, choose test 3; inspect and then rerun for all remaining tools.

## Geometry and caveats
- Compatible fields copied from a user-exported working FreeCAD 1.1 `drill.fcstd` tool: `Diameter`, `CuttingEdgeHeight`, `Length`, `TipAngle`, etc.
- All are **generic representations**, NOT exact equivalents of the mixed-brand cheap drill kits sold online.
- Shank is **3.175 mm nominal in the name and CSV only**; FreeCAD's standard `drill.fcstd` shape does not model a stepped 3.175-mm shank for these tiny cutting diameters. Thus this representation is *unsafe for shank/holder collision checks*.
- Tip angle **118° is an assumption** compatible with some published carbide PCB drill series, not verified for all stock cutters. Adjust after checking what you own.
- Flute lengths through 0.25 mm use Kechtek MC published reference values. 0.30–3.00 mm use Amony UPX published reference bands. Tool lengths use 38.1 mm (small series) and 38.0 mm (UPX) respectively. Not all nominal size steps appear in both manufacturers' actual catalogs. The 3.10 and 3.175 mm entries are **placeholders** with an assumed 12 mm flute and 38 mm overall; confirm these exist and measure your specific cutters.
- Recommended RPM/feed, stickout, actual length, point angle, manufacturer/part numbers and collisions require real tool data, not generic library values.

## Sources
- Amony UPX sizes and flute lengths: https://www.hmntool.com/upx-1-8-inch-shank-micro-drills.html
- Kechtek MC range: https://www.kechtek.com/product/pcb-cutting-tools/pcb-drills/pcb-micro-drill.html
- YAMAMOTO PCB drill point angle 118 degrees as representative only: https://ysk-drills.com/en/pcb/
