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
    create_empty_issue_type,
    create_issue_type,
    deactivate_issue_type,
    flatten_issue_type,
    list_examples,
    list_working_observations,
    merge_issue_types,
    move_issue_type,
    remove_issue_type,
    rename_issue_type,
    split_issue_type,
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
        definition="too strong",
    )
    move_issue_type(issue.id, parent_id=None, position=0)
    assert _event_types() == ["add"]


def test_move_undo_restores_sibling_order(db):
    create_issue_type(code="A", name="Alpha", definition="")
    writing = create_issue_type(code="W", name="Writing", definition="")
    create_issue_type(code="S", name="Style", definition="")
    move_issue_type(writing.id, parent_id=None, position=2)
    undo()
    with get_session() as session:
        roots = sorted(
            [row for row in session.find(IssueType) if row.status == "active" and row.parent_id is None],
            key=lambda row: row.position,
        )
        assert [row.name for row in roots] == ["Alpha", "Writing", "Style"]


def test_flatten_undo_restores_descendants(db):
    parent = create_issue_type(code="P", name="Parent", definition="")
    child = create_issue_type(code="C", name="Child", definition="", parent_id=parent.id)
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-flat",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="too strong",
                fingerprint="fp-flat",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-flat",
                comment_id="c-flat",
                issue_type_id=child.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    flatten_issue_type(parent.id)
    undo()
    with get_session() as session:
        child_row = session.get(IssueType, child.id)
        assert child_row.status == "active"
        assert child_row.parent_id == parent.id
        coding = session.get(Coding, "coding-flat")
        assert coding.issue_type_id == child.id


def test_flatten_undo_redo_restores_nested_tree_and_coding(db):
    parent = create_issue_type(code="P", name="Parent", definition="")
    child = create_issue_type(code="C", name="Child", definition="", parent_id=parent.id)
    grand = create_issue_type(code="G", name="Grand", definition="", parent_id=child.id)
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-nest",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="too strong",
                fingerprint="fp-nest",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-nest",
                comment_id="c-nest",
                issue_type_id=grand.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    flatten_issue_type(parent.id)
    undo()
    with get_session() as session:
        assert session.get(IssueType, child.id).parent_id == parent.id
        assert session.get(IssueType, grand.id).parent_id == child.id
        assert session.get(IssueType, child.id).status == "active"
        assert session.get(IssueType, grand.id).status == "active"
        assert session.get(Coding, "coding-nest").issue_type_id == grand.id
    redo()
    with get_session() as session:
        assert session.get(IssueType, child.id).status == "inactive"
        assert session.get(IssueType, grand.id).status == "inactive"
        assert session.get(Coding, "coding-nest").issue_type_id == parent.id


def test_deactivate_parent_redo_then_create_appends_last(db):
    create_issue_type(code="A", name="Alpha", definition="")
    parent = create_issue_type(code="Z", name="Zeta", definition="")
    kid = create_issue_type(code="K", name="Kid", definition="", parent_id=parent.id)
    create_issue_type(code="G", name="Gamma", definition="")
    deactivate_issue_type(parent.id)
    undo()
    redo()
    created = create_empty_issue_type(parent_id=None)
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Kid", "Gamma", "New type"]
    assert [row.position for row in roots] == [0, 1, 2, 3]
    assert created.position == 3
    with get_session() as session:
        assert session.get(IssueType, parent.id).status == "inactive"
        assert session.get(IssueType, kid.id).parent_id is None


def test_move_nest_undo_redo_restores_parent(db):
    parent = create_issue_type(code="A", name="Alpha", definition="")
    child = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    move_issue_type(child.id, parent_id=parent.id, position=0)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma"]
    assert [row.position for row in roots] == [0, 1, 2]
    redo()
    with get_session() as session:
        assert session.get(IssueType, child.id).parent_id == parent.id
        assert session.get(IssueType, child.id).position == 0
    assert [row.name for row in _active_siblings(None)] == ["Alpha", "Gamma"]
    assert [row.name for row in _active_siblings(parent.id)] == ["Zeta"]


def _active_siblings(parent_id: str | None) -> list[IssueType]:
    with get_session() as session:
        rows = [
            row
            for row in session.find(IssueType)
            if row.status == "active" and row.parent_id == parent_id
        ]
        return sorted(rows, key=lambda row: (row.position, row.name, row.id))


def test_remove_undo_restores_subtree(db):
    parent = create_issue_type(code="P", name="Parent", definition="")
    child = create_issue_type(code="C", name="Child", definition="", parent_id=parent.id)
    remove_issue_type(parent.id)
    undo()
    with get_session() as session:
        assert session.get(IssueType, parent.id) is not None
        assert session.get(IssueType, child.id) is not None


def test_deactivate_undo_restores_child_parent(db):
    parent = create_issue_type(code="P", name="Parent", definition="")
    child = create_issue_type(code="C", name="Child", definition="", parent_id=parent.id)
    deactivate_issue_type(parent.id)
    undo()
    with get_session() as session:
        assert session.get(IssueType, parent.id).status == "active"
        assert session.get(IssueType, child.id).parent_id == parent.id


def test_undo_add_compacts_remaining_siblings(db):
    create_issue_type(code="A", name="Alpha", definition="")
    create_issue_type(code="B", name="Beta", definition="")
    extra = create_issue_type(code="C", name="Style", definition="")
    undo()
    created = create_empty_issue_type(parent_id=None)
    with get_session() as session:
        roots = sorted(
            [row for row in session.find(IssueType) if row.status == "active" and row.parent_id is None],
            key=lambda row: row.position,
        )
        assert [row.name for row in roots] == ["Alpha", "Beta", "New type"]
        assert session.get(IssueType, created.id).position == 2
        assert session.get(IssueType, extra.id).status == "inactive"


def test_merge_undo_restores_child_positions(db):
    source = create_issue_type(code="S", name="Source", definition="")
    first = create_issue_type(code="K1", name="KidA", definition="", parent_id=source.id)
    second = create_issue_type(code="K2", name="KidB", definition="", parent_id=source.id)
    target = create_issue_type(code="T", name="Target", definition="")
    create_issue_type(code="TK", name="Mid", definition="", parent_id=target.id)
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    undo()
    with get_session() as session:
        kids = sorted(
            [row for row in session.find(IssueType) if row.parent_id == source.id and row.status == "active"],
            key=lambda row: row.position,
        )
        assert [row.id for row in kids] == [first.id, second.id]
        assert [row.position for row in kids] == [0, 1]


def test_deactivate_undo_restores_sibling_order(db):
    create_issue_type(code="A", name="Alpha", definition="")
    middle = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    deactivate_issue_type(middle.id)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma"]
    assert [row.position for row in roots] == [0, 1, 2]


def test_remove_undo_restores_sibling_order(db):
    create_issue_type(code="A", name="Alpha", definition="")
    middle = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    remove_issue_type(middle.id)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma"]
    assert [row.position for row in roots] == [0, 1, 2]


def test_remove_redo_compacts_remaining_siblings(db):
    create_issue_type(code="A", name="Alpha", definition="")
    middle = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    remove_issue_type(middle.id)
    undo()
    redo()
    created = create_empty_issue_type(parent_id=None)
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Gamma", "New type"]
    assert [row.position for row in roots] == [0, 1, 2]
    assert created.position == 2


def test_merge_undo_restores_source_sibling_order(db):
    create_issue_type(code="A", name="Alpha", definition="")
    source = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    target = create_issue_type(code="T", name="Target", definition="")
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma", "Target"]
    assert [row.position for row in roots] == [0, 1, 2, 3]


def test_merge_redo_matches_forward_child_order(db):
    source = create_issue_type(code="S", name="Source", definition="")
    create_issue_type(code="K1", name="KidA", definition="", parent_id=source.id)
    create_issue_type(code="K2", name="KidB", definition="", parent_id=source.id)
    target = create_issue_type(code="T", name="Target", definition="")
    create_issue_type(code="TK", name="Mid", definition="", parent_id=target.id)
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    forward = _active_siblings(target.id)
    forward_names = [row.name for row in forward]
    forward_positions = [row.position for row in forward]
    undo()
    redo()
    after = _active_siblings(target.id)
    assert [row.name for row in after] == forward_names
    assert [row.position for row in after] == forward_positions
    assert forward_positions == list(range(len(forward_positions)))


def test_split_undo_then_create_appends_last(db):
    create_issue_type(code="A", name="Alpha", definition="")
    middle = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    split_issue_type(
        middle.id,
        left={"code": "ZL", "name": "Zeta Left", "definition": "l"},
        right={"code": "ZR", "name": "Zeta Right", "definition": "r"},
    )
    undo()
    created = create_empty_issue_type(parent_id=None)
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma", "New type"]
    assert [row.position for row in roots] == [0, 1, 2, 3]
    assert created.position == 3


def test_split_redo_matches_forward_sibling_order(db):
    create_issue_type(code="A", name="Alpha", definition="")
    middle = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    split_issue_type(
        middle.id,
        left={"code": "ZL", "name": "Zeta Left", "definition": "l"},
        right={"code": "ZR", "name": "Zeta Right", "definition": "r"},
    )
    forward = [row.name for row in _active_siblings(None)]
    undo()
    redo()
    after = _active_siblings(None)
    assert [row.name for row in after] == forward
    assert [row.position for row in after] == [0, 1, 2, 3]
    created = create_empty_issue_type(parent_id=None)
    roots = _active_siblings(None)
    assert roots[-1].name == "New type"
    assert created.position == 4
    assert [row.position for row in roots] == [0, 1, 2, 3, 4]


def test_split_redo_keeps_pair_before_later_sibling(db):
    first = create_issue_type(code="Z", name="Zeta", definition="")
    create_issue_type(code="G", name="Gamma", definition="")
    split_issue_type(
        first.id,
        left={"code": "ZL", "name": "Zeta Left", "definition": "l"},
        right={"code": "ZR", "name": "Zeta Right", "definition": "r"},
    )
    forward = [row.name for row in _active_siblings(None)]
    undo()
    redo()
    assert [row.name for row in _active_siblings(None)] == forward
    assert [row.position for row in _active_siblings(None)] == [0, 1, 2]


def test_edit_does_not_log_move(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.post(
        f"/api/taxonomy/{issue.id}/edit",
        json={"definition": "A claim exceeds the evidence.", "notes": ""},
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
        definition="A design choice is unexplained.",
    )
    second = create_issue_type(
        code="WEAK",
        name="Weak evidence",
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
    assert propose[0]["summary"].startswith("Label with AI")
    undo()
    with get_session() as session:
        assert session.find(Coding) == []
    assert len(inbox_items()) == 2


def test_new_action_drops_redo_tail(db):
    issue = create_issue_type(
        code="STRONG",
        name="Overly strong claim",
        definition="old",
    )
    rename_issue_type(issue.id, name="Overclaiming", code="OVERCLAIM")
    undo()
    create_issue_type(code="AMBIG", name="Ambiguous terminology", definition="vague")
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

    create_issue_type(code="U", name="Unsupported claim", definition="a")
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
