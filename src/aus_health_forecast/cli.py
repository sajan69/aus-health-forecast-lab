"""Offline commands with bounded inputs and exclusive outputs."""
import argparse
import json
import os
from . import __version__
from .contract import ForecastError, load_series, write_report, write_bytes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    v = sub.add_parser('validate')
    v.add_argument('input')
    e = sub.add_parser('evaluate')
    e.add_argument('input')
    e.add_argument('--out', required=True)
    e.add_argument('--format', choices=('json','csv','html'), default='json')
    b = sub.add_parser('benchmark')
    b.add_argument('input')
    b.add_argument('--repeats',type=int,default=3,choices=range(1,4))
    b.add_argument('--out',required=True)
    args = p.parse_args()
    try:
        if args.command == 'benchmark':
            from .benchmark import benchmark
            if os.path.lexists(args.out):
                raise ForecastError('output_already_exists')
            report=benchmark(args.input,args.repeats)
            write_report(args.out,report)
            print(json.dumps({'completed':report['completed'],'samples':report['samples'],'median_milliseconds':report['median_milliseconds']}))
            return
        series = load_series(args.input)
        if args.command == 'evaluate':
            from .evaluation import evaluate
            if os.path.lexists(args.out):
                raise ForecastError('output_already_exists')
            report = evaluate(series)
            if args.format == 'json':
                write_report(args.out, report)
            else:
                from .reports import html_report, csv_report
                value=html_report(series,report) if args.format=='html' else csv_report(report)
                write_bytes(args.out,value.encode('utf-8'))
            print(json.dumps({'selected_model': report['selected_model'], 'holdout': report['holdout'], 'intervals': report['holdout_intervals']}))
            return
        print(json.dumps({'rows': len(series.values), 'first_month': series.months[0],
                          'last_month': series.months[-1], 'projection_sha256': series.provenance['projection_sha256']}))
    except (ForecastError, OSError) as e:
        print(json.dumps({'error': str(e) if isinstance(e, ForecastError) else 'file_access_failed'}))
        raise SystemExit(2) from None


if __name__ == '__main__':
    main()
