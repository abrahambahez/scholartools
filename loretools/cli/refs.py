import argparse
import json
import sys

import loretools
from loretools.cli._fmt import exit_result, read_arg
from loretools.models import Result


def _add(args: argparse.Namespace) -> None:
    raw = read_arg(args.json, stdin=sys.stdin)
    try:
        ref_dict = json.loads(raw)
    except json.JSONDecodeError as e:
        exit_result(Result(ok=False, error=str(e)))
    exit_result(loretools.add_reference(ref_dict))


def _get(args: argparse.Namespace) -> None:
    exit_result(loretools.get_reference(citekey=args.citekey, uid=getattr(args, "uid", None)))


def _update(args: argparse.Namespace) -> None:
    raw = read_arg(args.json, stdin=sys.stdin)
    try:
        fields = json.loads(raw)
    except json.JSONDecodeError as e:
        exit_result(Result(ok=False, error=str(e)))
    exit_result(loretools.update_reference(args.citekey, fields))


def _rename(args: argparse.Namespace) -> None:
    exit_result(loretools.rename_reference(args.old, args.new))


def _delete(args: argparse.Namespace) -> None:
    exit_result(loretools.delete_reference(args.citekey))


def _list(args: argparse.Namespace) -> None:
    exit_result(loretools.list_references(page=args.page))


def _filter(args: argparse.Namespace) -> None:
    exit_result(loretools.filter_references(
        query=args.query,
        author=args.author,
        year=int(args.year) if args.year else None,
        ref_type=getattr(args, "type", None),
        has_file=True if args.has_file else None,
        staging=args.staging,
        page=args.page,
    ))


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="refs_cmd")

    p_add = cmds.add_parser(
        "add",
        help="Create a new reference in the library from CSL-JSON. Fails if a reference with the same uid already exists.",
    )
    p_add.add_argument(
        "json",
        nargs="?",
        default=None,
        help="CSL-JSON dict as a string, or '-' to read from stdin. Must include at minimum 'type' and 'title'.",
    )
    p_add.set_defaults(func=_add)

    p_get = cmds.add_parser(
        "get",
        help="Retrieve a committed reference by citekey or uid. Returns full CSL-JSON metadata.",
    )
    p_get.add_argument(
        "citekey",
        help="Human-readable reference identifier assigned at merge (e.g. smith2021).",
    )
    p_get.add_argument(
        "--uid",
        default=None,
        help="Unique internal identifier (alternative to citekey for lookup).",
    )
    p_get.set_defaults(func=_get)

    p_update = cmds.add_parser(
        "update",
        help="Patch fields on an existing reference. Only provided fields are updated; others are unchanged.",
    )
    p_update.add_argument(
        "citekey",
        help="Citekey of the reference to update.",
    )
    p_update.add_argument(
        "json",
        nargs="?",
        default=None,
        help="Partial CSL-JSON dict of fields to patch, as a string or '-' for stdin.",
    )
    p_update.set_defaults(func=_update)

    p_rename = cmds.add_parser(
        "rename",
        help="Change a reference's citekey. Updates all internal indexes.",
    )
    p_rename.add_argument("old", help="Current citekey of the reference to rename.")
    p_rename.add_argument("new", help="New citekey to assign.")
    p_rename.set_defaults(func=_rename)

    p_delete = cmds.add_parser(
        "delete",
        help="Remove a reference from the library. Does not delete any attached file.",
    )
    p_delete.add_argument(
        "citekey",
        help="Citekey of the reference to remove.",
    )
    p_delete.set_defaults(func=_delete)

    p_list = cmds.add_parser(
        "list",
        help="List all committed library references, paginated (20 per page).",
    )
    p_list.add_argument("--page", type=int, default=1, help="Page number (default: 1).")
    p_list.set_defaults(func=_list)

    p_filter = cmds.add_parser(
        "filter",
        help="Search committed references by any combination of keyword, author, year, type, or file presence.",
    )
    p_filter.add_argument("--query", default=None, help="Full-text search across title and abstract.")
    p_filter.add_argument("--author", default=None, help="Filter by author family name.")
    p_filter.add_argument("--year", default=None, help="Filter by 4-digit publication year.")
    p_filter.add_argument("--type", dest="type", default=None, help="CSL type (e.g. article-journal, book, chapter, dataset).")
    p_filter.add_argument("--has-file", action="store_true", default=False, help="Only return references with an attached file.")
    p_filter.add_argument("--staging", action="store_true", default=False, help="Search the staging area instead of the committed library.")
    p_filter.add_argument("--page", type=int, default=1, help="Page number (default: 1).")
    p_filter.set_defaults(func=_filter)
