from __future__ import annotations

from pathlib import Path

import typer

from reviewdistill.cli.cluster import run_cluster
from reviewdistill.cli.extract import run_extract
from reviewdistill.cli.init import init_project
from reviewdistill.taxonomy.export import export_rubric

app = typer.Typer(help="ReviewDistill: distill informal review comments into reusable review knowledge.")
taxonomy_app = typer.Typer(hidden=True, help="Hidden alias for `export`.")
app.add_typer(taxonomy_app, name="taxonomy")


def _write_export(fmt: str, output: Path | None) -> None:
    text = export_rubric(fmt=fmt)
    path = output or Path("review-rubric.md" if fmt == "md" else f"review-rubric.{fmt}")
    path.write_text(text)
    typer.echo(f"Wrote {path}")


@app.command("init")
def init_cmd(
    name: str | None = typer.Option(None, "--name", help="Project name"),
    command: list[str] | None = typer.Option(
        None,
        "--command",
        help="LaTeX comment command (repeatable). Default: myremark",
    ),
) -> None:
    """Initialize a ReviewDistill project in the current repository."""
    init_project(name=name, commands=command)


@app.command()
def extract(
    watch: bool = typer.Option(
        False,
        "--watch",
        help="Keep extracting after .tex files settle.",
    ),
) -> None:
    """Extract new proofreading comments from the manuscript."""
    run_extract(watch=watch)


@app.command("export")
def export_cmd(
    format: str = typer.Option("md", "--format", help="md | yaml | json"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Export reusable review knowledge."""
    _write_export(format, output)


@app.command(hidden=True)
def cluster() -> None:
    """Hidden alias. Discover recurring patterns among comments."""
    run_cluster()


@taxonomy_app.command("export")
def taxonomy_export(
    format: str = typer.Option("md", "--format", help="md | yaml | json"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Hidden alias for `export`."""
    _write_export(format, output)


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """Start the local workbench web UI."""
    from reviewdistill.cli.serve import run_serve

    run_serve(host=host, port=port)


@app.command("watch", hidden=True)
def watch_cmd() -> None:
    """Hidden alias for `extract --watch`."""
    run_extract(watch=True)
