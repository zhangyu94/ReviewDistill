import re

import pytest
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
    for name in ("init", "extract", "export", "ui", "paths"):
        assert _lists_command(text, name)
    assert not _lists_command(text, "serve")


def test_export_help_lists_format_and_output():
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    text = _plain(result.stdout)
    assert "--format" in text
    assert "--output" in text
    assert "--id" in text


def test_paths_prints_home_and_database(rd_home):
    result = runner.invoke(app, ["paths"])
    assert result.exit_code == 0, result.stdout
    from reviewdistill.paths import data_location

    loc = data_location()
    assert f"Home: {loc['home']}" in result.stdout
    assert f"Comments: {loc['comments']}" in result.stdout
    assert "REVIEWDISTILL_HOME" not in result.stdout
    assert "whole folder" in result.stdout
    assert "paths move" in result.stdout
    assert "paths use" in result.stdout


def test_paths_help_lists_use_and_move():
    result = runner.invoke(app, ["paths", "--help"])
    assert result.exit_code == 0, result.stdout
    text = _plain(result.stdout)
    assert _lists_command(text, "use")
    assert _lists_command(text, "move")


def test_paths_use_persists_folder(rd_home, tmp_path):
    dest = tmp_path / "Documents" / "reviewdistill"
    result = runner.invoke(app, ["paths", "use", str(dest)])
    assert result.exit_code == 0, result.stdout
    assert f"Home: {dest.resolve()}" in result.stdout
    shown = runner.invoke(app, ["paths"])
    assert shown.exit_code == 0, shown.stdout
    assert f"Home: {dest.resolve()}" in shown.stdout


def test_paths_move_copies_then_uses(rd_home, tmp_path):
    (rd_home / "comments.jsonl").write_text("{}\n")
    dest = tmp_path / "Documents" / "reviewdistill"
    result = runner.invoke(app, ["paths", "move", str(dest)])
    assert result.exit_code == 0, result.stdout
    assert f"Home: {dest.resolve()}" in result.stdout
    assert (dest / "comments.jsonl").is_file()
    assert (rd_home / "comments.jsonl").is_file()


def test_paths_move_exits_when_already_using_folder(rd_home):
    result = runner.invoke(app, ["paths", "move", str(rd_home)])
    assert result.exit_code == 1
    assert "Already using that folder." in result.output


def test_paths_move_exits_when_destination_is_nonempty(rd_home, tmp_path):
    dest = tmp_path / "taken"
    dest.mkdir()
    (dest / "other.txt").write_text("no")
    result = runner.invoke(app, ["paths", "move", str(dest)])
    assert result.exit_code == 1
    assert "already has files" in result.output


@pytest.mark.parametrize("name", ["code", "watch", "taxonomy", "cluster", "serve"])
def test_removed_commands_are_unknown(name):
    result = runner.invoke(app, [name])
    assert result.exit_code != 0
    text = _plain(f"{result.stdout}\n{result.stderr}\n{result.output}").lower()
    assert "no such command" in text
