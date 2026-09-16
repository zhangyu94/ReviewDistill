import json

from reviewdistill.db.models import Coding, LabelExample, ProofreadingComment, TaxonomyEvent
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import (
    add_example,
    create_label,
    example_text,
    list_active_labels,
    list_examples,
)


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


def test_add_example_updates_text_for_same_comment(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    add_example(label.id, text="demo", source_comment_id="c1")
    add_example(label.id, text="demo again", source_comment_id="c1")
    with get_session() as session:
        rows = session.find(LabelExample)
        assert len(rows) == 1
        assert rows[0].text == "demo again"


def test_list_examples_and_export_use_current_manuscript_context(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Too strong.",
                context_text="The experiment only shows a correlation.",
                status="active",
            )
        )
        session.add(
            Coding(
                id="k1",
                comment_id="c1",
                label_id=label.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    add_example(label.id, text="Too strong.", source_comment_id="c1")
    shown = list_examples(label.id)
    assert shown[0].text == "The experiment only shows a correlation."
    with get_session() as session:
        assert session.first(LabelExample).text == "Too strong."
    md = export_rubric(fmt="md")
    assert "The experiment only shows a correlation." in md
    assert "Too strong." not in md


def test_export_keeps_multiline_context_as_one_list_item(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is too strong.",
    )
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Too strong.",
                context_text="The experiment only shows\na correlation.",
                status="active",
            )
        )
        session.add(
            Coding(
                id="k1",
                comment_id="c1",
                label_id=label.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    add_example(label.id, text="Too strong.", source_comment_id="c1")
    md = export_rubric(fmt="md")
    assert "- The experiment only shows a correlation." in md
    assert "- The experiment only shows\n" not in md


def test_example_text_prefers_manuscript_context():
    comment = type(
        "C",
        (),
        {"raw_text": "Too strong.", "context_text": "The experiment only shows a correlation."},
    )()
    assert example_text(comment) == "The experiment only shows a correlation."


def test_example_text_falls_back_to_remark_when_context_empty():
    comment = type("C", (), {"raw_text": "Too strong.", "context_text": "  "})()
    assert example_text(comment) == "Too strong."


def test_example_text_collapses_whitespace():
    comment = type(
        "C",
        (),
        {"raw_text": "Too strong.", "context_text": "The experiment only shows\na correlation."},
    )()
    assert example_text(comment) == "The experiment only shows a correlation."
