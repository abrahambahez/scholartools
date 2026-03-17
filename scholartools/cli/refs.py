import argparse
import json
import sys

import scholartools
from scholartools.cli._fmt import exit_result, read_arg
from scholartools.models import Result


def _fmt_table(rows) -> str:
    header = f"{'citekey':<20} {'title':<50} {'authors':<30} {'year':<6} {'type':<15}"
    sep = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        title = (r.title or "")[:50]
        authors = (r.authors or "")[:30]
        year = str(r.year) if r.year else ""
        ref_type = getattr(r, "ref_type", "") or ""
        lines.append(
            f"{r.citekey:<20} {title:<50} {authors:<30} {year:<6} {ref_type:<15}"
        )
    return "\n".join(lines)


def _add(args: argparse.Namespace) -> None:
    raw = read_arg(args.json, stdin=sys.stdin)
    try:
        ref_dict = json.loads(raw)
    except json.JSONDecodeError as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    try:
        result = scholartools.add_reference(ref_dict)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _get(args: argparse.Namespace) -> None:
    try:
        result = scholartools.get_reference(
            citekey=args.citekey, uid=getattr(args, "uid", None)
        )
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _update(args: argparse.Namespace) -> None:
    raw = read_arg(args.json, stdin=sys.stdin)
    try:
        fields = json.loads(raw)
    except json.JSONDecodeError as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    try:
        result = scholartools.update_reference(args.citekey, fields)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _rename(args: argparse.Namespace) -> None:
    try:
        result = scholartools.rename_reference(args.old, args.new)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _delete(args: argparse.Namespace) -> None:
    try:
        result = scholartools.delete_reference(args.citekey)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _list(args: argparse.Namespace) -> None:
    try:
        result = scholartools.list_references(page=args.page)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    if args.plain:
        print(_fmt_table(result.references))
        sys.exit(0)
    exit_result(result, args.plain)


def _filter(args: argparse.Namespace) -> None:
    try:
        result = scholartools.filter_references(
            query=args.query,
            author=args.author,
            year=int(args.year) if args.year else None,
            ref_type=getattr(args, "type", None),
            has_file=True if args.has_file else None,
            staging=args.staging,
            page=args.page,
        )
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    if args.plain:
        print(_fmt_table(result.references))
        sys.exit(0)
    exit_result(result, args.plain)


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="refs_cmd")

    p_add = cmds.add_parser("add")
    p_add.add_argument("json", nargs="?", default=None)
    p_add.set_defaults(func=_add)

    p_get = cmds.add_parser("get")
    p_get.add_argument("citekey")
    p_get.add_argument("--uid", default=None)
    p_get.set_defaults(func=_get)

    p_update = cmds.add_parser("update")
    p_update.add_argument("citekey")
    p_update.add_argument("json", nargs="?", default=None)
    p_update.set_defaults(func=_update)

    p_rename = cmds.add_parser("rename")
    p_rename.add_argument("old")
    p_rename.add_argument("new")
    p_rename.set_defaults(func=_rename)

    p_delete = cmds.add_parser("delete")
    p_delete.add_argument("citekey")
    p_delete.set_defaults(func=_delete)

    p_list = cmds.add_parser("list")
    p_list.add_argument("--page", type=int, default=1)
    p_list.set_defaults(func=_list)

    p_filter = cmds.add_parser("filter")
    p_filter.add_argument("--query", default=None)
    p_filter.add_argument("--author", default=None)
    p_filter.add_argument("--year", default=None)
    p_filter.add_argument("--type", dest="type", default=None)
    p_filter.add_argument("--has-file", action="store_true", default=False)
    p_filter.add_argument("--staging", action="store_true", default=False)
    p_filter.add_argument("--page", type=int, default=1)
    p_filter.set_defaults(func=_filter)
