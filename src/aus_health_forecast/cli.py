"""Offline commands with bounded inputs and exclusive outputs."""
import argparse
import json
from . import __version__
from .contract import ForecastError, load_series


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    v = sub.add_parser('validate')
    v.add_argument('input')
    args = p.parse_args()
    try:
        series = load_series(args.input)
        print(json.dumps({'rows': len(series.values), 'first_month': series.months[0],
                          'last_month': series.months[-1], 'projection_sha256': series.provenance['projection_sha256']}))
    except (ForecastError, OSError) as e:
        print(json.dumps({'error': str(e) if isinstance(e, ForecastError) else 'file_access_failed'}))
        raise SystemExit(2) from None


if __name__ == '__main__':
    main()
