"""Prefix-only deterministic point models; no fitted object is deserialized."""
import math
import warnings
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from .contract import ForecastError
from .protocol import MODELS


def features(values, t, h):
    """t is the last known observation index; never access beyond t."""
    diffs = np.diff(np.asarray(values[:t+1], dtype=float))
    angle = 2 * math.pi * ((t + h) % 12) / 12
    return [diffs[-1], diffs[-2], diffs[-3], diffs[-12],
            float(np.mean(diffs[-3:])), float(np.mean(diffs[-12:])),
            math.sin(angle), math.cos(angle)]


def predict(model, history):
    y = np.asarray(history, dtype=float)
    if model not in MODELS or y.ndim != 1 or not 60 <= len(y) <= 177 or not np.isfinite(y).all() or (y < 0).any():
        raise ForecastError('invalid_model_or_history')
    if model == 'last_value':
        output = np.repeat(y[-1], 3)
    elif model == 'seasonal_naive':
        output = y[-12:-9]
    elif model == 'damped_holt':
        if np.ptp(y) == 0:
            output = np.repeat(y[0], 3)
        else:
            scale = max(float(y.mean()), 1.0)
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                try:
                    fit = ExponentialSmoothing(y/scale, trend='add', damped_trend=True,
                                               seasonal=None, initialization_method='estimated').fit(
                        optimized=True, use_brute=False, method='L-BFGS-B',
                        minimize_kwargs={'options': {'maxiter': 1000}})
                except (ConvergenceWarning, ValueError, FloatingPointError) as e:
                    raise ForecastError('holt_fit_failed') from e
            if not fit.mle_retvals.success:
                raise ForecastError('holt_fit_failed')
            output = np.asarray(fit.forecast(3)) * scale
    else:
        output = []
        for h in (1, 2, 3):
            # Label y[t+h] must be observed in this history, never the full series.
            indices = range(13, len(y)-h)
            x = np.asarray([features(y, t, h) for t in indices])
            target = np.asarray([y[t+h]-y[t] for t in indices])
            fit = make_pipeline(StandardScaler(), Ridge(alpha=10.0, solver='cholesky'))
            fit.fit(x, target)
            output.append(y[-1] + fit.predict([features(y, len(y)-1, h)])[0])
    output = np.maximum(np.asarray(output, dtype=float), 0)
    if output.shape != (3,) or not np.isfinite(output).all():
        raise ForecastError('invalid_forecast')
    return output.tolist()
