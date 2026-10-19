"""Run isolated native checks using the installed FreeCAD Flatpak.

Usage: python3 tests/run_native_flatpak.py
All profiles, assets and logs go into .test-runs/<fresh UUID>. User CAM data
is not selected. Exit status alone is insufficient for FreeCADCmd, so each
stage must also produce its success marker after all assertions pass.
"""
import os, pathlib, subprocess, uuid
root=pathlib.Path(__file__).resolve().parents[1]
(root/'.test-runs').mkdir(exist_ok=True)
base=root/'.test-runs'/('native-'+str(uuid.uuid4()))
base.mkdir()
(root/'.test-runs/latest-native-run.txt').write_text(str(base))
for name in ('config','data','temp'):(base/name).mkdir()
for stage in ('smoke','install','reload','upgrade'):
 command=['flatpak','run',f'--env=FREECAD_USER_HOME={base}/config',f'--env=FREECAD_USER_DATA={base}/data',f'--env=FREECAD_USER_TEMP={base}/temp',f'--env=FREECAD_CAM_TEST_ROOT={base}',f'--env=FREECAD_CAM_TEST_STAGE={stage}','--command=FreeCADCmd','org.freecad.FreeCAD','-u',str(base/'user.cfg'),'-s',str(base/'system.cfg'),str(root/'tests/native_check.py')]
 with (base/(stage+'.log')).open('w') as stream:
  proc=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
 marker=base/(stage+'-passed.json')
 print(stage,'process status',proc.returncode,'verified marker',marker.exists(), 'log', base/(stage+'.log'),flush=True)
 if proc.returncode or not marker.exists():
  print((base/(stage+'.log')).read_text()[-5000:]);raise SystemExit(1)
print('PASS all stages',base,flush=True)
