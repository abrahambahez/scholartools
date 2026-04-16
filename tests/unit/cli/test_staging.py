import json
from unittest.mock import patch

import pytest

from loretools.cli import _build_parser
from loretools.models import (
    DeleteStagedResult,
    ListStagedResult,
    MergeResult,
    ReferenceRow,
    StageResult,
)


def _run(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def test_stage_calls_stage_reference():
    result = StageResult(citekey="x2024")
    with patch("loretools.stage_reference", return_value=result) as mock:
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "stage", '{"title":"X"}'])
        assert exc_info.value.code == 0
        mock.assert_called_once_with({"title": "X"}, file_path=None)


def test_stage_with_file_calls_stage_reference_with_file_path():
    result = StageResult(citekey="x2024")
    with patch("loretools.stage_reference", return_value=result) as mock:
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "stage", '{"title":"X"}', "--file", "/path/to/file"])
        assert exc_info.value.code == 0
        mock.assert_called_once_with({"title": "X"}, file_path="/path/to/file")


def test_stage_invalid_json_outputs_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _run(["staging", "stage", "not-json"])
    assert exc_info.value.code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["error"] is not None


def test_list_staged_calls_list_staged():
    result = ListStagedResult(references=[], total=0, page=1, pages=1)
    with patch("loretools.list_staged", return_value=result) as mock:
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "list-staged"])
        assert exc_info.value.code == 0
        mock.assert_called_once_with(page=1)


def test_list_staged_json_output(capsys):
    row = ReferenceRow(
        citekey="abc2020", title="Some Title", authors="Doe, J.", year=2020
    )
    result = ListStagedResult(references=[row], total=1, page=1, pages=1)
    with patch("loretools.list_staged", return_value=result):
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "list-staged"])
        assert exc_info.value.code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["references"][0]["citekey"] == "abc2020"


def test_delete_staged_calls_delete_staged():
    result = DeleteStagedResult(deleted=True)
    with patch("loretools.delete_staged", return_value=result) as mock:
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "delete-staged", "foo"])
        assert exc_info.value.code == 0
        mock.assert_called_once_with("foo")


def test_merge_calls_merge_defaults():
    result = MergeResult(promoted=[], errors={}, skipped=[])
    with patch("loretools.merge", return_value=result) as mock:
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "merge"])
        assert exc_info.value.code == 0
        mock.assert_called_once_with(omit=None, allow_semantic=False)


def test_merge_with_omit_and_allow_semantic():
    result = MergeResult(promoted=["k1", "k2"], errors={}, skipped=[])
    with patch("loretools.merge", return_value=result) as mock:
        with pytest.raises(SystemExit) as exc_info:
            _run(["staging", "merge", "--omit", "k1,k2", "--allow-semantic"])
        assert exc_info.value.code == 0
        mock.assert_called_once_with(omit=["k1", "k2"], allow_semantic=True)
