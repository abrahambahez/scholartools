import argparse
import json
import sys

import scholartools
from scholartools.cli._fmt import exit_result, read_arg
from scholartools.models import PeerIdentity, Result


def _parse_identity(raw: str) -> PeerIdentity:
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "data": None, "error": str(exc)}))
        sys.exit(1)
    return PeerIdentity.model_validate(d)


def _init(args: argparse.Namespace) -> None:
    try:
        result = scholartools.peer_init(args.peer_id, args.device_id)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _register(args: argparse.Namespace) -> None:
    raw = read_arg(args.identity_json, stdin=sys.stdin)
    identity = _parse_identity(raw)
    try:
        result = scholartools.peer_register(identity)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _add_device(args: argparse.Namespace) -> None:
    raw = read_arg(args.identity_json, stdin=sys.stdin)
    identity = _parse_identity(raw)
    try:
        result = scholartools.peer_add_device(args.peer_id, identity)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _revoke_device(args: argparse.Namespace) -> None:
    try:
        result = scholartools.peer_revoke_device(args.peer_id, args.device_id)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _revoke(args: argparse.Namespace) -> None:
    try:
        result = scholartools.peer_revoke(args.peer_id)
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def _register_self(args: argparse.Namespace) -> None:
    try:
        result = scholartools.peer_register_self()
    except Exception as e:
        exit_result(Result(ok=False, error=str(e)), plain=False)
    exit_result(result, args.plain)


def register(sub: argparse.ArgumentParser) -> None:
    cmds = sub.add_subparsers(dest="peers_cmd")

    p_init = cmds.add_parser("init")
    p_init.add_argument("peer_id")
    p_init.add_argument("device_id")
    p_init.set_defaults(func=_init)

    p_register = cmds.add_parser("register")
    p_register.add_argument("identity_json", nargs="?", default=None)
    p_register.set_defaults(func=_register)

    p_add_device = cmds.add_parser("add-device")
    p_add_device.add_argument("peer_id")
    p_add_device.add_argument("identity_json", nargs="?", default=None)
    p_add_device.set_defaults(func=_add_device)

    p_revoke_device = cmds.add_parser("revoke-device")
    p_revoke_device.add_argument("peer_id")
    p_revoke_device.add_argument("device_id")
    p_revoke_device.set_defaults(func=_revoke_device)

    p_revoke = cmds.add_parser("revoke")
    p_revoke.add_argument("peer_id")
    p_revoke.set_defaults(func=_revoke)

    cmds.add_parser("register-self").set_defaults(func=_register_self)
