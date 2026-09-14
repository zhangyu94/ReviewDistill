"""Registered papers in the store. Disk YAML stays in ``config``."""

from __future__ import annotations

from pathlib import Path

from reviewdistill.db.models import Project
from reviewdistill.db.session import get_session, init_db
from reviewdistill.paths import find_project_root


def list_registered_project_rows() -> list[dict]:
    init_db()
    rows = []
    with get_session() as session:
        for project in session.find(Project):
            rows.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "root_path": project.root_path,
                }
            )
    return rows


def default_registered_project_id(*, cwd: Path | None = None) -> str | None:
    root = find_project_root(cwd)
    if root is None:
        return None
    resolved = root.resolve()
    for row in list_registered_project_rows():
        if Path(row["root_path"]).resolve() == resolved:
            return row["id"]
    return None
