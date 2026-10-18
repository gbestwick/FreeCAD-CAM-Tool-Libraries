"""Generate the reviewed DESKAR 2023 p115 metric flat endmill table.

Offline developer utility. No interpolation, unit substitution, manufacturer
SKU invention, or changes to installed FreeCAD assets. CSV dimensions are mm.
"""
import argparse
import csv
from decimal import Decimal
import json
from pathlib import Path
import re
import uuid

NAMESPACE = uuid.UUID('d16bce8f-cd18-5dc7-84b1-d10d038629ae')
FIELDS = ('catalog_model', 'cutting_diameter_mm', 'shank_diameter_mm',
          'cutting_length_mm', 'overall_length_mm', 'flute_options', 'material',
          'review_status', 'source_url', 'source_sha256', 'source_locator')
FAMILY = '2023-p115-hrc50-flat'
DIRECTORIES = {n: f'deskar-hrc50-metric-{n}f' for n in (2, 4)}


def reviewed_rows(path):
    with Path(path).open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError('CSV header does not match the reviewed table schema')
        rows = list(reader)
    if not rows:
        raise ValueError('Empty source catalog')
    seen = set()
    for number, row in enumerate(rows, 2):
        if None in row or any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError(f'Row {number}: missing or extra values')
        model = row['catalog_model']
        if model in seen or not re.fullmatch(r'\d+(?:\.\d+)?(?:\*\d+(?:\.\d+)?){3}', model):
            raise ValueError(f'Row {number}: invalid or repeated catalog model')
        keys = ('cutting_diameter_mm', 'shank_diameter_mm', 'cutting_length_mm', 'overall_length_mm')
        for key in keys:
            if not re.fullmatch(r'\d+(?:\.\d+)?', row[key]) or Decimal(row[key]) <= 0:
                raise ValueError(f'Row {number}: invalid explicit mm dimension {key}')
        # The table's MODEL column explicitly repeats D1*D2*L1*L. Check the
        # transcription against it; do not derive unknown values from a SKU.
        if [Decimal(v) for v in model.split('*')] != [Decimal(row[k]) for k in keys]:
            raise ValueError(f'Row {number}: model and dimension columns disagree')
        if Decimal(row['cutting_length_mm']) >= Decimal(row['overall_length_mm']):
            raise ValueError(f'Row {number}: cutting length must be less than overall length')
        if row['flute_options'] != '2;4' or row['material'] != 'Carbide':
            raise ValueError(f'Row {number}: unsupported flute options or material')
        if row['review_status'] != 'visually-transcribed':
            raise ValueError(f'Row {number}: source not visually reviewed')
        if not row['source_url'].startswith('https://') or not re.fullmatch(r'[0-9a-f]{64}', row['source_sha256']):
            raise ValueError(f'Row {number}: missing source URL/hash evidence')
        seen.add(model)
    return rows


def definition(row, flutes):
    if type(flutes) is not int or flutes not in (2, 4):
        raise ValueError('Expected an explicit 2 or 4 flute option')
    # Catalog MODEL is a dimension reference, not a unique manufacturer SKU.
    identity = f"DESKAR/{FAMILY}/{row['catalog_model']}/{flutes}F"
    return {
        'version': 2, 'id': str(uuid.uuid5(NAMESPACE, identity)),
        'name': f"DESKAR HRC50 Flat {row['catalog_model']} mm | {flutes} Flute",
        'shape': 'endmill.fcstd', 'shape-type': 'Endmill',
        'parameter': {
            'Diameter': row['cutting_diameter_mm'] + ' mm',
            'ShankDiameter': row['shank_diameter_mm'] + ' mm',
            'CuttingEdgeHeight': row['cutting_length_mm'] + ' mm',
            'Length': row['overall_length_mm'] + ' mm',
            'Flutes': flutes, 'Material': row['material'],
        },
        'attribute': {},
    }


def generate(catalog, output, check=False):
    output = Path(output)
    rows = reviewed_rows(catalog)
    expected = {}
    for row in rows:
        for flutes, directory in DIRECTORIES.items():
            data = definition(row, flutes)
            relative = Path(directory) / (data['id'] + '.fctb')
            expected[relative] = (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('utf-8')
    # Preflight both collections before writing. Preserve modified outputs and
    # refuse stale tools. Other collections under the parent are not touched.
    if output.is_symlink():
        raise ValueError('Refusing output directory symlink')
    for directory in DIRECTORIES.values():
        target = output / directory
        if target.is_symlink():
            raise ValueError('Refusing collection directory symlink')
        for path in target.glob('*.fctb'):
            if path.relative_to(output) not in expected:
                raise ValueError('Unexpected/stale tool file: ' + str(path))
    for relative, payload in expected.items():
        path = output / relative
        if path.is_symlink():
            raise ValueError('Refusing tool symlink: ' + str(path))
        if path.exists() and path.read_bytes() != payload:
            raise ValueError('Refusing to overwrite modified tool: ' + str(path))
        if check and not path.is_file():
            raise ValueError('Missing generated tool: ' + str(path))
    if not check:
        for relative, payload in expected.items():
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                with path.open('xb') as stream:
                    stream.write(payload)
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('output', type=Path, help='Parent directory for both collections')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    count = generate(args.catalog, args.output, args.check)
    print(f'{"Checked" if args.check else "Generated"} {count} DESKAR definitions')


if __name__ == '__main__':
    main()
