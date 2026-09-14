from pathlib import Path

from typer.testing import CliRunner

from reviewdistill.cli.app import app
from reviewdistill.config import load_project_config
from reviewdistill.db.models import Project
from reviewdistill.db.session import get_session

runner = CliRunner()


def test_init_writes_project_config_and_db_row(db, tmp_path: Path, monkeypatch):
    repo = tmp_path / "paper-01"
    repo.mkdir()
    monkeypatch.chdir(repo)
    result = runner.invoke(
        app,
        ["init", "--name", "paper-01", "--command", "note", "--command", "myremark"],
    )
    assert result.exit_code == 0, result.stdout

    config = load_project_config(repo)
    assert config.name == "paper-01"
    assert config.latex_commands == ["note", "myremark"]
    assert (repo / ".reviewdistill" / "config.yaml").is_file()
    gitignore = (repo / ".reviewdistill" / ".gitignore").read_text()
    assert ".env" in gitignore
    assert not (repo / ".reviewdistill" / ".env.example").exists()
    readme = (repo / ".reviewdistill" / "README.md").read_text()
    assert "ReviewDistill" in readme
    assert "latex_commands:" in readme
    assert "llm:" not in readme
    assert "DEEPSEEK_API_KEY" not in readme
    assert "Settings" in readme
    assert "inbox" not in readme.lower()

    with get_session() as session:
        project = session.get(Project, config.id)
        assert project is not None
        assert project.root_path == str(repo.resolve())


def test_init_is_idempotent(db, tmp_path: Path, monkeypatch):
    repo = tmp_path / "paper-01"
    repo.mkdir()
    monkeypatch.chdir(repo)
    first = runner.invoke(app, ["init", "--name", "paper-01"])
    second = runner.invoke(app, ["init", "--name", "paper-01"])
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "already initialized" in second.stdout.lower()


def test_init_adds_missing_scaffold_on_existing_project(db, tmp_path: Path, monkeypatch):
    repo = tmp_path / "paper-01"
    repo.mkdir()
    monkeypatch.chdir(repo)
    runner.invoke(app, ["init", "--name", "paper-01"])
    readme = repo / ".reviewdistill" / "README.md"
    readme.unlink()
    again = runner.invoke(app, ["init", "--name", "paper-01"])
    assert again.exit_code == 0
    assert readme.is_file()
    assert not (repo / ".reviewdistill" / ".env.example").exists()
