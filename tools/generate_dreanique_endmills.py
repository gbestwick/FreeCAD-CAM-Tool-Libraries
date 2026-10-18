"""Generate FreeCAD tools from individually reviewed DREANIQUE catalog rows.

No dimensions are inferred from part numbers, neighboring sizes, or generic
ratios. This is an offline development utility, not an installer dependency.
The output directory is supplied explicitly; this utility does not enable
collections or alter FreeCAD assets.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import uuid

NAMESPACE = uuid.UUID('fe4ec464-3846-58ac-8f87-1b6ac0b0af29')
# Only families whose flat-end identity has been reviewed are accepted.
SERIES_FLUTES = {'P4E': '4'}
FIELDS = ('part_number', 'series', 'cutting_diameter_mm', 'cutting_length_mm',
          'shank_diameter_mm', 'overall_length_mm', 'flutes', 'material',
          'review_status', 'source_url', 'source_sha256', 'source_locator')


def reviewed_rows(path):
    """Reject incomplete or ambiguous input rather than fill missing values."""
    with Path(path).open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError('CSV header must exactly match the documented source schema')
        rows = list(reader)
    seen = set()
    for number, row in enumerate(rows, 2):
        if None in row or any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError(f'Row {number}: missing or extra values')
        part = row['part_number']
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]*', part) or part in seen:
            raise ValueError(f'Row {number}: invalid or repeated part number')
        if not re.fullmatch(r'[A-Z][A-Z0-9]*', row['series']) or not part.startswith(row['series'] + '-'):
            raise ValueError(f'Row {number}: inconsistent series')
        if row['review_status'] != 'visually-transcribed':
            raise ValueError(f'Row {number}: row has not passed visual source review')
        if not row['source_url'].startswith('https://') or not re.fullmatch(r'[0-9a-f]{64}', row['source_sha256']):
            raise ValueError(f'Row {number}: missing source URL/hash evidence')
        if row['series'] not in SERIES_FLUTES or row['flutes'] != SERIES_FLUTES[row['series']]:
            raise ValueError(f'Row {number}: unsupported series or inconsistent flute count')
        if row['material'] != 'Carbide' or row['flutes'] not in ('2', '4'):
            raise ValueError(f'Row {number}: expected explicit Carbide and 2 or 4 flutes')
        values = {}
        for key in ('cutting_diameter_mm', 'cutting_length_mm', 'shank_diameter_mm', 'overall_length_mm'):
            value = row[key]
            if not re.fullmatch(r'\d+(?:\.\d+)?', value):
                raise ValueError(f'Row {number}: {key} must be an explicit decimal in mm')
            try:
                values[key] = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError(f'Row {number}: invalid decimal') from exc
            if values[key] <= 0:
                raise ValueError(f'Row {number}: {key} must be positive')
        if values['cutting_length_mm'] >= values['overall_length_mm']:
            raise ValueError(f'Row {number}: cutting length must be less than overall length')
        seen.add(part)
    return rows


def definition(row):
    """UUID is tied to the manufacturer's part number, not mutable geometry."""
    ident = str(uuid.uuid5(NAMESPACE, 'DREANIQUE/' + row['part_number']))
    return {
        'version': 2,
        'id': ident,
        'name': f"DREANIQUE {row['part_number']} | {row['cutting_diameter_mm']} mm | {row['flutes']} Flute Carbide Flat Endmill",
        'shape': 'endmill.fcstd',
        'shape-type': 'Endmill',
        'parameter': {
            'Diameter': row['cutting_diameter_mm'] + ' mm',
            'CuttingEdgeHeight': row['cutting_length_mm'] + ' mm',
            'ShankDiameter': row['shank_diameter_mm'] + ' mm',
            'Length': row['overall_length_mm'] + ' mm',
            'Flutes': int(row['flutes']),
            'Material': row['material'],
        },
        'attribute': {},
    }


def generate(catalog, output, check=False):
    rows = reviewed_rows(catalog)
    output = Path(output)
    expected = {}
    for row in rows:
        data = definition(row)
        payload = (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
        expected[data['id'] + '.fctb'] = payload
    # Preflight every output before writing any file. Never replace a modified
    # definition, mix unrelated tools into the directory, or delete old files.
    if output.exists():
        extra = {p.name for p in output.glob('*.fctb')} - expected.keys()
        if extra:
            raise ValueError('Unrelated/stale tool files in output: ' + ', '.join(sorted(extra)))
    for name, payload in expected.items():
        path = output / name
        if path.is_symlink():
            raise ValueError('Refusing output symlink: ' + str(path))
        if path.exists() and path.read_bytes() != payload:
            raise ValueError('Refusing to overwrite a different definition: ' + str(path))
        if check and not path.is_file():
            raise ValueError('Missing generated definition: ' + str(path))
    if not check:
        output.mkdir(parents=True, exist_ok=True)
        for name, payload in expected.items():
            path = output / name
            if not path.exists():
                with path.open('xb') as stream:
                    stream.write(payload)
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--check', action='store_true', help='Check deterministic output without writing')
    args = parser.parse_args()
    count = generate(args.catalog, args.output, args.check)
    print(f'{"Checked" if args.check else "Generated"} {count} reviewed tool definitions in {args.output}')


if __name__ == '__main__':
    main()
