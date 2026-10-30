"""Bounded static views: escaped HTML, no scripts or external assets."""
import base64
import csv
import hashlib
import html
import io
import json
import unicodedata

STYLE = '''body{font:16px system-ui,sans-serif;color:#153044;background:#f4f7f8;margin:0}main{max-width:1100px;margin:auto;padding:32px 20px}h1{font-size:2.4rem;line-height:1.1;max-width:800px}h2{margin-top:2rem}p{line-height:1.6}article,.notice{background:white;border:1px solid #d7e2e6;border-radius:12px;padding:20px;margin:18px 0}.notice{border-left:5px solid #be7923;background:#fff8ed}.eyebrow{color:#196b6d;font-weight:700;letter-spacing:.06em}.scroll{overflow-x:auto}table{border-collapse:collapse;min-width:650px;width:100%;font-size:.9rem}th,td{text-align:right;border-bottom:1px solid #d7e2e6;padding:12px}th:first-child,td:first-child{text-align:left}th{background:#edf3f4}svg{width:100%;height:auto;min-width:650px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem}li{margin:.8em 0;line-height:1.5}small{color:#435c69}@media(max-width:500px){main{padding:20px 12px}h1{font-size:1.9rem}article{padding:12px}}'''
NAMES = {'last_value':'Last value', 'seasonal_naive':'Seasonal naive',
         'damped_holt':'Damped Holt', 'ridge_change':'Ridge change'}


def esc(value):
    return html.escape(str(value), quote=True)


def chart(series, report):
    values=list(series.values[-24:])
    future=report['series_end_extrapolation']['points']
    bounds=[p['intervals']['0.95'][k] for p in future for k in ('lower','upper')]
    low,high=min(values+bounds),max(values+bounds)
    span=max(high-low,1)
    low-=span*.1; high+=span*.1
    def x(i):return 60+i*890/26
    def y(v):return 265-(v-low)/(high-low)*235
    actual=' '.join(f'{x(i):.2f},{y(v):.2f}' for i,v in enumerate(values))
    prediction=' '.join([f'{x(23):.2f},{y(values[-1]):.2f}']+[f'{x(24+i):.2f},{y(p["prediction"]):.2f}' for i,p in enumerate(future)])
    bands=''
    for level,color in [('0.95','#d7e9e8'),('0.8','#a3ceca')]:
        points=[(x(23),y(values[-1]))]+[(x(24+i),y(p['intervals'][level]['upper'])) for i,p in enumerate(future)]
        points += [(x(24+i),y(future[i]['intervals'][level]['lower'])) for i in reversed(range(3))]
        bands+=f'<polygon points="{" ".join(f"{a:.2f},{b:.2f}" for a,b in points)}" fill="{color}"/>'
    return f'''<svg viewBox="0 0 1000 320" role="img" aria-label="Published rounded national totals and three month series-end extrapolation with uncertainty bands"><title>National Carer Payment: series-end extrapolation</title>{bands}<polyline points="{actual}" fill="none" stroke="#365c72" stroke-width="3"/><polyline points="{prediction}" fill="none" stroke="#087e80" stroke-width="3" stroke-dasharray="7 5"/><text x="60" y="300" font-size="14">{esc(series.months[-24])}</text><text x="790" y="300" font-size="14">Sep 2026</text><text x="900" y="300" font-size="14">Dec 2026</text><text x="5" y="25" font-size="13">{high:,.0f}</text><text x="5" y="265" font-size="13">{low:,.0f}</text></svg>'''


def number(value):
    return 'undefined' if value is None else f'{value:.3f}'


def html_report(series, report):
    token=base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    selected=report['selected_model']
    table=''
    for model, data in report['holdout'].items():
        for h,m in data['by_horizon'].items():
            table+=f'<tr><td>{esc(NAMES[model])}{" • selected" if model==selected else ""}</td><td>{h}</td><td>{m["n"]}</td><td>{m["mae"]:,.1f}</td><td>{m["rmse"]:,.1f}</td><td>{m["bias_prediction_minus_actual"]:+,.1f}</td><td>{number(m["mase"])}</td></tr>'
    intervals=''
    for h, levels in report['holdout_intervals'].items():
        for level,m in levels.items():
            intervals+=f'<tr><td>{h} month</td><td>{float(level):.0%}</td><td>{m["covered"]} / {m["n"]}</td><td>{m["coverage"]:.1%}</td><td>{m["mean_width"]:,.0f}</td></tr>'
    points=''
    for p in report['series_end_extrapolation']['points']:
        b=p['intervals']['0.95']
        points+=f'<tr><td>{esc(p["month"])}</td><td>{p["prediction"]:,.0f}</td><td>{b["lower"]:,.0f}–{b["upper"]:,.0f}</td></tr>'
    provenance=json.dumps({'source':report['source'],'protocol':report['protocol'],'environment':report['environment']},indent=2)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'sha256-{token}'; base-uri 'none'; form-action 'none'"><meta name="referrer" content="no-referrer"><title>Carer Payment | Retrospective forecast research</title><style>{STYLE}</style></head><body><main><p class="eyebrow">AUSTRALIAN AGGREGATE WELFARE RESEARCH</p><h1>How predictable is the national Carer Payment caseload?</h1><p>177 published monthly totals · January 2012–September 2026 · Australia</p><div class="notice"><strong>Research use only.</strong> Administrative recipient counts do not measure unmet caring need. These estimates must not determine individual benefits, adverse action or automatic resource allocation.</div><article><h2>Series-end extrapolation</h2><p>Basis: September 2026 observation, from the DSS September 2026 release. Publication and acquisition occur later. This is a historical-series-end extrapolation, not a live operational forecast.</p><div class="scroll">{chart(series,report)}</div><p><small>Solid: published rounded totals. Dashed: {esc(NAMES[selected])} estimates. Bands: nominal 80% (dark) and 95% (light), without a coverage guarantee.</small></p><div class="scroll"><table><thead><tr><th>Reporting month</th><th>Estimate</th><th>Nominal 95% bounds</th></tr></thead><tbody>{points}</tbody></table></div></article><article><h2>Reserved-period errors</h2><p>Model selected using development MAE through September 2024: <strong>{esc(NAMES[selected])}</strong>. The model choice stayed fixed during evaluation. Earlier holdout observations enter training only after their dates. Each horizon has 22 cases with overlapping targets.</p><div class="scroll"><table><thead><tr><th>Model</th><th>Months ahead</th><th>Cases</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>MASE</th></tr></thead><tbody>{table}</tbody></table></div><p><small>Errors are in published recipients. Bias = prediction minus observation. MASE uses each training window's lag-12 scale. Zero scale gives null in the JSON report.</small></p></article><article><h2>Observed interval coverage</h2><p>Calibration uses development residuals only. A small dependent evaluation sample cannot establish future coverage.</p><div class="scroll"><table><thead><tr><th>Horizon</th><th>Nominal</th><th>Covered</th><th>Observed coverage</th><th>Mean width</th></tr></thead><tbody>{intervals}</tbody></table></div></article><article><h2>Interpretation limits</h2><ul>{''.join('<li>'+esc(w)+'</li>' for w in report['warnings'])}</ul><p>Source: Australian Government Department of Social Services, <em>DSS Income Support Recipients – Monthly Time Series</em>, September 2026. CC BY 2.5 Australia. National totals selected and month labels normalised; estimates and analysis are derivatives. No DSS endorsement implied.</p><p><a href="https://creativecommons.org/licenses/by/2.5/au/">Licence</a> · <a href="https://data.gov.au/data/api/3/action/package_show?id=dss-income-support-recipients-monthly-time-series">Source catalogue</a></p></article><details><summary>Source, method and environment</summary><pre>{esc(provenance)}</pre></details></main></body></html>'''


def cell(value):
    if isinstance(value,str):
        normalized=unicodedata.normalize('NFKC',value).lstrip()
        if normalized.startswith(('=','+','-','@')):
            return "'"+value
    return value


def csv_report(report):
    out=io.StringIO(newline='')
    w=csv.writer(out,quoting=csv.QUOTE_ALL)
    w.writerow(['stage','model','horizon_months','n','mae','rmse','bias_prediction_minus_actual','underpredicted','mase','selected','projection_sha256','unit','source_title','license','warning'])
    for stage in ('development','holdout'):
        for model,data in report[stage].items():
            for h,m in data['by_horizon'].items():
                w.writerow([cell(v) for v in [stage,model,h,m['n'],m['mae'],m['rmse'],m['bias_prediction_minus_actual'],m['underpredicted'],m['mase'],model==report['selected_model'],report['source']['projection_sha256'],report['source']['unit'],report['source'].get('attribution',{}).get('title','DSS Income Support Recipients – Monthly Time Series'),'CC BY 2.5 Australia',' | '.join(report['warnings'])]])
    return out.getvalue()
