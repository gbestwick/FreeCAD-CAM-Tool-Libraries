"""Offline generation of visually reviewed PTD R18 #61–#80 drills.

Nominal dimensions are transcribed, never interpolated. Existing tool files
are preflighted and never overwritten. Does not access FreeCAD user assets.
"""
import argparse
import csv
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import re
import uuid

NAMESPACE = uuid.UUID('da1dce97-b562-50fb-85c0-c975b79abb67')
FIELDS = ('number', 'part_number', 'diameter_in', 'flute_length_in', 'overall_length_in',
          'source_url', 'source_sha256', 'source_locator', 'review_status')


def inches(text):
    if not re.fullmatch(r'\d+(?:\.\d+)?|\d+/\d+|\d+ \d+/\d+', text):
        raise ValueError('Expected explicit decimal or fraction inches')
    value = sum((Fraction(piece) for piece in text.split()), Fraction(0))
    if value <= 0:
        raise ValueError('Dimension must be positive')
    return Decimal(value.numerator) / Decimal(value.denominator)


def reviewed_rows(path):
    with Path(path).open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError('Unexpected reviewed CSV header')
        rows = list(reader)
    seen = set()
    for row in rows:
        if None in row or any(not isinstance(v,str) or not v.strip() for v in row.values()):
            raise ValueError('Missing or extra CSV values')
        if not row['number'].isdigit():
            raise ValueError('Invalid drill number')
        number = int(row['number'])
        if number not in range(61,81) or number in seen or row['part_number'] != f'018{number:03d}':
            raise ValueError('Unexpected or repeated R18 part/number')
        dims = [inches(row[k]) for k in ('diameter_in','flute_length_in','overall_length_in')]
        if not dims[0] < dims[1] < dims[2]:
            raise ValueError('Invalid dimensional relationships')
        if row['review_status'] != 'visually-transcribed' or not row['source_url'].startswith('https://') or not re.fullmatch(r'[a-f0-9]{64}', row['source_sha256']):
            raise ValueError('Missing source review evidence')
        seen.add(number)
    if seen != set(range(61,81)):
        raise ValueError('Expected every numbered drill #61–#80 exactly once')
    return rows


def definition(row):
    def mm(key):
        return format(inches(row[key])*Decimal('25.4'),'f') + ' mm'
    return {'version':2, 'id':str(uuid.uuid5(NAMESPACE,'PTD/R18/'+row['part_number'])),
            'name':f"Drill #{row['number']} ({row['diameter_in']} in) - HSS Jobber 118deg [PTD R18 {row['part_number']}]",
            'shape':'drill.fcstd', 'shape-type':'Drill', 'attribute':{},
            'parameter':{'Diameter':mm('diameter_in'), 'CuttingEdgeHeight':mm('flute_length_in'),
                         'Length':mm('overall_length_in'), 'TipAngle':'118°', 'Flutes':2,
                         'Material':'HSS', 'Coating':'Steam Oxide'}}


def generate(catalog, output, check=False):
    output = Path(output)
    expected = {}
    for row in reviewed_rows(catalog):
        data = definition(row)
        expected[data['id']+'.fctb'] = (json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
    if output.is_symlink():
        raise ValueError('Refusing output directory symlink')
    # Existing #1–#60 files deliberately coexist in the same directory.
    for name, raw in expected.items():
        path = output/name
        if path.is_symlink() or (path.exists() and path.read_bytes() != raw):
            raise ValueError('Refusing to overwrite existing tool: '+str(path))
        if check and not path.is_file():
            raise ValueError('Missing generated tool: '+str(path))
    if not check:
        output.mkdir(parents=True,exist_ok=True)
        for name, raw in expected.items():
            path = output/name
            if not path.exists():
                with path.open('xb') as stream: stream.write(raw)
    return len(expected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    print(generate(args.catalog,args.output,args.check),'reviewed definitions')
