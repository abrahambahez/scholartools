import argparse
import importlib.metadata
import sys

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
        version = "unknown"

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

    for group in _GROUPS:
        sub = subparsers.add_parser(group, help=_DESCRIPTIONS[group])
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
