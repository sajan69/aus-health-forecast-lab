"""Release-specific, bounded offline input; hashes identify bytes, not authority."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

ROW_HASH = '6a72d3c5d9f5dac939c7173d5fc883cff4a28f5732e203e71954beb0c58b6c2c'
RAW_HASH = 'af25df58fec196687935f950c1802640394dbe381ecada03fc387edb70b60d52'
REQUIRED = {'schema_version', 'source_release', 'series', 'geography', 'unit', 'time_basis',
            'rounding', 'population', 'raw_sha256', 'projection_sha256', 'rows'}
OPTIONAL = {'attribution', 'acquired_at', 'evidence'}


class ForecastError(ValueError):
    pass


@dataclass(frozen=True)
class Series:
    months: tuple[str, ...]
    values: tuple[int, ...]
    provenance: dict


def strict_json(body):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ForecastError('duplicate_json_key')
            d[k] = v
        return d
    def reject(_):
        raise ForecastError('unsupported_json_number')
    try:
        return json.loads(body.decode('utf-8-sig'), object_pairs_hook=pairs,
                          parse_constant=reject, parse_float=reject)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as e:
        raise ForecastError('invalid_json') from e


def load_series(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ForecastError('input_requires_regular_file')
    with path.open('rb') as f:
        body = f.read(256 * 1024 + 1)
    if len(body) > 256 * 1024:
        raise ForecastError('input_size_limit')
    d = strict_json(body)
    if not isinstance(d, dict) or not REQUIRED <= d.keys() or d.keys() - REQUIRED - OPTIONAL:
        raise ForecastError('input_schema')
    expected = {'source_release': 'DSS September 2026', 'series': 'Carer Payment',
                'geography': 'Australia', 'unit': 'published rounded recipient count',
                'time_basis': 'last Friday of month; workbook dates label reporting month',
                'rounding': 'nearest 5; source maps values 1..7 to 5; zero is actual zero',
                'population': 'current including zero-rate, or suspended, on Centrelink system'}
    if type(d['schema_version']) is not int or d['schema_version'] != 1 or any(d[k] != v for k, v in expected.items()):
        raise ForecastError('unreviewed_source_or_unit')
    for key in ('time_basis', 'rounding', 'population'):
        if not isinstance(d[key], str) or not 1 <= len(d[key]) <= 200 or any(ord(c) < 32 for c in d[key]):
            raise ForecastError('invalid_source_description')
    rows = d['rows']
    if not isinstance(rows, list) or len(rows) != 177:
        raise ForecastError('release_row_count')
    for i, row in enumerate(rows):
        month = f'{2012 + i // 12}-{i % 12 + 1:02}'
        if not isinstance(row, dict) or set(row) != {'month', 'published_recipients'} or row['month'] != month:
            raise ForecastError('month_gap_order_or_schema')
        v = row['published_recipients']
        if type(v) is not int or not 0 <= v <= 99_999_999 or v % 5:
            raise ForecastError('missing_or_invalid_count')
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if d['projection_sha256'] != digest or digest != ROW_HASH or d['raw_sha256'] != RAW_HASH:
        raise ForecastError('unreviewed_release_hash')
    # Optional annotations are retained only after an allowlisted shallow schema.
    allowed = {'attribution': {'publisher', 'title', 'release', 'source_url', 'catalog_url', 'license', 'license_url', 'changes', 'endorsement'},
               'evidence': {'commit', 'run_url'}}
    for key, keys in allowed.items():
        if key in d and (not isinstance(d[key], dict) or set(d[key]) != keys or
                        any(not isinstance(v, str) or len(v) > 1000 or any(ord(c) < 32 for c in v) for v in d[key].values())):
            raise ForecastError('annotation_schema')
    if 'acquired_at' in d:
        try:
            dt = datetime.fromisoformat(d['acquired_at'])
            if dt.utcoffset() is None or dt.year != 2026 or dt.month < 9:
                raise ValueError()
        except (ValueError, TypeError):
            raise ForecastError('invalid_acquisition_time') from None
    provenance = {k: v for k, v in d.items() if k != 'rows'}
    provenance['input_sha256'] = hashlib.sha256(body).hexdigest()
    return Series(tuple(r['month'] for r in rows), tuple(r['published_recipients'] for r in rows), provenance)


def write_report(path, report):
    payload = (json.dumps(report, allow_nan=False, ensure_ascii=True, indent=2) + '\n').encode()
    write_bytes(path, payload)


def write_bytes(path, payload):
    if len(payload) > 2 * 1024 * 1024:
        raise ForecastError('report_size_limit')
    # Serialize and cap before exclusive creation. A physical write failure may
    # leave an incomplete file. The parent directory must be trusted.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
        f.write(payload)
