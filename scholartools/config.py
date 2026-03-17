import json
from pathlib import Path

from scholartools.models import (
    Settings,
)

CONFIG_PATH = Path.home() / ".config" / "scholartools" / "config.json"

_settings: Settings | None = None

_REQUIRED_KEYS = {"backend", "local", "apis", "llm"}

_LOCAL_COMPUTED = {
    "library_file",
    "files_dir",
    "staging_file",
    "staging_dir",
    "peers_dir",
}


def load_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            Settings().model_dump_json(indent=2, exclude={"local": _LOCAL_COMPUTED})
        )
    data = json.loads(CONFIG_PATH.read_text())
    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(
            f"Config file at {CONFIG_PATH} is incomplete. "
            f"Missing required keys: {sorted(missing)}. "
            "Please add them or delete the file to regenerate defaults."
        )
    _settings = Settings.model_validate(data)
    if _settings.sync is not None and _settings.peer is None:
        raise ValueError(
            "config.json has a 'sync' block but no 'peer' block. "
            "Add a 'peer' block with 'peer_id' and 'device_id' to identify"
            " this researcher."
        )
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
