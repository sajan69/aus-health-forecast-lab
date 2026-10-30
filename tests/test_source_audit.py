import io
import unittest
import warnings
import zipfile
from pathlib import Path
import tempfile
from scripts.audit_source import AuditError, MAX_EXPANDED, workbook_inventory, xml, PublicLinks, summarize, acquire


def workbook():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Example" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c t="inlineStr"><is><t>Monthly example</t></is></c><c><f>1+1</f><v>2</v></c></row></sheetData></worksheet>')
    return out.getvalue()


class SourceAuditTests(unittest.TestCase):
    def test_inventory_never_evaluates_or_exposes_formula_cached_value(self):
        result = workbook_inventory(workbook())
        sheet = result['sheets'][0]
        self.assertEqual(sheet['preview'], [['Monthly example']])
        self.assertEqual(sheet['formula_cells'], 1)
        self.assertEqual(sheet['notes'], ['Monthly example'])

    def test_entity_and_alternative_encoding_rejected(self):
        for body in [b'<!DOCTYPE a [<!ENTITY x "expanded">]><a>&x;</a>', '<a/>'.encode('utf-16')]:
            with self.subTest(body=body), self.assertRaises(AuditError):
                xml(body)

    def test_duplicate_and_traversal_zip_members_rejected(self):
        for name in ['../outside.xml', '/absolute.xml']:
            out = io.BytesIO()
            with zipfile.ZipFile(out, 'w') as z:
                z.writestr(name, '<a/>')
            with self.subTest(name=name), self.assertRaises(AuditError):
                workbook_inventory(out.getvalue())
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as z, warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            z.writestr('duplicate.xml', '<a/>')
            z.writestr('duplicate.xml', '<a/>')
        with self.assertRaisesRegex(AuditError, 'member_limit_or_duplicate'):
            workbook_inventory(out.getvalue())

    def test_expansion_budget_precedes_xml_parsing(self):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('large.xml', b' ' * (MAX_EXPANDED + 1))
        with self.assertRaisesRegex(AuditError, 'expanded_limit'):
            workbook_inventory(out.getvalue())

    def test_link_inventory_is_data_not_fetch_instruction(self):
        p = PublicLinks()
        p.feed('<a href="/getmedia/example.xlsx">data</a><a href="javascript:download()">bad</a>')
        self.assertEqual(p.links, {'https://www.aihw.gov.au/getmedia/example.xlsx'})

    def test_csv_inventory_preserves_quarter_label_without_exposing_metrics(self):
        body = b'Facility/HHS Code,Last Month in QTR,Triage_Category,Number of Attendances\r\nX,Sep-25,All,123\r\n'
        result = summarize('example.csv', body)
        self.assertEqual(result['periods'], ['Sep-25'])
        self.assertEqual(result['rows'], 1)
        self.assertNotIn('123', str(result))
        with self.assertRaises(AuditError):
            summarize('example.csv', b'a,a\n1,2\n')
        with self.assertRaises(AuditError):
            summarize('example.csv', b'a,b\n1\n')

    def test_existing_directory_refused_before_any_network(self):
        with tempfile.TemporaryDirectory() as d:
            sentinel = Path(d) / 'keep'
            sentinel.write_text('unchanged')
            with self.assertRaises(FileExistsError):
                acquire(Path(d), catalog_only=True)
            self.assertEqual(sentinel.read_text(), 'unchanged')


if __name__ == '__main__':
    unittest.main()
