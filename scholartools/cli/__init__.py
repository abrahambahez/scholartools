import argparse
import importlib.metadata
import os
import sys

from scholartools.cli import discover as _discover
from scholartools.cli import extract as _extract
from scholartools.cli import fetch as _fetch
from scholartools.cli import files as _files
from scholartools.cli import peers as _peers
from scholartools.cli import refs as _refs
from scholartools.cli import staging as _staging
from scholartools.cli import sync as _sync

_GROUPS = ["refs", "discover", "fetch", "extract", "files", "staging", "peers", "sync"]

_DESCRIPTIONS = {
    "refs": "manage references in the library",
    "discover": "search external sources for references",
    "fetch": "fetch a reference by identifier",
    "extract": "extract metadata from a local file",
    "files": "manage files linked to references",
    "staging": "manage staged references before merging",
    "peers": "manage peer identities and devices",
    "sync": "push, pull, and resolve sync conflicts",
}


def _not_implemented(args: argparse.Namespace) -> None:
    print("not yet implemented", file=sys.stderr)
    sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    try:
        version = importlib.metadata.version("scholartools")
    except importlib.metadata.PackageNotFoundError:
        version = os.environ.get("SCHT_VERSION", "unknown")

    parser = argparse.ArgumentParser(
        prog="scht",
        description="scholartools CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version}")
    parser.add_argument(
        "--plain",
        action="store_true",
        default=False,
        help="human-readable output instead of JSON",
    )

    subparsers = parser.add_subparsers(dest="group", metavar="group")

    _group_registers = {
        "refs": _refs.register,
        "discover": _discover.register,
        "fetch": _fetch.register,
        "extract": _extract.register,
        "files": _files.register,
        "peers": _peers.register,
        "staging": _staging.register,
        "sync": _sync.register,
    }

    for group in _GROUPS:
        sub = subparsers.add_parser(group, help=_DESCRIPTIONS[group])
        if group in _group_registers:
            _group_registers[group](sub)
        else:
            sub.set_defaults(func=_not_implemented)

    return parser


def main() -> None:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--plain", action="store_true", default=False)
    pre_args, remaining = pre.parse_known_args()

    parser = _build_parser()
    args = parser.parse_args(remaining)
    args.plain = pre_args.plain

    if args.group is None:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        _not_implemented(args)
