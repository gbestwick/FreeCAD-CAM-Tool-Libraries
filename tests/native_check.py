"""Opt-in FreeCAD native checks; not part of unittest discovery.

Run inside FreeCADCmd with FREECAD_CAM_TEST_ROOT and FREECAD_USER_HOME/DATA/
TEMP pointing inside the repository's ignored .test-runs directory. Set
FREECAD_CAM_TEST_STAGE to smoke, install, or reload. See docs/TESTING.md.
"""
import ast
import json
import os
from pathlib import Path
import sys


def main():
    import FreeCAD as App
    root = Path(__file__).resolve().parents[1]
    base = Path(os.environ['FREECAD_CAM_TEST_ROOT']).resolve()
    allowed = root / '.test-runs'
    if base == allowed or not base.is_relative_to(allowed):
        raise RuntimeError('Native checks require a dedicated directory inside .test-runs')
    # Check isolation BEFORE importing CAM or querying preferences: queries can
    # create a default asset directory. Flatpak overrides XDG_*; use FREECAD_*.
    data_path = Path(App.getUserAppDataDir()).resolve()
    cfg_path = Path(App.ConfigGet('UserParameter')).resolve()
    if not data_path.is_relative_to(base) or not cfg_path.is_relative_to(base):
        raise RuntimeError(f'Profile not isolated: data={data_path}, config={cfg_path}')
    from Path import Preferences
    if not Preferences.getAssetPath().resolve().is_relative_to(base):
        raise RuntimeError('CAM asset store is not isolated')
    sys.path.insert(0, str(root / 'src'))
    from freecad_cam_libraries.compatibility import FreeCADAdapter
    from freecad_cam_libraries.installer import Installer
    from freecad_cam_libraries.library_manager import library_id
    from freecad_cam_libraries.manifest import load_manifest, read_json
    from freecad_cam_libraries.validation import validate_tool
    adapter = FreeCADAdapter()
    stage = os.environ.get('FREECAD_CAM_TEST_STAGE', 'smoke')
    collections = [c for c in load_manifest(root / 'libraries/manifest.json') if c.status == 'available']
    expected = sum(c.expected_count for c in collections)
    if stage == 'smoke':
        path = root / 'IntegrationTest.FCMacro'
        module = ast.parse(path.read_text(), filename=str(path))
        # The GUI macro reports exceptions to Report view. Let the harness
        # propagate them rather than treating a swallowed failure as success.
        if not isinstance(module.body[-1], ast.Try):
            raise RuntimeError('Integration macro wrapper changed; review harness')
        module.body.pop()
        namespace = {'__file__': str(path)}
        exec(compile(module, str(path), 'exec'), namespace)
        namespace['integration_test']()
        assert not adapter.assets.list_assets('toolbitlibrary', store='local')
        assert not adapter.assets.list_assets('toolbit', store='local')
    elif stage == 'install':
        assert not adapter.assets.list_assets('toolbitlibrary', store='local'), 'Use a fresh test profile'
        assert not adapter.assets.list_assets('toolbit', store='local'), 'Use a fresh test profile'
        engine = Installer(adapter, base / 'backups', App.Version())
        preview = engine.run(collections, True, equivalent_policy='distinct')
        assert not preview.errors and preview.tools_imported == expected, preview.summary()
        assert not adapter.assets.list_assets('toolbit', store='local'), 'Dry-run wrote assets'
        assert not (base / 'backups').exists(), 'Dry-run wrote backups'
        first = engine.run(collections, False, equivalent_policy='distinct')
        assert not first.errors and first.tools_imported == expected, first.errors
        _, before = adapter.snapshot()
        second = engine.run(collections, False, equivalent_policy='distinct')
        _, after = adapter.snapshot()
        assert not second.errors and second.tools_skipped == expected and second.tools_imported == 0, second.errors
        assert {lib['id']: lib['raw'] for lib in before} == {lib['id']: lib['raw'] for lib in after}, 'Rerun changed library bytes'
        print(first.summary(), flush=True)
        print(second.summary(), flush=True)
    elif stage == 'reload':
        # Run in a second FreeCAD process against only this disposable profile.
        count = 0
        for collection in collections:
            ident = library_id(collection.id)
            library = adapter.assets.get('toolbitlibrary://' + ident)
            bits = library.get_bits()
            assert len(bits) == collection.expected_count, collection.id
            assert {bit.get_id() for bit in bits} == {p.stem for p in collection.files()}, collection.id
            assert sorted(library.get_bit_no_from_bit(bit) for bit in bits) == list(range(1, len(bits) + 1))
            for path in collection.files():
                tool = validate_tool(path, collection.category)
                assert adapter.tool_data(tool.id) == tool.data, 'Stored definition changed: ' + tool.id
            count += len(bits)
        assert count == expected
        print(f'New-process reload verified {count} tools in {len(collections)} libraries.', flush=True)
    else:
        raise ValueError('Unknown test stage: ' + stage)
    result = {'stage': stage, 'result': 'PASS', 'version': App.Version(),
              'user_data': str(data_path), 'asset_path': str(Preferences.getAssetPath())}
    (base / f'{stage}-passed.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS native stage: ' + stage, flush=True)


if __name__ == '__main__' or os.environ.get('FREECAD_CAM_TEST_ROOT'):
    main()
