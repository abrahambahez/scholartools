import json

import pytest

from scholartools.config import load_settings, reset_settings


@pytest.fixture(autouse=True)
def clear_settings():
    reset_settings()
    yield
    reset_settings()


def test_defaults_when_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHOLARTOOLS_CONFIG", str(tmp_path / "nonexistent.json"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = load_settings()
    assert s.backend == "local"
    assert s.local.library_path == "lib.json"
    assert s.local.files_dir == "data/files"
    assert len(s.apis.sources) == 5
    assert s.apis.sources[0].name == "crossref"
    assert s.llm.model == "claude-sonnet-4-6"
    assert s.llm.anthropic_api_key is None


def test_loads_from_config_file(tmp_path, monkeypatch):
    config = {
        "backend": "local",
        "local": {"library_path": "custom/lib.json", "files_dir": "custom/files"},
        "apis": {"sources": [{"name": "crossref", "enabled": True}]},
        "llm": {"model": "claude-opus-4-6"},
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    monkeypatch.setenv("SCHOLARTOOLS_CONFIG", str(config_file))
    s = load_settings()
    assert s.local.library_path == "custom/lib.json"
    assert s.apis.sources[0].name == "crossref"
    assert s.llm.model == "claude-opus-4-6"


def test_anthropic_key_fallback_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHOLARTOOLS_CONFIG", str(tmp_path / "nonexistent.json"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    s = load_settings()
    assert s.llm.anthropic_api_key == "sk-test-key"


def test_config_key_overrides_env(tmp_path, monkeypatch):
    config = {"llm": {"anthropic_api_key": "sk-from-config"}}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    monkeypatch.setenv("SCHOLARTOOLS_CONFIG", str(config_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
    s = load_settings()
    assert s.llm.anthropic_api_key == "sk-from-config"


def test_settings_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHOLARTOOLS_CONFIG", str(tmp_path / "nonexistent.json"))
    s1 = load_settings()
    s2 = load_settings()
    assert s1 is s2


def test_source_order_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHOLARTOOLS_CONFIG", str(tmp_path / "nonexistent.json"))
    s = load_settings()
    names = [src.name for src in s.apis.sources]
    assert names == [
        "crossref",
        "semantic_scholar",
        "arxiv",
        "latindex",
        "google_books",
    ]
