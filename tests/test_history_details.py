from reviewdistill.coding.split import SplitPlan
from reviewdistill.coding.validation import change_coding
from reviewdistill.db.models import ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.history import list_history
from reviewdistill.history_details import HistoryLookup, collect_ids, event_details
from reviewdistill.taxonomy.operations import apply_split, create_label, flatten_label, rename_label

EMPTY = HistoryLookup(comments={}, labels={}, coding_comments={})


def test_rename_uses_payload_names_not_ids():
    details = event_details(
        "rename",
        {
            "label_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "before": {"name": "Overly strong claim"},
            "after": {"name": "Overclaiming"},
        },
        EMPTY,
        summary="Rename Overly strong claim → Overclaiming",
    )
    assert details["explanation"] == "Renamed Overly strong claim to Overclaiming."
    assert details["comments"] == []
    assert details["quotes"] == []
    assert "aaaa" not in details["explanation"]


def test_add_names_the_new_type():
    details = event_details(
        "add",
        {"label_id": "t1", "name": "New label"},
        EMPTY,
        summary="Add New label",
    )
    assert details["explanation"] == "Added the label New label."
    assert details["comments"] == []
    assert details["quotes"] == []


def test_add_leaf_split_mentions_ungrouped_and_lists_reassigned_comment():
    lookup = HistoryLookup(
        comments={"c1": "too strong"},
        labels={},
        coding_comments={"k1": "c1"},
    )
    details = event_details(
        "add",
        {
            "label_id": "t-new",
            "name": "New label",
            "ungrouped_id": "t-u",
            "ungrouped_name": "ungrouped",
            "reassigned_codings": [
                {"id": "k1", "comment_id": "c1", "from_label_id": "t-parent"}
            ],
        },
        lookup,
        summary="Add New label",
    )
    assert details["explanation"] == (
        "Added the label New label. Existing label assignments on the parent were moved onto ungrouped."
    )
    assert details["comments"] == [{"text": "too strong", "label_name": "ungrouped"}]


def test_add_lists_reassigned_comment_from_payload_without_live_coding():
    lookup = HistoryLookup(
        comments={"c1": "too strong"},
        labels={},
        coding_comments={},
    )
    details = event_details(
        "add",
        {
            "label_id": "t-new",
            "name": "New label",
            "ungrouped_id": "t-u",
            "ungrouped_name": "ungrouped",
            "reassigned_codings": [
                {"id": "k1", "comment_id": "c1", "from_label_id": "t-parent"}
            ],
        },
        lookup,
        summary="Add New label",
    )
    assert details["comments"] == [{"text": "too strong", "label_name": "ungrouped"}]


def test_edit_quotes_definition_and_ignores_notes():
    lookup = HistoryLookup(comments={}, labels={"t1": "Overclaiming"}, coding_comments={})
    details = event_details(
        "edit",
        {
            "label_id": "t1",
            "before": {"definition": "old", "notes": None, "detection_guidance": None},
            "after": {
                "definition": "A claim is stronger than the evidence supports.",
                "notes": "Watch epistemic verbs.",
                "detection_guidance": None,
            },
        },
        lookup,
        summary="Edit definition",
    )
    assert details["explanation"] == "Edited the definition of Overclaiming."
    assert details["comments"] == []
    assert details["quotes"] == [
        {"heading": "Definition", "body": "A claim is stronger than the evidence supports."},
    ]


def test_edit_quotes_changed_detection_guidance():
    lookup = HistoryLookup(comments={}, labels={"t1": "Overclaiming"}, coding_comments={})
    details = event_details(
        "edit",
        {
            "label_id": "t1",
            "before": {"definition": "old", "notes": None, "detection_guidance": None},
            "after": {
                "definition": "old",
                "notes": None,
                "detection_guidance": "demonstrate, prove",
            },
        },
        lookup,
        summary="Edit definition",
    )
    assert details["quotes"] == [
        {"heading": "Definition", "body": "old"},
        {"heading": "Detection guidance", "body": "demonstrate, prove"},
    ]


def test_move_under_parent_and_to_root():
    lookup = HistoryLookup(comments={}, labels={"parent": "Claims"}, coding_comments={})
    nested = event_details(
        "move",
        {
            "label_id": "child",
            "name": "Overclaiming",
            "from_parent_id": None,
            "to_parent_id": "parent",
            "from_position": 0,
            "to_position": 0,
        },
        lookup,
        summary="Move Overclaiming",
    )
    assert nested["explanation"] == "Moved Overclaiming under Claims."
    root = event_details(
        "move",
        {
            "label_id": "child",
            "name": "Overclaiming",
            "from_parent_id": "parent",
            "to_parent_id": None,
            "from_position": 0,
            "to_position": 0,
        },
        lookup,
        summary="Move Overclaiming",
    )
    assert root["explanation"] == "Moved Overclaiming to the top of the taxonomy."


def test_flatten_names_descendants_and_lists_reassigned_comment():
    lookup = HistoryLookup(
        comments={"c-flat": "too strong"},
        labels={"parent": "Parent", "child": "Child"},
        coding_comments={"coding-flat": "c-flat"},
    )
    details = event_details(
        "flatten",
        {
            "label_id": "parent",
            "name": "Parent",
            "descendant_ids": ["child"],
            "reassigned_codings": [{"id": "coding-flat", "from_label_id": "child"}],
        },
        lookup,
        summary="Flatten Parent",
    )
    assert details["explanation"] == (
        "Flattened Parent. These descendant labels were retired, and their comments were assigned to Parent: Child."
    )
    assert details["comments"] == [{"text": "too strong", "label_name": "Parent"}]


def test_remove_names_subtree_and_lists_unlabeled_comment():
    lookup = HistoryLookup(
        comments={"c1": "too strong"},
        labels={},
        coding_comments={},
    )
    details = event_details(
        "remove",
        {
            "label_id": "root",
            "name": "Parent",
            "types": [
                {"id": "root", "name": "Parent"},
                {"id": "child", "name": "Child"},
            ],
            "deleted_codings": [{"id": "k1", "comment_id": "c1", "label_id": "child"}],
        },
        lookup,
        summary="Remove Parent",
    )
    assert details["explanation"] == (
        "Removed Parent and its subtree (Child). Labeled comments on those labels returned to Unlabeled."
    )
    assert details["comments"] == [{"text": "too strong", "label_name": None}]


def test_remove_leaf_omits_subtree_parenthetical():
    details = event_details(
        "remove",
        {"label_id": "leaf", "name": "Overclaiming", "types": [{"id": "leaf", "name": "Overclaiming"}]},
        EMPTY,
        summary="Remove Overclaiming",
    )
    assert details["explanation"] == (
        "Removed Overclaiming. Labeled comments on those labels returned to Unlabeled."
    )


def test_deactivate_lists_unlabeled_comment():
    lookup = HistoryLookup(comments={"c-deact": "Too strong."}, labels={}, coding_comments={})
    details = event_details(
        "deactivate",
        {
            "label_id": "t1",
            "name": "Overclaiming",
            "deleted_codings": [{"id": "k1", "comment_id": "c-deact", "label_id": "t1"}],
        },
        lookup,
        summary="Deactivate Overclaiming",
    )
    assert details["explanation"] == (
        "Deactivated Overclaiming. Its children became siblings, and labeled comments on this label returned to Unlabeled."
    )
    assert details["comments"] == [{"text": "Too strong.", "label_name": None}]


def test_merge_names_sources_and_target():
    lookup = HistoryLookup(
        comments={"c-a": "observation from A"},
        labels={"a": "Type A", "b": "Type B", "target": "Overclaiming"},
        coding_comments={"k-a": "c-a"},
    )
    details = event_details(
        "merge",
        {
            "source_ids": ["a", "b"],
            "target_id": "target",
            "reassigned_codings": [{"id": "k-a", "from_label_id": "a"}],
        },
        lookup,
        summary="Merge labels",
    )
    assert details["explanation"] == "Merged Type A, Type B into Overclaiming."
    assert details["comments"] == [{"text": "observation from A", "label_name": "Overclaiming"}]


def test_legacy_split_still_says_unlabeled():
    lookup = HistoryLookup(
        comments={"c1": "too strong"},
        labels={"src": "Overclaiming", "left": "Evidence", "right": "Wording"},
        coding_comments={},
    )
    details = event_details(
        "split",
        {
            "source_id": "src",
            "created_ids": ["left", "right"],
            "deleted_codings": [{"id": "k1", "comment_id": "c1", "label_id": "src"}],
        },
        lookup,
        summary="Split label",
    )
    assert details["explanation"] == (
        "Split Overclaiming into Evidence and Wording. "
        "Labeled comments on Overclaiming returned to Unlabeled."
    )
    assert details["comments"] == [{"text": "too strong", "label_name": None}]


def test_keep_source_split_captions_labeled_child():
    lookup = HistoryLookup(
        comments={"c1": "too strong", "c2": "hedge this"},
        labels={"src": "Overclaiming", "a": "Evidence", "b": "Wording"},
        coding_comments={},
    )
    details = event_details(
        "split",
        {
            "keep_source": True,
            "source_id": "src",
            "created_ids": ["a", "b"],
            "created": [
                {"comment_id": "c1", "label_id": "a"},
                {"comment_id": "c2", "label_id": "b"},
            ],
            "deleted_codings": [],
            "replaced": [],
        },
        lookup,
        summary="Split Overclaiming into 2 labels",
    )
    assert details["explanation"] == (
        "Split Overclaiming into Evidence and Wording. "
        "Comments were labeled onto those labels."
    )
    assert details["comments"] == [
        {"text": "too strong", "label_name": "Evidence"},
        {"text": "hedge this", "label_name": "Wording"},
    ]


def test_header_split_details_have_no_source():
    lookup = HistoryLookup(
        comments={"c1": "too strong", "c2": "hedge this"},
        labels={"a": "Evidence", "b": "Wording"},
        coding_comments={},
    )
    details = event_details(
        "split",
        {
            "keep_source": True,
            "source_id": None,
            "created_ids": ["a", "b"],
            "created": [
                {"comment_id": "c1", "label_id": "a"},
                {"comment_id": "c2", "label_id": "b"},
            ],
        },
        lookup,
        summary="Split unlabeled comments into 2 labels",
    )
    assert details["explanation"] == (
        "Split unlabeled comments into Evidence and Wording. "
        "Comments were labeled onto those labels."
    )


def test_propose_lists_every_created_comment():
    lookup = HistoryLookup(
        comments={"c1": "First.", "c2": "Second."},
        labels={},
        coding_comments={},
    )
    details = event_details(
        "propose",
        {
            "created": [
                {"id": "k1", "comment_id": "c1", "proposed_label_name": "Unclear thesis"},
                {"id": "k2", "comment_id": "c2", "proposed_label_name": "Unclear thesis"},
            ],
            "replaced": [],
        },
        lookup,
        summary="Label with AI (2)",
    )
    assert details["explanation"] == "Labeled 2 comments with AI."
    assert details["comments"] == [
        {"text": "First.", "label_name": "Unclear thesis"},
        {"text": "Second.", "label_name": "Unclear thesis"},
    ]


def test_propose_skips_missing_comments():
    lookup = HistoryLookup(comments={"c1": "First."}, labels={}, coding_comments={})
    details = event_details(
        "propose",
        {
            "created": [
                {"comment_id": "c1", "proposed_label_name": "Unclear thesis"},
                {"comment_id": "gone", "proposed_label_name": "Unclear thesis"},
            ]
        },
        lookup,
        summary="Label with AI (2)",
    )
    assert details["comments"] == [{"text": "First.", "label_name": "Unclear thesis"}]


def test_accept_shows_comment_and_type():
    lookup = HistoryLookup(
        comments={"c1": "The claim is stronger than the evidence supports."},
        labels={"t1": "Overclaiming"},
        coding_comments={},
    )
    details = event_details(
        "accept",
        {"comment_id": "c1", "label_id": "t1", "coding_id": "k1"},
        lookup,
        summary="Accept suggested label assignment",
    )
    assert details["explanation"] == "Accepted the label Overclaiming for this comment."
    assert details["comments"] == [
        {"text": "The claim is stronger than the evidence supports.", "label_name": "Overclaiming"}
    ]


def test_change_from_previous_type():
    lookup = HistoryLookup(
        comments={"c1": "The claim is stronger than the evidence supports."},
        labels={"old": "Unsupported claim", "new": "Overclaiming"},
        coding_comments={},
    )
    details = event_details(
        "change",
        {
            "comment_id": "c1",
            "coding": {"label_id": "new"},
            "retired_accepted": [{"label_id": "old"}],
        },
        lookup,
        summary="Change label assignment",
    )
    assert details["explanation"] == "Changed the label from Unsupported claim to Overclaiming."
    assert details["comments"][0]["label_name"] == "Overclaiming"
    assert details["comments"][0]["text"] == "The claim is stronger than the evidence supports."


def test_change_without_previous_type():
    lookup = HistoryLookup(
        comments={"c1": "The claim is stronger than the evidence supports."},
        labels={"new": "Overclaiming"},
        coding_comments={},
    )
    details = event_details(
        "change",
        {"comment_id": "c1", "coding": {"label_id": "new"}, "retired_accepted": []},
        lookup,
        summary="Change label assignment",
    )
    assert details["explanation"] == "Assigned this comment to Overclaiming."


def test_accept_missing_comment_uses_placeholder():
    details = event_details(
        "accept",
        {"comment_id": "gone", "label_id": None},
        EMPTY,
        summary="Accept suggested label assignment",
    )
    assert details["comments"] == [
        {"text": "Comment is no longer available", "label_name": "a label that is no longer available"}
    ]


def test_verify_shows_comment_without_type():
    lookup = HistoryLookup(comments={"c1": "Keep me."}, labels={}, coding_comments={})
    verified = event_details("verify", {"comment_id": "c1"}, lookup, summary="Verify comment")
    assert verified["explanation"] == "Verified this comment."
    assert verified["comments"] == [{"text": "Keep me.", "label_name": None}]
    unverified = event_details("unverify", {"comment_id": "c1"}, lookup, summary="Unverify comment")
    assert unverified["explanation"] == "Unverified this comment."
    assert unverified["comments"] == [{"text": "Keep me.", "label_name": None}]


def test_delete_shows_dumped_comment_without_type():
    lookup = HistoryLookup(comments={}, labels={}, coding_comments={})
    details = event_details(
        "delete",
        {
            "comment_id": "c1",
            "comment": {"id": "c1", "raw_text": "Bad extract."},
        },
        lookup,
        summary="Delete comment",
    )
    assert details["explanation"] == "Deleted this comment."
    assert details["comments"] == [{"text": "Bad extract.", "label_name": None}]


def _add_comment(comment_id: str, text: str) -> None:
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
                status="active",
            )
        )
        session.commit()


def test_collect_ids_reads_nested_dumps():
    comments, labels, codings = collect_ids(
        {
            "comment_id": "c1",
            "label_id": "t1",
            "created": [{"comment_id": "c2", "label_id": "t2"}],
            "reassigned_codings": [
                {"id": "k1", "comment_id": "c9", "from_label_id": "t3"}
            ],
        }
    )
    assert comments == {"c1", "c2", "c9"}
    assert labels == {"t1", "t2", "t3"}
    assert codings == {"k1"}


def test_flatten_history_comments_survive_later_split(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
    _add_comment("c1", "Too strong.")
    _add_comment("c2", "Hedge this.")
    change_coding("c1", label_id=child.id)
    change_coding("c2", label_id=child.id)
    flatten_label(parent.id)
    apply_split(
        source_id=parent.id,
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
    event = next(item for item in list_history()["events"] if item["event_type"] == "flatten")
    texts = {row["text"] for row in event["details"]["comments"]}
    assert "Too strong." in texts
    assert "Hedge this." in texts


def test_list_history_change_includes_comment_text(db):
    label = create_label(name="Overclaiming", definition="")
    _add_comment("c-change", "The claim is stronger than the evidence supports.")
    change_coding("c-change", label_id=label.id)
    event = next(item for item in list_history()["events"] if item["event_type"] == "change")
    assert event["details"]["explanation"] == "Assigned this comment to Overclaiming."
    assert event["details"]["comments"][0]["text"] == "The claim is stronger than the evidence supports."
    assert isinstance(event["payload"], dict)


def test_list_history_rename_keeps_payload_names(db):
    label = create_label(name="Overly strong claim", definition="")
    rename_label(label.id, name="Overclaiming")
    event = next(item for item in list_history()["events"] if item["event_type"] == "rename")
    assert event["details"]["explanation"] == "Renamed Overly strong claim to Overclaiming."


def test_broken_handler_does_not_fail_list(db, monkeypatch):
    from reviewdistill import history_details as module

    create_label(name="Overclaiming", definition="")

    def boom(*_args, **_kwargs):
        raise RuntimeError("nope")

    monkeypatch.setitem(module.HANDLERS, "add", boom)
    body = list_history()
    add_event = next(item for item in body["events"] if item["event_type"] == "add")
    assert add_event["details"] == {
        "explanation": add_event["summary"],
        "comments": [],
        "quotes": [],
    }


def test_recycle_lists_assigned_comments():
    lookup = HistoryLookup(
        comments={"c1": "too strong", "c2": "hedge this"},
        labels={"u": "ungrouped"},
        coding_comments={},
    )
    details = event_details(
        "recycle",
        {
            "label_id": "u",
            "name": "ungrouped",
            "created": [
                {"comment_id": "c1", "label_id": "u"},
                {"comment_id": "c2", "label_id": "u"},
            ],
        },
        lookup,
        summary="Group unlabeled comments onto ungrouped",
    )
    assert details["explanation"] == (
        "Added the label ungrouped and assigned 2 unlabeled comments to it."
    )
    assert details["comments"] == [
        {"text": "too strong", "label_name": "ungrouped"},
        {"text": "hedge this", "label_name": "ungrouped"},
    ]
    assert details["quotes"] == []
