"""Registered papers in the store. Disk YAML/env stays in ``config``."""

from __future__ import annotations

from pathlib import Path

from reviewdistill.config import llm_config_from_project_root, paper_key_set
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


def llm_selected_payload(project_id: str) -> dict | None:
    init_db()
    with get_session() as session:
        project = session.get(Project, project_id)
    if project is None:
        return None
    root = Path(project.root_path)
    cfg = llm_config_from_project_root(root)
    provider = cfg.llm_provider if cfg else None
    model = cfg.llm_model if cfg else None
    if provider and provider.lower() == "mock":
        provider = None
        model = None
    return {
        "project_id": project.id,
        "provider": provider,
        "model": model,
        "key_set": paper_key_set(root, provider),
    }
