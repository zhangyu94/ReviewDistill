import re

from typer.testing import CliRunner

from reviewdistill.cli.app import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Help under FORCE_COLOR splits tokens with ANSI (``-`` then ``-watch``)."""
    return _ANSI.sub("", text)


def _lists_command(text: str, name: str) -> bool:
    return f"│ {name} " in text or f"\n  {name} " in text or f"\n  {name}\n" in text


def test_reviewdistill_help_lists_core_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    text = _plain(result.stdout)
    for name in ("init", "extract", "export", "serve"):
        assert _lists_command(text, name)


def test_extract_help_lists_watch_flag():
    result = runner.invoke(app, ["extract", "--help"])
    assert result.exit_code == 0
    assert "--watch" in _plain(result.stdout)


def test_export_help_lists_format_and_output():
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    text = _plain(result.stdout)
    assert "--format" in text
    assert "--output" in text


def test_serve_help_describes_workbench():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    text = _plain(result.stdout).lower()
    assert "workbench" in text


def test_reviewdistill_code_command_removed():
    result = runner.invoke(app, ["code"])
    assert result.exit_code != 0


def test_cluster_hidden_alias_still_runs(db):
    result = runner.invoke(app, ["cluster"])
    assert result.exit_code == 0, result.stdout
    assert "No recurring clusters found." in result.stdout
