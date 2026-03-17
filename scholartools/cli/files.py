import argparse
import json
import os
import sys

import scholartools
from scholartools.cli._fmt import exit_result


def _link(args: argparse.Namespace) -> None:
    result = scholartools.link_file(args.citekey, args.path)
    exit_result(result, args.plain)


def _unlink(args: argparse.Namespace) -> None:
    result = scholartools.unlink_file(args.citekey)
    exit_result(result, args.plain)


def _get(args: argparse.Namespace) -> None:
    result = scholartools.get_file(args.citekey)
    print(
        json.dumps({"ok": True, "data": str(result) if result else None, "error": None})
    )
    sys.exit(0)


def _move(args: argparse.Namespace) -> None:
    result = scholartools.move_file(args.citekey, args.dest_name)
    exit_result(result, args.plain)


def _list(args: argparse.Namespace) -> None:
    result = scholartools.list_files(page=args.page)
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
    result = scholartools.prefetch_blobs(citekeys=citekeys)
    exit_result(result, args.plain)


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="files_cmd")

    p_link = cmds.add_parser("link")
    p_link.add_argument("citekey")
    p_link.add_argument("path")
    p_link.set_defaults(func=_link)

    p_unlink = cmds.add_parser("unlink")
    p_unlink.add_argument("citekey")
    p_unlink.set_defaults(func=_unlink)

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
