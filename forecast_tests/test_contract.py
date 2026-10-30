import copy
import json
from pathlib import Path
import tempfile
import unittest
from aus_health_forecast.contract import ForecastError, load_series, strict_json, write_report
from aus_health_forecast.protocol import origins

SOURCE = Path(__file__).resolve().parents[1] / 'examples/carer-national-sep2026.json'


class ContractTests(unittest.TestCase):
    def changed(self, fn):
        d = json.loads(SOURCE.read_text())
        fn(d)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'in.json'
            p.write_text(json.dumps(d))
            with self.assertRaises(ForecastError):
                load_series(p)

    def test_real_release_hash_and_units(self):
        s = load_series(SOURCE)
        self.assertEqual(len(s.values), 177)
        self.assertEqual(s.months[-1], '2026-09')
        self.assertEqual(s.values[0], 197435)

    def test_missing_counts_types_order_and_extra_fields_refused(self):
        for field, value in [('published_recipients', None), ('published_recipients', True),
                             ('published_recipients', -5), ('published_recipients', 6),
                             ('month', '2012-02'), ('patient_name', 'no')]:
            with self.subTest(field=field, value=value):
                self.changed(lambda d: d['rows'][0].update({field: value}))

    def test_changed_values_even_with_recomputed_hash_require_release_review(self):
        import hashlib
        def change(d):
            d['rows'][0]['published_recipients'] += 5
            d['projection_sha256'] = hashlib.sha256(json.dumps(d['rows'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.changed(change)

    def test_nonfinite_duplicate_and_float_json_refused(self):
        for b in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'{"a":1.0}']:
            with self.subTest(body=b), self.assertRaises(ForecastError):
                strict_json(b)

    def test_input_cap_and_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'x'
            p.write_bytes(b' ' * (256*1024+1))
            with self.assertRaises(ForecastError): load_series(p)
            q = Path(td)/'link'
            q.symlink_to(SOURCE)
            with self.assertRaises(ForecastError): load_series(q)

    def test_output_exclusive_cap_and_nonfinite_before_creation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'out'
            write_report(p, {'ok': True})
            before = p.read_bytes()
            with self.assertRaises(FileExistsError): write_report(p, {})
            self.assertEqual(p.read_bytes(), before)
            q = Path(td)/'q'
            for obj in [{'a': float('nan')}, {'a': 'x'*(2*1024*1024)}]:
                with self.assertRaises(ValueError): write_report(q, obj)
                self.assertFalse(q.exists())

    def test_split_targets_never_cross_development_boundary(self):
        self.assertEqual(len(origins('development')), 91)
        self.assertEqual(len(origins('holdout')), 22)
        self.assertTrue(all(n+h-1 < 153 for n in origins('development') for h in (1,2,3)))
        self.assertTrue(all(153 <= n+h-1 < 177 for n in origins('holdout') for h in (1,2,3)))
