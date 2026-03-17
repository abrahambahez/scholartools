import argparse

import scholartools
from scholartools.cli._fmt import exit_result
from scholartools.models import Result


def _extract(args: argparse.Namespace) -> None:
    try:
        result = scholartools.extract_from_file(args.file_path)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, plain=False)


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("file_path")
    sub.set_defaults(func=_extract)
