import json

import pytest
from sqlmodel import select

from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import code_uncoded_comments, uncoded_comments
from reviewdistill.coding.validation import (
    KEEP_FILE_MISSING,
    KEEP_MANUSCRIPT_CHANGED,
    RETRACT_UNCHANGED,
    accept_coding,
    change_coding,
    disappearance_guess,
    disappeared_items,
    inbox_items,
    keep_comment,
    reject_coding,
    retract_comment,
)
from reviewdistill.context.manuscript import extract_context
from reviewdistill.db.models import Coding, IssueType, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import create_issue_type, list_active_issue_types, list_examples


def _seed_proposed(tmp_path, response: dict) -> str:
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why did we choose this method?}\n")
    extract_project(repo)
    code_uncoded_comments(provider=MockLLMProvider(scripted_response=json.dumps(response)))
    items = inbox_items()
    assert len(items) == 1
    return items[0].comment.id


def test_accept_existing_marks_coding_and_adds_example(db, tmp_path):
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        category="Methodology",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    result = accept_coding(comment_id)
    assert result.issue_type_id == issue.id
    assert inbox_items() == []
    examples = list_examples(issue.id)
    assert examples[0].source_comment_id == comment_id
    with get_session() as session:
        coding = session.exec(select(Coding)).first()
        assert coding.status == "accepted"
        assert coding.coder_type == "ai"


def test_accept_new_creates_issue_type(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "issue_name": "Missing methodological justification",
            "category": "Methodology",
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    result = accept_coding(comment_id)
    with get_session() as session:
        issue = session.get(IssueType, result.issue_type_id)
        assert issue is not None
        assert issue.name == "Missing methodological justification"
        assert issue.status == "active"


def test_accept_new_reuses_existing_code(db, tmp_path):
    existing = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "OVERCLAIM",
            "issue_name": "Overclaiming",
            "category": "Argumentation",
            "definition": "A claim exceeds the evidence.",
            "confidence": 0.9,
            "rationale": "duplicate proposal",
        },
    )
    result = accept_coding(comment_id)
    assert result.issue_type_id == existing.id
    assert [issue.code for issue in list_active_issue_types()] == ["OVERCLAIM"]


def test_change_creates_human_coding(db, tmp_path):
    chosen = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    other = create_issue_type(
        code="WEAK",
        name="Weak evidence",
        category="Argumentation",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": other.id,
            "confidence": 0.4,
            "rationale": "wrong guess",
        },
    )
    change_coding(comment_id, issue_type_id=chosen.id)
    assert inbox_items() == []
    with get_session() as session:
        rows = list(session.exec(select(Coding).where(Coding.comment_id == comment_id)))
        statuses = {row.coder_type: row.status for row in rows}
        assert statuses["ai"] == "modified"
        assert statuses["human"] == "accepted"
        human = next(row for row in rows if row.coder_type == "human")
        assert human.issue_type_id == chosen.id


def test_reject_leaves_no_issue_assignment(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "X",
            "issue_name": "Nope",
            "category": "General",
            "definition": "nope",
            "confidence": 0.2,
            "rationale": "weak",
        },
    )
    reject_coding(comment_id)
    assert inbox_items() == []
    with get_session() as session:
        coding = session.exec(select(Coding)).first()
        assert coding.status == "rejected"
        assert coding.issue_type_id is None


def test_kept_uncoded_comment_stays_in_inbox(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Still useful.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.exec(select(ProofreadingComment)).first()
        row.status = "kept"
        session.add(row)
        session.commit()
    assert len(uncoded_comments()) == 1
    assert len(inbox_items()) == 1


def test_retracted_comment_is_not_uncoded(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Retract me.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.exec(select(ProofreadingComment)).first()
        row.status = "retracted"
        session.add(row)
        session.commit()
    assert uncoded_comments() == []
    assert inbox_items() == []


def test_keep_and_retract_status(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{A.}\n\\myremark{B.}\n")
    extract_project(repo)
    (repo / "main.tex").write_text("\\myremark{A.}\n")
    extract_project(repo)
    items = disappeared_items()
    assert len(items) == 1
    gone_id = items[0].comment.id
    keep_comment(gone_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, gone_id).status == "kept"
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    remaining = disappeared_items()
    assert remaining
    retract_comment(remaining[0].comment.id)
    with get_session() as session:
        assert session.get(ProofreadingComment, remaining[0].comment.id).status == "retracted"


def test_disappearance_guess_labels():
    unchanged = "The results demonstrate that X.\n"
    comment = ProofreadingComment(
        id="g",
        project_id="p",
        source_type="latex_command",
        source_command="myremark",
        file_path="main.tex",
        line_number=1,
        raw_text="Too strong.",
        context_text=extract_context(unchanged, 1).context_text,
        fingerprint="x",
        status="pending_disappeared",
    )
    assert disappearance_guess(comment, source=None) == KEEP_FILE_MISSING
    assert disappearance_guess(comment, source=unchanged) == RETRACT_UNCHANGED
    changed = "Intro\n\nThe experiment only suggests Y.\n"
    comment.line_number = 3
    assert disappearance_guess(comment, source=changed) == KEEP_MANUSCRIPT_CHANGED


def test_disappearance_guess_compares_full_prose_not_first_line():
    source = (
        "\\section{Results}\n"
        "\\subsection{Accuracy}\n"
        "Model A achieved higher accuracy than Model B.\n"
        "Therefore, Model A is more suitable.\n"
    )
    prose = extract_context(source, line_number=4).context_text
    comment = ProofreadingComment(
        id="g2",
        project_id="p",
        source_type="latex_command",
        source_command="myremark",
        file_path="main.tex",
        line_number=4,
        raw_text="Too strong.",
        context_text=prose + "\nCitations: skip | Refs: fig:1",
        fingerprint="x",
        status="pending_disappeared",
    )
    assert disappearance_guess(comment, source=source) == RETRACT_UNCHANGED


def test_keep_and_retract_require_pending_disappeared(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Still here.}\n")
    extract_project(repo)
    with get_session() as session:
        active_id = session.exec(select(ProofreadingComment)).first().id
    with pytest.raises(ValueError, match="pending_disappeared"):
        keep_comment(active_id)
    with pytest.raises(ValueError, match="pending_disappeared"):
        retract_comment(active_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, active_id).status == "active"
