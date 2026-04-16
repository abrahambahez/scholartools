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

    p_stage = cmds.add_parser("stage")
    p_stage.add_argument("json", nargs="?", default=None)
    p_stage.add_argument("--file", default=None)
    p_stage.set_defaults(func=_stage)

    p_list = cmds.add_parser("list-staged")
    p_list.add_argument("--page", type=int, default=1)
    p_list.set_defaults(func=_list_staged)

    p_delete = cmds.add_parser("delete-staged")
    p_delete.add_argument("citekey")
    p_delete.set_defaults(func=_delete_staged)

    p_merge = cmds.add_parser("merge")
    p_merge.add_argument("--omit", default=None)
    p_merge.add_argument("--allow-semantic", action="store_true", default=False)
    p_merge.set_defaults(func=_merge)
