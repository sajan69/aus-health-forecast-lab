import copy
import json
import unittest
from scripts.audit_history import resource_summary, quarter_resource, parse_quarter, observed_number, inspect_table, strict_json
from scripts.audit_source import AuditError, QLD_FIELDS


def table():
    r = {k: '' for k in QLD_FIELDS}
    r.update({'_id': 1, 'Facility/HHS Code': 'X1', 'Facility/HHS Desc': 'Synthetic service',
              'Last Month in QTR': 'Sep-25', 'Triage_Category': 'ALL', 'Number of Attendances': '1,234'})
    return {'success': True, 'result': {'fields': [{'id': k} for k in sorted(QLD_FIELDS)],
                                      'records': [r], 'total': 1}}


class HistoryTests(unittest.TestCase):
    def test_periods_not_monthly_interpolated(self):
        self.assertEqual(parse_quarter('Sep-25'), '2025-09')
        self.assertEqual(quarter_resource({'name': 'September 2025 - Emergency Department Open data'}), '2025-09')
        self.assertIsNone(quarter_resource({'name': 'February 2020 - Emergency Department Summary 1'}))
        for v in ['Feb-20', 'Sep-2025', '', None]:
            with self.subTest(v=v), self.assertRaises(AuditError):
                parse_quarter(v)

    def test_null_and_suppression_not_zero(self):
        for v in ['', ' ', 'n.p.', '<5', '-', 'NaN', '1.5', '1,23']:
            self.assertIsNone(observed_number(v)[0])
        self.assertEqual(observed_number('0'), (0, 'numeric_text'))
        self.assertEqual(observed_number('1,234')[0], 1234)
        with self.assertRaises(AuditError):
            observed_number(0)

    def test_all_selected_without_adding_components(self):
        d = table()
        r = copy.deepcopy(d['result']['records'][0])
        r['Triage_Category'], r['Number of Attendances'] = '1', '20'
        d['result']['records'].append(r)
        d['result']['total'] = 2
        summary, rows = inspect_table(d, '2025-09')
        self.assertEqual(summary['all_rows'], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['observed_numeric_text'], 1234)

    def test_incomplete_wrong_period_and_duplicate_refused(self):
        for mode in ['incomplete', 'wrong_period', 'duplicate', 'new_field']:
            d = table()
            if mode == 'incomplete': d['result']['total'] = 2
            if mode == 'wrong_period': d['result']['records'][0]['Last Month in QTR'] = 'Jun-25'
            if mode == 'duplicate':
                d['result']['records'] *= 2
                d['result']['total'] = 2
            if mode == 'new_field': d['result']['records'][0]['patient_name'] = 'not accepted'
            with self.subTest(mode=mode), self.assertRaises(AuditError):
                inspect_table(d, '2025-09')

    def test_catalogue_licence_and_duplicate_ids(self):
        d = {'success': True, 'result': {'license_id': 'CC-BY-4.0', 'resources': []}}
        self.assertEqual(resource_summary(d)['resources'], [])
        d['result']['license_id'] = 'unspecified'
        with self.assertRaises(AuditError): resource_summary(d)
        d['result']['license_id'] = 'CC-BY-4.0'
        d['result']['resources'] = [{'id': '11111111-1111-4111-8111-111111111111'}] * 2
        with self.assertRaises(AuditError): resource_summary(d)

    def test_json_duplicates_and_nonfinite_refused(self):
        for s in ['{"a":1,"a":2}', '[NaN]', '[1e999]']:
            with self.subTest(s=s), self.assertRaises(AuditError): strict_json(s.encode())
        self.assertEqual(strict_json(b'[1.2]'), [1.2])


if __name__ == '__main__': unittest.main()
