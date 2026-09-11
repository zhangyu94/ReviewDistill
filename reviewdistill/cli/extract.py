from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import typer
from watchfiles import DefaultFilter
from watchfiles import watch as watch_files

from reviewdistill.extraction.incremental import extract_project, format_extract_summary
from reviewdistill.paths import find_project_root

Watcher = Callable[..., Iterator[Any]]


class TexFilter(DefaultFilter):
    ignore_dirs = (*DefaultFilter.ignore_dirs, ".reviewdistill")

    def __call__(self, change, path: str) -> bool:
        return super().__call__(change, path) and path.endswith(".tex")


def run_extract(
    cwd: Path | None = None,
    *,
    watch: bool = False,
    watcher: Watcher | None = None,
) -> None:
    root = find_project_root(cwd or Path.cwd())
    if root is None:
        raise typer.BadParameter("No .reviewdistill/config.yaml found. Run `reviewdistill init` first.")
    if not watch:
        summary = extract_project(root)
        typer.echo(format_extract_summary(summary))
        return
    loop = watcher or watch_files
    try:
        # Pause after LaTeX saves (750ms), then the same extract. No labeling, no quality stamps.
        for _changes in loop(root, debounce=750, step=750, watch_filter=TexFilter()):
            summary = extract_project(root)
            typer.echo(format_extract_summary(summary))
    except KeyboardInterrupt:
        return
