"""Run native CAM checks against an existing FreeCAD Pixi development build.

Usage: python3 tests/run_native_pixi.py /path/to/FreeCAD-checkout
Does not configure, rebuild, or modify the FreeCAD checkout. All test assets
and preferences are isolated under this project's ignored .test-runs folder.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--binary', default='build/relWithDebInfo/bin/FreeCADCmd')
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    binary = (checkout / args.binary).resolve()
    if not binary.is_file() or not (checkout / 'pixi.toml').is_file():
        parser.error('An existing Pixi checkout and built FreeCADCmd are required')
    root = Path(__file__).resolve().parents[1]
    base = root / '.test-runs' / ('pixi-native-' + str(uuid.uuid4()))
    base.mkdir(parents=True)
    env = dict(os.environ)
    for name in ('config', 'data', 'temp'):
        (base / name).mkdir()
    env.update(FREECAD_USER_HOME=str(base/'config'), FREECAD_USER_DATA=str(base/'data'),
               FREECAD_USER_TEMP=str(base/'temp'), FREECAD_CAM_TEST_ROOT=str(base))
    for stage in ('smoke', 'install', 'reload', 'upgrade'):
        env['FREECAD_CAM_TEST_STAGE'] = stage
        command = ['pixi', 'run', '--frozen', str(binary), '-u', str(base/'user.cfg'),
                   '-s', str(base/'system.cfg'), str(root/'tests/native_check.py')]
        log = base / (stage + '.log')
        with log.open('w') as stream:
            result = subprocess.run(command, cwd=checkout, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=300)
        marker = base / (stage + '-passed.json')
        print(stage, 'status', result.returncode, 'verified marker', marker.exists(), 'log', log, flush=True)
        if result.returncode or not marker.is_file():
            print(log.read_text()[-5000:])
            raise SystemExit(1)
        print('FreeCAD:', json.loads(marker.read_text())['version'], flush=True)
    print('PASS all Pixi native stages', base, flush=True)


if __name__ == '__main__':
    main()
