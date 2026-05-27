"""Persistent app-level settings (paths, EA file, Telegram URL).

Stored as JSON in `%APPDATA%\\Pro100GUI\\settings.json` (or the
platform-appropriate equivalent). Never overlaps with per-run state
held by orchestrator.SessionState -- those are run snapshots, this
is user preferences.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pro100gui.adapters.ea_version_checker import DEFAULT_POST_URL
from pro100gui.adapters.paths import DEFAULT_INSTALL_DIR, DEFAULT_PROJECT_DIR


def appdata_root() -> Path:
    """Per-user application data root (creates it if missing)."""
    base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    root = base / "Pro100GUI"
    root.mkdir(parents=True, exist_ok=True)
    return root


def default_settings_path() -> Path:
    return appdata_root() / "settings.json"


def default_results_dir() -> Path:
    return appdata_root() / "results"


@dataclass(slots=True)
class AppSettings:
    """User-facing app configuration -- persists across launches."""

    mt5_install_dir: str = str(DEFAULT_INSTALL_DIR)
    """Absolute path to the portable MT5 terminal root."""

    project_dir: str = str(DEFAULT_PROJECT_DIR)
    """User home root (used to locate the Common\\Files folder)."""

    ea_path: str = ""
    """Absolute path to the EA .ex5 the user downloaded from the
    canonical Telegram post. Empty until set in the GUI."""

    telegram_post_url: str = DEFAULT_POST_URL
    """Canonical post URL used by EAVersionChecker."""

    results_dir: str = ""
    """Output directory for per-run CSVs and the final PDF. Defaults
    to the appdata results subfolder when left blank."""

    last_session_path: str = ""
    """Path to the most recently saved session JSON (for Resume)."""

    def effective_results_dir(self) -> Path:
        return Path(self.results_dir) if self.results_dir else default_results_dir()


def load_settings(path: Path | None = None) -> AppSettings:
    """Load settings or return defaults if the file does not yet exist."""
    p = path or default_settings_path()
    if not p.is_file():
        return AppSettings()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()
    fields = {f for f in AppSettings.__slots__}
    clean = {k: v for k, v in raw.items() if k in fields}
    return AppSettings(**clean)


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    """Atomically write settings JSON. Returns the path written."""
    p = path or default_settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(asdict(settings), f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return p
