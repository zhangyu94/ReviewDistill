import json

from fastapi.testclient import TestClient
from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import code_uncoded_comments
from reviewdistill.coding.validation import (
    accept_coding,
    change_coding,
    inbox_items,
    verify_comment,
)
from reviewdistill.db.models import Coding, IssueType, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.history import list_history, redo, undo
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import (
    create_issue_type,
    list_examples,
    list_working_observations,
    move_issue_type,
    rename_issue_type,
)
from reviewdistill.web.app import create_app


def _event_types(include_undone: bool = False) -> list[str]:
    events = list_history()["events"]
    if include_undone:
        return [event["event_type"] for event in events]
    return [event["event_type"] for event in events if not event["undone"]]


def test_rename_undo_and_redo(db):
    issue = create_issue_type(
        code="STRONG",
        name="Overly strong claim",
        category="Argumentation",
        definition="old",
    )
    rename_issue_type(issue.id, name="Overclaiming", code="OVERCLAIM")
    undo()
    with get_session() as session:
        row = session.get(IssueType, issue.id)
        assert row.name == "Overly strong claim"
        assert row.code == "STRONG"
    history = list_history()
    assert history["events"][0]["undone"] is True
    assert history["can_redo"] is True
    assert history["can_undo"] is True
    redo()
    with get_session() as session:
        row = session.get(IssueType, issue.id)
        assert row.name == "Overclaiming"
        assert row.code == "OVERCLAIM"
    assert list_history()["can_redo"] is False


def test_no_op_move_is_not_logged(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    move_issue_type(issue.id, category="Argumentation")
    assert _event_types() == ["add"]


def test_edit_same_category_does_not_log_move(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.post(
        f"/api/taxonomy/{issue.id}/edit",
        json={"definition": "A claim exceeds the evidence.", "notes": "", "category": "Argumentation"},
    )
    assert response.status_code == 200
    assert "move" not in _event_types()
    assert "edit" in _event_types()


def test_accept_is_logged_and_undo_returns_to_inbox(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why this method?}\n")
    extract_project(repo)
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        category="Methodology",
        definition="A design choice is unexplained.",
    )
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "issue_type_id": issue.id,
                    "confidence": 0.84,
                    "rationale": "Asks why the method was chosen.",
                }
            )
        )
    )
    comment_id = inbox_items()[0].comment.id
    accept_coding(comment_id)
    assert "accept" in _event_types()
    assert inbox_items() == []
    undo()
    items = inbox_items()
    assert len(items) == 1
    assert items[0].comment.id == comment_id
    assert list_examples(issue.id) == []
    with get_session() as session:
        coding = session.first(Coding)
        assert coding.status == "proposed"


def test_undo_change_restores_previous_label(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why this method?}\n")
    extract_project(repo)
    first = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        category="Methodology",
        definition="A design choice is unexplained.",
    )
    second = create_issue_type(
        code="WEAK",
        name="Weak evidence",
        category="Argumentation",
        definition="evidence is thin",
    )
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "issue_type_id": first.id,
                    "confidence": 0.84,
                    "rationale": "Asks why the method was chosen.",
                }
            )
        )
    )
    comment_id = inbox_items()[0].comment.id
    accept_coding(comment_id)
    change_coding(comment_id, issue_type_id=second.id)
    assert [row.id for row in list_working_observations(second.id)] == [comment_id]
    assert list_working_observations(first.id) == []
    undo()
    assert [row.id for row in list_working_observations(first.id)] == [comment_id]
    assert list_working_observations(second.id) == []
    assert [row.source_comment_id for row in list_examples(first.id)] == [comment_id]
    assert list_examples(second.id) == []
    redo()
    assert [row.id for row in list_working_observations(second.id)] == [comment_id]
    assert list_working_observations(first.id) == []
    assert list_examples(first.id) == []
    assert [row.source_comment_id for row in list_examples(second.id)] == [comment_id]


def test_propose_is_one_event_and_undo_removes_suggestions(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{First.}\n\\myremark{Second.}\n")
    extract_project(repo)
    summary = code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {"recommendation": "new", "issue_name": "Unclear thesis", "confidence": 0.7, "rationale": "Unclear."}
            )
        )
    )
    assert summary.coded == 2
    propose = [event for event in list_history()["events"] if event["event_type"] == "propose"]
    assert len(propose) == 1
    assert len(propose[0]["payload"]["created"]) == 2
    assert propose[0]["summary"].startswith("Get AI suggestions")
    undo()
    with get_session() as session:
        assert session.find(Coding) == []
    assert len(inbox_items()) == 2


def test_new_action_drops_redo_tail(db):
    issue = create_issue_type(
        code="STRONG",
        name="Overly strong claim",
        category="Argumentation",
        definition="old",
    )
    rename_issue_type(issue.id, name="Overclaiming", code="OVERCLAIM")
    undo()
    create_issue_type(code="AMBIG", name="Ambiguous terminology", category="Clarity", definition="vague")
    history = list_history()
    assert history["can_redo"] is False
    assert "rename" not in _event_types(include_undone=True)


def test_verify_undo_restores_previous_quality(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Keep me.}\n")
    extract_project(repo)
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        comment_id = comment.id
        assert comment.status == "pending_disappeared"
        assert comment.quality == "unreviewed"
    verify_comment(comment_id)
    assert "verify" in _event_types()
    undo()
    with get_session() as session:
        row = session.get(ProofreadingComment, comment_id)
        assert row.quality == "unreviewed"
        assert row.status == "pending_disappeared"


def test_history_api_undo_redo_and_empty_errors(db):
    client = TestClient(create_app())
    empty = client.get("/api/history")
    assert empty.status_code == 200
    assert empty.json()["events"] == []
    assert empty.json()["can_undo"] is False
    assert empty.json()["can_redo"] is False
    assert client.post("/api/history/undo").status_code == 400
    assert client.post("/api/history/redo").status_code == 400

    create_issue_type(code="U", name="Unsupported claim", category="Argumentation", definition="a")
    listed = client.get("/api/history").json()
    assert listed["can_undo"] is True
    assert listed["events"][0]["summary"]
    assert listed["events"][0]["undone"] is False
    assert client.post("/api/history/undo").status_code == 200
    after = client.get("/api/history").json()
    assert after["can_redo"] is True
    assert after["events"][0]["undone"] is True
    assert client.post("/api/history/redo").status_code == 200
    assert client.get("/api/history").json()["can_redo"] is False
