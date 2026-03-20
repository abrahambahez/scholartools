import argparse
import json
import os
import sys

import scholartools
from scholartools.cli._fmt import exit_result
from scholartools.models import Result


def _attach(args: argparse.Namespace) -> None:
    try:
        result = scholartools.attach_file(args.citekey, args.path)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _detach(args: argparse.Namespace) -> None:
    try:
        result = scholartools.detach_file(args.citekey)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _reindex(args: argparse.Namespace) -> None:
    try:
        r = scholartools.reindex_files()
    except Exception as e:
        print(json.dumps({"ok": False, "data": None, "error": str(e)}))
        sys.exit(1)
    print(
        f"Repaired: {r.repaired}, already ok: {r.already_ok}, not found: {r.not_found}"
    )
    sys.exit(0)


def _get(args: argparse.Namespace) -> None:
    try:
        result = scholartools.get_file(args.citekey)
    except Exception as e:
        print(json.dumps({"ok": False, "data": None, "error": str(e)}))
        sys.exit(1)
    print(
        json.dumps({"ok": True, "data": str(result) if result else None, "error": None})
    )
    sys.exit(0)


def _move(args: argparse.Namespace) -> None:
    try:
        result = scholartools.move_file(args.citekey, args.dest_name)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _list(args: argparse.Namespace) -> None:
    try:
        result = scholartools.list_files(page=args.page)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    if args.plain:
        rows = result.files
        col_w = 20
        header = f"{'citekey':<{col_w}}  {'filename':<{col_w}}  size"
        lines = [header]
        for row in rows:
            filename = os.path.basename(row.path)
            lines.append(
                f"{row.citekey:<{col_w}}  {filename:<{col_w}}  {row.size_bytes}"
            )
        print("\n".join(lines))
        sys.exit(0)
    exit_result(result, args.plain)


def _prefetch(args: argparse.Namespace) -> None:
    citekeys = [k.strip() for k in args.citekeys.split(",")] if args.citekeys else None
    try:
        result = scholartools.prefetch_blobs(citekeys=citekeys)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="files_cmd")

    p_attach = cmds.add_parser("attach")
    p_attach.add_argument("citekey")
    p_attach.add_argument("path")
    p_attach.set_defaults(func=_attach)

    p_detach = cmds.add_parser("detach")
    p_detach.add_argument("citekey")
    p_detach.set_defaults(func=_detach)

    cmds.add_parser("reindex").set_defaults(func=_reindex)

    p_get = cmds.add_parser("get")
    p_get.add_argument("citekey")
    p_get.set_defaults(func=_get)

    p_move = cmds.add_parser("move")
    p_move.add_argument("citekey")
    p_move.add_argument("dest_name")
    p_move.set_defaults(func=_move)

    p_list = cmds.add_parser("list")
    p_list.add_argument("--page", type=int, default=1)
    p_list.set_defaults(func=_list)

    p_prefetch = cmds.add_parser("prefetch")
    p_prefetch.add_argument("--citekeys", default=None)
    p_prefetch.set_defaults(func=_prefetch)
