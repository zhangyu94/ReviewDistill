from __future__ import annotations

import os
from pathlib import Path

HOME_ENV = "REVIEWDISTILL_HOME"
PROJECT_DIRNAME = ".reviewdistill"
PROJECT_CONFIG_NAME = "config.yaml"


def home_dir() -> Path:
    raw = os.environ.get(HOME_ENV)
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".reviewdistill"


def db_path() -> Path:
    return home_dir() / "reviewdistill.db"


def home_config_path() -> Path:
    return home_dir() / "config.yaml"


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
