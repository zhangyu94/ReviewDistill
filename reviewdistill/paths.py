from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

PROJECT_DIRNAME = ".reviewdistill"
PROJECT_CONFIG_NAME = "config.yaml"


class HomePathError(Exception):
    """User-facing error when choosing or moving the data folder."""


def locator_path() -> Path:
    return Path.home() / ".config" / "reviewdistill" / "home"


def home_dir() -> Path:
    loc = locator_path()
    if loc.is_file():
        text = loc.read_text(encoding="utf-8").strip()
        if text:
            return Path(text).expanduser()
    return Path.home() / ".reviewdistill"


def db_path() -> Path:
    return home_dir() / "reviewdistill.db"


def data_location() -> dict[str, str]:
    """Absolute home folder and database path for CLI, API, and backup docs."""
    home = home_dir().expanduser().resolve()
    return {
        "home": str(home),
        "database": str(home / "reviewdistill.db"),
    }


def home_config_path() -> Path:
    return home_dir() / "config.yaml"


def use_home(directory: Path | str) -> Path:
    dest = Path(directory).expanduser().resolve()
    if dest.exists() and not dest.is_dir():
        raise HomePathError(f"{dest} is not a folder.")
    dest.mkdir(parents=True, exist_ok=True)
    loc = locator_path()
    loc.parent.mkdir(parents=True, exist_ok=True)
    loc.write_text(str(dest) + "\n", encoding="utf-8")
    return dest


def home_is_busy(home: Path) -> bool:
    db = home / "reviewdistill.db"
    if not db.is_file():
        return False
    try:
        conn = sqlite3.connect(str(db), timeout=0.2)
        try:
            conn.execute("PRAGMA locking_mode=EXCLUSIVE")
            conn.execute("BEGIN EXCLUSIVE")
            conn.rollback()
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return True
    except sqlite3.DatabaseError as exc:
        raise HomePathError(
            f"Could not lock {db}. Stop reviewdistill serve and extract, then try again."
        ) from exc
    return False


def move_home(directory: Path | str) -> Path:
    dest = Path(directory).expanduser().resolve()
    src = home_dir().expanduser().resolve()
    if dest == src:
        raise HomePathError("Already using that folder.")
    if dest.is_relative_to(src):
        raise HomePathError("Choose a folder outside the current home.")
    if not src.exists():
        raise HomePathError(f"Nothing to copy from {src}.")
    if dest.exists() and not dest.is_dir():
        raise HomePathError(f"{dest} is not a folder.")
    if dest.exists() and any(dest.iterdir()):
        raise HomePathError(f"{dest} already has files. Choose an empty folder.")
    if home_is_busy(src):
        raise HomePathError("Stop reviewdistill serve and extract, then try again.")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, dirs_exist_ok=True)
    except OSError as exc:
        raise HomePathError(f"Could not copy {src} to {dest}.") from exc
    return use_home(dest)


def find_project_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / PROJECT_DIRNAME / PROJECT_CONFIG_NAME).is_file():
            return candidate
    return None


def project_config_path(root: Path) -> Path:
    return root / PROJECT_DIRNAME / PROJECT_CONFIG_NAME


def project_env_path(root: Path) -> Path:
    return root / PROJECT_DIRNAME / ".env"
