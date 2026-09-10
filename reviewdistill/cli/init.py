from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import typer

from reviewdistill.config import ProjectConfig, ensure_project_scaffold, write_project_config
from reviewdistill.db.models import Project
from reviewdistill.db.session import get_session, init_db
from reviewdistill.paths import find_project_root, project_config_path


def init_project(
    name: str | None = None,
    commands: list[str] | None = None,
    cwd: Path | None = None,
) -> None:
    root = (cwd or Path.cwd()).resolve()
    existing_root = find_project_root(root)
    if existing_root is not None and project_config_path(existing_root).is_file():
        ensure_project_scaffold(existing_root)
        typer.echo(f"Project already initialized at {existing_root}")
        return

    init_db()
    config = ProjectConfig(
        id=str(uuid4()),
        name=name or root.name,
        latex_commands=commands or ["myremark"],
    )
    write_project_config(root, config)
    ensure_project_scaffold(root)
    with get_session() as session:
        session.add(Project(id=config.id, name=config.name, root_path=str(root)))
        session.commit()
    typer.echo(f"Initialized ReviewDistill project '{config.name}' ({config.id})")
