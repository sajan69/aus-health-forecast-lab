import io
from datetime import date
import unittest
import zipfile
from scripts.audit_source import AuditError
from scripts.project_carer import project


def fixture(change=None):
    cells = {'A3': '<c r="A3" t="inlineStr"><is><t>Date</t></is></c>',
             'B3': '<c r="B3" t="inlineStr"><is><t>All recipients</t></is></c>'}
    for i in range(177):
        r = i + 6
        serial = (date(2012 + i // 12, i % 12 + 1, 1) - date(1899, 12, 30)).days
        cells[f'A{r}'] = f'<c r="A{r}"><v>{serial}</v></c>'
        cells[f'B{r}'] = f'<c r="B{r}"><v>{i * 5}</v></c>'
    if change:
        change(cells)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Carer Payment" r:id="one"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="one" Target="worksheets/sheet.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row>' + ''.join(cells.values()) + '<c r="C6"><v>987654321</v></c></row></sheetData></worksheet>')
    return out.getvalue()


class CarerTests(unittest.TestCase):
    def test_national_projection_retains_zero_excludes_demographics_and_hashes(self):
        p = project(fixture())
        self.assertEqual(len(p['rows']), 177)
        self.assertEqual(p['rows'][0], {'month': '2012-01', 'published_recipients': 0})
        self.assertEqual(p['rows'][-1]['month'], '2026-09')
        self.assertNotIn('987654321', str(p))
        self.assertEqual(p, project(fixture()))

    def test_missing_suppressed_and_unreviewed_rounding_fail_without_zero_fill(self):
        for value in ['', 'N/A', '<5', '-5', '6']:
            with self.subTest(value=value), self.assertRaises(AuditError):
                project(fixture(lambda c: c.update(B6=f'<c r="B6"><v>{value.replace("<", "&lt;")}</v></c>')))

    def test_formula_and_header_change_refused(self):
        for ref, value in [('B6', '<c r="B6"><f>1+1</f><v>0</v></c>'),
                           ('B3', '<c r="B3" t="inlineStr"><is><t>Females</t></is></c>')]:
            with self.subTest(ref=ref), self.assertRaises(AuditError):
                project(fixture(lambda c: c.update({ref: value})))

    def test_gap_duplicate_month_and_extra_release_rows_refused(self):
        for change in [lambda c: c.pop('A7'),
                       lambda c: c.update(A7=c['A6'].replace('A6', 'A7')),
                       lambda c: c.update(A183='<c r="A183"><v>46300</v></c>')]:
            with self.assertRaises(AuditError):
                project(fixture(change))
