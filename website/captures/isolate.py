from __future__ import annotations

import os
from pathlib import Path

_SITECUSTOMIZE = """\
import logging


class _QuietBlake2(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return "blake2" not in msg


logging.getLogger().addFilter(_QuietBlake2())
"""


def capture_environ(work: Path) -> dict[str, str]:
    """Fake HOME in work. There is no REVIEWDISTILL_HOME; locator + store follow HOME."""
    home = work / "home"
    home.mkdir(parents=True, exist_ok=True)
    py_path = work / "pythonpath"
    py_path.mkdir(parents=True, exist_ok=True)
    (py_path / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
    env = os.environ.copy()
    env["HOME"] = str(home)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(py_path) + (":" + existing if existing else "")
    export = f'export PYTHONPATH="{py_path}:${{PYTHONPATH}}"\n'
    for name in (".bashrc", ".profile", ".bash_profile"):
        (home / name).write_text(export, encoding="utf-8")
    return env
