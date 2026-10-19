# Validation and integration testing

## Executed in this development environment

- Python standard-library unittest suite: **73 tests passed**.
- All 358 curated definitions parse, have unique canonical UUIDs matching filenames, and pass their shape-specific validators.
- Curated source bytes match the original files and recorded SHA-256 hashes.
- All jobber, PCB, and Harvey CSV dimension transcriptions match the supplied `.fctb` values. This is internal consistency, not independent manufacturer/physical verification.
- The 118 jobber aggregate copies are byte-identical to the separate folders.
- Mock full-inventory install/repeat: default policy imports 357 and reports one equivalent-definition pair; repeat skips 357 and retains that conflict. Explicit distinct-UUID policy imports 358; repeat skips all 358.
- Core tests cover missing/malformed files, non-finite/duplicate-key JSON, schemas and required fields, path escapes, UUID conflicts, custom numbering, source duplicates, renamed/ambiguous libraries, broken references, backup failure, failed registration, failed save/retry, concurrent-change detection, and native adapter call contracts.

Commands are in the README. The initial check missed the Flatpak installation. After the user reported a Base.Quantity deepcopy failure, native checks were run against the installed FreeCAD 1.1.3. CI configuration remains unrun remotely. Unit tests alone do not establish native compatibility.

## Native API smoke test — executed in FreeCADCmd; GUI rerun pending

1. Back up CAM assets and use a disposable FreeCAD profile where possible.
2. Open FreeCAD **1.1.x** and CAM. Run `IntegrationTest.FCMacro` from the complete repository root.
3. Inspect Report view. The macro creates a fresh temporary library and three fresh synthetic UUID tools (drill, endmill, thread mill), prepares/resolves their native shapes, registers them, saves the library through the native model, and reads it back to verify membership and numbers 1–3.
4. It deletes its temporary library first, then its tool assets in `finally`. If library cleanup fails, tools are retained to avoid leaving broken dependencies. Any cleanup failure prints exact IDs. A PASS line for API assertions does not negate a later cleanup error; both must succeed.
5. Record version/build, operating system, package type, output, and any residual temporary assets. Synthetic test dimensions are not production specifications.

This test exercises native adapter calls, not the full GUI/engine or application restart. It deliberately avoids deleting preexisting UUIDs or modifying source collections.

## Native automated results — 2026-10-18

FreeCAD **1.1.3**, revision **44987**, commit **145529fe741292ff0b3977a01195bf0247425794**, Linux Flatpak, bundled Python 3.13. Tests used FreeCADCmd in disposable profiles, not a mock runtime or the user's CAM store.

- Three-shape API smoke test: PASS, including cleanup and no residual local test libraries/tools. The user also reported a successful interactive three-shape macro run after the fix.
- Full supplied inventory: PASS, 358 tools added to eight new libraries with the explicit distinct-UUID policy.
- Dry-run: PASS, no local tool assets or installer backups written.
- Repeated install: PASS, all 358 memberships skipped with library bytes unchanged.
- Second FreeCADCmd process: PASS, all eight libraries and 358 native ToolBits fully reloaded; numbers and unchanged source definitions verified.

The original 169-tool native checks were repeated successfully after adding 121 recovered metric drills, bringing the tested inventory to 290. After adding 68 reviewed DESKAR endmills, the full test passed again with 358 tools in eight libraries. The latest native results are retained locally under `.test-runs/native-02582466-f0a4-4f88-8964-168268df5a59/`.

The first smoke failure was an implementation bug: Python deepcopy cannot copy Base.Quantity. Shape preparation now rehydrates native FCStd bytes through ToolBitShape.from_bytes. The integration macro reloads project modules before testing so a failed earlier import cannot keep the previous adapter cached.

Reproduce on a host with this Flatpak installed:

```bash
python3 tests/run_native_flatpak.py
```

The launcher creates a fresh `.test-runs/native-<UUID>` directory and sets FreeCAD's `FREECAD_USER_HOME`, `FREECAD_USER_DATA`, and `FREECAD_USER_TEMP`, plus explicit config-file paths. Flatpak overrides XDG variables, so those alone do not isolate the application. The native harness checks config/data isolation before importing CAM and checks the actual asset path before any test writes. Each stage produces a log and a JSON success marker only after assertions finish; FreeCADCmd may return exit code zero for a failed script, so exit code alone is insufficient. Profiles and logs remain under the ignored `.test-runs/` folder for inspection.

These results do not establish interactive GUI behavior, graphical application restart visibility, other FreeCAD builds, Windows, native Linux, or macOS compatibility.

## Full GUI acceptance protocol — pending

Run on Windows, Linux native, Linux Flatpak, and macOS with FreeCAD 1.1.x. Record the complete build, Python and Qt versions.

1. Open the installer from an extraction path containing spaces; confirm source discovery without manually locating tools. Also test a wrapper-folder extraction. For Flatpak verify filesystem access and the reported native user-data location.
2. Verify the eight available collections are selectable with correct counts and geometry notes. The two metric DESKAR endmill collections each contain 34 tools; imperial endmills are disabled. PCB displays assumed 118°, never 135°.
3. Preview several collections and then run with dry-run still checked. Compare the configured asset directory before/after; installer actions should not modify it. Account separately for normal CAM startup initialization. No installer backup directory should be created by dry-run.
4. Install a few selected collections into a clean test profile. Verify new library names, IDs, all parameters/material/flutes, registered UUIDs, memberships, and tool numbers.
5. Use the explicit distinct-UUID option for a full 358-tool test, or expect 357 plus the letter-E/fractional-1/4 equivalent conflict under the default policy.
6. Add a custom tool to a destination, change its number to 42 or another large number, and customize a supplied registered tool's geometry/name. Rerun. Verify the custom number and edits persist, the modified UUID is reported as a conflict, and newly missing tools append after the maximum number.
7. Repeat the successful install unchanged. No assets should be duplicated; tool numbers and library bytes should remain stable when no changes are needed.
8. Close FreeCAD completely, restart, and verify saved tools/libraries in CAM. This is required before claiming persistence compatibility.
9. Inspect per-run exact backups and journal. Exercise a controlled registration failure or read-only destination only in a disposable profile; verify partial-result reporting and safe rerun behavior.
10. Remove test memberships/libraries through the UI and confirm unrelated tools/libraries remain intact. Restore the offline backup if needed.

The first release is not accepted until this protocol, data provenance clearance, and missing inventory decisions are resolved. Add dated actual results below; do not replace pending items with mock-test outcomes.

## Clean interactive test without deleting existing tools

For the installed Linux Flatpak, open a brand-new test profile and the installer with:

```bash
python3 tests/launch_clean_flatpak.py
```

This creates a fresh `.test-runs/gui-<UUID>` directory on each launch and selects separate config, data, and temporary directories using the FreeCAD-specific environment variables. A wrapper macro checks actual config/data/CAM paths before opening the installer. Current libraries, custom tools, and normal application preferences are retained. The profile persists after the window closes, so its logs and assets can be inspected. No existing tool assets need to be deleted to test first-time library creation.

For this test, preview first, uncheck Dry-run and install, then rerun the installer in the same test window to check idempotency. Use the explicit distinct-UUID option if all 358 available entries are desired. Do not launch the helper a second time to check a rerun: each new helper launch intentionally creates a different empty profile.

## DREANIQUE generator checks

Eight new source-generator safeguards cover exact reviewed dimensions and native schema, deterministic regeneration, unreviewed/incomplete rows, family/flute consistency, no partial replacement of customized outputs, check-mode non-mutation, and stable identity when dimensions change. Two visually checked P4E examples passed real FreeCAD 1.1.3 registration, native-property reload, and repeat-install checks in a separate disposable profile. They are not bundled production definitions and do not contribute to the production inventory. See the DREANIQUE source review for evidence and the catalog access blocker.

## DESKAR catalog generation checks

Seven tests check all 34 reviewed table rows and both flute options against deterministic production outputs, required native properties, same-diameter variants with different shanks/lengths, invalid/unreviewed input rejection, byte-identical regeneration, preflight preservation of customized output, non-mutating check mode, and collection symlink rejection. Actual FreeCAD 1.1.3 full-inventory tests additionally registered and reloaded all 68 new endmills as part of the 358-tool run above. Nominal dimensions were visually reviewed against catalog printed p115; these tests do not establish physical cutter accuracy or collision suitability.

## Local Pixi development build — 2026-10-19

The local `/home/gord/FreeCAD-Local` checkout (HEAD `8fcd99b158`) reports
`FreeCAD.Version() = ['27', '1', '0', 'Dev Build', 'Dev Build', 'Dev Build']`.
Using its existing `build/relWithDebInfo/bin/FreeCADCmd` through `pixi run --frozen`,
the three-shape smoke test/cleanup, dry-run, 358-tool installation into eight
libraries, repeat-install (all 358 skipped, library bytes unchanged), and
new-process reload all passed. Preferences and CAM assets were isolated under
`.test-runs/pixi-native-acff7f86-3474-4f73-9da8-9e6550cfe429/`; the user's normal
profile and the FreeCAD checkout were not modified by the test harness.

Reproduce against an existing development build:

```bash
python3 tests/run_native_pixi.py /home/gord/FreeCAD-Local
```

The version allowlist explicitly supports `1.1.x` and `27.1.x`. Collection
compatibility is checked against the running family; future unrelated versions
remain rejected. This verifies the tested local development build, not all future
27.1 snapshots. Interactive GUI behavior on this build still needs user testing.
