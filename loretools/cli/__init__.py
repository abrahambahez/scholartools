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
    "refs": (
        "CRUD operations on committed library references. "
        "A reference is an epistemic object (paper, dataset, recording, interview, field note, etc.) "
        "stored with CSL-JSON metadata and identified by a citekey (e.g. smith2021)."
    ),
    "extract": (
        "Parse a local file (PDF, ebook) and extract CSL-JSON metadata "
        "ready for `staging stage` or `refs add`. "
        "Falls back to agent_extraction_needed=true if automatic parsing fails "
        "(vision-based fallback requires the loretools-llm plugin)."
    ),
    "files": (
        "Attach, retrieve, move, or detach a file linked to a library reference by its citekey. "
        "Files are copied into a managed archive; use `reindex` after any manual file operations."
    ),
    "staging": (
        "Manage the evaluation layer before library promotion. "
        "Stage incoming references for review, then merge into the library when ready. "
        "The library only contains validated, deduplicated records; staging does not."
    ),
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
        description=(
            "loretools — reference management for AI agents. "
            "References are epistemic objects (papers, datasets, recordings, interviews, etc.) "
            "stored with CSL-JSON metadata and optional attached files. "
            "References flow from staging (evaluation) to library (production) via a validated merge step. "
            "All commands output JSON."
        ),
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
