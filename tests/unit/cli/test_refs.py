import io
import json
from unittest.mock import patch

import pytest

from loretools.cli import _build_parser
from loretools.models import (
    AddResult,
    DeleteResult,
    GetResult,
    ListResult,
    Reference,
    ReferenceRow,
    RenameResult,
    UpdateResult,
)


def _run(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def test_refs_add_valid_json(capsys):
    result = AddResult(citekey="key1")
    with patch("loretools.add_reference", return_value=result) as mock_add:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "add", '{"title": "A"}'])
        assert exc_info.value.code == 0
        mock_add.assert_called_once_with({"title": "A"})
        data = json.loads(capsys.readouterr().out)
        assert data["citekey"] == "key1"
        assert data["error"] is None


def test_refs_add_invalid_json(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _run(["refs", "add", "not-json"])
    assert exc_info.value.code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["error"] is not None


def test_refs_add_from_stdin(capsys, monkeypatch):
    result = AddResult(citekey="key2")
    fake_stdin = io.StringIO('{"title": "B"}')
    fake_stdin.isatty = lambda: False
    monkeypatch.setattr("sys.stdin", fake_stdin)
    with patch("loretools.add_reference", return_value=result) as mock_add:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "add"])
        assert exc_info.value.code == 0
        mock_add.assert_called_once_with({"title": "B"})


def test_refs_get_calls_get_reference(capsys):
    ref = Reference(id="key1", type="article", title="T")
    result = GetResult(reference=ref)
    with patch("loretools.get_reference", return_value=result) as mock_get:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "get", "key1"])
        assert exc_info.value.code == 0
        mock_get.assert_called_once_with(citekey="key1", uid=None)


def test_refs_get_with_uid(capsys):
    ref = Reference(id="key1", type="article")
    result = GetResult(reference=ref)
    with patch("loretools.get_reference", return_value=result) as mock_get:
        with pytest.raises(SystemExit):
            _run(["refs", "get", "key1", "--uid", "abc123"])
        mock_get.assert_called_once_with(citekey="key1", uid="abc123")


def test_refs_update_valid_json(capsys):
    result = UpdateResult(citekey="key1")
    with patch("loretools.update_reference", return_value=result) as mock_update:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "update", "key1", '{"title": "New"}'])
        assert exc_info.value.code == 0
        mock_update.assert_called_once_with("key1", {"title": "New"})


def test_refs_update_invalid_json(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _run(["refs", "update", "key1", "bad-json"])
    assert exc_info.value.code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["error"] is not None


def test_refs_rename_calls_rename_reference():
    result = RenameResult(old_key="old", new_key="new")
    with patch("loretools.rename_reference", return_value=result) as mock_rename:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "rename", "old", "new"])
        assert exc_info.value.code == 0
        mock_rename.assert_called_once_with("old", "new")


def test_refs_delete_calls_delete_reference():
    result = DeleteResult(deleted=True)
    with patch("loretools.delete_reference", return_value=result) as mock_del:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "delete", "key1"])
        assert exc_info.value.code == 0
        mock_del.assert_called_once_with("key1")


def test_refs_list_json_output(capsys):
    rows = [ReferenceRow(citekey="k1", title="Title", authors="Auth", year=2020)]
    result = ListResult(references=rows, total=1, page=1)
    with patch("loretools.list_references", return_value=result) as mock_list:
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "list"])
        assert exc_info.value.code == 0
        mock_list.assert_called_once_with(page=1)
        data = json.loads(capsys.readouterr().out)
        assert "references" in data
        assert data["total"] == 1
        assert data["references"][0]["citekey"] == "k1"


def test_refs_list_page_arg():
    rows = []
    result = ListResult(references=rows, total=0, page=2)
    with patch("loretools.list_references", return_value=result) as mock_list:
        with pytest.raises(SystemExit):
            _run(["refs", "list", "--page", "2"])
        mock_list.assert_called_once_with(page=2)


def test_refs_filter_all_args(capsys):
    rows = [ReferenceRow(citekey="k1")]
    result = ListResult(references=rows, total=1, page=1)
    with patch("loretools.filter_references", return_value=result) as mock_filter:
        with pytest.raises(SystemExit) as exc_info:
            _run(
                [
                    "refs",
                    "filter",
                    "--query",
                    "Q",
                    "--author",
                    "A",
                    "--year",
                    "2021",
                    "--type",
                    "article",
                    "--has-file",
                    "--staging",
                    "--page",
                    "3",
                ]
            )
        assert exc_info.value.code == 0
        mock_filter.assert_called_once_with(
            query="Q",
            author="A",
            year=2021,
            ref_type="article",
            has_file=True,
            staging=True,
            page=3,
        )


def test_refs_filter_json_output(capsys):
    rows = [
        ReferenceRow(citekey="k2", title="Some Title", authors="Author X", year=2022)
    ]
    result = ListResult(references=rows, total=1, page=1)
    with patch("loretools.filter_references", return_value=result):
        with pytest.raises(SystemExit) as exc_info:
            _run(["refs", "filter", "--query", "test"])
        assert exc_info.value.code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["references"][0]["citekey"] == "k2"
