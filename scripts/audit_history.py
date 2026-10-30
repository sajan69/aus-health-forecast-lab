"""Inspect published Queensland ED history without joining reporting regimes."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from uuid import UUID

from .audit_source import AuditError, NoRedirect, MAX_DOWNLOAD, QLD_FIELDS, workbook_inventory

ROOT = 'https://www.data.qld.gov.au'
SLUGS = ('emergency-departments-quarterly-data', 'emergency-departments-pre-oct-20')
MONTHS = {'March': 3, 'June': 6, 'September': 9, 'December': 12}
SHORT_MONTHS = {'Mar': 3, 'Jun': 6, 'Sep': 9, 'Dec': 12}
DESCRIPTION = ROOT + '/dataset/aa3844e0-1b00-4f7b-be91-ef9fb7592c65/resource/492bb29f-bc29-4cda-ad2e-a7ea747de079/download/ed_website_descriptions.xlsx'


def strict_json(body):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise AuditError('duplicate_json_key')
            result[k] = v
        return result
    def invalid(value):
        raise AuditError('nonfinite_json_number')
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise AuditError('nonfinite_json_number')
        return number
    return json.loads(body.decode('utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=invalid, parse_float=finite)


def resource_summary(data):
    if data.get('success') is not True or not isinstance(data.get('result'), dict):
        raise AuditError('catalog_failed')
    result = data['result']
    if result.get('license_id') != 'CC-BY-4.0':
        raise AuditError('unreviewed_license')
    resources = result.get('resources')
    if not isinstance(resources, list) or len(resources) > 150:
        raise AuditError('catalog_limit')
    seen, output = set(), []
    for r in resources:
        rid = str(UUID(r['id']))
        if rid != r['id'] or rid in seen:
            raise AuditError('duplicate_or_invalid_resource')
        seen.add(rid)
        output.append({k: r.get(k) for k in ('id', 'name', 'format', 'datastore_active')})
    return {'title': result.get('title'), 'license_id': result['license_id'],
            'notes': result.get('notes'), 'resources': output}


def quarter_resource(resource):
    match = re.fullmatch(r'(March|June|September|December) (20\d{2}) - Emergency Department Open [Dd]ata', resource['name'] or '')
    if not match:
        return None
    return f'{match[2]}-{MONTHS[match[1]]:02d}'


def parse_quarter(value):
    if not isinstance(value, str):
        raise AuditError('invalid_quarter')
    m = re.fullmatch(r'(Mar|Jun|Sep|Dec)-(\d{2})', value)
    if not m:
        raise AuditError('invalid_quarter')
    return f'20{m[2]}-{SHORT_MONTHS[m[1]]:02d}'


def observed_number(value):
    """Lexical classification only; does not establish source measure semantics."""
    if not isinstance(value, str) or len(value) > 64:
        raise AuditError('invalid_measure_text')
    v = value.strip()
    if re.fullmatch(r'0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+', v):
        number = int(v.replace(',', ''))
        if number > 100_000_000:
            raise AuditError('measure_limit')
        return number, 'numeric_text'
    return None, 'blank' if not v else 'non_numeric_text'


def inspect_table(data, expected_quarter):
    if data.get('success') is not True:
        raise AuditError('table_failed')
    result = data['result']
    fields = result['fields']
    if len(fields) != len(QLD_FIELDS) or {f['id'] for f in fields} != QLD_FIELDS:
        raise AuditError('unreviewed_table_schema')
    records = result['records']
    if not isinstance(records, list) or len(records) > 1000 or type(result.get('total')) is not int:
        raise AuditError('table_limit')
    if result['total'] != len(records):
        raise AuditError('incomplete_page')
    selected, all_keys, categories = {}, set(), Counter()
    for r in records:
        if not isinstance(r, dict) or set(r) != QLD_FIELDS:
            raise AuditError('unreviewed_record_fields')
        quarter = parse_quarter(r['Last Month in QTR'])
        if quarter != expected_quarter:
            raise AuditError('resource_period_mismatch')
        code, label, triage = r['Facility/HHS Code'], r['Facility/HHS Desc'], r['Triage_Category']
        if not isinstance(code, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', code):
            raise AuditError('invalid_entity_code')
        if not isinstance(label, str) or not 1 <= len(label) <= 200 or any(ord(c) < 32 for c in label):
            raise AuditError('invalid_entity_label')
        if triage not in {'1', '2', '3', '4', '5', 'ALL'}:
            raise AuditError('unreviewed_triage')
        key = (code, triage)
        if key in all_keys:
            raise AuditError('duplicate_entity_triage')
        all_keys.add(key)
        categories[triage] += 1
        if triage != 'ALL':
            continue
        value, status = observed_number(r['Number of Attendances'])
        row = {'quarter': quarter, 'entity_code': code, 'entity_label': label,
               'observed_numeric_text': value, 'value_status': status}
        if code in selected:
            raise AuditError('duplicate_all_row')
        selected[code] = row
    return {'quarter': expected_quarter, 'reported_rows': len(records),
            'triage_rows': dict(sorted(categories.items())), 'all_rows': len(selected),
            'value_status_counts': dict(Counter(x['value_status'] for x in selected.values())),
            'entities': {code: r['entity_label'] for code, r in sorted(selected.items())}}, list(selected.values())


class Reader:
    def __init__(self, out):
        out.mkdir(mode=0o700, exist_ok=False)
        self.out, self.requests, self.bytes = out, [], 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def read(self, url, name, parser):
        # Callers use only the fixed catalogues, fixed description and UUID-only
        # DataStore URLs. Catalogue URL fields are never followed.
        if len(self.requests) >= 25:
            raise AuditError('request_budget')
        remaining = 24 * 1024 * 1024 - self.bytes
        if remaining <= 0:
            raise AuditError('byte_budget')
        record = {'url': url, 'requested_at': datetime.now(timezone.utc).isoformat()}
        self.requests.append(record)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'aus-health-forecast-lab-history-audit/0.1'})
            with self.opener.open(req, timeout=20) as response:
                record['http_status'] = response.status
                if response.status != 200:
                    raise AuditError('unexpected_status')
                body = response.read(min(MAX_DOWNLOAD, remaining) + 1)
            self.bytes += len(body)
            if len(body) > MAX_DOWNLOAD or self.bytes > 24 * 1024 * 1024:
                raise AuditError('byte_budget')
            record.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                          acquired_at=datetime.now(timezone.utc).isoformat())
            result = parser(body)
            with os.fdopen(os.open(self.out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
                f.write(body)
            record['status'] = 'inspected'
            return result
        except urllib.error.HTTPError as e:
            record.update(status='unavailable', http_status=e.code)
        except (OSError, ValueError, KeyError, TypeError) as e:
            record.update(status='refused', reason=str(e) if isinstance(e, AuditError) else type(e).__name__)
        return None


def acquire(out):
    reader = Reader(out)
    catalogs = []
    for slug in SLUGS:
        value = reader.read(ROOT + '/api/3/action/package_show?id=' + slug,
                            slug + '.json', lambda b: resource_summary(strict_json(b)))
        catalogs.append(value)
    description = reader.read(DESCRIPTION, 'quarterly-description.xlsx', workbook_inventory)
    # Legacy definitions are available through their expressly published API.
    legacy_definition = reader.read(ROOT + '/api/3/action/datastore_search?resource_id=0b85e426-a80c-4397-89a9-e8040cee48e5&limit=100',
                                    'legacy-definition.json', strict_json)
    summaries, projected, unavailable = [], [], []
    if catalogs[0]:
        dated = [(quarter_resource(r), r) for r in catalogs[0]['resources']]
        dated = sorted(((q, r) for q, r in dated if q and '2020-12' <= q <= '2025-09'), key=lambda pair: pair[0])
        if len(dated) > 20 or len({q for q, _ in dated}) != len(dated):
            raise AuditError('quarter_catalog_conflict')
        for quarter, resource in dated:
            if resource['datastore_active'] is not True:
                unavailable.append({'quarter': quarter, 'reason': 'no_published_datastore', 'resource_id': resource['id']})
                continue
            result = reader.read(ROOT + '/api/3/action/datastore_search?resource_id=' + resource['id'] + '&limit=1000',
                                 quarter + '.json', lambda b, q=quarter: inspect_table(strict_json(b), q))
            if result:
                summary, rows = result
                summaries.append(summary)
                projected.extend(rows)
            else:
                unavailable.append({'quarter': quarter, 'reason': 'table_not_accepted', 'resource_id': resource['id']})
    common = sorted(set.intersection(*(set(s['entities']) for s in summaries))) if summaries else []
    report = {'schema_version': 1, 'purpose': 'history_feasibility_not_forecast',
              'completed_at': datetime.now(timezone.utc).isoformat(), 'catalogs': catalogs,
              'quarterly_description': description, 'legacy_definition': legacy_definition,
              'quarter_tables': summaries, 'unavailable_quarters': unavailable,
              'common_entity_codes': common, 'requests': reader.requests,
              'model_ready': False, 'limitation': 'Lexical values and coverage inventory do not establish compatible measure definitions or a valid forecasting target.'}
    for name, value in [('history-inventory.json', report), ('projected-all-rows.json', projected)]:
        with os.fdopen(os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as f:
            json.dump(value, f, allow_nan=False, ensure_ascii=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    report = acquire(args.out)
    print('HISTORY_INVENTORY=' + json.dumps(report, ensure_ascii=True, allow_nan=False))
    if any(c is None for c in report['catalogs']):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
