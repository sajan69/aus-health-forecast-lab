import unittest
from unittest.mock import patch
import math
from aus_health_forecast.contract import ForecastError, Series
from aus_health_forecast.models import features, predict
from aus_health_forecast.evaluation import (stage_records, choose, calibrate, metrics,
                                          seasonal_scale, attach_intervals)
from aus_health_forecast.protocol import MODELS


class ModelTests(unittest.TestCase):
    def test_known_baseline_predictions_and_input_bounds(self):
        y = tuple(range(60))
        self.assertEqual(predict('last_value', y), [59,59,59])
        self.assertEqual(predict('seasonal_naive', y), [48,49,50])
        for bad in [(), (float('nan'),)*60, (-1,)*60, (1,)*178]:
            with self.assertRaises(ForecastError): predict('last_value', bad)

    def test_constant_all_models_and_finite_trend_outputs(self):
        for m in MODELS:
            with self.subTest(model=m):
                for p in predict(m, (500,)*60): self.assertAlmostEqual(p,500)
                self.assertTrue(all(math.isfinite(v) and v>=0 for v in predict(m,tuple(500+i*5 for i in range(60)))))

    def test_features_cannot_read_future_suffix(self):
        y = list(range(80))
        self.assertEqual(features(y,60,3),features(y[:61]+[999999]*19,60,3))

    def test_holt_optimizer_failure_is_explicit(self):
        from types import SimpleNamespace
        with patch('aus_health_forecast.models.ExponentialSmoothing') as model:
            model.return_value.fit.return_value = SimpleNamespace(mle_retvals=SimpleNamespace(success=False))
            with self.assertRaisesRegex(ForecastError,'holt_fit_failed'):
                predict('damped_holt',tuple(range(60)))

    def test_zero_scale_null_mase_and_signed_errors(self):
        self.assertIsNone(seasonal_scale((5,)*60))
        m=metrics([{'error': -3,'mase_scale': None},{'error': 1,'mase_scale': None}])
        self.assertEqual(m['mae'],2)
        self.assertEqual(m['bias_prediction_minus_actual'],-1)
        self.assertEqual(m['underpredicted'],1)
        self.assertIsNone(m['mase'])
        self.assertEqual(m['mase_undefined'],2)

    def test_interval_order_rank_and_lower_bound(self):
        rows=[{'model':'last_value','horizon':h,'error': i} for h in (1,2,3) for i in range(1,92)]
        c=calibrate(rows,'last_value')
        self.assertEqual(c['1']['0.8']['rank'],74)
        self.assertEqual(c['1']['0.95']['rank'],88)
        r=attach_intervals([{'model':'last_value','horizon':1,'prediction':1,'actual':0}], 'last_value',c)[0]
        self.assertEqual(r['intervals']['0.8']['lower'],0)
        self.assertTrue(r['intervals']['0.8']['covered'])

    def test_development_selection_and_calibration_invariant_to_holdout_mutation(self):
        months=tuple(f'{2012+i//12}-{i%12+1:02}' for i in range(177))
        a=Series(months,tuple(1000+i*5 for i in range(177)),{})
        b=Series(months,a.values[:153]+(900000,)*24,{})
        calls=[]
        def spy(model,history):
            calls.append(len(history))
            return [history[-1]]*3
        with patch('aus_health_forecast.evaluation.predict',side_effect=spy):
            da=stage_records(a,'development')
            db=stage_records(b,'development')
        self.assertEqual(da,db)
        self.assertLessEqual(max(calls),150)
        self.assertEqual(choose(da),choose(db))
        self.assertEqual(calibrate(da,choose(da)),calibrate(db,choose(db)))
        self.assertTrue(all(r['target']<'2024-10' for r in da))

    def test_holdout_prefixes_exclude_own_targets(self):
        months=tuple(f'{2012+i//12}-{i%12+1:02}' for i in range(177))
        series=Series(months,tuple(range(177)),{})
        def spy(model,history):
            self.assertEqual(history,series.values[:len(history)])
            return [history[-1]]*3
        with patch('aus_health_forecast.evaluation.predict',side_effect=spy):
            records=stage_records(series,'holdout')
        self.assertEqual(len(records),264)
        self.assertTrue(all(r['prediction']<r['actual'] for r in records))
        self.assertEqual(min(r['target'] for r in records),'2024-10')
        self.assertEqual(max(r['target'] for r in records),'2026-09')
