from typer.testing import CliRunner

from reviewdistill.cli.app import app
from reviewdistill.taxonomy.operations import create_issue_type

runner = CliRunner()


def test_taxonomy_cli_removed():
    result = runner.invoke(app, ["taxonomy"])
    assert result.exit_code != 0


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
