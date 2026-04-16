import argparse
import importlib.metadata
import os
import sys

from loretools.cli import extract as _extract
from loretools.cli import files as _files
from loretools.cli import refs as _refs
from loretools.cli import staging as _staging

_GROUPS = ["refs", "extract", "files", "staging"]

_DESCRIPTIONS = {
    "refs": "manage references in the library",
    "extract": "extract metadata from a local file",
    "files": "manage files linked to references",
    "staging": "manage staged references before merging",
}


def _not_implemented(args: argparse.Namespace) -> None:
    print("not yet implemented", file=sys.stderr)
    sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    try:
        version = importlib.metadata.version("loretools")
    except importlib.metadata.PackageNotFoundError:
        version = os.environ.get("LORE_VERSION", "unknown")

    parser = argparse.ArgumentParser(
        prog="lore",
        description="loretools CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version}")

    subparsers = parser.add_subparsers(dest="group", metavar="group")

    _group_registers = {
        "refs": _refs.register,
        "extract": _extract.register,
        "files": _files.register,
        "staging": _staging.register,
    }

    for group in _GROUPS:
        sub = subparsers.add_parser(group, help=_DESCRIPTIONS[group])
        if group in _group_registers:
            _group_registers[group](sub)
        else:
            sub.set_defaults(func=_not_implemented)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.group is None:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        _not_implemented(args)


if __name__ == "__main__":
    main()
