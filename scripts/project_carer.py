"""Project only published national Carer Payment totals from the reviewed release."""
from datetime import date, timedelta
import hashlib
import io
import json
import posixpath
import re
import zipfile

from .audit_source import AuditError, NS, workbook_inventory, xml


def project(body):
    # Validate archive/member/XML budgets before reading selected cells.
    workbook_inventory(body)
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        wb = xml(z.read('xl/workbook.xml'))
        props = wb.find('s:workbookPr', NS)
        if props is not None and props.get('date1904', '0') not in ('0', 'false'):
            raise AuditError('unsupported_date_system')
        sheets = [s for s in wb.findall('s:sheets/s:sheet', NS) if s.get('name') == 'Carer Payment']
        if len(sheets) != 1:
            raise AuditError('carer_sheet_missing_or_duplicate')
        rel = sheets[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        targets = [r.get('Target') for r in xml(z.read('xl/_rels/workbook.xml.rels'))
                   if r.get('Id') == rel and r.get('TargetMode') != 'External']
        if len(targets) != 1:
            raise AuditError('carer_sheet_relationship')
        member = targets[0].lstrip('/') if targets[0].startswith('/') else posixpath.normpath('xl/' + targets[0])
        if not member.startswith('xl/worksheets/'):
            raise AuditError('carer_sheet_relationship')
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(x.itertext()) for x in xml(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        values = {}
        for row in xml(z.read(member)).findall('s:sheetData/s:row', NS):
            for c in row.findall('s:c', NS):
                ref = c.get('r', '')
                if not re.fullmatch(r'[AB][1-9][0-9]{0,3}', ref):
                    continue
                if ref in values or c.find('s:f', NS) is not None:
                    raise AuditError('duplicate_or_formula_target')
                v = c.findtext('s:v', '', NS)
                if c.get('t') == 's':
                    if not re.fullmatch(r'0|[1-9][0-9]*', v) or int(v) >= len(shared):
                        raise AuditError('invalid_shared_string')
                    v = shared[int(v)]
                elif c.get('t') == 'inlineStr':
                    node = c.find('s:is', NS)
                    v = ''.join(node.itertext()) if node is not None else ''
                elif c.get('t') not in (None, 'n'):
                    raise AuditError('unsupported_target_type')
                values[ref] = v
        if values.get('A3') != 'Date' or values.get('B3') != 'All recipients':
            raise AuditError('unreviewed_total_header')
        output = []
        for i in range(177):
            row = i + 6
            serial, count = values.get(f'A{row}', ''), values.get(f'B{row}', '')
            if not re.fullmatch(r'[0-9]{5}', serial) or not re.fullmatch(r'0|[1-9][0-9]{0,7}', count):
                raise AuditError('missing_or_invalid_total')
            observed = date(1899, 12, 30) + timedelta(days=int(serial))
            year, month = 2012 + i // 12, i % 12 + 1
            if observed != date(year, month, 1):
                raise AuditError('noncontinuous_month_labels')
            if int(count) % 5:
                raise AuditError('unreviewed_rounding')
            output.append({'month': observed.strftime('%Y-%m'), 'published_recipients': int(count)})
        if any(v and int(k[1:]) > 182 for k, v in values.items()):
            raise AuditError('unexpected_additional_target_rows')
    canonical = json.dumps(output, sort_keys=True, separators=(',', ':')).encode()
    return {'schema_version': 1, 'source_release': 'DSS September 2026',
            'series': 'Carer Payment', 'geography': 'Australia',
            'unit': 'published rounded recipient count',
            'time_basis': 'last Friday of month; workbook dates label reporting month',
            'rounding': 'nearest 5; source maps values 1..7 to 5; zero is actual zero',
            'population': 'current including zero-rate, or suspended, on Centrelink system',
            'raw_sha256': hashlib.sha256(body).hexdigest(),
            'projection_sha256': hashlib.sha256(canonical).hexdigest(), 'rows': output}
