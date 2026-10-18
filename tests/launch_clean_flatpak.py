"""Open the installer in a fresh, persistent FreeCAD Flatpak test profile.

Usage: python3 tests/launch_clean_flatpak.py
Creates a new ignored .test-runs/gui-<UUID> profile on every launch. Close that
FreeCAD window when finished. The normal FreeCAD profile is not selected.
"""
import json
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / '.test-runs' / ('gui-' + str(uuid.uuid4()))
    base.mkdir(parents=True)
    for name in ('config', 'data', 'temp'):
        (base / name).mkdir()
    macro = root / 'InstallLibraries.FCMacro'
    wrapper = base / 'OpenInstaller.FCMacro'
    # Embed paths as Python literals, not interpolated shell code.
    wrapper.write_text(
        'from pathlib import Path\n'
        'import FreeCAD as App\n'
        f'base = Path({str(base)!r}).resolve()\n'
        'if not Path(App.getUserAppDataDir()).resolve().is_relative_to(base):\n'
        '    raise RuntimeError("Refusing to run: FreeCAD test data is not isolated")\n'
        'if not Path(App.ConfigGet("UserParameter")).resolve().is_relative_to(base):\n'
        '    raise RuntimeError("Refusing to run: FreeCAD test settings are not isolated")\n'
        'from Path import Preferences\n'
        'if not Preferences.getAssetPath().resolve().is_relative_to(base):\n'
        '    raise RuntimeError("Refusing to run: CAM test storage is not isolated")\n'
        f'macro = Path({str(macro)!r})\n'
        'exec(compile(macro.read_text(encoding="utf-8"), str(macro), "exec"), '
        '{"__file__": str(macro), "__name__": "__main__"})\n', encoding='utf-8')
    command = [
        'flatpak', 'run',
        f'--env=FREECAD_USER_HOME={base / "config"}',
        f'--env=FREECAD_USER_DATA={base / "data"}',
        f'--env=FREECAD_USER_TEMP={base / "temp"}',
        '--command=FreeCAD', 'org.freecad.FreeCAD',
        '-u', str(base / 'user.cfg'), '-s', str(base / 'system.cfg'),
        '--log-file', str(base / 'FreeCAD.log'), str(wrapper),
    ]
    (base / 'launch.json').write_text(json.dumps({'profile': str(base), 'command': command}, indent=2) + '\n')
    print('Opening FreeCAD with an empty test profile:', base, flush=True)
    print('Your normal tools and libraries are retained. Only test-profile settings/assets will be written.', flush=True)
    print('Close this FreeCAD window when finished. The test profile is retained for inspection.', flush=True)
    with (base / 'console.log').open('w', encoding='utf-8') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    print('FreeCAD exited with status', result.returncode, flush=True)
    print('Test profile and logs:', base, flush=True)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
