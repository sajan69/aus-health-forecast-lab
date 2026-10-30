"""Bounded full offline evaluation workload, without production capacity claims."""
from datetime import datetime, timezone
import os
from time import perf_counter
import statistics
from .contract import ForecastError, load_series
from .evaluation import evaluate


def benchmark(path, repeats=3):
    if type(repeats) is not int or not 1 <= repeats <= 3:
        raise ForecastError('benchmark_repeats_1_to_3')
    samples=[]
    expected=None
    for i in range(repeats):
        start=perf_counter()
        series=load_series(path)
        report=evaluate(series)
        elapsed=(perf_counter()-start)*1000
        if (len(report['records']['development']),len(report['records']['holdout'])) != (1092,264):
            raise ForecastError('benchmark_correctness_failed')
        result=(report['selected_model'],report['holdout'][report['selected_model']]['pooled']['mae'])
        if expected is None:
            expected=result
        if result[0]!=expected[0] or abs(result[1]-expected[1])>1e-7:
            raise ForecastError('benchmark_nondeterministic_result')
        samples.append({'repeat':i+1,'milliseconds':elapsed,'selected_model':result[0],
                        'selected_holdout_mae':result[1], 'development_records':1092,'holdout_records':264})
    return {'schema_version':1,'completed':True,'completed_at':datetime.now(timezone.utc).isoformat(),
            'workload':{'months':177,'models':4,'development_origins':91,'holdout_origins':22,
                        'horizons':[1,2,3],'candidate_point_predictions':1356,'series_end_predictions':3},
            'source':series.provenance,'environment':report['environment'],
            'reported_logical_cpus':os.cpu_count(),'samples':samples,
            'median_milliseconds':statistics.median(s['milliseconds'] for s in samples),
            'method':{'timer':'perf_counter wall milliseconds',
                      'included':'input read/strict parsing/hash validation, all fits/selection/calibration/metrics, environment metadata and series-end extrapolation',
                      'excluded':'CLI/dependency import, fixture acquisition, serialization/writes, assertions, browser, network/TLS',
                      'warmup':'no explicit warmup or cache clearing; prior tests and OS caches may benefit repeats',
                      'threads':'numerical pools limited to 1 within evaluation',
                      'limits':'single local client, shared host; not concurrent throughput or production capacity; no performance-improvement baseline'}}
