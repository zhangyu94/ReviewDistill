import json

import pytest

from reviewdistill.db.models import (
    CODING_ACCEPTED,
    ISSUE_INACTIVE,
    Coding,
    IssueType,
    ProofreadingComment,
    TaxonomyEvent,
)
from reviewdistill.db.session import get_session
from reviewdistill.coding.split import SplitPlan
from reviewdistill.errors import BadInput, NotFound
from reviewdistill.taxonomy.operations import (
    apply_split,
    create_empty_issue_type,
    create_issue_type,
    deactivate_issue_type,
    flatten_issue_type,
    list_active_issue_types,
    merge_issue_types,
    move_issue_type,
    remove_issue_type,
    rename_issue_type,
)


def test_create_empty_root(db):
    issue = create_empty_issue_type(parent_id=None)
    assert issue.name == "New type"
    assert issue.parent_id is None
    assert issue.definition == ""
    assert [row.name for row in list_active_issue_types()] == ["New type"]


def test_first_child_adds_ungrouped_and_moves_parent_labels(db):
    parent = create_issue_type(name="Parent", definition="")
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong", fingerprint="fp",
            status="active", quality="unreviewed",
        ))
        session.add(Coding(
            id="k1", comment_id="c1", issue_type_id=parent.id, coder_type="human",
            status=CODING_ACCEPTED,
        ))
        session.commit()
    created = create_empty_issue_type(parent_id=parent.id)
    kids = [row for row in list_active_issue_types() if row.parent_id == parent.id]
    kids.sort(key=lambda row: row.position)
    assert [row.name for row in kids] == ["New type", "ungrouped"]
    assert created.id == kids[0].id
    ungrouped = kids[1]
    with get_session() as session:
        assert session.get(Coding, "k1").issue_type_id == ungrouped.id
        events = session.find(TaxonomyEvent)
        adds = [row for row in events if row.event_type == "add"]
        assert len(adds) == 2
        payload = next(
            json.loads(row.payload_json) for row in adds if "ungrouped_id" in json.loads(row.payload_json)
        )
        assert payload["issue_type_id"] == created.id
        assert payload["ungrouped_id"] == ungrouped.id


def test_create_empty_child_appends(db):
    parent = create_issue_type(name="Parent", definition="")
    create_empty_issue_type(parent_id=parent.id)
    second = create_empty_issue_type(parent_id=parent.id)
    assert second.name == "New type (2)"
    assert second.parent_id == parent.id
    kids = [row for row in list_active_issue_types() if row.parent_id == parent.id]
    names = [row.name for row in sorted(kids, key=lambda row: row.position)]
    assert names == ["New type", "ungrouped", "New type (2)"]
    assert second.position == 2


def test_create_empty_uniquifies_new_type_name(db):
    first = create_empty_issue_type(parent_id=None)
    second = create_empty_issue_type(parent_id=None)
    third = create_empty_issue_type(parent_id=None)
    assert first.name == "New type"
    assert second.name == "New type (2)"
    assert third.name == "New type (3)"


def test_rename_to_taken_name_gets_suffix(db):
    create_issue_type(name="Overclaiming", definition="")
    other = create_issue_type(name="Other", definition="")
    renamed = rename_issue_type(other.id, name="Overclaiming")
    assert renamed.name == "Overclaiming (2)"
    same = rename_issue_type(renamed.id, name="Overclaiming (2)")
    assert same.name == "Overclaiming (2)"


def test_merge_refuses_descendant_target(db):
    parent = create_issue_type(name="Parent", definition="")
    child = create_issue_type(name="Child", definition="", parent_id=parent.id)
    with pytest.raises(BadInput):
        merge_issue_types(source_ids=[parent.id], target_id=child.id)
    with get_session() as session:
        assert session.get(IssueType, parent.id).status == "active"
        assert session.get(IssueType, child.id).parent_id == parent.id


def test_merge_moves_source_children_to_target(db):
    target = create_issue_type(name="Target", definition="t")
    source = create_issue_type(name="Source", definition="s")
    kid = create_issue_type(name="Kid", definition="k", parent_id=source.id)
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    with get_session() as session:
        kid_row = session.get(IssueType, kid.id)
        source_row = session.get(IssueType, source.id)
    assert kid_row.parent_id == target.id
    assert source_row.status == "inactive"


def test_flatten_reassigns_descendant_comments(db):
    parent = create_issue_type(name="Parent", definition="")
    child = create_issue_type(name="Child", definition="", parent_id=parent.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong", fingerprint="fp",
            status="active", quality="unreviewed",
        ))
        session.add(Coding(
            id="k1", comment_id="c1", issue_type_id=child.id, coder_type="human",
            status=CODING_ACCEPTED,
        ))
        session.commit()
    flatten_issue_type(parent.id)
    with get_session() as session:
        child_row = session.get(IssueType, child.id)
        coding = session.get(Coding, "k1")
        assert child_row.status == ISSUE_INACTIVE
        assert coding.issue_type_id == parent.id


def test_flatten_leaf_is_bad_input(db):
    leaf = create_issue_type(name="Leaf", definition="")
    with pytest.raises(BadInput):
        flatten_issue_type(leaf.id)


def test_remove_deletes_subtree_and_unlabels(db):
    root = create_issue_type(name="Root", definition="")
    child = create_issue_type(name="Child", definition="", parent_id=root.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong", fingerprint="fp",
            status="active", quality="unreviewed",
        ))
        session.add(Coding(
            id="k1", comment_id="c1", issue_type_id=child.id, coder_type="human",
            status=CODING_ACCEPTED,
        ))
        session.commit()
    remove_issue_type(root.id)
    with get_session() as session:
        assert session.get(IssueType, root.id) is None
        assert session.get(IssueType, child.id) is None
        assert session.find(Coding, comment_id="c1") == []


def test_deactivate_reparents_children(db):
    parent = create_issue_type(name="Parent", definition="")
    child = create_issue_type(name="Child", definition="", parent_id=parent.id)
    deactivate_issue_type(parent.id)
    with get_session() as session:
        child_row = session.get(IssueType, child.id)
        parent_row = session.get(IssueType, parent.id)
        assert parent_row.status == ISSUE_INACTIVE
        assert child_row.status == "active"
        assert child_row.parent_id is None


def test_split_refuses_type_with_children(db):
    parent = create_issue_type(name="Parent", definition="")
    create_issue_type(name="Child", definition="", parent_id=parent.id)
    with pytest.raises(BadInput):
        apply_split(
            source_id=parent.id,
            plan=SplitPlan(
                types=[
                    {"name": "Left", "definition": "l"},
                    {"name": "Right", "definition": "r"},
                ],
                assignments=[
                    {"comment_id": "c1", "type_index": 0},
                    {"comment_id": "c2", "type_index": 1},
                ],
            ),
        )
    with get_session() as session:
        assert session.get(IssueType, parent.id).status == "active"


def test_flatten_then_remove_leaves_store_loadable(db):
    parent = create_issue_type(name="Parent", definition="")
    child = create_issue_type(name="Child", definition="", parent_id=parent.id)
    flatten_issue_type(parent.id)
    remove_issue_type(parent.id)
    with get_session() as session:
        assert session.get(IssueType, parent.id) is None
        assert session.get(IssueType, child.id) is None


def _active_names(parent_id):
    with get_session() as session:
        rows = [
            row
            for row in session.find(IssueType)
            if row.status == "active" and row.parent_id == parent_id
        ]
        return [row.name for row in sorted(rows, key=lambda row: row.position)]


def test_remove_middle_sibling_then_create_appends_last(db):
    create_issue_type(name="Alpha", definition="")
    middle = create_issue_type(name="Beta", definition="")
    create_issue_type(name="Style", definition="")
    remove_issue_type(middle.id)
    created = create_empty_issue_type(parent_id=None)
    assert _active_names(None) == ["Alpha", "Style", "New type"]
    with get_session() as session:
        positions = sorted(
            row.position
            for row in session.find(IssueType)
            if row.status == "active" and row.parent_id is None
        )
        assert positions == [0, 1, 2]
        assert session.get(IssueType, created.id).position == 2


def test_merge_compacts_source_siblings(db):
    create_issue_type(name="Alpha", definition="")
    source = create_issue_type(name="Beta", definition="")
    create_issue_type(name="Style", definition="")
    target = create_issue_type(name="Target", definition="")
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    created = create_empty_issue_type(parent_id=None)
    assert _active_names(None)[-1] == "New type"
    with get_session() as session:
        positions = sorted(
            row.position
            for row in session.find(IssueType)
            if row.status == "active" and row.parent_id is None
        )
        assert positions == list(range(len(positions)))
        assert session.get(IssueType, created.id).position == positions[-1]


def test_inactive_type_mutations_are_not_found(db):
    issue = create_issue_type(name="Leaf", definition="")
    deactivate_issue_type(issue.id)
    with pytest.raises(NotFound):
        move_issue_type(issue.id, parent_id=None, position=0)
    with pytest.raises(NotFound):
        flatten_issue_type(issue.id)
    with pytest.raises(NotFound):
        apply_split(
            source_id=issue.id,
            plan=SplitPlan(
                types=[
                    {"name": "Left", "definition": "l"},
                    {"name": "Right", "definition": "r"},
                ],
                assignments=[
                    {"comment_id": "c1", "type_index": 0},
                    {"comment_id": "c2", "type_index": 1},
                ],
            ),
        )
    with pytest.raises(NotFound):
        remove_issue_type(issue.id)


def test_merge_inactive_types_are_not_found(db):
    source = create_issue_type(name="Source", definition="")
    create_issue_type(name="Kid", definition="", parent_id=source.id)
    target = create_issue_type(name="Target", definition="")
    deactivate_issue_type(target.id)
    with pytest.raises(NotFound):
        merge_issue_types(source_ids=[source.id], target_id=target.id)
    with get_session() as session:
        child = session.first(IssueType, name="Kid")
        assert child.parent_id == source.id
        assert child.status == "active"
        assert session.get(IssueType, source.id).status == "active"
    other = create_issue_type(name="Leaf", definition="")
    deactivate_issue_type(other.id)
    with pytest.raises(NotFound):
        merge_issue_types(source_ids=[other.id], target_id=source.id)


def test_move_under_labeled_leaf_parks_labels_on_ungrouped(db):
    parent = create_issue_type(name="Parent", definition="")
    child = create_issue_type(name="Child", definition="")
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c1", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="too strong", fingerprint="fp",
            status="active", quality="unreviewed",
        ))
        session.add(Coding(
            id="k1", comment_id="c1", issue_type_id=parent.id, coder_type="human",
            status=CODING_ACCEPTED,
        ))
        session.commit()
    move_issue_type(child.id, parent_id=parent.id, position=0)
    kids = [row for row in list_active_issue_types() if row.parent_id == parent.id]
    kids.sort(key=lambda row: row.position)
    ungrouped = next(row for row in kids if row.name == "ungrouped")
    assert {row.name for row in kids} == {"Child", "ungrouped"}
    with get_session() as session:
        assert session.get(Coding, "k1").issue_type_id == ungrouped.id
        moves = [row for row in session.find(TaxonomyEvent) if row.event_type == "move"]
        payload = json.loads(moves[-1].payload_json)
        assert payload["ungrouped_id"] == ungrouped.id


def test_merge_parent_into_labeled_leaf_parks_labels_on_ungrouped(db):
    target = create_issue_type(name="Target", definition="t")
    source = create_issue_type(name="Source", definition="s")
    kid = create_issue_type(name="Kid", definition="k", parent_id=source.id)
    with get_session() as session:
        session.add(ProofreadingComment(
            id="c-tgt", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=1, raw_text="on target", fingerprint="fp-tgt",
            status="active", quality="unreviewed",
        ))
        session.add(Coding(
            id="k-tgt", comment_id="c-tgt", issue_type_id=target.id, coder_type="human",
            status=CODING_ACCEPTED,
        ))
        session.add(ProofreadingComment(
            id="c-src", project_id="p", source_type="latex_command", source_command="myremark",
            file_path="main.tex", line_number=2, raw_text="on source", fingerprint="fp-src",
            status="active", quality="unreviewed",
        ))
        session.add(Coding(
            id="k-src", comment_id="c-src", issue_type_id=source.id, coder_type="human",
            status=CODING_ACCEPTED,
        ))
        session.commit()
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    kids = [row for row in list_active_issue_types() if row.parent_id == target.id]
    ungrouped = next(row for row in kids if row.name == "ungrouped")
    with get_session() as session:
        assert session.get(IssueType, kid.id).parent_id == target.id
        assert session.get(Coding, "k-tgt").issue_type_id == ungrouped.id
        assert session.get(Coding, "k-src").issue_type_id == ungrouped.id
        merges = [row for row in session.find(TaxonomyEvent) if row.event_type == "merge"]
        payload = json.loads(merges[-1].payload_json)
        assert payload["ungrouped_id"] == ungrouped.id