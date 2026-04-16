import argparse
import json
import sys

import loretools
from loretools.cli._fmt import exit_result, read_arg


def _stage(args: argparse.Namespace) -> None:
    raw = read_arg(args.json, stdin=sys.stdin)
    try:
        ref_dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
    exit_result(loretools.stage_reference(ref_dict, file_path=args.file))


def _list_staged(args: argparse.Namespace) -> None:
    exit_result(loretools.list_staged(page=args.page))


def _delete_staged(args: argparse.Namespace) -> None:
    exit_result(loretools.delete_staged(args.citekey))


def _merge(args: argparse.Namespace) -> None:
    omit = [k.strip() for k in args.omit.split(",")] if args.omit else None
    exit_result(loretools.merge(omit=omit, allow_semantic=args.allow_semantic))


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="staging_cmd")

    p_stage = cmds.add_parser(
        "stage",
        help="Add a reference to the staging area for evaluation. Accepts the same JSON as `refs add` but does not commit to the library. Optionally attaches a file.",
    )
    p_stage.add_argument(
        "json",
        nargs="?",
        default=None,
        help="CSL-JSON dict as a string, or '-' to read from stdin.",
    )
    p_stage.add_argument(
        "--file",
        default=None,
        help="Path to a file to attach to this staged reference.",
    )
    p_stage.set_defaults(func=_stage)

    p_list = cmds.add_parser(
        "list-staged",
        help="List all references currently in the staging area, paginated (20 per page).",
    )
    p_list.add_argument("--page", type=int, default=1, help="Page number (default: 1).")
    p_list.set_defaults(func=_list_staged)

    p_delete = cmds.add_parser(
        "delete-staged",
        help="Discard a staged reference without merging it into the library.",
    )
    p_delete.add_argument("citekey", help="Citekey of the staged reference to discard.")
    p_delete.set_defaults(func=_delete_staged)

    p_merge = cmds.add_parser(
        "merge",
        help=(
            "Promote staged references into the library. "
            "Validates schema completeness, detects duplicates, moves attached files to the archive, and assigns citekeys. "
            "Failed references are reported with reasons and remain in staging."
        ),
    )
    p_merge.add_argument(
        "--omit",
        default=None,
        help="Comma-separated citekeys to exclude from this merge run.",
    )
    p_merge.add_argument(
        "--allow-semantic",
        action="store_true",
        default=False,
        help=(
            "Allow merging references whose duplicate check used fuzzy title/author matching "
            "(uid_confidence='semantic') rather than a stable identifier such as a DOI. "
            "Only enable after manually reviewing the matched pairs."
        ),
    )
    p_merge.set_defaults(func=_merge)
