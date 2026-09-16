import json

from fastapi.testclient import TestClient

from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import code_uncoded_comments
from reviewdistill.coding.validation import (
    accept_coding,
    change_coding,
    delete_comment,
    inbox_items,
    verify_comment,
)
from reviewdistill.db.models import CODING_MODIFIED, Coding, Label, LabelExample, ProofreadingComment, is_labeled
from reviewdistill.coding.split import SplitPlan
from reviewdistill.db.session import get_session
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.history import list_history, record, redo, undo
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import (
    add_example,
    apply_split,
    create_empty_label,
    create_label,
    deactivate_label,
    flatten_label,
    list_examples,
    list_working_observations,
    merge_labels,
    move_label,
    recycle_ungrouped,
    remove_label,
    rename_label,
)
from reviewdistill.web.app import create_app


def _event_types(include_undone: bool = False) -> list[str]:
    events = list_history()["events"]
    if include_undone:
        return [event["event_type"] for event in events]
    return [event["event_type"] for event in events if not event["undone"]]


def test_rename_undo_and_redo(db):
    label = create_label(
        name="Overly strong claim",
        definition="old",
    )
    rename_label(label.id, name="Overclaiming")
    undo()
    with get_session() as session:
        row = session.get(Label, label.id)
        assert row.name == "Overly strong claim"
    history = list_history()
    assert history["events"][0]["undone"] is True
    assert history["can_redo"] is True
    assert history["can_undo"] is True
    redo()
    with get_session() as session:
        row = session.get(Label, label.id)
        assert row.name == "Overclaiming"
    assert list_history()["can_redo"] is False


def test_rename_undo_uniquifies_when_old_name_is_taken(db):
    first = create_label(name="Foo", definition="")
    rename_label(first.id, name="Bar")
    with get_session() as session:
        session.add(
            Label(
                id="other",
                name="Foo",
                definition="",
                parent_id=None,
                position=99,
                status="active",
            )
        )
        session.commit()
    undo()
    with get_session() as session:
        assert session.get(Label, first.id).name == "Foo (2)"


def test_no_op_move_is_not_logged(db):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    move_label(label.id, parent_id=None, position=0)
    assert _event_types() == ["add"]


def test_move_undo_restores_sibling_order(db):
    create_label(name="Alpha", definition="")
    writing = create_label(name="Writing", definition="")
    create_label(name="Style", definition="")
    move_label(writing.id, parent_id=None, position=2)
    undo()
    with get_session() as session:
        roots = sorted(
            [row for row in session.find(Label) if row.status == "active" and row.parent_id is None],
            key=lambda row: row.position,
        )
        assert [row.name for row in roots] == ["Alpha", "Writing", "Style"]


def test_flatten_undo_restores_descendants(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
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
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-flat",
                comment_id="c-flat",
                label_id=child.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    flatten_label(parent.id)
    undo()
    with get_session() as session:
        child_row = session.get(Label, child.id)
        assert child_row.status == "active"
        assert child_row.parent_id == parent.id
        coding = session.get(Coding, "coding-flat")
        assert coding.label_id == child.id


def test_flatten_undo_redo_restores_nested_tree_and_coding(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    grand = create_label(name="Grand", definition="", parent_id=child.id)
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
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-nest",
                comment_id="c-nest",
                label_id=grand.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    flatten_label(parent.id)
    undo()
    with get_session() as session:
        assert session.get(Label, child.id).parent_id == parent.id
        assert session.get(Label, grand.id).parent_id == child.id
        assert session.get(Label, child.id).status == "active"
        assert session.get(Label, grand.id).status == "active"
        assert session.get(Coding, "coding-nest").label_id == grand.id
    redo()
    with get_session() as session:
        assert session.get(Label, child.id).status == "inactive"
        assert session.get(Label, grand.id).status == "inactive"
        assert session.get(Coding, "coding-nest").label_id == parent.id


def test_deactivate_parent_redo_then_create_appends_last(db):
    create_label(name="Alpha", definition="")
    parent = create_label(name="Zeta", definition="")
    kid = create_label(name="Kid", definition="", parent_id=parent.id)
    create_label(name="Gamma", definition="")
    deactivate_label(parent.id)
    undo()
    redo()
    created = create_empty_label(parent_id=None)
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Kid", "Gamma", "New label"]
    assert [row.position for row in roots] == [0, 1, 2, 3]
    assert created.position == 3
    with get_session() as session:
        assert session.get(Label, parent.id).status == "inactive"
        assert session.get(Label, kid.id).parent_id is None


def test_move_nest_undo_redo_restores_parent(db):
    parent = create_label(name="Alpha", definition="")
    child = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    move_label(child.id, parent_id=parent.id, position=0)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma"]
    assert [row.position for row in roots] == [0, 1, 2]
    redo()
    with get_session() as session:
        assert session.get(Label, child.id).parent_id == parent.id
        assert session.get(Label, child.id).position == 0
    assert [row.name for row in _active_siblings(None)] == ["Alpha", "Gamma"]
    assert [row.name for row in _active_siblings(parent.id)] == ["Zeta"]


def test_move_under_labeled_leaf_undo_redo_restores_labels(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="")
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c-move", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong",
            status="active",
        ))
        session.add(Coding(
            id="k-move", comment_id="c-move", label_id=parent.id, coder_type="human",
            status="accepted",
        ))
        session.commit()
    move_label(child.id, parent_id=parent.id, position=0)
    undo()
    with get_session() as session:
        assert session.get(Coding, "k-move").label_id == parent.id
        assert session.get(Label, child.id).parent_id is None
        kids = [
            row for row in session.find(Label)
            if row.parent_id == parent.id and row.status == "active"
        ]
        assert kids == []
    redo()
    with get_session() as session:
        kids = _active_siblings(parent.id)
        ungrouped = next(row for row in kids if row.name == "ungrouped")
        assert session.get(Label, child.id).parent_id == parent.id
        assert session.get(Coding, "k-move").label_id == ungrouped.id


def _active_siblings(parent_id: str | None) -> list[Label]:
    with get_session() as session:
        rows = [
            row
            for row in session.find(Label)
            if row.status == "active" and row.parent_id == parent_id
        ]
        return sorted(rows, key=lambda row: (row.position, row.name, row.id))


def test_remove_undo_restores_subtree(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    remove_label(parent.id)
    undo()
    with get_session() as session:
        assert session.get(Label, parent.id) is not None
        assert session.get(Label, child.id) is not None


def test_deactivate_undo_restores_child_parent(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    deactivate_label(parent.id)
    undo()
    with get_session() as session:
        assert session.get(Label, parent.id).status == "active"
        assert session.get(Label, child.id).parent_id == parent.id


def test_undo_add_compacts_remaining_siblings(db):
    create_label(name="Alpha", definition="")
    create_label(name="Beta", definition="")
    extra = create_label(name="Style", definition="")
    undo()
    created = create_empty_label(parent_id=None)
    with get_session() as session:
        roots = sorted(
            [row for row in session.find(Label) if row.status == "active" and row.parent_id is None],
            key=lambda row: row.position,
        )
        assert [row.name for row in roots] == ["Alpha", "Beta", "New label"]
        assert session.get(Label, created.id).position == 2
        assert session.get(Label, extra.id).status == "inactive"


def test_undo_first_child_restores_parent_labels(db):
    parent = create_label(name="Parent", definition="")
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong",
            status="active",
        ))
        session.add(Coding(
            id="k1", comment_id="c1", label_id=parent.id, coder_type="human",
            status="accepted",
        ))
        session.commit()
    created = create_empty_label(parent_id=parent.id)
    undo()
    with get_session() as session:
        kids = [
            row for row in session.find(Label)
            if row.parent_id == parent.id and row.status == "active"
        ]
        assert kids == []
        assert session.get(Label, created.id).status == "inactive"
        assert session.get(Coding, "k1").label_id == parent.id
    redo()
    with get_session() as session:
        kids = sorted(
            [
                row for row in session.find(Label)
                if row.parent_id == parent.id and row.status == "active"
            ],
            key=lambda row: row.position,
        )
        assert [row.name for row in kids] == ["New label", "ungrouped"]
        assert session.get(Coding, "k1").label_id == kids[1].id


def test_merge_undo_restores_child_positions(db):
    source = create_label(name="Source", definition="")
    first = create_label(name="KidA", definition="", parent_id=source.id)
    second = create_label(name="KidB", definition="", parent_id=source.id)
    target = create_label(name="Target", definition="")
    create_label(name="Mid", definition="", parent_id=target.id)
    merge_labels(source_ids=[source.id], target_id=target.id)
    undo()
    with get_session() as session:
        kids = sorted(
            [row for row in session.find(Label) if row.parent_id == source.id and row.status == "active"],
            key=lambda row: row.position,
        )
        assert [row.id for row in kids] == [first.id, second.id]
        assert [row.position for row in kids] == [0, 1]


def test_deactivate_undo_restores_sibling_order(db):
    create_label(name="Alpha", definition="")
    middle = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    deactivate_label(middle.id)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma"]
    assert [row.position for row in roots] == [0, 1, 2]


def test_remove_undo_restores_sibling_order(db):
    create_label(name="Alpha", definition="")
    middle = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    remove_label(middle.id)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma"]
    assert [row.position for row in roots] == [0, 1, 2]


def test_remove_redo_compacts_remaining_siblings(db):
    create_label(name="Alpha", definition="")
    middle = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    remove_label(middle.id)
    undo()
    redo()
    created = create_empty_label(parent_id=None)
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Gamma", "New label"]
    assert [row.position for row in roots] == [0, 1, 2]
    assert created.position == 2


def test_merge_undo_restores_source_sibling_order(db):
    create_label(name="Alpha", definition="")
    source = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    target = create_label(name="Target", definition="")
    merge_labels(source_ids=[source.id], target_id=target.id)
    undo()
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma", "Target"]
    assert [row.position for row in roots] == [0, 1, 2, 3]


def test_merge_redo_matches_forward_child_order(db):
    source = create_label(name="Source", definition="")
    create_label(name="KidA", definition="", parent_id=source.id)
    create_label(name="KidB", definition="", parent_id=source.id)
    target = create_label(name="Target", definition="")
    create_label(name="Mid", definition="", parent_id=target.id)
    merge_labels(source_ids=[source.id], target_id=target.id)
    forward = _active_siblings(target.id)
    forward_names = [row.name for row in forward]
    forward_positions = [row.position for row in forward]
    undo()
    redo()
    after = _active_siblings(target.id)
    assert [row.name for row in after] == forward_names
    assert [row.position for row in after] == forward_positions
    assert forward_positions == list(range(len(forward_positions)))


def test_merge_parent_into_labeled_leaf_undo_redo_restores_labels(db):
    target = create_label(name="Target", definition="t")
    source = create_label(name="Source", definition="s")
    kid = create_label(name="Kid", definition="k", parent_id=source.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c-tgt", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="on target",
            status="active",
        ))
        session.add(Coding(
            id="k-tgt", comment_id="c-tgt", label_id=target.id, coder_type="human",
            status="accepted",
        ))
        session.add(ProofreadingComment(
            id="c-src", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=2, raw_text="on source",
            status="active",
        ))
        session.add(Coding(
            id="k-src", comment_id="c-src", label_id=source.id, coder_type="human",
            status="accepted",
        ))
        session.commit()
    merge_labels(source_ids=[source.id], target_id=target.id)
    undo()
    with get_session() as session:
        assert session.get(Coding, "k-tgt").label_id == target.id
        assert session.get(Coding, "k-src").label_id == source.id
        assert session.get(Label, kid.id).parent_id == source.id
        assert session.get(Label, source.id).status == "active"
        extras = [
            row for row in session.find(Label)
            if row.parent_id == target.id and row.status == "active"
        ]
        assert extras == []
    redo()
    with get_session() as session:
        kids = _active_siblings(target.id)
        ungrouped = next(row for row in kids if row.name == "ungrouped")
        assert session.get(Label, kid.id).parent_id == target.id
        assert session.get(Label, source.id).status == "inactive"
        assert session.get(Coding, "k-tgt").label_id == ungrouped.id
        assert session.get(Coding, "k-src").label_id == ungrouped.id


def test_split_undo_then_create_appends_last(db):
    create_label(name="Alpha", definition="")
    middle = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    apply_split(
        source_id=middle.id,
        plan=SplitPlan(
            labels=[
                {"name": "Zeta Left", "definition": "l"},
                {"name": "Zeta Right", "definition": "r"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    undo()
    created = create_empty_label(parent_id=None)
    roots = _active_siblings(None)
    assert [row.name for row in roots] == ["Alpha", "Zeta", "Gamma", "New label"]
    assert [row.position for row in roots] == [0, 1, 2, 3]
    assert created.position == 3


def test_split_redo_matches_forward_sibling_order(db):
    create_label(name="Alpha", definition="")
    middle = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    apply_split(
        source_id=middle.id,
        plan=SplitPlan(
            labels=[
                {"name": "Zeta Left", "definition": "l"},
                {"name": "Zeta Right", "definition": "r"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    forward = [row.name for row in _active_siblings(None)]
    undo()
    redo()
    after = _active_siblings(None)
    assert [row.name for row in after] == forward
    assert [row.position for row in after] == [0, 1, 2]
    created = create_empty_label(parent_id=None)
    roots = _active_siblings(None)
    assert roots[-1].name == "New label"
    assert created.position == 3
    assert [row.position for row in roots] == [0, 1, 2, 3]


def test_split_redo_keeps_children_under_source(db):
    first = create_label(name="Zeta", definition="")
    create_label(name="Gamma", definition="")
    apply_split(
        source_id=first.id,
        plan=SplitPlan(
            labels=[
                {"name": "Zeta Left", "definition": "l"},
                {"name": "Zeta Right", "definition": "r"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    forward = [row.name for row in _active_siblings(None)]
    undo()
    redo()
    assert [row.name for row in _active_siblings(None)] == forward
    assert [row.position for row in _active_siblings(None)] == [0, 1]
    assert [row.name for row in _active_siblings(first.id)] == ["Zeta Left", "Zeta Right"]


def test_legacy_split_payload_still_inverts(db):
    source = create_label(name="Source", definition="")
    left = create_label(name="Left", definition="")
    right = create_label(name="Right", definition="")
    with get_session() as session:
        row = session.get(Label, source.id)
        row.status = "inactive"
        session.add(row)
        record(
            session,
            "split",
            {
                "source_id": source.id,
                "created_ids": [left.id, right.id],
                "deleted_codings": [],
            },
        )
        session.commit()
    undo()
    with get_session() as session:
        assert session.get(Label, source.id).status == "active"
        assert session.get(Label, left.id).status == "inactive"
        assert session.get(Label, right.id).status == "inactive"


def test_edit_does_not_log_move(db):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.post(
        f"/api/labels/{label.id}/edit",
        json={"definition": "A claim exceeds the evidence."},
    )
    assert response.status_code == 200
    assert "move" not in _event_types()
    assert "edit" in _event_types()


def test_undo_edit_ignores_notes_in_legacy_payload(db):
    label = create_label(name="Overclaiming", definition="new def")
    with get_session() as session:
        record(
            session,
            "edit",
            {
                "label_id": label.id,
                "before": {
                    "definition": "old def",
                    "notes": "Watch epistemic verbs.",
                    "detection_guidance": None,
                },
                "after": {
                    "definition": "new def",
                    "notes": "Watch epistemic verbs.",
                    "detection_guidance": None,
                },
            },
        )
        session.commit()
    undo()
    with get_session() as session:
        row = session.get(Label, label.id)
        assert row.definition == "old def"
        assert "notes" not in row.model_dump()


def test_accept_is_logged_and_undo_returns_to_inbox(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why this method?}\n")
    extract_project(repo)
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        comment_id = comment.id
        session.add(
            Coding(
                id="seed-proposed",
                comment_id=comment.id,
                label_id=label.id,
                coder_type="ai",
                status="proposed",
                confidence=0.84,
                rationale="Asks why the method was chosen.",
            )
        )
        session.commit()
    accept_coding(comment_id)
    assert "accept" in _event_types()
    assert inbox_items() == []
    undo()
    items = inbox_items()
    assert len(items) == 1
    assert items[0].comment.id == comment_id
    assert list_examples(label.id) == []
    with get_session() as session:
        coding = session.first(Coding)
        assert coding.status == "proposed"


def test_accept_undo_restores_previous_example_text(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why this method?}\n")
    extract_project(repo)
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        comment_id = comment.id
        comment.raw_text = "Why this method?"
        comment.context_text = "The experiment only shows a correlation."
        session.add(
            Coding(
                id="seed-proposed",
                comment_id=comment.id,
                label_id=label.id,
                coder_type="ai",
                status="proposed",
                confidence=0.84,
                rationale="Asks why the method was chosen.",
            )
        )
        session.commit()
    add_example(label.id, text="Why this method?", source_comment_id=comment_id)
    accept_coding(comment_id)
    with get_session() as session:
        assert session.first(LabelExample).text == "The experiment only shows a correlation."
    undo()
    with get_session() as session:
        assert session.first(LabelExample).text == "Why this method?"
    redo()
    with get_session() as session:
        assert session.first(LabelExample).text == "The experiment only shows a correlation."


def test_undo_change_restores_previous_label(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why this method?}\n")
    extract_project(repo)
    first = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    second = create_label(
        name="Weak evidence",
        definition="evidence is thin",
    )
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "label_id": first.id,
                    "confidence": 0.84,
                    "rationale": "Asks why the method was chosen.",
                }
            )
        )
    )
    comment_id = list_working_observations(first.id)[0].id
    change_coding(comment_id, label_id=second.id)
    change = next(event for event in list_history()["events"] if event["event_type"] == "change")
    assert "example_updates" not in change["payload"]
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
                {"recommendation": "new", "label_name": "Unclear thesis", "confidence": 0.7, "rationale": "Unclear."}
            )
        )
    )
    assert summary.coded == 2
    propose = [event for event in list_history()["events"] if event["event_type"] == "propose"]
    assert len(propose) == 1
    assert len(propose[0]["payload"]["created"]) == 2
    assert propose[0]["payload"]["created_label_ids"]
    assert propose[0]["summary"].startswith("Label with AI")
    undo()
    with get_session() as session:
        assert session.find(Coding, status="accepted") == []
        minted = session.get(Label, propose[0]["payload"]["created_label_ids"][0])
        assert minted.status == "inactive"
    assert len(inbox_items()) == 2


def test_propose_undo_redo_restores_previous_example_text(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why this method?}\n")
    extract_project(repo)
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        comment_id = comment.id
        comment.raw_text = "Why this method?"
        comment.context_text = "The experiment only shows a correlation."
        session.commit()
    add_example(label.id, text="Why this method?", source_comment_id=comment_id)
    summary = code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "label_id": label.id,
                    "confidence": 0.84,
                    "rationale": "Asks why the method was chosen.",
                }
            )
        )
    )
    assert summary.coded == 1
    propose = next(event for event in list_history()["events"] if event["event_type"] == "propose")
    assert propose["payload"]["example_updates"]
    with get_session() as session:
        assert session.first(LabelExample).text == "The experiment only shows a correlation."
    undo()
    with get_session() as session:
        assert session.first(LabelExample).text == "Why this method?"
    redo()
    with get_session() as session:
        assert session.first(LabelExample).text == "The experiment only shows a correlation."


def test_new_action_drops_redo_tail(db):
    label = create_label(
        name="Overly strong claim",
        definition="old",
    )
    rename_label(label.id, name="Overclaiming")
    undo()
    create_label(name="Ambiguous terminology", definition="vague")
    history = list_history()
    assert history["can_redo"] is False
    assert "rename" not in _event_types(include_undone=True)


def test_delete_undo_restores_comment_and_dependents(db, tmp_path):
    from reviewdistill.db.models import LabelExample
    from reviewdistill.taxonomy.operations import add_example

    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Keep me.}\n")
    extract_project(repo)
    label = create_label(name="Overclaiming", definition="too strong")
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
        raw = session.get(ProofreadingComment, comment_id).raw_text
    change_coding(comment_id, label_id=label.id)
    add_example(label.id, text="Too strong.", source_comment_id=comment_id)
    delete_comment(comment_id)
    assert "delete" in _event_types()
    undo()
    with get_session() as session:
        row = session.get(ProofreadingComment, comment_id)
        assert row is not None
        assert row.raw_text == raw
        assert session.find(Coding, comment_id=comment_id)
        assert session.find(LabelExample, source_comment_id=comment_id)
    assert list_examples(label.id)
    redo()
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id) is None


def test_unverify_undo_restores_verified(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Keep me.}\n")
    extract_project(repo)
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    verify_comment(comment_id)
    verify_comment(comment_id)
    assert "unverify" in _event_types()
    undo()
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id).verified
    redo()
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id).verified is False


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
        assert comment.verified is False
    verify_comment(comment_id)
    assert "verify" in _event_types()
    undo()
    with get_session() as session:
        row = session.get(ProofreadingComment, comment_id)
        assert row.verified is False
        assert row.status == "pending_disappeared"


def test_comment_from_dump_maps_quality():
    from reviewdistill.history import comment_from_dump

    row = comment_from_dump(
        {
            "id": "c1",
            "project_id": "p1",
            "source_type": "latex_command",
            "source_command": "myremark",
            "file_path": "main.tex",
            "line_number": 1,
            "raw_text": "Too strong.",
            "status": "active",
            "quality": "verified",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    assert row.verified is True


def test_history_api_undo_redo_and_empty_errors(db):
    client = TestClient(create_app())
    empty = client.get("/api/history")
    assert empty.status_code == 200
    assert empty.json()["events"] == []
    assert empty.json()["can_undo"] is False
    assert empty.json()["can_redo"] is False
    assert client.post("/api/history/undo").status_code == 400
    assert client.post("/api/history/redo").status_code == 400

    create_label(name="Unsupported claim", definition="a")
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


def test_list_history_sorts_naive_and_aware_created_at(rd_home):
    from reviewdistill.db.session import init_db, reset_engine

    reset_engine()
    (rd_home / "taxonomy_events.jsonl").write_text(
        json.dumps(
            {
                "id": "old",
                "event_type": "add",
                "payload_json": "{}",
                "undone": False,
                "created_at": "2026-09-08T06:41:03.626817",
            }
        )
        + "\n"
        + json.dumps(
            {
                "id": "new",
                "event_type": "add",
                "payload_json": "{}",
                "undone": False,
                "created_at": "2026-09-13T09:42:18.900855Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    body = list_history()
    assert [event["id"] for event in body["events"]] == ["new", "old"]


def test_recycle_undo_redo_restores_unlabeled(db):
    create_label(name="Existing", definition="")
    with get_session() as session:
        for comment_id, text in (("c1", "too strong"), ("c2", "hedge this")):
            session.add(
                ProofreadingComment(
                    id=comment_id,
                    project_id="p",
                    source_type="latex_command",
                    source_command="myremark",
                    file_path="main.tex",
                    line_number=1,
                    raw_text=text,
                    status="active",
                    quality="unreviewed",
                )
            )
        session.add(
            Coding(
                id="k-prop",
                comment_id="c1",
                label_id=None,
                coder_type="ai",
                status="proposed",
                proposed_label_name="Maybe",
                proposed_label_definition="too strong",
            )
        )
        session.commit()
    created = recycle_ungrouped()
    history = list_history()
    assert history["events"][0]["event_type"] == "recycle"
    assert history["events"][0]["summary"] == "Group unlabeled comments onto ungrouped"
    assert history["can_undo"] is True
    undo()
    with get_session() as session:
        assert session.get(Label, created.id).status == "inactive"
        assert not is_labeled(session, "c1")
        assert not is_labeled(session, "c2")
        assert session.get(Coding, "k-prop").status == "proposed"
    redo()
    with get_session() as session:
        assert session.get(Label, created.id).status == "active"
        assert is_labeled(session, "c1")
        assert is_labeled(session, "c2")
        assert session.get(Coding, "k-prop").status == CODING_MODIFIED

