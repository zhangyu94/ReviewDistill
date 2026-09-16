from reviewdistill.labeling.retrieval import retrieve_candidates
from reviewdistill.db.models import ProofreadingComment
from reviewdistill.taxonomy.operations import add_example, create_label, deactivate_label, list_examples


def _comment(text: str, context: str = "") -> ProofreadingComment:
    return ProofreadingComment(
        id="c1",
        project_id="p1",
        source_type="latex_command",
        source_command="myremark",
        file_path="main.tex",
        line_number=1,
        raw_text=text,
        context_text=context,
        status="active",
    )


def _count_store_loads(monkeypatch):
    from reviewdistill.db.session import StoreSession

    counts = {"n": 0}
    original = StoreSession._load

    def wrapped(self):
        counts["n"] += 1
        return original(self)

    monkeypatch.setattr(StoreSession, "_load", wrapped)
    return counts


def test_retrieval_ranks_overlapping_issue_highest(db):
    overclaim = create_label(
        name="Overclaiming",
        definition="A claim is stated more strongly than the evidence supports.",
    )
    add_example(overclaim.id, text="demonstrate is too strong; prefer suggest")
    create_label(
        name="Ambiguous terminology",
        definition="A term is used without a precise definition.",
    )
    ranked = retrieve_candidates(
        _comment('I think "demonstrate" is too strong here.', "The results demonstrate that"),
        limit=3,
    )
    assert ranked[0].id == overclaim.id
    assert ranked[0].score > 0


def test_retrieval_ignores_inactive_issues(db):
    label = create_label(
        name="Overclaiming",
        definition="demonstrate too strong",
    )
    deactivate_label(label.id)
    ranked = retrieve_candidates(_comment("demonstrate is too strong"))
    assert ranked == []


def test_retrieval_skips_types_that_have_children(db):
    parent = create_label(
        name="Overclaiming parent",
        definition="demonstrate too strong",
    )
    child = create_label(
        name="Child leaf",
        definition="demonstrate too strong",
        parent_id=parent.id,
    )
    ranked = retrieve_candidates(_comment("demonstrate is too strong"))
    assert [row.id for row in ranked] == [child.id]


def test_retrieval_ignores_examples_from_comments_not_to_distill(db):
    from reviewdistill.db.models import ProofreadingComment as Row
    from reviewdistill.db.session import get_session

    label = create_label(
        name="Overclaiming",
        definition="A claim exceeds the evidence.",
    )
    with get_session() as session:
        session.add(
            Row(
                id="dropped-src",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="UNIQUE_DROPPED_TOKEN",
                status="pending_disappeared",
            )
        )
        session.commit()
    add_example(label.id, text="UNIQUE_DROPPED_TOKEN is too strong", source_comment_id="dropped-src")
    ranked = retrieve_candidates(_comment("UNIQUE_DROPPED_TOKEN is too strong"))
    assert list_examples(label.id) == []
    assert all("UNIQUE_DROPPED_TOKEN" not in (item.label.definition or "") for item in ranked)


def test_retrieve_candidates_loads_store_once(db, monkeypatch):
    for index in range(3):
        create_label(
            name=f"Issue {index} demonstrate",
            definition="A claim is stated more strongly than the evidence supports.",
        )
    loads = _count_store_loads(monkeypatch)
    retrieve_candidates(_comment("demonstrate is too strong"))
    assert loads["n"] == 1
