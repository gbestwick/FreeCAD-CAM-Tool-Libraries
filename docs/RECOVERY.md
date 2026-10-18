# Backup and failure recovery

Before first testing, close FreeCAD and copy the entire configured CAM asset directory. Inspect its location with `Path.Preferences.getAssetPath()` in the FreeCAD console before closing. Preserve that offline copy separately. This is the most complete recovery method, including user tools and shapes; installer backups only cover affected libraries.

## Installer records

The log and final report identify `<FreeCAD user data>/FreeCADCAMLibraries/backups/<run UUID>/`.

- `journal.json` records state, intended registrations, intended library saves, successful operations, and the final report when possible.
- `libraries` maps each target library ID to its exact original backup filename. A `null` value means the destination was absent at the start of this run.
- `library-0000.fctl`, etc. are exact original library payloads, not complete tool exports. Backup filenames are generated independently of user-controlled library IDs.
- `register-intent`/`save-intent` without a later success record mean the operation may have failed **or may have completed before an interruption**. Inspect native state before deciding what happened.

Backups and journal content are flushed before writes; journal updates use temporary-file replacement. This does not make FreeCAD asset writes atomic or guarantee survival of filesystem/power failures. An in-progress journal after a crash is evidence for recovery, not proof that all pending changes are absent.

## Ordinary retry

If a tool registered but failed to enter its library, a normal rerun reuses its unchanged UUID and adds the missing membership. Completed earlier tools are skipped and custom numbers retained. Conflicts are not overwritten. After an error, close/reopen the library manager and inspect the stored library before rerunning. A library-save failure stops that collection to prevent proceeding with uncertain in-memory state.

Disk-full, permission, and backup failures must be resolved first. Native dependency or shape errors may be limited to individual tools. Provide the log and journal when reporting a failure.

## Restore a specific library

Restoring replaces the current library membership and numbers with its pre-run state. It would also remove later user edits, so inspect and back up the current state first. Use FreeCAD's native asset API, not hand-edited files inside its storage directory. In the FreeCAD Python console:

```python
import pathlib, json
from Path.Tool import cam_assets
run_dir = pathlib.Path(r"REPLACE WITH THE RUN DIRECTORY FROM THE REPORT")
record = json.loads((run_dir / "journal.json").read_text(encoding="utf-8"))
print(record["libraries"])
```

After choosing and verifying the exact target and backup:

```python
library_id = "REPLACE WITH THE TARGET LIBRARY ID"
backup_name = record["libraries"][library_id]
assert backup_name is not None, "This library did not exist before installation"
current = cam_assets.get_raw("toolbitlibrary://" + library_id, store="local")
(run_dir / "before-manual-restore.fctl").write_bytes(current)
original = (run_dir / backup_name).read_bytes()
cam_assets.add_raw("toolbitlibrary", library_id, original, store="local")
```

Use a fresh filename for each manual backup. Close/reopen the library manager and restart FreeCAD to verify. This restores a library, not any preexisting tool data; the installer never overwrites preexisting tools.

If `backup_name` is `null`, the installer originally created that destination. Remove it through the CAM library UI only after checking that it contains no later custom additions. Do not blindly execute deletes from a journal.

## Orphan tools

Registered tool assets are shared globally. Removing a library or restoring a library backup can leave tools unlinked. Leaving them is safer than deleting shared assets automatically. Journal tool IDs identify candidates for inspection, but another library or saved job may now use them. Remove only after checking all references and taking a full backup. No automatic rollback deletes registered tool assets.

For extensive damage or uncertain state, close FreeCAD and restore the complete offline CAM asset backup. Retain the failed-state directory separately for investigation.
