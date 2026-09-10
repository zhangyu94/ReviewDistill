from reviewdistill.coding.retrieval import retrieve_candidates
from reviewdistill.db.models import ProofreadingComment
from reviewdistill.taxonomy.operations import add_example, create_issue_type, deactivate_issue_type, list_examples


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
        fingerprint="x",
        status="active",
    )


def test_retrieval_ranks_overlapping_issue_highest(db):
    overclaim = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="A claim is stated more strongly than the evidence supports.",
    )
    add_example(overclaim.id, text="demonstrate is too strong; prefer suggest")
    create_issue_type(
        code="AMBIG",
        name="Ambiguous terminology",
        category="Clarity",
        definition="A term is used without a precise definition.",
    )
    ranked = retrieve_candidates(
        _comment('I think "demonstrate" is too strong here.', "The results demonstrate that"),
        limit=3,
    )
    assert ranked[0].id == overclaim.id
    assert ranked[0].score > 0


def test_retrieval_ignores_inactive_issues(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="demonstrate too strong",
    )
    deactivate_issue_type(issue.id)
    ranked = retrieve_candidates(_comment("demonstrate is too strong"))
    assert ranked == []


def test_retrieval_ignores_examples_from_retracted_comments(db):
    from reviewdistill.db.models import ProofreadingComment as Row
    from reviewdistill.db.session import get_session

    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="A claim exceeds the evidence.",
    )
    with get_session() as session:
        session.add(
            Row(
                id="retracted-src",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="UNIQUE_RETRACTED_TOKEN",
                fingerprint="fp-r",
                status="retracted",
            )
        )
        session.commit()
    add_example(issue.id, text="UNIQUE_RETRACTED_TOKEN is too strong", source_comment_id="retracted-src")
    ranked = retrieve_candidates(_comment("UNIQUE_RETRACTED_TOKEN is too strong"))
    assert list_examples(issue.id) == []
    assert all("UNIQUE_RETRACTED_TOKEN" not in (item.issue.definition or "") for item in ranked)
