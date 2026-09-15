import json

import pytest

from reviewdistill.coding.split import (
    SPLIT_TASK,
    SplitPlan,
    build_split_prompt,
    parse_split_output,
    run_header_split,
    run_leaf_split,
)
from reviewdistill.db.models import Coding, Label, ProofreadingComment, TaxonomyEvent, is_labeled
from reviewdistill.db.session import get_session
from reviewdistill.errors import BadInput
from reviewdistill.history import list_history, redo, undo
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import apply_split, create_label, list_active_labels
from reviewdistill.taxonomy.tree import active_children


def test_parse_split_output_maps_every_comment():
    plan = parse_split_output(
        json.dumps(
            {
                "labels": [
                    {"name": "Evidence", "definition": "Too strong for the data."},
                    {"name": "Wording", "definition": "A hedge would be enough."},
                ],
                "assignments": [
                    {"comment_id": "c1", "label_index": 0},
                    {"comment_id": "c2", "label_index": 1},
                ],
            }
        ),
        ["c1", "c2"],
    )
    assert plan == SplitPlan(
        labels=[
            {"name": "Evidence", "definition": "Too strong for the data."},
            {"name": "Wording", "definition": "A hedge would be enough."},
        ],
        assignments=[
            {"comment_id": "c1", "label_index": 0},
            {"comment_id": "c2", "label_index": 1},
        ],
    )


def test_parse_split_output_drops_unused_type_and_reindexes():
    plan = parse_split_output(
        json.dumps(
            {
                "labels": [
                    {"name": "Keep A", "definition": "a"},
                    {"name": "Drop me", "definition": "d"},
                    {"name": "Keep B", "definition": "b"},
                ],
                "assignments": [
                    {"comment_id": "c1", "label_index": 0},
                    {"comment_id": "c2", "label_index": 2},
                ],
            }
        ),
        ["c1", "c2"],
    )
    assert [row["name"] for row in plan.labels] == ["Keep A", "Keep B"]
    assert plan.assignments == [
        {"comment_id": "c1", "label_index": 0},
        {"comment_id": "c2", "label_index": 1},
    ]


def test_parse_split_output_rejects_one_type_after_drop():
    with pytest.raises(ValueError, match="at least two"):
        parse_split_output(
            json.dumps(
                {
                    "labels": [
                        {"name": "Only", "definition": "a"},
                        {"name": "Unused", "definition": "b"},
                    ],
                    "assignments": [
                        {"comment_id": "c1", "label_index": 0},
                        {"comment_id": "c2", "label_index": 0},
                    ],
                }
            ),
            ["c1", "c2"],
        )


def test_parse_split_output_rejects_missing_comment():
    with pytest.raises(ValueError, match="comment"):
        parse_split_output(
            json.dumps(
                {
                    "labels": [
                        {"name": "A", "definition": "a"},
                        {"name": "B", "definition": "b"},
                    ],
                    "assignments": [{"comment_id": "c1", "label_index": 0}],
                }
            ),
            ["c1", "c2"],
        )


def test_build_split_prompt_includes_source_and_comment_ids():
    comment = type(
        "C",
        (),
        {
            "id": "c1",
            "raw_text": "Too strong.",
            "context_text": "We demonstrate X.",
            "section": "Results",
        },
    )()
    prompt = build_split_prompt(
        source_name="Overclaiming",
        source_definition="A claim is stronger than the evidence.",
        comments=[comment],
    )
    assert "Task: split these comments into more specific labels." in prompt
    assert "Overclaiming" in prompt
    assert "id=c1" in prompt
    assert "Too strong." in prompt


def _add_comment(
    comment_id: str,
    text: str,
    *,
    label_id: str | None = None,
    coding_status: str = "accepted",
    status: str = "active",
):
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id=comment_id,
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text=text,
                status=status,
            )
        )
        if label_id:
            session.add(
                Coding(
                    id=f"k-{comment_id}",
                    comment_id=comment_id,
                    label_id=label_id,
                    coder_type="human",
                    status=coding_status,
                    rationale=None,
                )
            )
        session.commit()


def test_apply_split_keeps_source_and_accepts_children(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)
    created = apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "Evidence", "definition": "Too strong for the data."},
                {"name": "Wording", "definition": "A hedge would be enough."},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    assert [row.name for row in created] == ["Evidence", "Wording"]
    with get_session() as session:
        parent = session.get(Label, source.id)
        assert parent.status == "active"
        kids = active_children(session.find(Label), source.id)
        assert [row.name for row in kids] == ["Evidence", "Wording"]
        assert [row.position for row in kids] == [0, 1]
        accepted = session.first(Coding, comment_id="c1", status="accepted")
        assert accepted.label_id == created[0].id
        assert accepted.coder_type == "ai"
        assert session.find(Coding, comment_id="c1", status="proposed") == []


def test_apply_split_moves_leftover_labels_onto_ungrouped(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)
    _add_comment(
        "c-gone",
        "Old remark.",
        label_id=source.id,
        status="pending_disappeared",
    )
    created = apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "Evidence", "definition": "Too strong for the data."},
                {"name": "Wording", "definition": "A hedge would be enough."},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    with get_session() as session:
        kids = active_children(session.find(Label), source.id)
        ungrouped = next(row for row in kids if row.name == "ungrouped")
        gone = session.first(Coding, comment_id="c-gone", status="accepted")
        assert gone is not None
        assert gone.label_id == ungrouped.id
        assert not active_children(session.find(Label), ungrouped.id)
        assert session.first(Coding, comment_id="c1", status="accepted").label_id == created[0].id
        assert session.find(Coding, comment_id="c1", status="proposed") == []


def test_apply_split_undo_restores_leftover_label_to_source(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)
    _add_comment(
        "c-gone",
        "Old remark.",
        label_id=source.id,
        status="pending_disappeared",
    )
    apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "Evidence", "definition": "a"},
                {"name": "Wording", "definition": "b"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    undo()
    with get_session() as session:
        gone = session.first(Coding, comment_id="c-gone", status="accepted")
        assert gone is not None
        assert gone.label_id == source.id
        assert not active_children(session.find(Label), source.id)


def test_run_leaf_split_returns_privacy_warning_for_non_mock(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)

    class _Provider:
        name = "openai"

        def generate(self, prompt: str) -> str:
            return json.dumps(
                {
                    "labels": [
                        {"name": "Evidence", "definition": "Too strong for the data."},
                        {"name": "Wording", "definition": "A hedge would be enough."},
                    ],
                    "assignments": [
                        {"comment_id": "c1", "label_index": 0},
                        {"comment_id": "c2", "label_index": 1},
                    ],
                }
            )

    summary = run_leaf_split(source.id, provider=_Provider())
    assert summary.privacy_warning is not None
    assert "openai" in summary.privacy_warning


def test_apply_split_header_creates_roots(db):
    _add_comment("c1", "Too strong.")
    _add_comment("c2", "Hedge this.")
    created = apply_split(
        source_id=None,
        plan=SplitPlan(
            labels=[
                {"name": "Evidence", "definition": "a"},
                {"name": "Wording", "definition": "b"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    assert {row.parent_id for row in created} == {None}
    names = {i.name for i in list_active_labels()}
    assert names == {"Evidence", "Wording"}
    with get_session() as session:
        assert is_labeled(session, "c1")
        assert is_labeled(session, "c2")
        assert session.first(Coding, comment_id="c1", status="accepted") is not None
        assert session.find(Coding, comment_id="c1", status="proposed") == []


def test_apply_split_refuses_type_with_children(db):
    parent = create_label(name="Parent", definition="")
    create_label(name="Child", definition="", parent_id=parent.id)
    with pytest.raises(BadInput, match="children"):
        apply_split(
            source_id=parent.id,
            plan=SplitPlan(
                labels=[
                    {"name": "A", "definition": "a"},
                    {"name": "B", "definition": "b"},
                ],
                assignments=[
                    {"comment_id": "c1", "label_index": 0},
                    {"comment_id": "c2", "label_index": 1},
                ],
            ),
        )


def test_keep_source_split_undo_restores_accepted_labels(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)
    created = apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "Evidence", "definition": "a"},
                {"name": "Wording", "definition": "b"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    history = list_history()
    assert history["events"][0]["summary"] == "Split Overclaiming into 2 labels"
    undo()
    with get_session() as session:
        assert session.get(Label, source.id).status == "active"
        assert session.get(Label, created[0].id).status == "inactive"
        assert session.first(Coding, comment_id="c1", status="accepted") is not None
        assert session.find(Coding, comment_id="c1", status="proposed") == []
    redo()
    with get_session() as session:
        assert session.get(Label, created[0].id).status == "active"
        child = session.first(Coding, comment_id="c1", status="accepted")
        assert child.label_id == created[0].id
        assert session.find(Coding, comment_id="c1", status="proposed") == []


def test_keep_source_split_is_invertible(db):
    source = create_label(name="Overclaiming", definition="x")
    _add_comment("c1", "a", label_id=source.id)
    _add_comment("c2", "b", label_id=source.id)
    apply_split(
        source_id=source.id,
        plan=SplitPlan(
            labels=[
                {"name": "A", "definition": "a"},
                {"name": "B", "definition": "b"},
            ],
            assignments=[
                {"comment_id": "c1", "label_index": 0},
                {"comment_id": "c2", "label_index": 1},
            ],
        ),
    )
    with get_session() as session:
        event = session.find(TaxonomyEvent, event_type="split")[-1]
        payload = json.loads(event.payload_json)
    assert payload["keep_source"] is True
    assert "created" in payload
    assert list_history()["can_undo"] is True


def test_run_leaf_split_uses_provider_json(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)
    provider = MockLLMProvider(
        json.dumps(
            {
                "labels": [
                    {"name": "Evidence", "definition": "Too strong for the data."},
                    {"name": "Wording", "definition": "A hedge would be enough."},
                ],
                "assignments": [
                    {"comment_id": "c1", "label_index": 0},
                    {"comment_id": "c2", "label_index": 1},
                ],
            }
        )
    )
    run_leaf_split(source.id, provider=provider)
    with get_session() as session:
        kids = active_children(session.find(Label), source.id)
        assert {row.name for row in kids} == {"Evidence", "Wording"}


def test_run_leaf_split_refuses_fewer_than_two_labels(db):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    with pytest.raises(BadInput, match="two"):
        run_leaf_split(source.id, provider=MockLLMProvider("{}"))


def test_run_header_split_refuses_existing_types(db):
    create_label(name="Already", definition="x")
    _add_comment("c1", "a")
    _add_comment("c2", "b")
    with pytest.raises(BadInput, match="taxonomy"):
        run_header_split(provider=MockLLMProvider("{}"))


def test_mock_provider_returns_split_json_for_split_prompt():
    prompt = f"{SPLIT_TASK}\n- id=c1\n- id=c2\n"
    text = MockLLMProvider().generate(prompt)
    plan = parse_split_output(text, ["c1", "c2"])
    assert len(plan.labels) == 2
    assert {row["comment_id"] for row in plan.assignments} == {"c1", "c2"}
