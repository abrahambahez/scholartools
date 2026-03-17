import argparse

import scholartools
from scholartools.cli._fmt import exit_result


def _extract(args: argparse.Namespace) -> None:
    result = scholartools.extract_from_file(args.file_path)
    exit_result(result, plain=False)


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("file_path")
    sub.set_defaults(func=_extract)
