"""Catalog-generation safeguards; does not infer or verify manufacturer data."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from freecad_cam_libraries.validation import validate_tool, quantity

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dreanique_generator', ROOT/'tools/generate_dreanique_endmills.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
CATALOG = ROOT/'docs/source-catalogs/dreanique/endmills-reviewed.csv'


class EndmillGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base/'tools'

    def modified_catalog(self, **changes):
        rows = generator.reviewed_rows(CATALOG)
        rows[0].update(changes)
        path = self.base/'input.csv'
        with path.open('w',newline='',encoding='utf-8') as stream:
            writer = csv.DictWriter(stream,fieldnames=generator.FIELDS)
            writer.writeheader();writer.writerows(rows)
        return path

    def test_reviewed_examples_have_exact_dimensions_and_native_schema(self):
        self.assertEqual(generator.generate(CATALOG,self.output),2)
        tools=[validate_tool(p,'endmills') for p in self.output.glob('*.fctb')]
        by_diameter={quantity(t.data['parameter']['Diameter']):t for t in tools}
        for diameter,cutting in ((1,3),(2,6)):
            params=by_diameter[diameter].data['parameter']
            self.assertEqual(quantity(params['CuttingEdgeHeight']),cutting)
            self.assertEqual(quantity(params['ShankDiameter']),4)
            self.assertEqual(quantity(params['Length']),50)
            self.assertEqual(params['Flutes'],4)
            self.assertEqual(params['Material'],'Carbide')

    def test_repeat_and_check_preserve_exact_bytes(self):
        generator.generate(CATALOG,self.output)
        before={p.name:p.read_bytes() for p in self.output.glob('*.fctb')}
        generator.generate(CATALOG,self.output)
        generator.generate(CATALOG,self.output,check=True)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.glob('*.fctb')})

    def test_unreviewed_rows_do_not_generate(self):
        path=self.modified_catalog(review_status='search-snippet-only')
        with self.assertRaises(ValueError):generator.generate(path,self.output)
        self.assertFalse(self.output.exists())

    def test_missing_or_invalid_dimensions_do_not_generate(self):
        for changes in ({'cutting_length_mm':''},{'overall_length_mm':'unknown'},
                        {'shank_diameter_mm':'0'},{'cutting_length_mm':'50'},
                        {'cutting_diameter_mm':'1/8 in'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                generator.generate(self.modified_catalog(**changes),self.output)
        self.assertFalse(self.output.exists())

    def test_mismatched_family_or_flutes_do_not_generate(self):
        for changes in ({'flutes':'2'},{'series':'T4B','part_number':'T4B-R1'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                generator.generate(self.modified_catalog(**changes),self.output)

    def test_customized_output_not_overwritten_or_partially_generated(self):
        self.output.mkdir()
        row=generator.reviewed_rows(CATALOG)[1]
        ident=generator.definition(row)['id']
        path=self.output/(ident+'.fctb')
        path.write_text('{"custom": true}')
        with self.assertRaises(ValueError):generator.generate(CATALOG,self.output)
        self.assertEqual(len(list(self.output.glob('*.fctb'))),1)
        self.assertEqual(json.loads(path.read_text()),{'custom':True})

    def test_check_mode_never_creates_missing_output(self):
        with self.assertRaises(ValueError):generator.generate(CATALOG,self.output,check=True)
        self.assertFalse(self.output.exists())

    def test_identity_stays_stable_when_reviewed_geometry_changes(self):
        row=generator.reviewed_rows(CATALOG)[0]
        changed=dict(row,cutting_length_mm='4')
        self.assertEqual(generator.definition(row)['id'],generator.definition(changed)['id'])
        self.assertNotEqual(generator.definition(row)['parameter'],generator.definition(changed)['parameter'])
