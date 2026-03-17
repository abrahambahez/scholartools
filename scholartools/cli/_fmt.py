import json
import sys
from typing import Any


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def _list_data(result: Any) -> list | None:
    for attr in ("references", "files", "items"):
        if hasattr(result, attr):
            val = getattr(result, attr)
            if isinstance(val, list):
                return [_serialize(r) for r in val]
    return None


def output(result: Any, plain: bool) -> str:
    ok: bool = getattr(result, "ok", getattr(result, "error", None) is None)
    error: str | None = getattr(result, "error", None)

    if hasattr(result, "page"):
        rows = _list_data(result) or []
        page = getattr(result, "page", 1)
        total = getattr(result, "total", len(rows))
        if plain:
            lines = [f"{r}" for r in rows]
            return "\n".join(lines)
        envelope = {
            "ok": ok,
            "data": rows,
            "page_info": {"page": page, "page_size": total},
            "error": error,
        }
        return json.dumps(envelope, default=str)

    data = _serialize(result)
    if plain:
        if isinstance(data, dict):
            return "\n".join(
                f"{k}={v}" for k, v in data.items() if k not in ("ok", "error")
            )
        return str(data)
    return json.dumps({"ok": ok, "data": data, "error": error}, default=str)


def exit_result(result: Any, plain: bool) -> None:
    print(output(result, plain))
    sys.exit(0 if getattr(result, "ok", getattr(result, "error", None) is None) else 1)


def read_arg(value: str | None, *, stdin) -> str:
    if value is not None:
        return value
    if not stdin.isatty():
        return stdin.read().strip()
    print("error: argument required (or pipe via stdin)", file=sys.stderr)
    raise SystemExit(2)
