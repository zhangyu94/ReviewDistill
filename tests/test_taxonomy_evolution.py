import json

import pytest

from reviewdistill.db.models import Assignment, LabelExample, Label, ProofreadingComment, TaxonomyEvent
from reviewdistill.db.session import get_session
from reviewdistill.history import list_history
from reviewdistill.labeling.split import SplitPlan
from reviewdistill.taxonomy.operations import (
    add_example,
    apply_split,
    create_label,
    deactivate_label,
    edit_label,
    list_active_labels,
    list_working_observations,
    merge_labels,
    move_label,
    rename_label,
)


def test_rename_and_edit_keep_id(db):
    label = create_label(
        name="Overly strong claim",
        definition="old",
    )
    renamed = rename_label(label.id, name="Overclaiming")
    edited = edit_label(
        label.id,
        definition="A claim is stronger than the evidence supports.",
        detection_guidance="demonstrate, prove, establish",
    )
    assert renamed.id == label.id
    assert edited.name == "Overclaiming"
    assert edited.definition.startswith("A claim is stronger")
    assert "notes" not in edited.model_dump()
    payload = next(
        event["payload"]
        for event in list_history()["events"]
        if event["event_type"] == "edit"
    )
    assert "notes" not in payload["before"]
    assert "notes" not in payload["after"]
    assert "detection_guidance" in payload["after"]


def test_move_inner_nests_under_target(db):
    parent = create_label(name="Parent", definition="p")
    child = create_label(name="Child", definition="c")
    moved = move_label(child.id, parent_id=parent.id, position=0)
    assert moved.parent_id == parent.id
    assert moved.position == 0


def test_move_refuses_under_descendant(db):
    from reviewdistill.errors import BadInput

    root = create_label(name="Root", definition="r")
    child = create_label(name="A", definition="a", parent_id=root.id)
    with pytest.raises(BadInput):
        move_label(root.id, parent_id=child.id, position=0)


def test_deactivate_hides_from_active_list(db):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    deactivate_label(label.id)
    assert list_active_labels() == []
    with get_session() as session:
        assert session.get(Label, label.id).status == "inactive"


def test_deactivate_returns_accepted_comments_to_unlabeled(db):
    from reviewdistill.labeling.validation import inbox_items
    from reviewdistill.history import redo, undo

    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    other = create_label(
        name="Weak evidence",
        definition="evidence is thin",
    )
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-deact",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Too strong.",
                status="active",
            )
        )
        session.add(
            Assignment(
                id="coding-deact",
                comment_id="c-deact",
                label_id=label.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Assignment(
                id="coding-deact-old",
                comment_id="c-deact",
                label_id=label.id,
                coder_type="ai",
                status="modified",
            )
        )
        session.add(
            ProofreadingComment(
                id="c-other",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=2,
                raw_text="Weak evidence.",
                status="active",
            )
        )
        session.add(
            Assignment(
                id="coding-other",
                comment_id="c-other",
                label_id=other.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Assignment(
                id="coding-other-old",
                comment_id="c-other",
                label_id=label.id,
                coder_type="ai",
                status="modified",
            )
        )
        session.commit()

    deactivate_label(label.id)
    items = inbox_items()
    assert [item.comment.id for item in items] == ["c-deact"]
    assert items[0].labeled is False
    with get_session() as session:
        assert session.find(Assignment, comment_id="c-deact") == []
        other_assignments = {row.id: row.status for row in session.find(Assignment, comment_id="c-other")}
        assert other_assignments == {"coding-other": "accepted", "coding-other-old": "modified"}
    assert [row.id for row in list_working_observations(other.id)] == ["c-other"]
    undo()
    assert inbox_items() == []
    with get_session() as session:
        restored = session.get(Assignment, "coding-deact")
        assert restored is not None
        assert restored.status == "accepted"
        assert session.get(Assignment, "coding-deact-old").status == "modified"
        assert session.get(Label, label.id).status == "active"
        assert session.get(Assignment, "coding-other").status == "accepted"
    redo()
    assert [item.comment.id for item in inbox_items()] == ["c-deact"]
    with get_session() as session:
        assert session.find(Assignment, comment_id="c-deact") == []
        assert session.get(Assignment, "coding-other").status == "accepted"


def test_merge_moves_assignments_and_examples_to_target(db):
    a = create_label(name="Unsupported claim", definition="a")
    b = create_label(name="Overly strong claim", definition="b")
    target = create_label(
        name="Overclaiming", definition="c"
    )
    add_example(a.id, text="from A", source_comment_id="c1")
    add_example(a.id, text="unique from A", source_comment_id="c2")
    add_example(target.id, text="already on target", source_comment_id="c1")
    with get_session() as session:
        session.add(
            Assignment(
                id="coding-a",
                comment_id="c1",
                label_id=a.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()

    merged = merge_labels(source_ids=[a.id, b.id], target_id=target.id)
    assert merged.id == target.id
    assert {i.id for i in list_active_labels()} == {target.id}

    with get_session() as session:
        coding = session.get(Assignment, "coding-a")
        assert coding.label_id == target.id
        examples = session.find(LabelExample, label_id=target.id)
        texts = {row.text for row in examples}
        assert texts == {"already on target", "unique from A"}
        assert session.find(LabelExample, label_id=a.id) == []
        assert session.get(Label, a.id).status == "inactive"
        events = [e for e in session.find(TaxonomyEvent) if e.event_type == "merge"]
        payload = json.loads(events[-1].payload_json)
        assert payload["target_id"] == target.id
        assert set(payload["source_ids"]) == {a.id, b.id}


def test_create_label_suffixes_duplicate_active_name(db):
    create_label(name="Overclaiming", definition="a")
    second = create_label(name="Overclaiming", definition="b")
    assert second.name == "Overclaiming (2)"
    assert {i.name for i in list_active_labels()} == {"Overclaiming", "Overclaiming (2)"}


def test_apply_split_uniquifies_duplicate_child_names(db):
    source = create_label(
        name="Insufficient explanation",
        definition="too broad",
    )
    apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "Dup", "definition": "a"},
                {"name": "Dup", "definition": "b"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    assert {i.name for i in list_active_labels()} == {
        "Insufficient explanation",
        "Dup",
        "Dup (2)",
    }


def test_apply_split_suffixes_child_named_like_source(db):
    source = create_label(
        name="Insufficient explanation",
        definition="too broad",
    )
    apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "Insufficient explanation", "definition": "a"},
                {"name": "Missing methodological justification", "definition": "b"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    assert {i.name for i in list_active_labels()} == {
        "Insufficient explanation",
        "Insufficient explanation (2)",
        "Missing methodological justification",
    }
