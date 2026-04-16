import argparse

import loretools
from loretools.cli._fmt import exit_result


def _attach(args: argparse.Namespace) -> None:
    exit_result(loretools.attach_file(args.citekey, args.path))


def _detach(args: argparse.Namespace) -> None:
    exit_result(loretools.detach_file(args.citekey))


def _reindex(args: argparse.Namespace) -> None:
    exit_result(loretools.reindex_files())


def _get(args: argparse.Namespace) -> None:
    exit_result(loretools.get_file(args.citekey))


def _move(args: argparse.Namespace) -> None:
    exit_result(loretools.move_file(args.citekey, args.dest_name))


def _list(args: argparse.Namespace) -> None:
    exit_result(loretools.list_files(page=args.page))


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
