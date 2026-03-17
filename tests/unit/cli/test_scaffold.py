from unittest.mock import MagicMock

import pytest

from scholartools.cli import _build_parser
from scholartools.cli._fmt import read_arg


def test_parser_loads():
    parser = _build_parser()
    assert parser is not None


def test_help_exits_zero():
    parser = _build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])
    assert exc_info.value.code == 0


def test_unknown_group_exits_nonzero():
    parser = _build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["unknown-group"])
    assert exc_info.value.code != 0


def test_read_arg_returns_value_when_provided():
    stdin = MagicMock()
    assert read_arg("foo", stdin=stdin) == "foo"


def test_read_arg_reads_stdin_when_not_tty():
    stdin = MagicMock()
    stdin.isatty.return_value = False
    stdin.read.return_value = "bar\n"
    assert read_arg(None, stdin=stdin) == "bar"


def test_read_arg_raises_when_tty():
    stdin = MagicMock()
    stdin.isatty.return_value = True
    with pytest.raises(SystemExit) as exc_info:
        read_arg(None, stdin=stdin)
    assert exc_info.value.code == 2
