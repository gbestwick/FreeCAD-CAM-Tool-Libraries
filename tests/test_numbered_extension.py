import csv
from dataclasses import replace
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

from test_installer import MockAssets, definition
from freecad_cam_libraries.installer import Installer
from freecad_cam_libraries.library_manager import find_library, library_id
from freecad_cam_libraries.manifest import load_manifest, ManifestError
from freecad_cam_libraries.validation import validate_tool, quantity

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/'docs/source-catalogs/numbered-extension/reviewed.csv'
spec = importlib.util.spec_from_file_location('numbered_generator',ROOT/'tools/generate_numbered_extension.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class NumberedExtensionTests(unittest.TestCase):
    def test_reviewed_output_and_complete_number_range(self):
        directory=ROOT/'libraries/drills/numbered-118'
        self.assertEqual(generator.generate(CATALOG,directory,check=True),20)
        numbers=[]
        for path in directory.glob('*.fctb'):
            tool=validate_tool(path,'drills')
            numbers.append(int(re.search(r'Drill #(\d+)',tool.data['name']).group(1)))
        self.assertEqual(sorted(numbers),list(range(1,81)))
        rows=generator.reviewed_rows(CATALOG)
        for row in rows:
            tool=generator.definition(row)
            for prop,col in [('Diameter','diameter_in'),('Length','overall_length_in'),('CuttingEdgeHeight','flute_length_in')]:
                self.assertEqual(Decimal(tool['parameter'][prop].split()[0]),generator.inches(row[col])*Decimal('25.4'))
        by_number={r['number']:generator.definition(r) for r in rows}
        self.assertEqual(quantity(by_number['80']['parameter']['Length']),Decimal('19.05'))
        self.assertEqual(quantity(by_number['61']['parameter']['Diameter']),Decimal('0.9906'))

    def test_generator_preserves_existing_and_modified_files(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'output';output.mkdir()
            existing=output/'existing.fctb';existing.write_text('untouched')
            generator.generate(CATALOG,output)
            before={p.name:p.read_bytes() for p in output.iterdir()}
            generator.generate(CATALOG,output)
            self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})
            self.assertEqual(existing.read_text(),'untouched')
            row=generator.reviewed_rows(CATALOG)[-1]
            path=output/(generator.definition(row)['id']+'.fctb')
            path.write_text('custom')
            with self.assertRaises(ValueError):generator.generate(CATALOG,output)
            self.assertEqual(path.read_text(),'custom')

    def test_incomplete_and_unreviewed_catalogs_rejected(self):
        rows=generator.reviewed_rows(CATALOG)
        for change in ('missing','unreviewed','duplicate','invalid-length'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temp:
                changed=[dict(r) for r in rows]
                if change=='missing':changed.pop()
                elif change=='unreviewed':changed[0]['review_status']='unreviewed'
                elif change=='duplicate':changed.append(dict(changed[0]))
                else:changed[0]['overall_length_in']='unknown'
                path=Path(temp)/'input.csv'
                with path.open('w',newline='') as stream:
                    w=csv.DictWriter(stream,fieldnames=generator.FIELDS);w.writeheader();w.writerows(changed)
                with self.assertRaises(ValueError):generator.generate(path,Path(temp)/'output')
                self.assertFalse((Path(temp)/'output').exists())

    def test_existing_sixty_tool_library_upgrades_preserving_name_and_numbers(self):
        collection=next(c for c in load_manifest(ROOT/'libraries/manifest.json') if c.id=='jobber-numbered-118')
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);old_dir=base/'old';old_dir.mkdir()
            for path in collection.files():
                if '[PTD R18 ' not in json.loads(path.read_text())['name']:
                    (old_dir/path.name).write_bytes(path.read_bytes())
            old=replace(collection,name=collection.legacy_names[0],directory=old_dir,expected_count=60,legacy_names=())
            assets=MockAssets();engine=Installer(assets,base/'backups')
            initial=engine.run([old],False)
            self.assertEqual(initial.tools_imported,60)
            ident=library_id(collection.id);lib=assets.libraries[ident]
            lib['tools'][0]['nr']=500
            custom=definition(diameter='99 mm');assets.tools[custom['id']]=custom
            lib['tools'].append({'nr':900,'path':custom['id']+'.fctb'})
            before={row['path']:row['nr'] for row in lib['tools']}
            result=engine.run([collection],False)
            self.assertFalse(result.errors)
            self.assertEqual(result.tools_imported,20)
            self.assertEqual(result.tools_skipped,60)
            self.assertEqual(len(assets.libraries),1)
            saved=assets.libraries[ident]
            self.assertEqual(saved['label'],old.name)
            after={row['path']:row['nr'] for row in saved['tools']}
            self.assertEqual(before,{key:after[key] for key in before})
            self.assertEqual(sorted(value for key,value in after.items() if key not in before),list(range(901,921)))
            repeat=engine.run([collection],False)
            self.assertFalse(repeat.errors)
            self.assertEqual(repeat.tools_skipped,80)

    def test_aliases_do_not_accept_custom_rename_or_ambiguous_libraries(self):
        collection=load_manifest(ROOT/'libraries/manifest.json')[0]
        ident=library_id(collection.id)
        with self.assertRaises(ValueError):find_library(collection,[{'id':ident,'label':'User custom name'}])
        libraries=[{'id':ident,'label':collection.legacy_names[0]},{'id':'other','label':collection.name}]
        with self.assertRaises(ValueError):find_library(collection,libraries)
        self.assertEqual(find_library(collection,[{'id':'manual','label':collection.legacy_names[0]}])['id'],'manual')

    def test_manifest_alias_validation_and_range_names(self):
        original=json.loads((ROOT/'libraries/manifest.json').read_text())
        for c in load_manifest(ROOT/'libraries/manifest.json'):
            if c.status=='available':self.assertTrue(c.legacy_names)
        self.assertIn('1/64-1/2 in by 1/64',original['collections'][0]['name'])
        with tempfile.TemporaryDirectory() as temp:
            for aliases in ('bad',[''],['same','same'],[original['collections'][0]['name']]):
                data=json.loads(json.dumps(original));data['collections'][0]['legacy_names']=aliases
                path=Path(temp)/'manifest.json';path.write_text(json.dumps(data))
                with self.assertRaises(ManifestError):load_manifest(path)
