import argparse

import loretools
from loretools.cli._fmt import exit_result


def _extract(args: argparse.Namespace) -> None:
    exit_result(loretools.extract_from_file(args.file_path))


def register(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "file_path",
        help=(
            "Path to a local PDF or supported file to extract metadata from. "
            "Returns CSL-JSON metadata on success. "
            "Returns agent_extraction_needed=true if automatic parsing fails."
        ),
    )
    sub.set_defaults(func=_extract)
