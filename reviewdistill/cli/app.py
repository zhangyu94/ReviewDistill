from __future__ import annotations

from pathlib import Path

import typer

from reviewdistill.cli.extract import run_extract
from reviewdistill.cli.init import init_project
from reviewdistill.taxonomy.export import default_export_filename, export_rubric

app = typer.Typer(help="ReviewDistill: distill informal review comments into reusable review knowledge.")
paths_app = typer.Typer(help="Show or change the data folder.")
app.add_typer(paths_app, name="paths")


def _write_export(fmt: str, output: Path | None, label_ids: list[str] | None) -> None:
    text = export_rubric(fmt=fmt, label_ids=label_ids)
    path = output or Path(default_export_filename(fmt))
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
    id: list[str] | None = typer.Option(
        None,
        "--id",
        help="Label id to include (repeatable). Default: all active labels. Does not change labels in the UI.",
    ),
) -> None:
    """Export a review skill (Markdown) or taxonomy (YAML/JSON)."""
    _write_export(format, output, id or None)


@paths_app.callback(invoke_without_command=True)
def paths_callback(ctx: typer.Context) -> None:
    """Show where comments and labels are stored."""
    if ctx.invoked_subcommand is not None:
        return
    from reviewdistill.paths import data_location

    loc = data_location()
    typer.echo(f"Home: {loc['home']}")
    typer.echo(f"Comments: {loc['comments']}")
    typer.echo("")
    typer.echo(
        "Copy the home folder to back up (JSONL files; the whole folder, not a single file). "
        "reviewdistill paths move DIR copies this folder to DIR and keeps using it. "
        "reviewdistill paths use DIR points at a folder you already have. "
        "Restart ui or extract after changing the folder."
    )


@paths_app.command("use")
def paths_use(
    directory: Path = typer.Argument(..., help="Folder to store comments and labels."),
) -> None:
    """Use this folder for comments and labels from now on."""
    from reviewdistill.paths import HomePathError, use_home

    try:
        path = use_home(directory)
    except HomePathError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Home: {path}")
    typer.echo("Restart ui or extract if they are running.")


@paths_app.command("move")
def paths_move(
    directory: Path = typer.Argument(..., help="Empty folder to copy the current data into."),
) -> None:
    """Copy the current data folder here and keep using it."""
    from reviewdistill.paths import HomePathError, move_home

    try:
        path = move_home(directory)
    except HomePathError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Home: {path}")
    typer.echo("Left the previous folder in place. Restart ui or extract if they are running.")


@app.command("ui")
def ui_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """Start the local web UI."""
    from reviewdistill.cli.serve import run_serve

    run_serve(host=host, port=port)
