"""UI-independent installer with per-tool saves and recoverable partial success."""
from dataclasses import dataclass, field, asdict
from pathlib import Path, PureWindowsPath
import json
import os
import uuid
from .compatibility import check_version
from .library_manager import find_library, library_id, next_number
from .manifest import read_json
from .tool_manager import classify
from .validation import validate_tool


@dataclass
class Report:
    dry_run: bool
    libraries_created: int = 0
    libraries_present: int = 0
    tools_imported: int = 0  # Successfully saved memberships, or planned in dry-run.
    tools_registered: int = 0
    tools_skipped: int = 0
    conflicts: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    events: list = field(default_factory=list)
    recovery_directory: str = ""

    def summary(self):
        prefix = "Dry-run plan" if self.dry_run else "Installation results"
        return (f"{prefix}: libraries created {self.libraries_created}, already present {self.libraries_present}; "
                f"tools added {self.tools_imported}, registered {self.tools_registered}, "
                f"skipped {self.tools_skipped}, conflicts {self.conflicts}, errors {len(self.errors)}.")


class Journal:
    """Write-ahead record outside FreeCAD storage, plus exact original libraries."""
    def __init__(self, base):
        self.directory = Path(base) / str(uuid.uuid4())
        self.directory.mkdir(parents=True, exist_ok=False)
        self.data = {"schema_version": 1, "state": "in-progress", "libraries": {}, "actions": []}
        self.flush()

    def flush(self):
        target = self.directory / "journal.json"
        temp = self.directory / "journal.tmp"
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(self.data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(target)

    def backup(self, ident, raw):
        if ident in self.data["libraries"]:
            return
        # Library identifiers can come from user filenames; never use as paths.
        name = f"library-{len(self.data['libraries']):04d}.fctl" if raw is not None else None
        if name:
            with (self.directory / name).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        self.data["libraries"][ident] = name
        self.flush()

    def action(self, kind, **details):
        self.data["actions"].append({"kind": kind, **details})
        self.flush()

    def finish(self, report):
        self.data["state"] = "finished-with-errors" if report.errors else "finished"
        self.data["report"] = asdict(report)
        self.flush()


def memberships(data):
    if not isinstance(data, dict) or set(data) - {"label", "version", "tools"}:
        raise ValueError("Nonstandard library metadata; refusing a potentially lossy native save")
    if data.get("version") != 1 or not isinstance(data.get("tools"), list):
        raise ValueError("Unsupported library format")
    numbers, ids = set(), set()
    for row in data["tools"]:
        if not isinstance(row, dict) or set(row) != {"nr", "path"}:
            raise ValueError("Nonstandard library entry")
        number, path = row["nr"], row["path"]
        if type(number) is not int or number <= 0 or number in numbers:
            raise ValueError("Invalid/duplicate library tool number")
        if (not isinstance(path, str) or not path.endswith(".fctb") or "/" in path
                or "\\" in path or PureWindowsPath(path).drive or path[:-5] in ids):
            raise ValueError("Nonstandard/duplicate library tool path")
        numbers.add(number); ids.add(path[:-5])
    return numbers, ids


class Installer:
    def __init__(self, adapter, backup_directory, version=(1, 1, 0)):
        self.version_family = check_version(version)
        self.adapter = adapter
        self.backup_directory = Path(backup_directory)

    def run(self, collections, dry_run=True, log=None, progress=None, equivalent_policy="skip"):
        if equivalent_policy not in ("skip", "distinct"):
            raise ValueError("equivalent_policy must be skip or distinct")
        report, journal = Report(dry_run), None
        collections = list(collections)
        def emit(message):
            report.events.append(message)
            if log:
                log(message)
        try:
            existing, libraries = self.adapter.snapshot()
        except Exception as exc:
            report.errors.append(f"Cannot inventory FreeCAD assets; no changes made: {exc}")
            emit(report.errors[-1])
            return report
        files_by_id, seen, duplicate_ids = {}, {}, set()
        # Validate all selected input before writes. A repeated UUID is an error
        # even if both files are identical: manifests must have one owner per ID.
        for collection in collections:
            try:
                if self.version_family not in collection.compatible_versions:
                    raise ValueError(f"Collection does not support FreeCAD {self.version_family}")
                available, count = collection.availability()
                if not available:
                    raise ValueError(f"Unavailable/incomplete collection: found {count}, expected {collection.expected_count}")
                files_by_id[collection.id] = []
                for path in collection.files():
                    try:
                        tool = validate_tool(path, collection.category)
                        if tool.id in seen:
                            duplicate_ids.add(tool.id)
                            raise ValueError(f"UUID repeated in selected source: {tool.id}")
                        seen[tool.id] = tool
                        files_by_id[collection.id].append(tool)
                    except Exception as exc:
                        report.errors.append(f"{collection.name}: {exc}")
            except Exception as exc:
                report.errors.append(f"{collection.name}: {exc}")
                emit(report.errors[-1])
        total = sum(len(tools) for tools in files_by_id.values())
        done = 0
        fatal = False
        for collection in collections:
            if fatal:
                break
            if collection.id not in files_by_id:
                continue
            warning = f"{collection.name}: {collection.geometry['accuracy']}: {collection.geometry['notes']}"
            report.warnings.append(warning); emit(warning)
            try:
                found = find_library(collection, libraries)
                ident = found["id"] if found else library_id(collection.id)
                current_raw = found["raw"] if found else None
                data = read_json(current_raw) if found else {"version": 1, "label": collection.name, "tools": []}
                numbers, ids = memberships(data)
                # Refuse to rewrite broken dependencies rather than drop them.
                if ids - existing.keys():
                    raise ValueError(f"Library has unresolved tool references: {sorted(ids - existing.keys())}")
                if found:
                    report.libraries_present += 1
                created = False
            except Exception as exc:
                report.errors.append(f"{collection.name}: {exc}"); emit(report.errors[-1])
                continue
            for tool in files_by_id[collection.id]:
                done += 1
                if progress:
                    progress(done, total)
                try:
                    if tool.id in duplicate_ids:
                        report.conflicts += 1
                        emit(f"CONFLICT source UUID appears more than once: {tool.id}")
                        continue
                    status, other = classify(tool, existing)
                    if status in ("conflict", "equivalent"):
                        report.conflicts += 1
                        if status == "equivalent" and equivalent_policy == "distinct":
                            emit(f"DISTINCT {tool.data['name']}: equivalent to {other}; explicit policy keeps separate UUIDs")
                            status = "new"
                        else:
                            emit(f"CONFLICT {tool.data['name']}: {status}, existing UUID {other}; left unchanged")
                            continue
                    if tool.id in ids:
                        report.tools_skipped += 1
                        emit(f"SKIP {tool.data['name']}: already in library")
                        continue
                    number = next_number(numbers)
                    next_data = dict(data, tools=data["tools"] + [{"nr": number, "path": f"{tool.id}.fctb"}])
                    if not dry_run:
                        # Validate native dependencies before registering anything.
                        prepared = self.adapter.prepare(tool)
                        if journal is None:
                            journal = Journal(self.backup_directory)
                            report.recovery_directory = str(journal.directory)
                        journal.backup(ident, current_raw)
                        # Recheck UUID ownership immediately before a possible write.
                        fresh = self.adapter.tool_data(tool.id)
                        if fresh is not None:
                            fresh_status, _ = classify(tool, {tool.id: fresh})
                            if fresh_status != "reuse":
                                raise ValueError("Tool changed since preview; preserving it")
                        if fresh is None:
                            journal.action("register-intent", tool_id=tool.id, library_id=ident)
                            self.adapter.register(tool, prepared)
                            report.tools_registered += 1
                            existing[tool.id] = tool.data
                            journal.action("registered", tool_id=tool.id)
                        # A failed library save can leave an unlinked new asset.
                        # Its write-ahead record enables inspection/recovery.
                        journal.action("save-intent", library_id=ident, tool_id=tool.id, number=number)
                        try:
                            current_raw = self.adapter.save_library(ident, next_data, current_raw)
                        except Exception as exc:
                            report.errors.append(f"{collection.name}: library save failed: {exc}. Stop this collection; consult recovery journal.")
                            emit(report.errors[-1])
                            break
                    existing[tool.id] = tool.data
                    data = next_data
                    numbers.add(number); ids.add(tool.id)
                    report.tools_imported += 1
                    if not found and not created:
                        report.libraries_created += 1
                        created = True
                        libraries.append({"id": ident, "label": data["label"], "data": data, "raw": current_raw})
                    emit(f"{'PLAN' if dry_run else 'ADD'} T{number}: {tool.data['name']}")
                    if not dry_run:
                        journal.action("saved", library_id=ident, tool_id=tool.id, number=number)
                except Exception as exc:
                    report.errors.append(f"{collection.name}/{tool.path.name}: {exc}")
                    emit(report.errors[-1])
                    # Disk/backup failures make further writes unsafe. Other
                    # native tool errors may be isolated and can continue.
                    if isinstance(exc, OSError):
                        fatal = True
                        break
        if journal:
            try:
                journal.finish(report)
            except Exception as exc:
                report.errors.append(f"Could not finalize recovery journal: {exc}")
        for error in report.errors:
            if error not in report.events:
                emit(error)
        emit(report.summary())
        return report
