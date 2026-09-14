from __future__ import annotations

from pathlib import Path


def comment_source_file(root_path: str, file_path: str) -> Path | None:
    """Absolute `.tex` path if it is a file still under ``root_path``."""
    try:
        root = Path(root_path).resolve()
        path = (root / file_path).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return None
    if not path.is_file():
        return None
    return path
