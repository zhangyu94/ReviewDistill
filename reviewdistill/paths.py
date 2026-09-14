from __future__ import annotations

import fcntl
import shutil
from pathlib import Path

PROJECT_DIRNAME = ".reviewdistill"
PROJECT_CONFIG_NAME = "config.yaml"
COMMENTS_FILE = "comments.jsonl"
LOCK_NAME = ".lock"
STAGING_DIRNAME = ".commit"

HOME_README = """\
# ReviewDistill data

Comments, issue types, and coding live in this folder as JSONL files.

## Backup

Copy the whole folder. Do not edit JSONL while `reviewdistill serve` or `extract` is running.

## Move

Quit `reviewdistill serve`, then:

    reviewdistill paths move ~/Documents/reviewdistill

Or point at a folder you already copied:

    reviewdistill paths use DIR

Restart `reviewdistill serve` afterwards.

The assistant API key is in `.env` (gitignored). Do not commit `.env`.
"""


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


def comments_path() -> Path:
    return home_dir() / COMMENTS_FILE


def data_location() -> dict[str, str]:
    """Absolute home folder and comments JSONL path for CLI, API, and backup docs."""
    home = home_dir().expanduser().resolve()
    return {
        "home": str(home),
        "comments": str(home / COMMENTS_FILE),
    }


def home_config_path() -> Path:
    return home_dir() / "config.yaml"


def home_env_path() -> Path:
    """Assistant API keys. ``paths move`` copies this with the home tree."""
    return home_dir() / ".env"


def ensure_home_readme(home: Path) -> None:
    path = home / "README.md"
    if path.exists():
        return
    path.write_text(HOME_README, encoding="utf-8")


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
    lock = home / LOCK_NAME
    home.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as fp:
        try:
            fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fp, fcntl.LOCK_UN)
    return False


def _ignore_ephemeral(_directory: str, names: list[str]) -> list[str]:
    return [
        name
        for name in names
        if name in {LOCK_NAME, STAGING_DIRNAME} or name.endswith(".jsonl.tmp")
    ]


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
    dest.parent.mkdir(parents=True, exist_ok=True)
    lock = src / LOCK_NAME
    src.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as fp:
        try:
            fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HomePathError("Stop reviewdistill serve and extract, then try again.") from exc
        if dest.exists() and any(dest.iterdir()):
            raise HomePathError(f"{dest} already has files. Choose an empty folder.")
        from reviewdistill.db.session import apply_pending_commit

        apply_pending_commit(src)
        try:
            shutil.copytree(src, dest, dirs_exist_ok=True, ignore=_ignore_ephemeral)
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
