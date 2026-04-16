import sys
from typing import Any


def exit_result(result: Any) -> None:
    print(result.model_dump_json())
    sys.exit(0 if getattr(result, "error", None) is None else 1)


def read_arg(value: str | None, *, stdin) -> str:
    if value is not None:
        return value
    if not stdin.isatty():
        return stdin.read().strip()
    print("error: argument required (or pipe via stdin)", file=sys.stderr)
    raise SystemExit(2)
