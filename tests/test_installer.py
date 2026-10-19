"""Standard-library tests. Synthetic dimensions here are test fixtures only."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from freecad_cam_libraries.compatibility import check_version
from freecad_cam_libraries.installer import Installer, memberships
from freecad_cam_libraries.library_manager import library_id, next_number
from freecad_cam_libraries.manifest import load_manifest, ManifestError, read_json, Collection
from freecad_cam_libraries.tool_manager import classify
from freecad_cam_libraries.validation import validate_tool, ValidationError, quantity

ROOT = Path(__file__).resolve().parents[1]


def definition(shape="drill.fcstd", ident=None, diameter="3 mm"):
    params = {"Diameter": diameter, "Length": "40 mm", "Flutes": 2, "Material": "Carbide"}
    if shape == "drill.fcstd":
        params.update(CuttingEdgeHeight="10 mm", TipAngle="118°")
        kind = "Drill"
    elif shape == "endmill.fcstd":
        params.update(CuttingEdgeHeight="10 mm", ShankDiameter="3 mm")
        kind = "Endmill"
    else:
        params.update(NeckDiameter="2 mm", NeckLength="10 mm", ShankDiameter="3 mm", Crest="0.1 mm", cuttingAngle="60°")
        kind = "ThreadMill"
    return {"id": ident or str(uuid.uuid4()), "name": "Synthetic test tool", "version": 2,
            "shape": shape, "shape-type": kind, "parameter": params, "attribute": {}}


class MockAssets:
    """Contract mock. Does not establish real FreeCAD compatibility."""
    def __init__(self):
        self.tools, self.libraries, self.writes = {}, {}, []
        self.fail_prepare = set()
        self.fail_save = False
        self.fail_register = set()

    def snapshot(self):
        return copy.deepcopy(self.tools), [dict(id=i, label=d["label"], data=copy.deepcopy(d), raw=self.library_raw(i)) for i, d in self.libraries.items()]

    def tool_data(self, ident):
        return copy.deepcopy(self.tools.get(ident))

    def prepare(self, tool):
        if tool.id in self.fail_prepare:
            raise RuntimeError("test shape load failure")
        return object()

    def register(self, tool, prepared):
        if tool.id in self.fail_register:
            raise RuntimeError("test registration failure")
        assert tool.id not in self.tools
        self.tools[tool.id] = copy.deepcopy(tool.data)
        self.writes.append(("register", tool.id))

    def library_raw(self, ident):
        return json.dumps(self.libraries[ident], sort_keys=True).encode() if ident in self.libraries else None

    def save_library(self, ident, data, expected_raw):
        if self.fail_save:
            raise RuntimeError("test disk failure")
        if self.library_raw(ident) != expected_raw:
            raise RuntimeError("concurrent change")
        self.libraries[ident] = copy.deepcopy(data)
        self.writes.append(("save", ident))
        return self.library_raw(ident)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.directory = self.base / "tools with spaces"
        self.directory.mkdir()
        self.collection = Collection("test-tools", "Test Library", "drills", self.directory, 2,
            {"attribution": "synthetic tests", "redistribution": "test"}, "metric",
            {"description": "test", "accuracy": "provisional", "notes": "test only"}, ("1.1.x",), "available")
        self.data = [definition(diameter=f"{i} mm", ident=str(uuid.UUID(int=i))) for i in (1, 2)]
        for d in self.data:
            self.write(d)
        self.assets = MockAssets()
        self.backups = self.base / "backups"
        self.engine = Installer(self.assets, self.backups)

    def test_development_family_uses_collection_compatibility(self):
        engine = Installer(self.assets, self.backups, ('27', '1', '0', 'dev'))
        report = engine.run([self.collection], dry_run=False)
        self.assertTrue(report.errors)
        self.assertIn('27.1.x', report.errors[0])
        self.assertFalse(self.assets.writes)
        collection = replace(self.collection, compatible_versions=('27.1.x',))
        first = engine.run([collection], dry_run=False)
        second = engine.run([collection], dry_run=False)
        self.assertFalse(first.errors + second.errors)
        self.assertEqual(first.tools_imported, 2)
        self.assertEqual(second.tools_skipped, 2)
        stable = self.engine.run([collection], dry_run=False)
        self.assertTrue(stable.errors)
        self.assertIn('1.1.x', stable.errors[0])

    def write(self, data):
        path = self.directory / (data['id'] + '.fctb')
        path.write_text(json.dumps(data))
        return path

    def run_install(self, dry=False):
        return self.engine.run([self.collection], dry_run=dry)

    def existing_library(self, numbers=(7,)):
        tool = self.data[0]
        self.assets.tools[tool['id']] = copy.deepcopy(tool)
        ident = library_id(self.collection.id)
        self.assets.libraries[ident] = {"label": self.collection.name, "version": 1,
            "tools": [{"nr": numbers[0], "path": tool['id'] + '.fctb'}]}
        return ident

    def test_install_and_repeat(self):
        first = self.run_install()
        self.assertEqual((first.tools_imported, first.tools_registered, first.libraries_created), (2, 2, 1))
        before = copy.deepcopy(self.assets.libraries)
        second = self.run_install()
        self.assertEqual((second.tools_imported, second.tools_skipped, second.libraries_present), (0, 2, 1))
        self.assertEqual(before, self.assets.libraries)
        self.assertFalse(second.errors)

    def test_dry_run_never_writes_or_creates_backup(self):
        report = self.run_install(True)
        self.assertEqual(report.tools_imported, 2)
        self.assertEqual(self.assets.writes, [])
        self.assertFalse(self.backups.exists())
        self.assertEqual(self.assets.tools, {})

    def test_custom_numbers_and_exact_backup(self):
        ident = self.existing_library((42,))
        raw = self.assets.library_raw(ident)
        report = self.run_install()
        self.assertEqual([t['nr'] for t in self.assets.libraries[ident]['tools']], [42, 43])
        journal = read_json((Path(report.recovery_directory)/'journal.json').read_bytes())
        self.assertEqual((Path(report.recovery_directory)/journal['libraries'][ident]).read_bytes(), raw)

    def test_modified_same_uuid_conflicts(self):
        ident = self.existing_library()
        self.assets.tools[self.data[0]['id']]['parameter']['Diameter'] = '9 mm'
        report = self.run_install()
        self.assertEqual(report.conflicts, 1)
        self.assertEqual(report.tools_imported, 1)
        self.assertEqual(self.assets.tools[self.data[0]['id']]['parameter']['Diameter'], '9 mm')
        self.assertEqual(self.assets.libraries[ident]['tools'][0]['nr'], 7)

    def test_equivalent_different_uuid_is_not_merged(self):
        other = copy.deepcopy(self.data[0]); other['id'] = str(uuid.uuid4())
        self.assets.tools[other['id']] = other
        report = self.run_install()
        self.assertEqual(report.conflicts, 1)
        self.assertNotIn(self.data[0]['id'], self.assets.tools)

    def test_global_existing_uuid_reused_without_registration(self):
        self.assets.tools[self.data[0]['id']] = copy.deepcopy(self.data[0])
        report = self.run_install()
        self.assertEqual((report.tools_imported, report.tools_registered), (2, 1))

    def test_same_name_user_library_used_without_rename(self):
        ident = self.existing_library()
        user_id = 'my-existing-library'
        self.assets.libraries[user_id] = self.assets.libraries.pop(ident)
        report = self.run_install()
        self.assertEqual(report.libraries_present, 1)
        self.assertEqual(set(self.assets.libraries), {user_id})

    def test_renamed_library_preserved(self):
        ident = self.existing_library()
        self.assets.libraries[ident]['label'] = 'User renamed this'
        before = copy.deepcopy(self.assets.libraries)
        report = self.run_install()
        self.assertTrue(report.errors)
        self.assertEqual(before, self.assets.libraries)
        self.assertFalse(self.assets.writes)

    def test_ambiguous_library_preserved(self):
        ident = self.existing_library()
        self.assets.libraries['another'] = copy.deepcopy(self.assets.libraries[ident])
        self.assertTrue(self.run_install().errors)
        self.assertFalse(self.assets.writes)

    def test_malformed_tool_does_not_block_independent_tool(self):
        self.write(self.data[0]).write_text('{bad')
        report = self.run_install()
        self.assertEqual(report.tools_imported, 1)
        self.assertEqual(len(report.errors), 1)

    def test_missing_file_blocks_incomplete_collection(self):
        (self.directory/(self.data[0]['id']+'.fctb')).unlink()
        report = self.run_install()
        self.assertTrue(report.errors)
        self.assertFalse(self.assets.writes)

    def test_unavailable_collection(self):
        self.collection = replace(self.collection, status='missing')
        self.assertTrue(self.run_install().errors)
        self.assertFalse(self.assets.writes)

    def test_prepare_failure_continues(self):
        self.assets.fail_prepare.add(self.data[0]['id'])
        report = self.run_install()
        self.assertEqual(report.tools_imported, 1)
        self.assertEqual(len(report.errors), 1)

    def test_registration_failure_continues(self):
        self.assets.fail_register.add(self.data[0]['id'])
        report = self.run_install()
        self.assertEqual(report.tools_imported, 1)
        self.assertEqual(len(report.errors), 1)

    def test_save_failure_journals_orphan_and_retry_recovers(self):
        self.assets.fail_save = True
        failed = self.run_install()
        self.assertTrue(failed.errors)
        self.assertEqual((failed.tools_imported, failed.tools_registered), (0, 1))
        journal = read_json((Path(failed.recovery_directory)/'journal.json').read_bytes())
        self.assertIn('register-intent', [a['kind'] for a in journal['actions']])
        self.assertEqual(journal['state'], 'finished-with-errors')
        self.assets.fail_save = False
        recovered = self.run_install()
        self.assertEqual((recovered.tools_imported, recovered.tools_registered), (2, 1))
        self.assertFalse(recovered.errors)

    def test_backup_failure_prevents_writes(self):
        self.backups.write_text('cannot use a file as a directory')
        report = self.run_install()
        self.assertTrue(report.errors)
        self.assertFalse(self.assets.writes)

    def test_snapshot_failure_prevents_writes(self):
        with patch.object(self.assets, 'snapshot', side_effect=RuntimeError('broken inventory')):
            report = self.run_install()
        self.assertTrue(report.errors)
        self.assertFalse(self.assets.writes)

    def test_unresolved_existing_library_preserved(self):
        self.existing_library()
        self.assets.tools.clear()
        self.assertTrue(self.run_install().errors)
        self.assertFalse(self.assets.writes)

    def test_unknown_library_metadata_preserved(self):
        ident = self.existing_library()
        self.assets.libraries[ident]['user-metadata'] = {'keep': True}
        self.assertTrue(self.run_install().errors)
        self.assertFalse(self.assets.writes)

    def test_multiple_collections_and_progress(self):
        other = replace(self.collection, id='other-tools', name='Other Library', directory=self.base/'other')
        other.directory.mkdir()
        for i in (3,4):
            data = definition(ident=str(uuid.UUID(int=i)),diameter=f'{i} mm')
            (other.directory/(data['id']+'.fctb')).write_text(json.dumps(data))
        progress = []
        report = self.engine.run([self.collection, other], False, progress=lambda a,b: progress.append((a,b)))
        self.assertEqual((report.libraries_created, report.tools_imported), (2,4))
        self.assertEqual(progress[-1], (4,4))

    def test_repeated_source_uuid_never_installed(self):
        other = replace(self.collection, id='other-tools', name='Other', directory=self.base/'other')
        other.directory.mkdir()
        for data in self.data:
            (other.directory/(data['id']+'.fctb')).write_text(json.dumps(data))
        report = self.engine.run([self.collection, other], False)
        self.assertTrue(report.errors)
        self.assertEqual(report.tools_imported, 0)
        self.assertFalse(self.assets.writes)

    def test_concurrent_library_change_not_overwritten(self):
        ident = self.existing_library()
        original_prepare = self.assets.prepare
        def mutate(tool):
            self.assets.libraries[ident]['label'] = 'concurrent modification'
            return original_prepare(tool)
        with patch.object(self.assets, 'prepare', side_effect=mutate):
            report = self.run_install()
        self.assertTrue(report.errors)
        self.assertEqual(self.assets.libraries[ident]['label'], 'concurrent modification')


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def validate(self, data):
        path = self.directory/(data['id']+'.fctb')
        path.write_text(json.dumps(data))
        return validate_tool(path)

    def test_all_shapes(self):
        for shape in ('drill.fcstd','endmill.fcstd','thread-mill.fcstd'):
            self.assertEqual(self.validate(definition(shape)).data['shape'],shape)

    def test_all_shape_required_parameters(self):
        from freecad_cam_libraries.validation import SCHEMAS
        for shape, (_, required) in SCHEMAS.items():
            for key in required:
                data = definition(shape); del data['parameter'][key]
                with self.subTest(shape=shape,key=key), self.assertRaises(ValidationError):
                    self.validate(data)

    def test_wrong_threadmill_filename(self):
        data=definition('thread-mill.fcstd');data['shape']='threadmill.fcstd'
        with self.assertRaises(ValidationError): self.validate(data)

    def test_shape_type_and_category(self):
        data=definition();data['shape-type']='Endmill'
        with self.assertRaises(ValidationError): self.validate(data)
        tool=self.validate(definition())
        with self.assertRaises(ValidationError): validate_tool(tool.path,'endmills')

    def test_invalid_quantities(self):
        for value in (True, None, [], 'NaN', 'inf', '1 s', '-1 mm', '0 mm'):
            data=definition();data['parameter']['Diameter']=value
            with self.subTest(value=value), self.assertRaises(ValidationError): self.validate(data)

    def test_invalid_flutes_and_material(self):
        for key,value in [('Flutes',True),('Flutes',0),('Flutes',2.5),('Material','unknown')]:
            data=definition();data['parameter'][key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValidationError): self.validate(data)

    def test_geometry_relationships(self):
        for shape,key,value in [('drill.fcstd','CuttingEdgeHeight','50 mm'),('drill.fcstd','TipAngle','180°'),('thread-mill.fcstd','NeckDiameter','4 mm')]:
            data=definition(shape);data['parameter'][key]=value
            with self.assertRaises(ValidationError): self.validate(data)

    def test_filename_uuid_mismatch(self):
        data=definition();path=self.directory/'wrong.fctb';path.write_text(json.dumps(data))
        with self.assertRaises(ValidationError): validate_tool(path)

    def test_uuid_invalid(self):
        data=definition();data['id']='invalid'
        with self.assertRaises(ValidationError): self.validate(data)

    def test_attribute_placement_and_conflict(self):
        data=definition();data['attribute']['Flutes']=data['parameter'].pop('Flutes')
        self.validate(data)
        data['parameter']['Flutes']=3
        with self.assertRaises(ValidationError):self.validate(data)

    def test_equivalent_units_and_names(self):
        data=definition(diameter='25.4 mm');tool=self.validate(data)
        other=copy.deepcopy(data);other['id']=str(uuid.uuid4());other['name']='Different label';other['parameter']['Diameter']='1 in'
        self.assertEqual(classify(tool,{other['id']:other})[0],'equivalent')
        other['id']=tool.id
        self.assertEqual(classify(tool,{other['id']:other})[0],'conflict')

    def test_strict_json(self):
        for raw in ('{"id": 1,"id": 2}', '{"x": NaN}', '{"x": Infinity}'):
            with self.assertRaises(ValueError): read_json(raw)

    def test_units(self):
        self.assertEqual(quantity('1 in'),quantity('25.4 mm'))
        self.assertEqual(quantity('1e-3 m'),quantity('1 mm'))

    def test_numbering_and_library_rows(self):
        self.assertEqual(next_number({1,4,42}),43)
        self.assertEqual(next_number(set()),1)
        for numbers in ({True},{-1},{0}):
            with self.assertRaises(ValueError): next_number(numbers)
        with self.assertRaises(ValueError): memberships({'version':1,'label':'x','tools':[{'nr':1,'path':'../bad.fctb'}]})

    def test_versions(self):
        for version in ((1,1,0),('1','1','3'),(27,1,0),('27','1','0','dev')):check_version(version)
        for version in ((1,0,0),(1,2,0),(2,1,0),(27,0,0),(27,2,0),(),('unknown',)):
            with self.assertRaises(RuntimeError):check_version(version)


class RepositoryTests(unittest.TestCase):
    def test_manifest_inventory_and_all_definitions(self):
        collections=load_manifest(ROOT/'libraries/manifest.json')
        self.assertEqual(len(collections),10)
        self.assertEqual(sum(c.expected_count for c in collections),388)
        ids=set();count=0
        for c in collections:
            available,n=c.availability()
            self.assertEqual(available,c.status=='available')
            self.assertEqual(n,c.expected_count if available else 0)
            for path in c.files():
                tool=validate_tool(path,c.category)
                self.assertNotIn(tool.id,ids);ids.add(tool.id);count+=1
        self.assertEqual(count,358)

    def test_originals_preserved_exactly(self):
        inventory=read_json((ROOT/'docs/source-inventory.json').read_bytes())
        for row in inventory['tools']:
            raw=(ROOT/row['installed_source']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
            if 'original' in row:
                self.assertEqual(raw,(ROOT/row['original']).read_bytes())
            elif row.get('source_kind') == 'manufacturer-catalog-transcription':
                self.assertTrue((ROOT/row['source_catalog']).is_file())
                self.assertTrue((ROOT/row['generator']).is_file())
            else:
                self.assertEqual(row['source_kind'],'installed-freecad-asset')
                self.assertEqual(row['source_library_id'],'2400f95a-837b-4b8f-be69-239007f417e4')

    def test_all_toolbits_duplicate_archive_not_in_manifest(self):
        job=ROOT/'FreeCAD Jobber/FreeCAD_Imperial_Jobber_Drills_FIXED'
        all_bits={p.stem:p.read_bytes() for p in (job/'All_ToolBits').glob('*.fctb')}
        separate={p.stem:p.read_bytes() for name in ('Fractional','Number','Letter') for p in (job/name).glob('*.fctb')}
        self.assertEqual(all_bits,separate)

    def test_pcb_angle_is_preserved_and_named(self):
        c=next(c for c in load_manifest(ROOT/'libraries/manifest.json') if c.id.startswith('pcb-'))
        self.assertIn('118deg',c.name)
        for p in c.files():
            self.assertEqual(quantity(validate_tool(p).data['parameter']['TipAngle'],True),118)

    def test_full_inventory_engine_idempotency(self):
        collections=[c for c in load_manifest(ROOT/'libraries/manifest.json') if c.status=='available']
        with tempfile.TemporaryDirectory() as temp:
            assets=MockAssets();engine=Installer(assets,temp)
            first=engine.run(collections,False);second=engine.run(collections,False)
            self.assertEqual(first.tools_imported,357)
            self.assertEqual(first.conflicts,1)
            self.assertEqual(second.tools_skipped,357)
            self.assertEqual(second.conflicts,1)
            self.assertFalse(first.errors+second.errors)

    def test_explicit_distinct_policy_installs_full_inventory(self):
        collections=[c for c in load_manifest(ROOT/'libraries/manifest.json') if c.status=='available']
        with tempfile.TemporaryDirectory() as temp:
            assets=MockAssets();engine=Installer(assets,temp)
            first=engine.run(collections,False,equivalent_policy='distinct')
            second=engine.run(collections,False,equivalent_policy='distinct')
            self.assertEqual(first.tools_imported,358)
            self.assertEqual(second.tools_skipped,358)
            self.assertFalse(first.errors+second.errors)

    def test_path_containment_and_schema(self):
        original=read_json((ROOT/'libraries/manifest.json').read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'manifest.json'
            for directory in ('../outside','/absolute','C:/tools','C:\\tools','foo\\bar','.'):
                data=copy.deepcopy(original);data['collections'][0]['directory']=directory
                path.write_text(json.dumps(data))
                with self.subTest(directory=directory),self.assertRaises(ManifestError):load_manifest(path)
            for key,value in [('id','UPPER ID'),('expected_count',True),('source',{}),('compatible_versions',['1.0.x'])]:
                data=copy.deepcopy(original);data['collections'][0][key]=value;path.write_text(json.dumps(data))
                with self.subTest(key=key),self.assertRaises(ManifestError):load_manifest(path)

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'inside').mkdir();(base/'outside.fctb').write_text('{}')
            try:(base/'inside/escape.fctb').symlink_to(base/'outside.fctb')
            except OSError:self.skipTest('symlinks unavailable')
            c=Collection('x','x','drills',base/'inside',1,{},'metric',{},('1.1.x',),'available')
            with self.assertRaises(ManifestError):c.files()

class CatalogConsistencyTests(unittest.TestCase):
    def test_jobber_csv_matches_definitions(self):
        import csv
        from decimal import Decimal
        path=ROOT/'FreeCAD Jobber/FreeCAD_Imperial_Jobber_Drills_FIXED'
        with (path/'Drill_Index.csv').open(newline='',encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),118)
        for row in rows:
            data=read_json((path/'All_ToolBits'/row['New filename']).read_bytes())
            for column,key in [('Diameter','Diameter'),('Flute length','CuttingEdgeHeight'),('Overall length','Length')]:
                self.assertEqual(quantity(row[column]),quantity(data['parameter'][key]))

    def test_harvey_csv_transcription_and_proxy(self):
        import csv
        path=ROOT/'FreeCAD_Harvey_Imperial_Internal_Threads_Through_Half_Inch_FIXED'
        with (path/'Harvey_Imperial_Tool_Index.csv').open(newline='',encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),15)
        for row in rows:
            data=read_json((path/'ToolBits'/row['FreeCAD file']).read_bytes())
            for column,key in [('Cutter diameter (in)','Diameter'),('Neck diameter (in)','NeckDiameter'),('Max threading depth (in)','NeckLength'),('Shank diameter (in)','ShankDiameter'),('Overall length (in)','Length')]:
                self.assertEqual(quantity(row[column]+' in'),quantity(data['parameter'][key]))

    def test_pcb_csv_matches_without_changing_assumed_angle(self):
        import csv
        path=ROOT/'FreeCAD_PCB_Micro_Drills_0p1_to_3p175mm'
        with (path/'Tool_Index.csv').open(newline='',encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),36)
        for row in rows:
            data=read_json((path/'ToolBits'/(row['uuid']+'.fctb')).read_bytes())
            for column,key in [('diameter_mm','Diameter'),('flute_length_mm','CuttingEdgeHeight'),('overall_length_mm','Length')]:
                self.assertEqual(quantity(row[column]),quantity(data['parameter'][key]))
            self.assertIn('assumed',row['tip_angle_deg'])


class RecoveredMetricTests(unittest.TestCase):
    def test_metric_inventory_and_parameters(self):
        from decimal import Decimal
        collection=next(c for c in load_manifest(ROOT/'libraries/manifest.json') if c.id=='jobber-metric-118')
        self.assertEqual(collection.availability(),(True,121))
        tools=[validate_tool(p,'drills') for p in collection.files()]
        self.assertEqual(sorted(quantity(t.data['parameter']['Diameter']) for t in tools),
                         [Decimal('1.0')+Decimal('0.1')*n for n in range(121)])
        for tool in tools:
            self.assertEqual(quantity(tool.data['parameter']['TipAngle'],True),118)
            self.assertEqual(tool.data['parameter']['Flutes'],2)
            self.assertEqual(tool.data['parameter']['Material'],'HSS')

    def test_recovered_catalog_snapshot_and_hashes(self):
        import csv
        snapshot=ROOT/'docs/source-catalogs/metric-installed'
        data=read_json((snapshot/'Jobber_Metric_Drills.fctl').read_bytes())
        self.assertEqual(len(data['tools']),121)
        with (snapshot/'Metric_Drill_Index.csv').open(newline='',encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),121)
        entries={row['path']:row['nr'] for row in data['tools']}
        for row in rows:
            tool=validate_tool(ROOT/'libraries/drills/metric-118'/row['File'],'drills')
            self.assertEqual(tool.id,row['UUID'])
            self.assertEqual(tool.data['name'],row['Name'])
            self.assertEqual(entries[row['File']],int(row['Source tool number']))
            for column,key in [('Diameter','Diameter'),('Cutting edge height','CuttingEdgeHeight'),
                               ('Overall length','Length')]:
                self.assertEqual(quantity(row[column]),quantity(tool.data['parameter'][key]))
        inventory=read_json((ROOT/'docs/source-inventory.json').read_bytes())
        recovered=inventory['recovered_collections'][0]
        self.assertEqual(recovered['snapshot_sha256'],hashlib.sha256((ROOT/recovered['snapshot']).read_bytes()).hexdigest())
