"""Fixed chronological protocol, committed before inspecting model errors."""
MODELS = ('last_value', 'seasonal_naive', 'damped_holt', 'ridge_change')
HORIZONS = (1, 2, 3)
DEVELOPMENT_END = 153  # Jan2012..Sep2024, exclusive index of Oct2024
MIN_TRAIN = 60
HOLDOUT_END = 177


def origins(stage):
    if stage == 'development':
        return range(MIN_TRAIN, DEVELOPMENT_END - max(HORIZONS) + 1)
    if stage == 'holdout':
        return range(DEVELOPMENT_END, HOLDOUT_END - max(HORIZONS) + 1)
    raise ValueError('unknown_stage')


def specification():
    return {'id': 'carer-national-v1', 'development_end': '2024-09',
            'holdout_window': ['2024-10', '2026-09'], 'minimum_training_months': MIN_TRAIN,
            'horizons': list(HORIZONS), 'models_in_tie_order': list(MODELS),
            'selection': 'lowest pooled development MAE; tie order fixed',
            'development_origins': len(origins('development')),
            'holdout_origins': len(origins('holdout')),
            'holdout_policy': 'selection and interval widths frozen; refit on observations strictly before each origin',
            'intervals': 'symmetric absolute development residual order statistics per horizon at ceil((n+1)*nominal), lower clipped to zero',
            'ridge': 'direct changes h=1..3; alpha10; train-only StandardScaler; deterministic cholesky',
            'holt': 'additive damped trend, no seasonal component; estimated initialization; train-mean scaling; L-BFGS-B',
            'interpretation': 'single revised release retrospective benchmark, not real-time vintage backtest'}
