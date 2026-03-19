import importlib.metadata
from unittest.mock import patch


def _get_version_from_parser():
    from scholartools.cli import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if hasattr(action, "version"):
            return action.version
    return None


def test_version_from_metadata():
    with patch("importlib.metadata.version", return_value="0.9.1"):
        version_str = _get_version_from_parser()
    assert version_str == "%(prog)s 0.9.1"


def test_version_fallback_to_env(monkeypatch):
    monkeypatch.setenv("SCHT_VERSION", "1.2.3")
    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        version_str = _get_version_from_parser()
    assert version_str == "%(prog)s 1.2.3"


def test_version_fallback_unknown(monkeypatch):
    monkeypatch.delenv("SCHT_VERSION", raising=False)
    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        version_str = _get_version_from_parser()
    assert version_str == "%(prog)s unknown"
