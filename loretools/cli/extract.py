import argparse

import loretools
from loretools.cli._fmt import exit_result


def _extract(args: argparse.Namespace) -> None:
    exit_result(loretools.extract_from_file(args.file_path))


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("file_path")
    sub.set_defaults(func=_extract)
