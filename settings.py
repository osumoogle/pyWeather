import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "theme": "system",
    "last_zipcode": "",
}


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return {**_DEFAULTS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
