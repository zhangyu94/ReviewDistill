from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import (
    add_example,
    create_label,
    list_examples,
)


def test_export_markdown_contains_operational_sections(db):
    label = create_label(
        name="Overclaiming",
        definition="Flag claims whose strength exceeds the evidence presented.",
    )
    add_example(label.id, text="The results demonstrate... when evidence is correlational.")
    md = export_rubric(fmt="md")
    assert md.startswith("---\nname: scholarly-review\n")
    assert "distilled label taxonomy" in md
    assert "# Scholarly Review Rubric" not in md
    assert "# Scholarly Review\n" in md
    assert (
        "Review the manuscript against the labels below. "
        "For each label, flag passages that match the definition and examples."
    ) in md
    assert "## Overclaiming" in md
    assert "### Definition" in md
    assert "### Examples" in md
    assert "### Counterexamples" not in md
    assert "### Review guidance" not in md
    assert "demonstrate" in md


def test_export_yaml_includes_ids_for_parent_links(db):
    import json as json_lib

    import yaml

    parent = create_label(name="Parent", definition="p")
    child = create_label(name="Child", definition="c", parent_id=parent.id)
    data = yaml.safe_load(export_rubric(fmt="yaml"))
    by_name = {row["name"]: row for row in data["labels"]}
    assert by_name["Parent"]["id"] == parent.id
    assert by_name["Parent"]["parent_id"] is None
    assert by_name["Child"]["id"] == child.id
    assert by_name["Child"]["parent_id"] == parent.id
    assert "notes" not in by_name["Parent"]
    assert "notes" not in by_name["Child"]
    parsed = json_lib.loads(export_rubric(fmt="json"))
    assert {row["name"]: row["id"] for row in parsed["labels"]} == {
        "Parent": parent.id,
        "Child": child.id,
    }
    assert all("notes" not in row for row in parsed["labels"])
    md = export_rubric(fmt="md")
    assert "Parent: Parent" in md


def test_export_includes_only_selected_ids(db):
    parent = create_label(name="Parent", definition="p")
    child = create_label(name="Child", definition="c", parent_id=parent.id)
    md = export_rubric(fmt="md", label_ids=[child.id])
    assert "## Child" in md
    assert "## Parent" not in md
    assert "Parent: Parent" in md
    data = __import__("yaml").safe_load(export_rubric(fmt="yaml", label_ids=[child.id]))
    assert [row["name"] for row in data["labels"]] == ["Child"]
    assert data["labels"][0]["parent_id"] == parent.id


def test_export_empty_ids_is_skill_preamble_only(db):
    create_label(name="Parent", definition="p")
    md = export_rubric(fmt="md", label_ids=[])
    assert md.startswith("---\nname: scholarly-review\n")
    assert "# Scholarly Review\n" in md
    assert "## Parent" not in md
    assert md.endswith("flag passages that match the definition and examples.\n")


def test_export_unknown_id_is_bad_input(db):
    import pytest

    from reviewdistill.errors import BadInput

    with pytest.raises(BadInput):
        export_rubric(fmt="md", label_ids=["missing"])


def test_export_omits_examples_from_dropped_comments(db, tmp_path):
    from reviewdistill.cli.init import init_project
    from reviewdistill.coding.validation import delete_comment
    from reviewdistill.extraction.incremental import extract_project
    from reviewdistill.llm.mock import MockLLMProvider
    from reviewdistill.coding.coder import code_uncoded_comments
    import json

    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{UNIQUE_DROPPED_EXAMPLE.}\n")
    extract_project(repo)
    label = create_label(
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "label_id": label.id,
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
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    delete_comment(comment_id)
    md = export_rubric(fmt="md")
    assert "UNIQUE_DROPPED_EXAMPLE" not in md
    assert list_examples(label.id) == []
