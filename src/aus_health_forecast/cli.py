"""Offline commands with bounded inputs and exclusive outputs."""
import argparse
import json
import os
from . import __version__
from .contract import ForecastError, load_series, write_report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    v = sub.add_parser('validate')
    v.add_argument('input')
    e = sub.add_parser('evaluate')
    e.add_argument('input')
    e.add_argument('--out', required=True)
    args = p.parse_args()
    try:
        series = load_series(args.input)
        if args.command == 'evaluate':
            from .evaluation import evaluate
            if os.path.lexists(args.out):
                raise ForecastError('output_already_exists')
            report = evaluate(series)
            write_report(args.out, report)
            print(json.dumps({'selected_model': report['selected_model'], 'holdout': report['holdout'], 'intervals': report['holdout_intervals']}))
            return
        print(json.dumps({'rows': len(series.values), 'first_month': series.months[0],
                          'last_month': series.months[-1], 'projection_sha256': series.provenance['projection_sha256']}))
    except (ForecastError, OSError) as e:
        print(json.dumps({'error': str(e) if isinstance(e, ForecastError) else 'file_access_failed'}))
        raise SystemExit(2) from None


if __name__ == '__main__':
    main()
