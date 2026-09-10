from typer.testing import CliRunner

from reviewdistill.cli.app import app
from reviewdistill.taxonomy.operations import create_issue_type

runner = CliRunner()


def test_taxonomy_no_longer_lists_issue_counts(db):
    create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    result = runner.invoke(app, ["taxonomy"])
    assert "Overclaiming" not in result.stdout
    assert "Argumentation" not in result.stdout


def test_export_cli_writes_markdown(db, tmp_path):
    create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    out = tmp_path / "review-rubric.md"
    result = runner.invoke(app, ["export", "--format", "md", "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    text = out.read_text()
    assert text.startswith("# Scholarly Review Rubric")
    assert "Overclaiming" in text
    assert f"Wrote {out}" in result.stdout


def test_taxonomy_export_hidden_alias_writes_markdown(db, tmp_path):
    create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    out = tmp_path / "alias.md"
    result = runner.invoke(app, ["taxonomy", "export", "--format", "md", "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    assert "Overclaiming" in out.read_text()
