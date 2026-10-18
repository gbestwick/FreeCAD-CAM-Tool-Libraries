"""Run with PYTHONPATH=src python -m freecad_cam_libraries.audit [--release]."""
import argparse
from pathlib import Path
from .manifest import load_manifest
from .validation import validate_tool, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[2]/'libraries/manifest.json')
    parser.add_argument('--release', action='store_true', help='Also require complete inventory and explicit data licensing')
    args = parser.parse_args()
    errors, seen, signatures = [], {}, {}
    total = 0
    for collection in load_manifest(args.manifest):
        available, count = collection.availability()
        total += count
        print(f'{collection.name}: {count}/{collection.expected_count}; {collection.status}; {collection.geometry["accuracy"]}')
        if collection.status == 'available' and not available:
            errors.append(f'{collection.id}: inventory mismatch')
        if args.release:
            if not available:
                errors.append(f'{collection.id}: incomplete release inventory')
            if collection.source['redistribution'] != 'cleared' or not collection.source.get('license') or not collection.source.get('permission_evidence'):
                errors.append(f'{collection.id}: data redistribution clearance/license/evidence missing')
        for path in collection.files():
            try:
                tool = validate_tool(path, collection.category)
                if tool.id in seen:
                    errors.append(f'Duplicate UUID: {tool.id}')
                seen[tool.id] = path
                sig = fingerprint(tool.data)
                if sig in signatures:
                    print(f'  Equivalent definitions (different UUIDs): {path} and {signatures[sig]}')
                signatures[sig] = path
            except Exception as exc:
                errors.append(str(exc))
    print(f'Total source files: {total}; unique validated UUIDs: {len(seen)}')
    for error in errors:
        print('ERROR: '+error)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
