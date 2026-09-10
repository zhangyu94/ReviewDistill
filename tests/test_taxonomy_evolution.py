import json

from sqlmodel import select

from reviewdistill.db.models import Coding, IssueCounterexample, IssueExample, IssueType, ProofreadingComment, TaxonomyEvent
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import (
    add_counterexample,
    add_example,
    create_issue_type,
    deactivate_issue_type,
    edit_issue_type,
    list_active_issue_types,
    merge_issue_types,
    move_issue_type,
    rename_issue_type,
    split_issue_type,
)


def test_rename_and_edit_keep_id(db):
    issue = create_issue_type(
        code="STRONG",
        name="Overly strong claim",
        category="Argumentation",
        definition="old",
    )
    renamed = rename_issue_type(issue.id, name="Overclaiming", code="OVERCLAIM")
    edited = edit_issue_type(
        issue.id,
        definition="A claim is stronger than the evidence supports.",
        notes="Watch epistemic verbs.",
        detection_guidance="demonstrate, prove, establish",
    )
    assert renamed.id == issue.id
    assert edited.name == "Overclaiming"
    assert edited.code == "OVERCLAIM"
    assert edited.definition.startswith("A claim is stronger")
    assert edited.notes is not None


def test_move_changes_category(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Clarity",
        definition="too strong",
    )
    moved = move_issue_type(issue.id, category="Argumentation")
    assert moved.category == "Argumentation"


def test_deactivate_hides_from_active_list(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="too strong",
    )
    deactivate_issue_type(issue.id)
    assert list_active_issue_types() == []
    with get_session() as session:
        assert session.get(IssueType, issue.id).status == "inactive"


def test_merge_moves_codings_examples_and_counterexamples_to_target(db):
    a = create_issue_type(code="U", name="Unsupported claim", category="Argumentation", definition="a")
    b = create_issue_type(code="S", name="Overly strong claim", category="Argumentation", definition="b")
    target = create_issue_type(
        code="OVERCLAIM", name="Overclaiming", category="Argumentation", definition="c"
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
        examples = list(session.exec(select(IssueExample).where(IssueExample.issue_type_id == target.id)))
        texts = {row.text for row in examples}
        assert texts == {"already on target", "unique from A"}
        assert list(session.exec(select(IssueExample).where(IssueExample.issue_type_id == a.id))) == []
        counters = list(
            session.exec(select(IssueCounterexample).where(IssueCounterexample.issue_type_id == target.id))
        )
        assert any(row.text == "not A" for row in counters)
        assert session.get(IssueType, a.id).status == "inactive"
        events = [e for e in session.exec(select(TaxonomyEvent)) if e.event_type == "merge"]
        payload = json.loads(events[-1].payload_json)
        assert payload["target_id"] == target.id
        assert set(payload["source_ids"]) == {a.id, b.id}


def test_split_deactivates_source_and_creates_two_active_types(db):
    source = create_issue_type(
        code="INSUFF",
        name="Insufficient explanation",
        category="Methodology",
        definition="too broad",
    )
    left, right = split_issue_type(
        source.id,
        left={
            "code": "MOTIVE",
            "name": "Missing motivation",
            "category": "Methodology",
            "definition": "Why this problem matters is missing.",
        },
        right={
            "code": "METHJUST",
            "name": "Missing methodological justification",
            "category": "Methodology",
            "definition": "A design choice is unexplained.",
        },
    )
    active = {i.code for i in list_active_issue_types()}
    assert active == {"MOTIVE", "METHJUST"}
    with get_session() as session:
        assert session.get(IssueType, source.id).status == "inactive"
        assert left.id != source.id
        assert right.id != source.id


def test_split_returns_accepted_comments_to_uncoded(db):
    from reviewdistill.coding.validation import inbox_items

    source = create_issue_type(
        code="INSUFF",
        name="Insufficient explanation",
        category="Methodology",
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
            "code": "MOTIVE",
            "name": "Missing motivation",
            "category": "Methodology",
            "definition": "Why this problem matters is missing.",
        },
        right={
            "code": "METHJUST",
            "name": "Missing methodological justification",
            "category": "Methodology",
            "definition": "A design choice is unexplained.",
        },
    )
    items = inbox_items()
    assert [item.comment.id for item in items] == ["c-split"]
    assert items[0].coding is None
    with get_session() as session:
        leftover = list(session.exec(select(Coding).where(Coding.comment_id == "c-split")))
        assert leftover == []


def test_create_issue_type_rejects_duplicate_active_code(db):
    create_issue_type(code="OVERCLAIM", name="Overclaiming", category="Argumentation", definition="a")
    try:
        create_issue_type(code="OVERCLAIM", name="Overclaiming 2", category="Argumentation", definition="b")
    except ValueError as exc:
        assert "OVERCLAIM" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    assert [i.name for i in list_active_issue_types()] == ["Overclaiming"]


def _split_sides(left_code: str, right_code: str) -> tuple[dict, dict]:
    return (
        {
            "code": left_code,
            "name": "Missing motivation",
            "category": "Methodology",
            "definition": "Why this problem matters is missing.",
        },
        {
            "code": right_code,
            "name": "Missing methodological justification",
            "category": "Methodology",
            "definition": "A design choice is unexplained.",
        },
    )


def test_split_rejects_duplicate_left_and_right_codes(db):
    source = create_issue_type(
        code="INSUFF",
        name="Insufficient explanation",
        category="Methodology",
        definition="too broad",
    )
    left, right = _split_sides("DUP", "DUP")
    try:
        split_issue_type(source.id, left=left, right=right)
    except ValueError as exc:
        assert "DUP" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    assert [i.code for i in list_active_issue_types()] == ["INSUFF"]


def test_split_rejects_code_taken_by_another_active_type(db):
    source = create_issue_type(
        code="INSUFF",
        name="Insufficient explanation",
        category="Methodology",
        definition="too broad",
    )
    create_issue_type(code="OVERCLAIM", name="Overclaiming", category="Argumentation", definition="a")
    left, right = _split_sides("OVERCLAIM", "METHJUST")
    try:
        split_issue_type(source.id, left=left, right=right)
    except ValueError as exc:
        assert "OVERCLAIM" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    active = {i.code for i in list_active_issue_types()}
    assert active == {"INSUFF", "OVERCLAIM"}


def test_split_may_reuse_source_code(db):
    source = create_issue_type(
        code="INSUFF",
        name="Insufficient explanation",
        category="Methodology",
        definition="too broad",
    )
    left, right = _split_sides("INSUFF", "METHJUST")
    split_issue_type(source.id, left=left, right=right)
    assert {i.code for i in list_active_issue_types()} == {"INSUFF", "METHJUST"}
