import argparse
import json
import sys

import scholartools
from scholartools.cli._fmt import exit_result


def _push(args: argparse.Namespace) -> None:
    result = scholartools.push()
    exit_result(result, args.plain)


def _pull(args: argparse.Namespace) -> None:
    result = scholartools.pull()
    exit_result(result, args.plain)


def _snapshot(args: argparse.Namespace) -> None:
    scholartools.create_snapshot()
    print(json.dumps({"ok": True, "data": None, "error": None}))
    sys.exit(0)


def _list_conflicts(args: argparse.Namespace) -> None:
    conflicts = scholartools.list_conflicts()
    print(
        json.dumps(
            {"ok": True, "data": [c.model_dump() for c in conflicts], "error": None}
        )
    )
    sys.exit(0)


def _resolve_conflict(args: argparse.Namespace) -> None:
    result = scholartools.resolve_conflict(args.uid, args.field, args.value)
    exit_result(result, args.plain)


def _restore(args: argparse.Namespace) -> None:
    result = scholartools.restore_reference(args.citekey)
    exit_result(result, args.plain)


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="sync_cmd")

    cmds.add_parser("push").set_defaults(func=_push)
    cmds.add_parser("pull").set_defaults(func=_pull)
    cmds.add_parser("snapshot").set_defaults(func=_snapshot)
    cmds.add_parser("list-conflicts").set_defaults(func=_list_conflicts)

    p_resolve = cmds.add_parser("resolve-conflict")
    p_resolve.add_argument("uid")
    p_resolve.add_argument("field")
    p_resolve.add_argument("value")
    p_resolve.set_defaults(func=_resolve_conflict)

    p_restore = cmds.add_parser("restore")
    p_restore.add_argument("citekey")
    p_restore.set_defaults(func=_restore)
