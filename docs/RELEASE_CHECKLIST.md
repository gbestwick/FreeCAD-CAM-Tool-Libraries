# First-release acceptance status

Completed locally:

- Manifest-driven core installer, compatibility boundary, and Qt macro entry point.
- Automatic native library creation/save path and UUID tool registration path implemented against inspected 1.1.0 APIs.
- Preservation, duplicate policies, deterministic numbering, dry-run, logs/results, exact library backups, and recovery journal.
- 290 unchanged source definitions curated (169 from supplied folders, 121 recovered from the installed metric library); 68 reviewed DESKAR metric endmills added; all 388 expected slots represented with missing collections disabled.
- Standard-library tests and inventory audit pass. GUI source compiles; its runtime behavior is unverified.
- Usage, contributions, API evidence, provenance, backup/removal/recovery, and testing documentation.

Remaining before claiming a first release:

- [x] Run native three-shape IntegrationTest.FCMacro logic in FreeCADCmd 1.1.3 Flatpak; verify outputs and cleanup.
- [x] Run 358-tool native install/repeat and full reload in a new FreeCADCmd process against an isolated profile.
- [ ] Rerun the updated integration macro interactively and verify the GUI workflows.
- [ ] Run full GUI installation, custom-tool preservation, repeat-install, and restart-persistence acceptance tests.
- [ ] Verify Windows, Linux native, Linux Flatpak, and macOS; record versions/builds.
- [x] Recover all 121 metric drill definitions unchanged from the installed library, with hashes and source snapshot.
- [x] Generate 68 metric endmills from reviewed DESKAR catalog rows; revise metric planning counts from 25 to 34 per flute count.
- [ ] Supply 30 verified imperial endmill definitions, or explicitly revise the release scope.
- [ ] Resolve PCB 135° requested inventory separately from the supplied assumed-118° set; never relabel dimensions silently.
- [ ] Resolve data/copy/legacy-artifact redistribution permissions with evidence; the entire data-bearing checkout is currently uncleared.
- [ ] Run the stricter release audit after actual clearance, and review evidence manually.
- [ ] Capture real screenshots; replace README placeholders.
- [ ] Configure the public repository/issue tracker, review included artifacts, and publish only cleared content.

Addon Manager metadata and packaging are a later milestone, not implemented or claimed here.
