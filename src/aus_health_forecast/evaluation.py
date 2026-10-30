"""Chronological evaluation with frozen selection and calibration before holdout."""
from datetime import datetime, timezone
import importlib.metadata
import math
import platform
import statistics
import sys
from threadpoolctl import threadpool_limits, threadpool_info
from .contract import ForecastError
from .models import predict
from .protocol import DEVELOPMENT_END, HORIZONS, MODELS, origins, specification

WARNINGS = [
    'Research only: no clinical, individual eligibility, adverse action or automatic allocation use.',
    'National administrative caseload is not healthcare demand or unmet caring need.',
    'One revised release; retrospective benchmark, not a historical-vintage or prospective test.',
    'Privacy-rounded observations are retained; forecast precision does not recover unrounded totals.',
    'Intervals use overlapping development errors after model selection; nominal coverage is not guaranteed.',
    'Policy shocks and reporting changes can invalidate extrapolation; no causal interpretation.',
    'No regional or demographic fairness validation is possible from this national total.',
    'Horizons start at the last reporting month; publication lag means this is not a live operational forecast.',
]


def seasonal_scale(history):
    if len(history) <= 12:
        return None
    value = statistics.fmean(abs(history[i]-history[i-12]) for i in range(12,len(history)))
    return value or None


def stage_records(series, stage):
    records = []
    for n in origins(stage):
        history = series.values[:n]
        scale = seasonal_scale(history)
        for model in MODELS:
            output = predict(model, history)
            for h in HORIZONS:
                actual = series.values[n+h-1]
                records.append({'model': model, 'origin': series.months[n-1], 'training_months': n,
                                'horizon': h, 'target': series.months[n+h-1],
                                'actual': actual, 'prediction': output[h-1],
                                'error': output[h-1]-actual, 'mase_scale': scale})
    return records


def metrics(rows):
    if not rows:
        raise ForecastError('empty_evaluation')
    errors = [r['error'] for r in rows]
    scaled = [abs(r['error'])/r['mase_scale'] for r in rows if r['mase_scale'] is not None]
    return {'n': len(rows), 'mae': statistics.fmean(abs(e) for e in errors),
            'rmse': math.sqrt(statistics.fmean(e*e for e in errors)),
            'bias_prediction_minus_actual': statistics.fmean(errors),
            'underpredicted': sum(e < 0 for e in errors),
            'underprediction_fraction': sum(e < 0 for e in errors)/len(rows),
            'mase': statistics.fmean(scaled) if scaled else None,
            'mase_eligible': len(scaled), 'mase_undefined': len(rows)-len(scaled)}


def summarize(rows):
    return {m: {'pooled': metrics([r for r in rows if r['model']==m]),
                'by_horizon': {str(h): metrics([r for r in rows if r['model']==m and r['horizon']==h]) for h in HORIZONS}}
            for m in MODELS}


def choose(development):
    scores = {m: metrics([r for r in development if r['model']==m])['mae'] for m in MODELS}
    return min(MODELS, key=lambda m: scores[m])


def calibrate(development, selected):
    result = {}
    for h in HORIZONS:
        errors = sorted(abs(r['error']) for r in development if r['model']==selected and r['horizon']==h)
        result[str(h)] = {}
        for level in (.8,.95):
            rank = math.ceil((len(errors)+1)*level)
            if rank > len(errors):
                raise ForecastError('insufficient_calibration')
            result[str(h)][str(level)] = {'absolute_error_radius': errors[rank-1],
                                         'calibration_n': len(errors), 'rank': rank}
    return result


def attach_intervals(records, selected, widths):
    output = []
    for r in records:
        if r['model'] != selected:
            continue
        intervals = {}
        for level, calibration in widths[str(r['horizon'])].items():
            radius = calibration['absolute_error_radius']
            lower, upper = max(0, r['prediction']-radius), r['prediction']+radius
            intervals[level] = {'lower': lower, 'upper': upper,
                                'covered': lower <= r['actual'] <= upper}
        output.append({**r, 'intervals': intervals})
    return output


def interval_metrics(rows):
    return {str(h): {str(level): {
        'n': len(part := [r for r in rows if r['horizon']==h]),
        'covered': sum(r['intervals'][str(level)]['covered'] for r in part),
        'coverage': statistics.fmean(r['intervals'][str(level)]['covered'] for r in part),
        'mean_width': statistics.fmean(r['intervals'][str(level)]['upper']-r['intervals'][str(level)]['lower'] for r in part)}
        for level in (.8,.95)} for h in HORIZONS}


def environment():
    names = ('numpy', 'scipy', 'pandas', 'statsmodels', 'scikit-learn', 'threadpoolctl')
    return {'python': sys.version.split()[0], 'platform': platform.platform(),
            'packages': {n: importlib.metadata.version(n) for n in names},
            'package_version': importlib.metadata.version('aus-health-forecast-lab'),
            'threadpools': [{k: p.get(k) for k in ('internal_api','num_threads','version','architecture')} for p in threadpool_info()]}


def _evaluate(series):
    if len(series.values) != 177 or len(series.months) != 177:
        raise ForecastError('protocol_requires_177_months')
    development = stage_records(series, 'development')
    # Holdout values do not participate in these two functions.
    selected = choose(development)
    widths = calibrate(development, selected)
    holdout = stage_records(series, 'holdout')
    intervals = attach_intervals(holdout, selected, widths)
    extrapolated = predict(selected, series.values)
    future = []
    for h in HORIZONS:
        # Reviewed source ends September 2026; this protocol is release-specific.
        future.append({'month': f'2026-{9+h:02}', 'horizon': h,
                       'prediction': extrapolated[h-1],
                       'intervals': {level: {'lower': max(0,extrapolated[h-1]-v['absolute_error_radius']),
                                             'upper': extrapolated[h-1]+v['absolute_error_radius']}
                                     for level,v in widths[str(h)].items()}})
    return {'schema_version': 1, 'completed_at': datetime.now(timezone.utc).isoformat(),
            'protocol': specification(), 'source': series.provenance, 'environment': environment(),
            'selected_model': selected, 'selection_uses_holdout': False,
            'warnings': WARNINGS, 'development': summarize(development),
            'holdout': summarize(holdout), 'interval_calibration': widths,
            'holdout_intervals': interval_metrics(intervals),
            'development_regimes': {
                label: metrics([r for r in development if r['model']==selected and ((start <= r['target'] <= end))])
                for label,start,end in [('pre_2020','2012-01','2019-12'),
                                         ('2020_2021','2020-01','2021-12'),
                                         ('2022_onward','2022-01','2024-09')]},
            'series_end_extrapolation': {'last_observation': series.months[-1],
                                        'label': 'historical-series-end, not a live operational forecast',
                                        'points': future},
            'records': {'development': development, 'holdout': holdout, 'selected_holdout_intervals': intervals}}


def evaluate(series):
    # Bound numerical worker pools independently of caller shell configuration.
    with threadpool_limits(limits=1):
        return _evaluate(series)
