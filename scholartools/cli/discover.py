import argparse

import scholartools
from scholartools.cli._fmt import exit_result


def _discover(args: argparse.Namespace) -> None:
    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None
    result = scholartools.discover_references(
        args.query, sources=sources, limit=args.limit
    )
    exit_result(result, plain=False)


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("query")
    sub.add_argument("--sources", default=None, help="comma-separated source names")
    sub.add_argument("--limit", type=int, default=10)
    sub.set_defaults(func=_discover)
