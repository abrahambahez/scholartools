import json
from unittest.mock import patch

import pytest

from scholartools.cli import _build_parser
from scholartools.models import ConflictRecord, PullResult, PushResult, Result


def _run(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def test_sync_push_calls_push():
    result = PushResult(entries_pushed=1)
    with patch("scholartools.push", return_value=result) as mock_push:
        with pytest.raises(SystemExit) as exc_info:
            _run(["sync", "push"])
        assert exc_info.value.code == 0
        mock_push.assert_called_once_with()


def test_sync_pull_calls_pull():
    result = PullResult(applied_count=2)
    with patch("scholartools.pull", return_value=result) as mock_pull:
        with pytest.raises(SystemExit) as exc_info:
            _run(["sync", "pull"])
        assert exc_info.value.code == 0
        mock_pull.assert_called_once_with()


def test_sync_snapshot_calls_create_snapshot(capsys):
    with patch("scholartools.create_snapshot", return_value=None) as mock_snap:
        with pytest.raises(SystemExit) as exc_info:
            _run(["sync", "snapshot"])
        assert exc_info.value.code == 0
        mock_snap.assert_called_once_with()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {"ok": True, "data": None, "error": None}


def test_sync_list_conflicts_calls_list_conflicts(capsys):
    record = ConflictRecord(
        uid="uid1",
        field="title",
        local_value="A",
        local_timestamp_hlc="0",
        remote_value="B",
        remote_timestamp_hlc="1",
        remote_peer_id="peer1",
    )
    with patch("scholartools.list_conflicts", return_value=[record]) as mock_lc:
        with pytest.raises(SystemExit) as exc_info:
            _run(["sync", "list-conflicts"])
        assert exc_info.value.code == 0
        mock_lc.assert_called_once_with()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["ok"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["uid"] == "uid1"


def test_sync_resolve_conflict_calls_resolve_conflict():
    result = Result(ok=True)
    with patch("scholartools.resolve_conflict", return_value=result) as mock_rc:
        with pytest.raises(SystemExit) as exc_info:
            _run(["sync", "resolve-conflict", "uid1", "field1", "value1"])
        assert exc_info.value.code == 0
        mock_rc.assert_called_once_with("uid1", "field1", "value1")


def test_sync_restore_calls_restore_reference():
    result = Result(ok=True)
    with patch("scholartools.restore_reference", return_value=result) as mock_rr:
        with pytest.raises(SystemExit) as exc_info:
            _run(["sync", "restore", "foo"])
        assert exc_info.value.code == 0
        mock_rr.assert_called_once_with("foo")
