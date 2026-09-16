import json

import pytest

from reviewdistill.db.models import (
    ASSIGNMENT_ACCEPTED,
    ASSIGNMENT_MODIFIED,
    ASSIGNMENT_PROPOSED,
    LABEL_INACTIVE,
    Assignment,
    Label,
    LabelExample,
    ProofreadingComment,
    TaxonomyEvent,
    is_labeled,
)
from reviewdistill.db.session import get_session
from reviewdistill.labeling.split import SplitPlan
from reviewdistill.errors import BadInput, NotFound
from reviewdistill.taxonomy.operations import (
    apply_split,
    create_empty_label,
    create_label,
    deactivate_label,
    flatten_label,
    list_active_labels,
    merge_labels,
    move_label,
    recycle_ungrouped,
    remove_label,
    rename_label,
)


def _working_comment(comment_id: str, text: str, *, status: str = "active", quality: str = "unreviewed"):
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
                quality=quality,
            )
        )
        session.commit()


def test_create_empty_root(db):
    label = create_empty_label(parent_id=None)
    assert label.name == "New label"
    assert label.parent_id is None
    assert label.definition == ""
    assert [row.name for row in list_active_labels()] == ["New label"]


def test_first_child_adds_ungrouped_and_moves_parent_labels(db):
    parent = create_label(name="Parent", definition="")
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong",
            status="active",
        ))
        session.add(Assignment(
            id="k1", comment_id="c1", label_id=parent.id, coder_type="human",
            status=ASSIGNMENT_ACCEPTED,
        ))
        session.commit()
    created = create_empty_label(parent_id=parent.id)
    kids = [row for row in list_active_labels() if row.parent_id == parent.id]
    kids.sort(key=lambda row: row.position)
    assert [row.name for row in kids] == ["New label", "ungrouped"]
    assert created.id == kids[0].id
    ungrouped = kids[1]
    with get_session() as session:
        assert session.get(Assignment, "k1").label_id == ungrouped.id
        events = session.find(TaxonomyEvent)
        adds = [row for row in events if row.event_type == "add"]
        assert len(adds) == 2
        payload = next(
            json.loads(row.payload_json) for row in adds if "ungrouped_id" in json.loads(row.payload_json)
        )
        assert payload["label_id"] == created.id
        assert payload["ungrouped_id"] == ungrouped.id


def test_create_empty_child_appends(db):
    parent = create_label(name="Parent", definition="")
    create_empty_label(parent_id=parent.id)
    second = create_empty_label(parent_id=parent.id)
    assert second.name == "New label (2)"
    assert second.parent_id == parent.id
    kids = [row for row in list_active_labels() if row.parent_id == parent.id]
    names = [row.name for row in sorted(kids, key=lambda row: row.position)]
    assert names == ["New label", "ungrouped", "New label (2)"]
    assert second.position == 2


def test_create_empty_uniquifies_new_label_name(db):
    first = create_empty_label(parent_id=None)
    second = create_empty_label(parent_id=None)
    third = create_empty_label(parent_id=None)
    assert first.name == "New label"
    assert second.name == "New label (2)"
    assert third.name == "New label (3)"


def test_rename_to_taken_name_gets_suffix(db):
    create_label(name="Overclaiming", definition="")
    other = create_label(name="Other", definition="")
    renamed = rename_label(other.id, name="Overclaiming")
    assert renamed.name == "Overclaiming (2)"
    same = rename_label(renamed.id, name="Overclaiming (2)")
    assert same.name == "Overclaiming (2)"


def test_merge_refuses_descendant_target(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    with pytest.raises(BadInput):
        merge_labels(source_ids=[parent.id], target_id=child.id)
    with get_session() as session:
        assert session.get(Label, parent.id).status == "active"
        assert session.get(Label, child.id).parent_id == parent.id


def test_merge_moves_source_children_to_target(db):
    target = create_label(name="Target", definition="t")
    source = create_label(name="Source", definition="s")
    kid = create_label(name="Kid", definition="k", parent_id=source.id)
    merge_labels(source_ids=[source.id], target_id=target.id)
    with get_session() as session:
        kid_row = session.get(Label, kid.id)
        source_row = session.get(Label, source.id)
    assert kid_row.parent_id == target.id
    assert source_row.status == "inactive"


def test_flatten_reassigns_descendant_comments(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong",
            status="active",
        ))
        session.add(Assignment(
            id="k1", comment_id="c1", label_id=child.id, coder_type="human",
            status=ASSIGNMENT_ACCEPTED,
        ))
        session.commit()
    flatten_label(parent.id)
    with get_session() as session:
        child_row = session.get(Label, child.id)
        coding = session.get(Assignment, "k1")
        assert child_row.status == LABEL_INACTIVE
        assert coding.label_id == parent.id


def test_flatten_leaf_is_bad_input(db):
    leaf = create_label(name="Leaf", definition="")
    with pytest.raises(BadInput):
        flatten_label(leaf.id)


def test_remove_deletes_subtree_and_unlabels(db):
    root = create_label(name="Root", definition="")
    child = create_label(name="Child", definition="", parent_id=root.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong",
            status="active",
        ))
        session.add(Assignment(
            id="k1", comment_id="c1", label_id=child.id, coder_type="human",
            status=ASSIGNMENT_ACCEPTED,
        ))
        session.commit()
    remove_label(root.id)
    with get_session() as session:
        assert session.get(Label, root.id) is None
        assert session.get(Label, child.id) is None
        assert session.find(Assignment, comment_id="c1") == []


def test_deactivate_reparents_children(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    deactivate_label(parent.id)
    with get_session() as session:
        child_row = session.get(Label, child.id)
        parent_row = session.get(Label, parent.id)
        assert parent_row.status == LABEL_INACTIVE
        assert child_row.status == "active"
        assert child_row.parent_id is None


def test_split_refuses_type_with_children(db):
    parent = create_label(name="Parent", definition="")
    create_label(name="Child", definition="", parent_id=parent.id)
    with pytest.raises(BadInput):
        apply_split(
            source_id=parent.id,
            plan=SplitPlan(
                labels=[
                    {"name": "Left", "definition": "l"},
                    {"name": "Right", "definition": "r"},
                ],
                assignments=[
                    {"comment_id": "c1", "label_index": 0},
                    {"comment_id": "c2", "label_index": 1},
                ],
            ),
        )
    with get_session() as session:
        assert session.get(Label, parent.id).status == "active"


def test_flatten_then_remove_leaves_store_loadable(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    flatten_label(parent.id)
    remove_label(parent.id)
    with get_session() as session:
        assert session.get(Label, parent.id) is None
        assert session.get(Label, child.id) is None


def _active_names(parent_id):
    with get_session() as session:
        rows = [
            row
            for row in session.find(Label)
            if row.status == "active" and row.parent_id == parent_id
        ]
        return [row.name for row in sorted(rows, key=lambda row: row.position)]


def test_remove_middle_sibling_then_create_appends_last(db):
    create_label(name="Alpha", definition="")
    middle = create_label(name="Beta", definition="")
    create_label(name="Style", definition="")
    remove_label(middle.id)
    created = create_empty_label(parent_id=None)
    assert _active_names(None) == ["Alpha", "Style", "New label"]
    with get_session() as session:
        positions = sorted(
            row.position
            for row in session.find(Label)
            if row.status == "active" and row.parent_id is None
        )
        assert positions == [0, 1, 2]
        assert session.get(Label, created.id).position == 2


def test_merge_compacts_source_siblings(db):
    create_label(name="Alpha", definition="")
    source = create_label(name="Beta", definition="")
    create_label(name="Style", definition="")
    target = create_label(name="Target", definition="")
    merge_labels(source_ids=[source.id], target_id=target.id)
    created = create_empty_label(parent_id=None)
    assert _active_names(None)[-1] == "New label"
    with get_session() as session:
        positions = sorted(
            row.position
            for row in session.find(Label)
            if row.status == "active" and row.parent_id is None
        )
        assert positions == list(range(len(positions)))
        assert session.get(Label, created.id).position == positions[-1]


def test_inactive_type_mutations_are_not_found(db):
    label = create_label(name="Leaf", definition="")
    deactivate_label(label.id)
    with pytest.raises(NotFound):
        move_label(label.id, parent_id=None, position=0)
    with pytest.raises(NotFound):
        flatten_label(label.id)
    with pytest.raises(NotFound):
        apply_split(
            source_id=label.id,
            plan=SplitPlan(
                labels=[
                    {"name": "Left", "definition": "l"},
                    {"name": "Right", "definition": "r"},
                ],
                assignments=[
                    {"comment_id": "c1", "label_index": 0},
                    {"comment_id": "c2", "label_index": 1},
                ],
            ),
        )
    with pytest.raises(NotFound):
        remove_label(label.id)


def test_merge_inactive_types_are_not_found(db):
    source = create_label(name="Source", definition="")
    create_label(name="Kid", definition="", parent_id=source.id)
    target = create_label(name="Target", definition="")
    deactivate_label(target.id)
    with pytest.raises(NotFound):
        merge_labels(source_ids=[source.id], target_id=target.id)
    with get_session() as session:
        child = session.first(Label, name="Kid")
        assert child.parent_id == source.id
        assert child.status == "active"
        assert session.get(Label, source.id).status == "active"
    other = create_label(name="Leaf", definition="")
    deactivate_label(other.id)
    with pytest.raises(NotFound):
        merge_labels(source_ids=[other.id], target_id=source.id)


def test_move_under_labeled_leaf_parks_labels_on_ungrouped(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="")
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong",
            status="active",
        ))
        session.add(Assignment(
            id="k1", comment_id="c1", label_id=parent.id, coder_type="human",
            status=ASSIGNMENT_ACCEPTED,
        ))
        session.commit()
    move_label(child.id, parent_id=parent.id, position=0)
    kids = [row for row in list_active_labels() if row.parent_id == parent.id]
    kids.sort(key=lambda row: row.position)
    ungrouped = next(row for row in kids if row.name == "ungrouped")
    assert {row.name for row in kids} == {"Child", "ungrouped"}
    with get_session() as session:
        assert session.get(Assignment, "k1").label_id == ungrouped.id
        moves = [row for row in session.find(TaxonomyEvent) if row.event_type == "move"]
        payload = json.loads(moves[-1].payload_json)
        assert payload["ungrouped_id"] == ungrouped.id


def test_merge_parent_into_labeled_leaf_parks_labels_on_ungrouped(db):
    target = create_label(name="Target", definition="t")
    source = create_label(name="Source", definition="s")
    kid = create_label(name="Kid", definition="k", parent_id=source.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c-tgt", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="on target",
            status="active",
        ))
        session.add(Assignment(
            id="k-tgt", comment_id="c-tgt", label_id=target.id, coder_type="human",
            status=ASSIGNMENT_ACCEPTED,
        ))
        session.add(ProofreadingComment(
            id="c-src", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=2, raw_text="on source",
            status="active",
        ))
        session.add(Assignment(
            id="k-src", comment_id="c-src", label_id=source.id, coder_type="human",
            status=ASSIGNMENT_ACCEPTED,
        ))
        session.commit()
    merge_labels(source_ids=[source.id], target_id=target.id)
    kids = [row for row in list_active_labels() if row.parent_id == target.id]
    ungrouped = next(row for row in kids if row.name == "ungrouped")
    with get_session() as session:
        assert session.get(Label, kid.id).parent_id == target.id
        assert session.get(Assignment, "k-tgt").label_id == ungrouped.id
        assert session.get(Assignment, "k-src").label_id == ungrouped.id
        merges = [row for row in session.find(TaxonomyEvent) if row.event_type == "merge"]
        payload = json.loads(merges[-1].payload_json)
        assert payload["ungrouped_id"] == ungrouped.id


def test_recycle_requires_existing_taxonomy(db):
    _working_comment("c1", "one")
    _working_comment("c2", "two")
    with pytest.raises(BadInput, match="until a taxonomy exists"):
        recycle_ungrouped()


def test_recycle_requires_two_unlabeled_working_comments(db):
    create_label(name="Existing", definition="")
    _working_comment("c1", "only one")
    with pytest.raises(BadInput, match="at least two unlabeled comments"):
        recycle_ungrouped()


def test_recycle_assigns_unlabeled_working_set_onto_ungrouped(db):
    create_label(name="Existing", definition="")
    _working_comment("c1", "too strong")
    _working_comment("c2", "hedge this")
    _working_comment("gone", "left", status="pending_disappeared", quality="unreviewed")
    with get_session() as session:
        session.add(
            Assignment(
                id="k-prop",
                comment_id="c1",
                label_id=None,
                coder_type="ai",
                status=ASSIGNMENT_PROPOSED,
                proposed_label_name="Maybe",
                proposed_label_definition="too strong",
            )
        )
        session.commit()
    created = recycle_ungrouped()
    assert created.name == "ungrouped"
    assert created.parent_id is None
    assert created.definition == ""
    with get_session() as session:
        assert is_labeled(session, "c1")
        assert is_labeled(session, "c2")
        assert not is_labeled(session, "gone")
        accepted = [
            row
            for row in session.find(Assignment, status=ASSIGNMENT_ACCEPTED)
            if row.label_id == created.id
        ]
        assert {row.comment_id for row in accepted} == {"c1", "c2"}
        assert all(row.coder_type == "human" for row in accepted)
        assert all(row.rationale == "Grouped unlabeled comments." for row in accepted)
        assert session.get(Assignment, "k-prop").status == ASSIGNMENT_MODIFIED
        examples = list(session.find(LabelExample, label_id=created.id))
        assert {row.source_comment_id for row in examples} == {"c1", "c2"}
        events = [row for row in session.find(TaxonomyEvent) if row.event_type == "recycle"]
        assert len(events) == 1
        payload = json.loads(events[0].payload_json)
        assert payload["label_id"] == created.id
        assert payload["name"] == "ungrouped"
        assert len(payload["created"]) == 2


def test_recycle_uniquifies_ungrouped_name(db):
    create_label(name="ungrouped", definition="")
    _working_comment("c1", "one")
    _working_comment("c2", "two")
    created = recycle_ungrouped()
    assert created.name == "ungrouped (2)"