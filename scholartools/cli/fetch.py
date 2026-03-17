import argparse

import scholartools
from scholartools.cli._fmt import exit_result


def _fetch(args: argparse.Namespace) -> None:
    result = scholartools.fetch_reference(args.identifier)
    exit_result(result, plain=False)


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("identifier")
    sub.set_defaults(func=_fetch)
