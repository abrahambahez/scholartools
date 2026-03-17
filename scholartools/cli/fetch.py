import argparse

import scholartools
from scholartools.cli._fmt import exit_result
from scholartools.models import Result


def _fetch(args: argparse.Namespace) -> None:
    try:
        result = scholartools.fetch_reference(args.identifier)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, plain=False)


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("identifier")
    sub.set_defaults(func=_fetch)
