import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scholartools.config import load_settings, reset_settings
from scholartools.models import LlmSettings, LocalSettings, SourceConfig


@pytest.fixture(autouse=True)
def clear_settings():
    reset_settings()
    yield
    reset_settings()


def test_defaults_when_no_config_creates_file(tmp_path, monkeypatch):
    config_path = tmp_path / ".config" / "scholartools" / "config.json"
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = load_settings()
    assert s.backend == "local"
    assert config_path.exists()
    data = json.loads(config_path.read_text())
    assert "local" in data


def test_loads_from_existing_config_file(tmp_path, monkeypatch):
    library_dir = str(tmp_path / "mylib")
    config_path = tmp_path / "config.json"
    config = {
        "backend": "local",
        "local": {"library_dir": library_dir},
        "apis": {"sources": [{"name": "crossref", "enabled": True}]},
        "llm": {"model": "claude-opus-4-6"},
    }
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    s = load_settings()
    assert s.local.library_dir == Path(library_dir)
    assert s.local.library_file == Path(library_dir) / "library.json"
    assert s.local.files_dir == Path(library_dir) / "files"
    assert s.apis.sources[0].name == "crossref"
    assert s.llm.model == "claude-opus-4-6"


def test_library_dir_derives_paths(tmp_path):
    ls = LocalSettings(library_dir=tmp_path / "mylib")
    assert ls.library_file == tmp_path / "mylib" / "library.json"
    assert ls.files_dir == tmp_path / "mylib" / "files"


def test_settings_cached(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    s1 = load_settings()
    s2 = load_settings()
    assert s1 is s2


def test_source_config_forbids_api_key():
    with pytest.raises(ValidationError):
        SourceConfig(name="google_books", api_key="secret")


def test_llm_settings_forbids_anthropic_api_key():
    with pytest.raises(ValidationError):
        LlmSettings(anthropic_api_key="sk-test")


def test_config_file_with_api_key_raises(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config = {
        "backend": "local",
        "local": {},
        "apis": {"sources": []},
        "llm": {"anthropic_api_key": "sk-from-config"},
    }
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    with pytest.raises(ValidationError):
        load_settings()


def test_source_order_preserved(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    s = load_settings()
    names = [src.name for src in s.apis.sources]
    assert names == [
        "crossref",
        "semantic_scholar",
        "arxiv",
        "google_books",
    ]


def test_partial_config_raises_with_message(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"backend": "local"}))
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    with pytest.raises(ValueError, match="incomplete"):
        load_settings()


def test_api_keys_not_in_settings(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("scholartools.config.CONFIG_PATH", config_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GBOOKS_API_KEY", "gbooks-test")
    s = load_settings()
    assert not hasattr(s.llm, "anthropic_api_key")
    for src in s.apis.sources:
        assert not hasattr(src, "api_key")
