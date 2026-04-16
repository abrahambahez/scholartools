import json
from unittest.mock import patch

import pytest

from loretools.cli import _build_parser
from loretools.models import (
    FileRow,
    FilesListResult,
    GetFileResult,
    MoveResult,
)


def _run(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def test_files_get_dispatches(capsys):
    result = GetFileResult(path="/files/smith2020.pdf")
    with patch("loretools.get_file", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["files", "get", "smith2020"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with("smith2020")
        data = json.loads(capsys.readouterr().out)
        assert data["path"] == "/files/smith2020.pdf"
        assert data["error"] is None


def test_files_get_none_result(capsys):
    result = GetFileResult(path=None)
    with patch("loretools.get_file", return_value=result):
        with pytest.raises(SystemExit):
            _run(["files", "get", "missing"])
        data = json.loads(capsys.readouterr().out)
        assert data["path"] is None


def test_files_move_dispatches():
    result = MoveResult(new_path="/files/smith2020_renamed.pdf")
    with patch("loretools.move_file", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["files", "move", "smith2020", "renamed.pdf"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with("smith2020", "renamed.pdf")


def test_files_list_json(capsys):
    row = FileRow(
        citekey="smith2020",
        path="/files/smith2020.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
    )
    result = FilesListResult(files=[row], total=1, page=1)
    with patch("loretools.list_files", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["files", "list"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with(page=1)
        data = json.loads(capsys.readouterr().out)
        assert "files" in data
        assert data["total"] == 1
        assert data["files"][0]["citekey"] == "smith2020"


def test_files_list_page_arg():
    result = FilesListResult(files=[], total=0, page=2)
    with patch("loretools.list_files", return_value=result) as mock_fn:
        with pytest.raises(SystemExit):
            _run(["files", "list", "--page", "2"])
        mock_fn.assert_called_once_with(page=2)
