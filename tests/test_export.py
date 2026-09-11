from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import (
    add_counterexample,
    add_example,
    create_issue_type,
    list_examples,
)


def test_export_markdown_contains_operational_sections(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="Flag claims whose strength exceeds the evidence presented.",
    )
    add_example(issue.id, text="The results demonstrate... when evidence is correlational.")
    add_counterexample(issue.id, text="Do not flag strong claims when the design supports them.")
    md = export_rubric(fmt="md")
    assert md.startswith("# Scholarly Review Rubric")
    assert "## Overclaiming" in md
    assert "### Definition" in md
    assert "### Examples" in md
    assert "### Counterexamples" in md
    assert "### Review guidance" not in md
    assert "demonstrate" in md


def test_export_yaml_and_json_are_structured(db):
    create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    yaml_text = export_rubric(fmt="yaml")
    json_text = export_rubric(fmt="json")
    assert "Overclaiming" in yaml_text
    assert "Overclaiming" in json_text


def test_export_omits_examples_from_dropped_comments(db, tmp_path):
    from reviewdistill.cli.init import init_project
    from reviewdistill.coding.validation import accept_coding, drop_comment
    from reviewdistill.extraction.incremental import extract_project
    from reviewdistill.llm.mock import MockLLMProvider
    from reviewdistill.coding.coder import code_uncoded_comments
    import json

    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{UNIQUE_DROPPED_EXAMPLE.}\n")
    extract_project(repo)
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="A claim is too strong.",
    )
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "issue_type_id": issue.id,
                    "confidence": 0.9,
                    "rationale": "unique",
                }
            )
        )
    )
    from reviewdistill.db.models import ProofreadingComment
    from reviewdistill.db.session import get_session
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    accept_coding(comment_id)
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    drop_comment(comment_id)
    md = export_rubric(fmt="md")
    assert "UNIQUE_DROPPED_EXAMPLE" not in md
    assert list_examples(issue.id) == []
