"""Internal adversarial rendering fixture; not a user-input endpoint."""
import json
from pathlib import Path
from aus_health_forecast.contract import load_series,write_bytes
from aus_health_forecast.reports import html_report
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'forecast-artifacts/evaluation.json').read_text())
d['warnings'].append('<img src=x onerror=alert(1)><script>alert(1)</script>')
write_bytes(root/'forecast-artifacts/probe.html',html_report(load_series(root/'examples/carer-national-sep2026.json'),d).encode())
