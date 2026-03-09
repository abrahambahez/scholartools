import json
import os
from pathlib import Path

from pydantic import BaseModel, Field


class LocalSettings(BaseModel):
    library_path: str = "lib.json"
    files_dir: str = "data/files"


class SourceConfig(BaseModel):
    name: str
    enabled: bool = True
    api_key: str | None = None
    email: str | None = None


def _default_sources() -> list[SourceConfig]:
    return [
        SourceConfig(name="crossref"),
        SourceConfig(name="semantic_scholar"),
        SourceConfig(name="arxiv"),
        SourceConfig(name="latindex"),
        SourceConfig(name="google_books"),
    ]


class ApiSettings(BaseModel):
    sources: list[SourceConfig] = Field(default_factory=_default_sources)


class LlmSettings(BaseModel):
    model: str = "claude-sonnet-4-6"
    anthropic_api_key: str | None = None


class Settings(BaseModel):
    backend: str = "local"
    local: LocalSettings = Field(default_factory=LocalSettings)
    apis: ApiSettings = Field(default_factory=ApiSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)


_settings: Settings | None = None


def _find_config() -> Path | None:
    if env := os.environ.get("SCHOLARTOOLS_CONFIG"):
        return Path(env)
    local = Path(".scholartools/config.json")
    if local.exists():
        return local
    global_ = Path.home() / ".config" / "scholartools" / "config.json"
    if global_.exists():
        return global_
    return None


def load_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    config_path = _find_config()
    if config_path and config_path.exists():
        _settings = Settings.model_validate(json.loads(config_path.read_text()))
    else:
        _settings = Settings()

    if not _settings.llm.anthropic_api_key:
        _settings.llm.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if lib_path := os.environ.get("SCHOLARTOOLS_LIBRARY_PATH"):
        _settings.local.library_path = lib_path
    if files_dir := os.environ.get("SCHOLARTOOLS_FILES_DIR"):
        _settings.local.files_dir = files_dir
    if api_key := os.environ.get("GBOOKS_API_KEY"):
        for src in _settings.apis.sources:
            if src.name == "google_books":
                src.api_key = api_key

    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
