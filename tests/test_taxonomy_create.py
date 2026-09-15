import json

from reviewdistill.db.models import LabelExample, TaxonomyEvent
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import add_example, create_label, list_active_labels


def test_create_label_logs_add_event(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is stated more strongly than the evidence supports.",
    )
    assert [t.name for t in list_active_labels()] == ["Overclaiming"]

    with get_session() as session:
        events = session.find(TaxonomyEvent)
        assert len(events) == 1
        assert events[0].event_type == "add"
        payload = json.loads(events[0].payload_json)
        assert payload["label_id"] == label.id


def test_add_example_from_comment_text(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    example = add_example(label.id, text=' "demonstrate" → "suggest" ', source_comment_id="c1")
    with get_session() as session:
        rows = session.find(LabelExample)
        assert rows[0].text == '"demonstrate" → "suggest"'
        assert rows[0].source_comment_id == "c1"
        assert example.id == rows[0].id


def test_add_example_is_idempotent_per_comment(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    add_example(label.id, text="demo", source_comment_id="c1")
    add_example(label.id, text="demo again", source_comment_id="c1")
    with get_session() as session:
        assert len(session.find(LabelExample)) == 1
