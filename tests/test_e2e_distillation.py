import json
from pathlib import Path

from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import code_uncoded_comments
from reviewdistill.coding.validation import accept_coding, inbox_items
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import list_active_labels


def test_second_paper_reuses_accepted_taxonomy(db, tmp_path):
    paper1 = tmp_path / "paper-01"
    paper1.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=paper1)
    (paper1 / "main.tex").write_text(Path("tests/fixtures/paper-01/main.tex").read_text())
    extract_project(paper1)

    provider_new = MockLLMProvider(
        scripted_response=json.dumps(
            {
                "recommendation": "new",
                "issue_code": "OVERCLAIM",
                "label_name": "Overclaiming",
                "parent_id": None,
                "definition": "A claim is stronger than the evidence supports.",
                "confidence": 0.9,
                "rationale": "Strength of claim vs evidence.",
            }
        )
    )
    code_uncoded_comments(provider=provider_new)
    for item in inbox_items():
        accept_coding(item.comment.id)

    types = list_active_labels()
    assert any(label.name == "Overclaiming" for label in types)
    overclaim = next(label for label in types if label.name == "Overclaiming")

    paper2 = tmp_path / "paper-02"
    paper2.mkdir()
    init_project(name="paper-02", commands=["myremark"], cwd=paper2)
    (paper2 / "main.tex").write_text(Path("tests/fixtures/paper-02/main.tex").read_text())
    extract_project(paper2)
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "label_id": overclaim.id,
                    "confidence": 0.88,
                    "rationale": "Causal overclaim.",
                }
            )
        )
    )
    items = inbox_items()
    assert len(items) == 1
    assert items[0].coding.label_id == overclaim.id
    accept_coding(items[0].comment.id)

    rubric = export_rubric("md")
    assert "Overclaiming" in rubric
    assert "stronger than the evidence" in rubric
