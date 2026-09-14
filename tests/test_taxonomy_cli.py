from typer.testing import CliRunner

from reviewdistill.cli.app import app
from reviewdistill.taxonomy.operations import create_issue_type

runner = CliRunner()


def test_export_cli_writes_markdown(db, tmp_path):
    create_issue_type(
        name="Overclaiming",
        definition="too strong",
    )
    out = tmp_path / "out.md"
    result = runner.invoke(app, ["export", "--format", "md", "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    text = out.read_text()
    assert "Overclaiming" in text
    assert f"Wrote {out}" in result.stdout


def test_export_cli_selected_id_omits_other_types(db, tmp_path):
    parent = create_issue_type(name="Parent", definition="p")
    child = create_issue_type(name="Child", definition="c", parent_id=parent.id)
    out = tmp_path / "out.md"
    result = runner.invoke(app, ["export", "--format", "md", "--id", child.id, "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    text = out.read_text()
    assert "## Child" in text
    assert "## Parent" not in text


def test_export_cli_default_markdown_is_skill_md(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_issue_type(name="Overclaiming", definition="too strong")
    result = runner.invoke(app, ["export", "--format", "md"])
    assert result.exit_code == 0, result.stdout
    path = tmp_path / "SKILL.md"
    assert path.is_file()
    assert "Wrote SKILL.md" in result.stdout


def test_export_cli_default_yaml_is_taxonomy(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_issue_type(name="Overclaiming", definition="too strong")
    result = runner.invoke(app, ["export", "--format", "yaml"])
    assert result.exit_code == 0, result.stdout
    path = tmp_path / "review-taxonomy.yaml"
    assert path.is_file()
    assert "Wrote review-taxonomy.yaml" in result.stdout
    assert "issue_types" in path.read_text()
