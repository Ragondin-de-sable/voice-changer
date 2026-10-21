import json
import os
from pathlib import Path

APP_FOLDER_NAME = "VoiceChanger"
SETTINGS_FILE_NAME = "settings.json"
ERROR_LOG_FILE_NAME = "error.log"
DEFAULT_SETTINGS = {
    "host_api": "",
    "input": "",
    "output": "",
    "monitor_enabled": False,
    "monitor": "",
    "noise_gate_db": -50.0,
    "last_preset": "Normale",
    "next_hotkey": "<ctrl>+<shift>+<page_down>",
    "previous_hotkey": "<ctrl>+<shift>+<page_up>",
}


def app_data_folder():
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / APP_FOLDER_NAME


def settings_path():
    return app_data_folder() / SETTINGS_FILE_NAME


def error_log_path():
    return app_data_folder() / ERROR_LOG_FILE_NAME


def load_settings():
    path = settings_path()
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        stored = {}
    return {**DEFAULT_SETTINGS, **stored}


def save_settings(settings):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
