import json

from reviewdistill.db.models import IssueExample, TaxonomyEvent
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import add_example, create_issue_type, list_active_issue_types


def test_create_issue_type_logs_add_event(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="A claim is stated more strongly than the evidence supports.",
    )
    assert issue.code == "OVERCLAIM"
    types = list_active_issue_types()
    assert [t.name for t in types] == ["Overclaiming"]

    with get_session() as session:
        events = session.find(TaxonomyEvent)
        assert len(events) == 1
        assert events[0].event_type == "add"
        payload = json.loads(events[0].payload_json)
        assert payload["issue_type_id"] == issue.id


def test_add_example_from_comment_text(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    example = add_example(issue.id, text=' "demonstrate" → "suggest" ', source_comment_id="c1")
    with get_session() as session:
        rows = session.find(IssueExample)
        assert rows[0].text == '"demonstrate" → "suggest"'
        assert rows[0].source_comment_id == "c1"
        assert example.id == rows[0].id


def test_add_example_is_idempotent_per_comment(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    add_example(issue.id, text="demo", source_comment_id="c1")
    add_example(issue.id, text="demo again", source_comment_id="c1")
    with get_session() as session:
        assert len(session.find(IssueExample)) == 1
