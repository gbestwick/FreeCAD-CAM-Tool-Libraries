"""Checks source transcription consistency and reproducible catalog generation."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest
from freecad_cam_libraries.validation import validate_tool, quantity

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deskar_generator', ROOT/'tools/generate_deskar_endmills.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
CATALOG = ROOT/'docs/source-catalogs/deskar/endmills-reviewed.csv'


class DeskarGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base/'endmills'

    def changed(self, **changes):
        rows = generator.reviewed_rows(CATALOG)
        rows[0].update(changes)
        path = self.base/'changed.csv'
        with path.open('w',newline='') as stream:
            writer = csv.DictWriter(stream,fieldnames=generator.FIELDS)
            writer.writeheader();writer.writerows(rows)
        return path

    def test_all_reviewed_rows_match_production_and_validate(self):
        rows = generator.reviewed_rows(CATALOG)
        self.assertEqual(len(rows),34)
        self.assertEqual(generator.generate(CATALOG,ROOT/'libraries/endmills',check=True),68)
        self.assertEqual(generator.generate(CATALOG,self.output),68)
        for row in rows:
            for flutes, directory in generator.DIRECTORIES.items():
                data = generator.definition(row,flutes)
                path = self.output/directory/(data['id']+'.fctb')
                tool = validate_tool(path,'endmills')
                for param,col in [('Diameter','cutting_diameter_mm'),('ShankDiameter','shank_diameter_mm'),('CuttingEdgeHeight','cutting_length_mm'),('Length','overall_length_mm')]:
                    self.assertEqual(quantity(tool.data['parameter'][param]),float(row[col]))
                self.assertEqual(tool.data['parameter']['Flutes'],flutes)
                self.assertEqual(tool.data['parameter']['Material'],'Carbide')

    def test_same_diameter_variants_are_retained(self):
        rows = [r for r in generator.reviewed_rows(CATALOG) if r['cutting_diameter_mm']=='4']
        self.assertEqual({(r['shank_diameter_mm'],r['cutting_length_mm'],r['overall_length_mm']) for r in rows},
                         {('4','10','50'),('6','10','50'),('4','16','75'),('6','16','75'),('6','16','100')})
        ids={generator.definition(r,f)['id'] for r in rows for f in (2,4)}
        self.assertEqual(len(ids),10)

    def test_unreviewed_or_inconsistent_input_is_rejected_before_writes(self):
        for changes in ({'review_status':'snippet'}, {'flute_options':'3'}, {'cutting_length_mm':'99'},
                        {'shank_diameter_mm':''}, {'source_sha256':'unknown'}, {'material':'HSS'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                generator.generate(self.changed(**changes),self.output)
            self.assertFalse(self.output.exists())

    def test_repeat_is_byte_identical(self):
        generator.generate(CATALOG,self.output)
        before={p.relative_to(self.output):p.read_bytes() for p in self.output.rglob('*.fctb')}
        generator.generate(CATALOG,self.output)
        generator.generate(CATALOG,self.output,check=True)
        self.assertEqual(before,{p.relative_to(self.output):p.read_bytes() for p in self.output.rglob('*.fctb')})

    def test_customized_tool_blocks_both_collections_before_writes(self):
        row=generator.reviewed_rows(CATALOG)[-1]
        data=generator.definition(row,4)
        path=self.output/generator.DIRECTORIES[4]/(data['id']+'.fctb')
        path.parent.mkdir(parents=True);path.write_text('customized')
        with self.assertRaises(ValueError):generator.generate(CATALOG,self.output)
        self.assertEqual(list(self.output.rglob('*.fctb')),[path])
        self.assertEqual(path.read_text(),'customized')

    def test_check_never_creates_files(self):
        with self.assertRaises(ValueError):generator.generate(CATALOG,self.output,check=True)
        self.assertFalse(self.output.exists())

    def test_symlink_collection_rejected(self):
        other=self.base/'other';other.mkdir();self.output.mkdir()
        try:
            (self.output/generator.DIRECTORIES[2]).symlink_to(other,target_is_directory=True)
        except OSError:
            self.skipTest('symlink creation unavailable on this platform')
        with self.assertRaises(ValueError):generator.generate(CATALOG,self.output)
        self.assertEqual(list(other.iterdir()),[])
