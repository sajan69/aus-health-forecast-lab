import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EvaluationIntegrationTests(unittest.TestCase):
    def test_installed_cli_real_release_records_metrics_intervals_and_overwrite(self):
        source=Path(__file__).resolve().parents[1]/'examples/carer-national-sep2026.json'
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'report.json'
            args=[sys.executable,'-m','aus_health_forecast.cli','evaluate',str(source),'--out',str(output)]
            completed=subprocess.run(args,capture_output=True,text=True,timeout=120)
            self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
            d=json.loads(output.read_text())
            self.assertFalse(d['selection_uses_holdout'])
            self.assertEqual(len(d['records']['development']),1092)
            self.assertEqual(len(d['records']['holdout']),264)
            self.assertEqual(len(d['records']['selected_holdout_intervals']),66)
            for r in d['records']['holdout']:
                self.assertAlmostEqual(r['error'],r['prediction']-r['actual'])
                self.assertLess(r['origin'],r['target'])
                self.assertGreaterEqual(r['target'],'2024-10')
            for h in ('1','2','3'):
                rows=[r for r in d['records']['selected_holdout_intervals'] if str(r['horizon'])==h]
                metric=d['holdout'][d['selected_model']]['by_horizon'][h]
                self.assertEqual(metric['n'],22)
                self.assertAlmostEqual(metric['mae'],sum(abs(r['error']) for r in rows)/22)
                for level in ('0.8','0.95'):
                    covered=sum(r['intervals'][level]['lower']<=r['actual']<=r['intervals'][level]['upper'] for r in rows)
                    self.assertEqual(covered,d['holdout_intervals'][h][level]['covered'])
            from aus_health_forecast.contract import load_series
            from aus_health_forecast.reports import html_report,csv_report
            from html.parser import HTMLParser
            import csv,io
            d['source']['attribution']['title']='  ＝1+1'
            d['warnings'].append('<img src=x onerror=alert(1)><script>alert(1)</script>')
            page=html_report(load_series(source),d)
            class Tags(HTMLParser):
                def __init__(self): super().__init__(); self.tags=[]
                def handle_starttag(self,tag,attrs): self.tags.append(tag)
            parser=Tags(); parser.feed(page)
            self.assertNotIn('script',parser.tags)
            self.assertNotIn('img',parser.tags)
            self.assertIn('&lt;img',page)
            self.assertIn("default-src 'none'",page)
            rows=list(csv.reader(io.StringIO(csv_report(d))))
            self.assertEqual(len(rows),25)
            self.assertTrue(rows[1][12].startswith("'"))
            self.assertEqual(float(rows[1][6]),d['development']['last_value']['by_horizon']['1']['bias_prediction_minus_actual'])
            before=output.read_bytes()
            # Reject existing destinations before expensive computation too.
            denied=subprocess.run(args,capture_output=True,text=True,timeout=120)
            self.assertEqual(denied.returncode,2)
            self.assertEqual(output.read_bytes(),before)
