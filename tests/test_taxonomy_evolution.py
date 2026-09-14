import json

import pytest

from reviewdistill.db.models import Coding, IssueCounterexample, IssueExample, IssueType, ProofreadingComment, TaxonomyEvent
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import (
    add_counterexample,
    add_example,
    create_issue_type,
    deactivate_issue_type,
    edit_issue_type,
    list_active_issue_types,
    list_working_observations,
    merge_issue_types,
    move_issue_type,
    rename_issue_type,
    split_issue_type,
)


def test_rename_and_edit_keep_id(db):
    issue = create_issue_type(
        name="Overly strong claim",
        definition="old",
    )
    renamed = rename_issue_type(issue.id, name="Overclaiming")
    edited = edit_issue_type(
        issue.id,
        definition="A claim is stronger than the evidence supports.",
        notes="Watch epistemic verbs.",
        detection_guidance="demonstrate, prove, establish",
    )
    assert renamed.id == issue.id
    assert edited.name == "Overclaiming"
    assert edited.definition.startswith("A claim is stronger")
    assert edited.notes is not None


def test_move_inner_nests_under_target(db):
    parent = create_issue_type(name="Parent", definition="p")
    child = create_issue_type(name="Child", definition="c")
    moved = move_issue_type(child.id, parent_id=parent.id, position=0)
    assert moved.parent_id == parent.id
    assert moved.position == 0


def test_move_refuses_under_descendant(db):
    from reviewdistill.errors import BadInput

    root = create_issue_type(name="Root", definition="r")
    child = create_issue_type(name="A", definition="a", parent_id=root.id)
    with pytest.raises(BadInput):
        move_issue_type(root.id, parent_id=child.id, position=0)


def test_deactivate_hides_from_active_list(db):
    issue = create_issue_type(
        name="Overclaiming",
        definition="too strong",
    )
    deactivate_issue_type(issue.id)
    assert list_active_issue_types() == []
    with get_session() as session:
        assert session.get(IssueType, issue.id).status == "inactive"


def test_deactivate_returns_accepted_comments_to_unlabeled(db):
    from reviewdistill.coding.validation import inbox_items
    from reviewdistill.history import redo, undo

    issue = create_issue_type(
        name="Overclaiming",
        definition="too strong",
    )
    other = create_issue_type(
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
                fingerprint="fp-deact",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-deact",
                comment_id="c-deact",
                issue_type_id=issue.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Coding(
                id="coding-deact-old",
                comment_id="c-deact",
                issue_type_id=issue.id,
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
                fingerprint="fp-other",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-other",
                comment_id="c-other",
                issue_type_id=other.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Coding(
                id="coding-other-old",
                comment_id="c-other",
                issue_type_id=issue.id,
                coder_type="ai",
                status="modified",
            )
        )
        session.commit()

    deactivate_issue_type(issue.id)
    items = inbox_items()
    assert [item.comment.id for item in items] == ["c-deact"]
    assert items[0].labeled is False
    with get_session() as session:
        assert session.find(Coding, comment_id="c-deact") == []
        other_codings = {row.id: row.status for row in session.find(Coding, comment_id="c-other")}
        assert other_codings == {"coding-other": "accepted", "coding-other-old": "modified"}
    assert [row.id for row in list_working_observations(other.id)] == ["c-other"]
    undo()
    assert inbox_items() == []
    with get_session() as session:
        restored = session.get(Coding, "coding-deact")
        assert restored is not None
        assert restored.status == "accepted"
        assert session.get(Coding, "coding-deact-old").status == "modified"
        assert session.get(IssueType, issue.id).status == "active"
        assert session.get(Coding, "coding-other").status == "accepted"
    redo()
    assert [item.comment.id for item in inbox_items()] == ["c-deact"]
    with get_session() as session:
        assert session.find(Coding, comment_id="c-deact") == []
        assert session.get(Coding, "coding-other").status == "accepted"


def test_merge_moves_codings_examples_and_counterexamples_to_target(db):
    a = create_issue_type(name="Unsupported claim", definition="a")
    b = create_issue_type(name="Overly strong claim", definition="b")
    target = create_issue_type(
        name="Overclaiming", definition="c"
    )
    add_example(a.id, text="from A", source_comment_id="c1")
    add_example(a.id, text="unique from A", source_comment_id="c2")
    add_example(target.id, text="already on target", source_comment_id="c1")
    add_counterexample(a.id, text="not A")
    with get_session() as session:
        session.add(
            Coding(
                id="coding-a",
                comment_id="c1",
                issue_type_id=a.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()

    merged = merge_issue_types(source_ids=[a.id, b.id], target_id=target.id)
    assert merged.id == target.id
    assert {i.id for i in list_active_issue_types()} == {target.id}

    with get_session() as session:
        coding = session.get(Coding, "coding-a")
        assert coding.issue_type_id == target.id
        examples = session.find(IssueExample, issue_type_id=target.id)
        texts = {row.text for row in examples}
        assert texts == {"already on target", "unique from A"}
        assert session.find(IssueExample, issue_type_id=a.id) == []
        counters = session.find(IssueCounterexample, issue_type_id=target.id)
        assert any(row.text == "not A" for row in counters)
        assert session.get(IssueType, a.id).status == "inactive"
        events = [e for e in session.find(TaxonomyEvent) if e.event_type == "merge"]
        payload = json.loads(events[-1].payload_json)
        assert payload["target_id"] == target.id
        assert set(payload["source_ids"]) == {a.id, b.id}


def test_split_creates_siblings_under_same_parent(db):
    parent = create_issue_type(name="Parent", definition="")
    source = create_issue_type(name="Source", definition="", parent_id=parent.id)
    left, right = split_issue_type(
        source.id,
        left={"name": "Left", "definition": "l"},
        right={"name": "Right", "definition": "r"},
    )
    assert left.parent_id == parent.id
    assert right.parent_id == parent.id
    assert {left.position, right.position} == {0, 1}


def test_split_inserts_pair_before_later_sibling(db):
    create_issue_type(name="Alpha", definition="")
    writing = create_issue_type(name="Writing", definition="")
    create_issue_type(name="Style", definition="")
    left, right = split_issue_type(
        writing.id,
        left={"name": "Writing (A)", "definition": "a"},
        right={"name": "Writing (B)", "definition": "b"},
    )
    with get_session() as session:
        roots = sorted(
            [row for row in session.find(IssueType) if row.status == "active" and row.parent_id is None],
            key=lambda row: row.position,
        )
        assert [row.name for row in roots] == ["Alpha", "Writing (A)", "Writing (B)", "Style"]
        assert left.position == 1
        assert right.position == 2


def test_split_deactivates_source_and_creates_two_active_types(db):
    source = create_issue_type(
        name="Insufficient explanation",
        definition="too broad",
    )
    left, right = split_issue_type(
        source.id,
        left={
            "name": "Missing motivation",
            "definition": "Why this problem matters is missing.",
        },
        right={
            "name": "Missing methodological justification",
            "definition": "A design choice is unexplained.",
        },
    )
    active = {i.name for i in list_active_issue_types()}
    assert active == {"Missing motivation", "Missing methodological justification"}
    with get_session() as session:
        assert session.get(IssueType, source.id).status == "inactive"
        assert left.id != source.id
        assert right.id != source.id


def test_split_returns_accepted_comments_to_unlabeled(db):
    from reviewdistill.coding.validation import inbox_items

    source = create_issue_type(
        name="Insufficient explanation",
        definition="too broad",
    )
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-split",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Why this method?",
                fingerprint="fp-split",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-split",
                comment_id="c-split",
                issue_type_id=source.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Coding(
                id="coding-split-old",
                comment_id="c-split",
                issue_type_id=source.id,
                coder_type="ai",
                status="modified",
            )
        )
        session.commit()

    split_issue_type(
        source.id,
        left={
            "name": "Missing motivation",
            "definition": "Why this problem matters is missing.",
        },
        right={
            "name": "Missing methodological justification",
            "definition": "A design choice is unexplained.",
        },
    )
    items = inbox_items()
    assert [item.comment.id for item in items] == ["c-split"]
    assert items[0].coding is None
    with get_session() as session:
        leftover = session.find(Coding, comment_id="c-split")
        assert leftover == []


def test_create_issue_type_suffixes_duplicate_active_name(db):
    create_issue_type(name="Overclaiming", definition="a")
    second = create_issue_type(name="Overclaiming", definition="b")
    assert second.name == "Overclaiming (2)"
    assert {i.name for i in list_active_issue_types()} == {"Overclaiming", "Overclaiming (2)"}


def test_split_uniquifies_duplicate_names(db):
    source = create_issue_type(
        name="Insufficient explanation",
        definition="too broad",
    )
    split_issue_type(
        source.id,
        left={"name": "Dup", "definition": "a"},
        right={"name": "Dup", "definition": "b"},
    )
    assert {i.name for i in list_active_issue_types()} == {"Dup", "Dup (2)"}


def test_split_reuses_source_name(db):
    source = create_issue_type(
        name="Insufficient explanation",
        definition="too broad",
    )
    split_issue_type(
        source.id,
        left={"name": "Insufficient explanation", "definition": "a"},
        right={"name": "Missing methodological justification", "definition": "b"},
    )
    assert {i.name for i in list_active_issue_types()} == {
        "Insufficient explanation",
        "Missing methodological justification",
    }
