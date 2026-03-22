import argparse
import json
import sys

import scholartools
from scholartools.cli._fmt import exit_result
from scholartools.models import Result


def _push(args: argparse.Namespace) -> None:
    try:
        result = scholartools.push()
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _pull(args: argparse.Namespace) -> None:
    try:
        result = scholartools.pull()
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _snapshot(args: argparse.Namespace) -> None:
    try:
        scholartools.create_snapshot()
    except Exception as e:
        print(json.dumps({"ok": False, "data": None, "error": str(e)}))
        sys.exit(1)
    print(json.dumps({"ok": True, "data": None, "error": None}))
    sys.exit(0)


def _list_conflicts(args: argparse.Namespace) -> None:
    try:
        conflicts = scholartools.list_conflicts()
    except Exception as e:
        print(json.dumps({"ok": False, "data": None, "error": str(e)}))
        sys.exit(1)
    print(
        json.dumps(
            {"ok": True, "data": [c.model_dump() for c in conflicts], "error": None}
        )
    )
    sys.exit(0)


def _resolve_conflict(args: argparse.Namespace) -> None:
    try:
        result = scholartools.resolve_conflict(args.uid, args.field, args.value)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _restore(args: argparse.Namespace) -> None:
    try:
        result = scholartools.restore_reference(args.citekey)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _sync_file(args: argparse.Namespace) -> None:
    try:
        result = scholartools.sync_file(args.citekey)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _unsync_file(args: argparse.Namespace) -> None:
    try:
        result = scholartools.unsync_file(args.citekey)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _upload_blobs(args: argparse.Namespace) -> None:
    try:
        result = scholartools.upload_blobs()
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    if args.plain:
        print(
            f"uploaded: {result.uploaded}  skipped: {result.skipped}  failed: {result.failed}"
        )
        sys.exit(0 if not result.errors else 1)
    exit_result(result, plain=False)


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

    p_sync_file = cmds.add_parser("sync-file")
    p_sync_file.add_argument("citekey")
    p_sync_file.set_defaults(func=_sync_file)

    p_unsync_file = cmds.add_parser("unsync-file")
    p_unsync_file.add_argument("citekey")
    p_unsync_file.set_defaults(func=_unsync_file)

    cmds.add_parser("upload-blobs").set_defaults(func=_upload_blobs)
