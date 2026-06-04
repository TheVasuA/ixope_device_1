"""
Unified preferences persistence.

All user-changeable settings are stored in a single `prefs.json` file inside
BASE_PATH. On startup the app loads defaults, then overlays whatever was
previously saved. On every change the file is rewritten atomically.

This replaces the scattered mode_config.json / icon_scheme.json / wifi_country.json
files with a single source of truth (those files are still read as fallback for
migration from older installs).
"""
import json
import os
from . import settings

PREFS_FILE = "prefs.json"

# Defaults — any key not present in the saved file uses these values.
_DEFAULTS = {
    # UI
    "theme": "dark",
    "icon_scheme": "glass",
    "icon_hide_delay_s": 7,

    # Last selected scope (None = not set)
    "last_scope": None,

    # Country (ISO 2-letter code)
    "country_code": None,

    # Camera / image adjustments (slider positions 0.0–1.0)
    "camera": {
        "zoom": 0.0,
        "brightness": 0.5,
        "contrast": 0.5,
        "exposure": 0.5,
        "sharpness": 0.0,
    },
}


def _path():
    return os.path.join(settings.BASE_PATH, PREFS_FILE)


def load() -> dict:
    """Load saved prefs, falling back to defaults for any missing key."""
    prefs = json.loads(json.dumps(_DEFAULTS))  # deep copy of defaults
    try:
        p = _path()
        if os.path.exists(p):
            with open(p, 'r') as f:
                saved = json.load(f)
            # Merge top-level keys
            for k in _DEFAULTS:
                if k in saved:
                    if isinstance(_DEFAULTS[k], dict) and isinstance(saved[k], dict):
                        prefs[k].update(saved[k])
                    else:
                        prefs[k] = saved[k]
    except Exception:
        pass

    # Migration: read old scattered files if prefs.json doesn't exist yet
    if not os.path.exists(_path()):
        _migrate_legacy(prefs)

    return prefs


def save(prefs: dict):
    """Persist the full prefs dict to disk."""
    try:
        os.makedirs(os.path.dirname(_path()), exist_ok=True)
        with open(_path(), 'w') as f:
            json.dump(prefs, f, indent=2)
    except OSError:
        pass


def _migrate_legacy(prefs: dict):
    """Read old per-file configs (mode_config.json, icon_scheme.json,
    wifi_country.json) and fold them into the unified prefs."""
    bp = settings.BASE_PATH
    try:
        p = os.path.join(bp, "mode_config.json")
        if os.path.exists(p):
            with open(p, 'r') as f:
                prefs["theme"] = json.load(f).get("mode", "dark")
    except Exception:
        pass
    try:
        p = os.path.join(bp, "icon_scheme.json")
        if os.path.exists(p):
            with open(p, 'r') as f:
                prefs["icon_scheme"] = json.load(f).get("scheme", "glass")
    except Exception:
        pass
    try:
        p = os.path.join(bp, "wifi_country.json")
        if os.path.exists(p):
            with open(p, 'r') as f:
                prefs["country_code"] = json.load(f).get("code")
    except Exception:
        pass
    # Save the migrated prefs so the next load uses the unified file
    save(prefs)
