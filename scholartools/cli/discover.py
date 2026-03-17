import argparse

import scholartools
from scholartools.cli._fmt import exit_result
from scholartools.models import Result


def _discover(args: argparse.Namespace) -> None:
    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None
    try:
        result = scholartools.discover_references(
            args.query, sources=sources, limit=args.limit
        )
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, plain=False)


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("query")
    sub.add_argument("--sources", default=None, help="comma-separated source names")
    sub.add_argument("--limit", type=int, default=10)
    sub.set_defaults(func=_discover)
