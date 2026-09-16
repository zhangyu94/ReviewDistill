from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIRNAME = ".reviewdistill"
PROJECT_CONFIG_NAME = "config.yaml"
COMMENTS_FILE = "comments.jsonl"
LOCK_NAME = ".lock"
STAGING_DIRNAME = ".commit"

HOME_README = """\
# ReviewDistill data

This folder is the ReviewDistill store on this computer: comments, labels, assignments, and assistant settings. It is not a paper repo. Each paper keeps comment-command names in its own `.reviewdistill/config.yaml`.

JSONL files hold one JSON object per line.

## Files

| File | What it is |
| --- | --- |
| `projects.jsonl` | Papers registered with ReviewDistill (`id`, `name`, `root_path`). |
| `comments.jsonl` | Extracted proofreading observations from those papers. |
| `assignments.jsonl` | AI and human label assignments on comments. |
| `labels.jsonl` | Live taxonomy: category names, parents, definitions. |
| `label_examples.jsonl` | Example passages attached to labels. |
| `history.jsonl` | Undo/redo log (header **History**). |
| `config.yaml` | Assistant provider and model (**Settings → Assistant**). |
| `.env` | Assistant API key. Gitignored. Do not commit it. |
| `.gitignore` | Ignores `.env` and `.lock`. |
| `.lock` | Held while `reviewdistill ui` or `extract` is using the store. Gitignored. |

`.commit/` and `*.jsonl.tmp` are write temporaries; ignore them.

## Backup

Copy the whole folder. Do not edit JSONL while `reviewdistill ui` or `extract` is running.

## Move

In Settings → Data, type a folder or Choose…, then Save to point ReviewDistill at it (same as `reviewdistill paths use DIR`). Open folder reveals it in the file manager.

To copy the current files into a new empty folder, quit `reviewdistill ui`, then:

    reviewdistill paths move ~/Documents/reviewdistill

Or point at a folder you already copied:

    reviewdistill paths use DIR

Restart `reviewdistill ui` afterwards.
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
        "file_url": home.as_uri(),
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
    text = str(directory).strip()
    if not text:
        raise HomePathError("Choose a folder.")
    dest = Path(text).expanduser().resolve()
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
            raise HomePathError("Stop reviewdistill ui and extract, then try again.") from exc
        if dest.exists() and any(dest.iterdir()):
            raise HomePathError(f"{dest} already has files. Choose an empty folder.")
        from reviewdistill.db.session import apply_pending_commit

        apply_pending_commit(src)
        try:
            shutil.copytree(src, dest, dirs_exist_ok=True, ignore=_ignore_ephemeral)
        except OSError as exc:
            raise HomePathError(f"Could not copy {src} to {dest}.") from exc
    return use_home(dest)


def _open_in_file_manager(path: Path) -> None:
    target = str(path)
    if sys.platform == "darwin":
        subprocess.Popen(["open", target])
    elif sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", target])


def reveal_in_file_manager(path: Path) -> None:
    """Select ``path`` in the OS file manager.

    Do not call ``_open_in_file_manager``: ``open`` / ``xdg-open`` on a ``.tex``
    file launches the default editor instead of showing the file in Finder.
    """
    target = str(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", target])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", target])
        else:
            _reveal_linux(path)
    except OSError as exc:
        raise HomePathError("Could not show this file on this computer.") from exc


def _reveal_linux(path: Path) -> None:
    for args in (
        ["nautilus", "--select", str(path)],
        ["dolphin", "--select", str(path)],
    ):
        try:
            subprocess.Popen(args)
            return
        except FileNotFoundError:
            continue
    subprocess.Popen(["xdg-open", str(path.parent)])


def open_data_folder() -> Path:
    home = home_dir().expanduser().resolve()
    if home.exists() and not home.is_dir():
        raise HomePathError(f"{home} is not a folder.")
    home.mkdir(parents=True, exist_ok=True)
    _open_in_file_manager(home)
    return home


def _applescript_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _choose_folder_macos(initial: Path | None) -> Path | None:
    prompt = _applescript_literal("Choose a ReviewDistill data folder")
    expr = f'choose folder with prompt "{prompt}"'
    if initial is not None and initial.is_dir():
        loc = _applescript_literal(str(initial))
        expr += f' default location POSIX file "{loc}"'
    result = subprocess.run(
        ["osascript", "-e", f"POSIX path of ({expr})"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    if text.endswith("/") and text != "/":
        text = text[:-1]
    return Path(text) if text else None


def _choose_folder_windows(initial: Path | None) -> Path | None:
    start = str(initial) if initial is not None and initial.is_dir() else ""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms\n"
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog\n"
        "$d.Description = 'Choose a ReviewDistill data folder'\n"
        "$d.ShowNewFolderButton = $true\n"
    )
    if start:
        escaped = start.replace("'", "''")
        script += f"$d.SelectedPath = '{escaped}'\n"
    script += (
        "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) "
        "{ Write-Output $d.SelectedPath }\n"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    text = result.stdout.strip()
    return Path(text) if text else None


def _choose_folder_linux(initial: Path | None) -> Path | None:
    start = str(initial) if initial is not None and initial.is_dir() else ""
    commands = [
        ["zenity", "--file-selection", "--directory", "--title=Choose a ReviewDistill data folder"],
        ["kdialog", "--getexistingdirectory", start or str(Path.home())],
    ]
    if start:
        commands[0].extend(["--filename", start.rstrip("/") + "/"])
    for args in commands:
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            continue
        if result.returncode != 0:
            return None
        text = result.stdout.strip()
        return Path(text) if text else None
    raise HomePathError("Could not open a folder picker. Type the path instead.")


def _choose_in_file_manager(initial: Path | None) -> Path | None:
    if sys.platform == "darwin":
        return _choose_folder_macos(initial)
    if sys.platform == "win32":
        return _choose_folder_windows(initial)
    return _choose_folder_linux(initial)


def choose_data_folder() -> Path | None:
    start = home_dir().expanduser()
    try:
        start = start.resolve()
    except OSError:
        pass
    initial = start if start.is_dir() else None
    chosen = _choose_in_file_manager(initial)
    if chosen is None:
        return None
    dest = chosen.expanduser().resolve()
    if dest.exists() and not dest.is_dir():
        raise HomePathError(f"{dest} is not a folder.")
    return dest


def find_project_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / PROJECT_DIRNAME / PROJECT_CONFIG_NAME).is_file():
            return candidate
    return None


def project_config_path(root: Path) -> Path:
    return root / PROJECT_DIRNAME / PROJECT_CONFIG_NAME
