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

    p_attach = cmds.add_parser(
        "attach",
        help="Copy a file into the archive and link it to a reference by citekey.",
    )
    p_attach.add_argument("citekey", help="Citekey of the reference to link the file to.")
    p_attach.add_argument("path", help="Filesystem path to the file to copy into the archive.")
    p_attach.set_defaults(func=_attach)

    p_detach = cmds.add_parser(
        "detach",
        help="Unlink a file from a reference. The file remains in the archive but is no longer associated.",
    )
    p_detach.add_argument("citekey", help="Citekey of the reference to unlink.")
    p_detach.set_defaults(func=_detach)

    cmds.add_parser(
        "reindex",
        help="Audit the file archive and rebuild the index. Run after any manual file operations.",
    ).set_defaults(func=_reindex)

    p_get = cmds.add_parser(
        "get",
        help="Return the absolute path of the file attached to a reference.",
    )
    p_get.add_argument("citekey", help="Citekey of the reference whose file path to retrieve.")
    p_get.set_defaults(func=_get)

    p_move = cmds.add_parser(
        "move",
        help="Rename an attached file within the archive.",
    )
    p_move.add_argument("citekey", help="Citekey of the reference whose file to rename.")
    p_move.add_argument("dest_name", help="New filename within the archive (basename only, no directory path).")
    p_move.set_defaults(func=_move)

    p_list = cmds.add_parser(
        "list",
        help="List all archived files with their linked citekeys, paginated (20 per page).",
    )
    p_list.add_argument("--page", type=int, default=1, help="Page number (default: 1).")
    p_list.set_defaults(func=_list)
