from __future__ import annotations

from uuid import uuid4

from reviewdistill.db.models import (
    CODING_ACCEPTED,
    CODING_PROPOSED,
    ISSUE_ACTIVE,
    ISSUE_INACTIVE,
    Coding,
    IssueCounterexample,
    IssueExample,
    IssueType,
    ProofreadingComment,
    in_working_set,
    utcnow,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.errors import BadInput, NotFound
from reviewdistill.history import dump_row, record
from reviewdistill.taxonomy.tree import (
    active_children,
    compact_positions,
    descendant_ids,
    is_under,
    lift_children,
    next_unique_name,
    place_among_siblings,
)


def _require_active(session, issue_type_id: str) -> IssueType:
    issue = session.get(IssueType, issue_type_id)
    if issue is None or issue.status != ISSUE_ACTIVE:
        raise NotFound(f"Unknown issue type {issue_type_id}")
    return issue


def _log(session, event_type: str, payload: dict) -> None:
    record(session, event_type, payload)


def _retire_codings_for_types(
    session, type_ids: set[str], comment_ids: set[str] | None = None
) -> list[dict]:
    deleted = []
    labeled_comments = {
        coding.comment_id
        for type_id in type_ids
        for coding in session.find(Coding, issue_type_id=type_id)
        if coding.status == CODING_ACCEPTED
        and (comment_ids is None or coding.comment_id in comment_ids)
    }
    for comment_id in labeled_comments:
        for row in list(session.find(Coding, comment_id=comment_id)):
            deleted.append(dump_row(row))
            session.delete(row)
    for type_id in type_ids:
        for row in list(session.find(Coding, issue_type_id=type_id, status=CODING_PROPOSED)):
            deleted.append(dump_row(row))
            session.delete(row)
    return deleted


def add_issue_type(
    session,
    *,
    name: str,
    definition: str,
    parent_id: str | None = None,
    detection_guidance: str | None = None,
    log: bool = True,
) -> IssueType:
    if parent_id is not None:
        parent = session.get(IssueType, parent_id)
        if parent is None or parent.status != ISSUE_ACTIVE:
            raise NotFound(f"Unknown issue type {parent_id}")
    taken_names = [row.name for row in session.find(IssueType, status=ISSUE_ACTIVE)]
    name = next_unique_name(taken_names, name)
    siblings = [
        row
        for row in session.find(IssueType, status=ISSUE_ACTIVE)
        if row.parent_id == parent_id
    ]
    issue = IssueType(
        id=str(uuid4()),
        name=name,
        parent_id=parent_id,
        position=len(siblings),
        definition=definition,
        detection_guidance=detection_guidance,
        status=ISSUE_ACTIVE,
    )
    session.add(issue)
    if log:
        record(session, "add", {"issue_type_id": issue.id, "name": name})
    return issue


def create_issue_type(
    *,
    name: str,
    definition: str,
    parent_id: str | None = None,
    detection_guidance: str | None = None,
) -> IssueType:
    init_db()
    with get_session() as session:
        issue = add_issue_type(
            session,
            name=name,
            definition=definition,
            parent_id=parent_id,
            detection_guidance=detection_guidance,
        )
        session.commit()
        session.refresh(issue)
        return issue


def _reassign_own_labels(session, from_id: str, to_id: str) -> dict:
    reassigned_codings = []
    for coding in session.find(Coding, issue_type_id=from_id):
        reassigned_codings.append(
            {"id": coding.id, "comment_id": coding.comment_id, "from_issue_type_id": from_id}
        )
        coding.issue_type_id = to_id
        session.add(coding)
    reassigned_examples = []
    for example in list(session.find(IssueExample, issue_type_id=from_id)):
        reassigned_examples.append({"id": example.id, "from_issue_type_id": from_id})
        example.issue_type_id = to_id
        session.add(example)
    reassigned_counters = []
    for counter in session.find(IssueCounterexample, issue_type_id=from_id):
        reassigned_counters.append({"id": counter.id, "from_issue_type_id": from_id})
        counter.issue_type_id = to_id
        session.add(counter)
    return {
        "reassigned_codings": reassigned_codings,
        "reassigned_examples": reassigned_examples,
        "reassigned_counters": reassigned_counters,
    }


def _has_own_labels(session, issue_type_id: str) -> bool:
    if session.first(Coding, issue_type_id=issue_type_id) is not None:
        return True
    if session.first(IssueExample, issue_type_id=issue_type_id) is not None:
        return True
    return session.first(IssueCounterexample, issue_type_id=issue_type_id) is not None


def _park_own_labels_on_ungrouped(session, parent_id: str) -> dict:
    ungrouped = add_issue_type(
        session,
        name="ungrouped",
        definition="",
        parent_id=parent_id,
        log=False,
    )
    moved = _reassign_own_labels(session, parent_id, ungrouped.id)
    return {
        "ungrouped_id": ungrouped.id,
        "ungrouped_name": ungrouped.name,
        **moved,
    }


def add_child_issue_type(
    session,
    *,
    name: str,
    definition: str,
    parent_id: str | None,
    detection_guidance: str | None = None,
) -> IssueType:
    """Add a type. If parent is a leaf, park its labels on ungrouped (one add event)."""
    split_leaf = False
    if parent_id is not None:
        _require_active(session, parent_id)
        split_leaf = not active_children(session.find(IssueType), parent_id)
    issue = add_issue_type(
        session,
        name=name,
        definition=definition,
        parent_id=parent_id,
        detection_guidance=detection_guidance,
        log=not split_leaf,
    )
    if split_leaf:
        parked = _park_own_labels_on_ungrouped(session, parent_id)
        record(
            session,
            "add",
            {
                "issue_type_id": issue.id,
                "name": issue.name,
                **parked,
            },
        )
    return issue


def create_empty_issue_type(*, parent_id: str | None) -> IssueType:
    init_db()
    with get_session() as session:
        issue = add_child_issue_type(
            session,
            name="New type",
            definition="",
            parent_id=parent_id,
        )
        session.commit()
        session.refresh(issue)
        return issue


def list_active_issue_types() -> list[IssueType]:
    init_db()
    with get_session() as session:
        return sorted(
            session.find(IssueType, status=ISSUE_ACTIVE),
            key=lambda issue: (issue.parent_id or "", issue.position, issue.name),
        )


def get_issue_type(issue_type_id: str) -> IssueType | None:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None or issue.status != ISSUE_ACTIVE:
            return None
        return issue


def ensure_example(
    session,
    issue_type_id: str,
    text: str,
    source_comment_id: str | None = None,
) -> tuple[IssueExample, bool]:
    cleaned = " ".join(text.split())
    if source_comment_id:
        existing = session.first(
            IssueExample,
            issue_type_id=issue_type_id,
            source_comment_id=source_comment_id,
        )
        if existing is not None:
            return existing, False
    row = IssueExample(
        id=str(uuid4()),
        issue_type_id=issue_type_id,
        text=cleaned,
        source_comment_id=source_comment_id,
    )
    session.add(row)
    return row, True


def add_example(issue_type_id: str, text: str, source_comment_id: str | None = None) -> IssueExample:
    with get_session() as session:
        row, _created = ensure_example(session, issue_type_id, text, source_comment_id)
        session.commit()
        session.refresh(row)
        return row


def add_counterexample(
    issue_type_id: str, text: str, source_comment_id: str | None = None
) -> IssueCounterexample:
    cleaned = " ".join(text.split())
    with get_session() as session:
        row = IssueCounterexample(
            id=str(uuid4()),
            issue_type_id=issue_type_id,
            text=cleaned,
            source_comment_id=source_comment_id,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_examples(issue_type_id: str) -> list[IssueExample]:
    with get_session() as session:
        rows = session.find(IssueExample, issue_type_id=issue_type_id)
        return [
            row
            for row in rows
            if _source_in_working_set(session, row.source_comment_id)
            and _example_matches_current_label(session, row)
        ]


def list_counterexamples(issue_type_id: str) -> list[IssueCounterexample]:
    with get_session() as session:
        rows = session.find(IssueCounterexample, issue_type_id=issue_type_id)
        return [row for row in rows if _source_in_working_set(session, row.source_comment_id)]


def _source_in_working_set(session, source_comment_id: str | None) -> bool:
    if source_comment_id is None:
        return True
    comment = session.get(ProofreadingComment, source_comment_id)
    return comment is not None and in_working_set(comment)


def _example_matches_current_label(session, example: IssueExample) -> bool:
    if example.source_comment_id is None:
        return True
    return any(
        coding.status == CODING_ACCEPTED and coding.issue_type_id == example.issue_type_id
        for coding in session.find(Coding, comment_id=example.source_comment_id)
    )


def accepted_counts_by_issue_type() -> dict[str, int]:
    init_db()
    counts: dict[str, int] = {}
    with get_session() as session:
        for coding in session.find(Coding, status=CODING_ACCEPTED):
            if not coding.issue_type_id:
                continue
            if not _source_in_working_set(session, coding.comment_id):
                continue
            counts[coding.issue_type_id] = counts.get(coding.issue_type_id, 0) + 1
    return counts


def list_working_observations(issue_type_id: str) -> list[ProofreadingComment]:
    init_db()
    with get_session() as session:
        types = session.find(IssueType)
        ids = descendant_ids(types, issue_type_id) | {issue_type_id}
        seen: set[str] = set()
        comments: list[ProofreadingComment] = []
        for coding in session.find(Coding, status=CODING_ACCEPTED):
            if coding.issue_type_id not in ids or coding.comment_id in seen:
                continue
            comment = session.get(ProofreadingComment, coding.comment_id)
            if comment is None or not in_working_set(comment):
                continue
            seen.add(comment.id)
            comments.append(comment)
        return comments


def rename_issue_type(issue_type_id: str, *, name: str) -> IssueType:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        taken_names = [
            row.name
            for row in session.find(IssueType, status=ISSUE_ACTIVE)
            if row.id != issue_type_id
        ]
        before = {"name": issue.name}
        issue.name = next_unique_name(taken_names, name)
        issue.updated_at = utcnow()
        _log(
            session,
            "rename",
            {
                "issue_type_id": issue_type_id,
                "before": before,
                "after": {"name": issue.name},
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def edit_issue_type(
    issue_type_id: str,
    *,
    definition: str | None = None,
    detection_guidance: str | None = None,
) -> IssueType:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        before = {
            "definition": issue.definition,
            "detection_guidance": issue.detection_guidance,
        }
        if definition is not None:
            issue.definition = definition
        if detection_guidance is not None:
            issue.detection_guidance = detection_guidance
        issue.updated_at = utcnow()
        _log(
            session,
            "edit",
            {
                "issue_type_id": issue_type_id,
                "before": before,
                "after": {
                    "definition": issue.definition,
                    "detection_guidance": issue.detection_guidance,
                },
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def move_issue_type(issue_type_id: str, *, parent_id: str | None, position: int) -> IssueType:
    with get_session() as session:
        issue = _require_active(session, issue_type_id)
        if parent_id is not None:
            parent = session.get(IssueType, parent_id)
            if parent is None or parent.status != ISSUE_ACTIVE:
                raise NotFound(f"Unknown issue type {parent_id}")
        types = session.find(IssueType)
        if parent_id is not None and is_under(types, child=parent_id, ancestor=issue_type_id):
            raise BadInput("Cannot move a type under itself or a descendant")
        before_parent = issue.parent_id
        before_pos = issue.position
        dest_is_leaf = parent_id is not None and not active_children(types, parent_id)
        place_among_siblings(types, issue, parent_id, position)
        for row in session.find(IssueType):
            session.add(row)
        if before_parent == parent_id and before_pos == issue.position:
            session.commit()
            session.refresh(issue)
            return issue
        parked = {}
        if dest_is_leaf and _has_own_labels(session, parent_id):
            parked = _park_own_labels_on_ungrouped(session, parent_id)
        issue.updated_at = utcnow()
        _log(
            session,
            "move",
            {
                "issue_type_id": issue_type_id,
                "from_parent_id": before_parent,
                "from_position": before_pos,
                "to_parent_id": parent_id,
                "to_position": issue.position,
                "name": issue.name,
                **parked,
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def deactivate_issue_type(issue_type_id: str) -> IssueType:
    """Hide this type. Children become siblings; labels on this type go Unlabeled."""
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        deleted_codings = _retire_codings_for_types(session, {issue_type_id})
        reparented_children = lift_children(session.find(IssueType), issue)
        for row in session.find(IssueType):
            session.add(row)
        issue.status = ISSUE_INACTIVE
        issue.updated_at = utcnow()
        _log(
            session,
            "deactivate",
            {
                "issue_type_id": issue_type_id,
                "name": issue.name,
                "deleted_codings": deleted_codings,
                "reparented_children": reparented_children,
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def merge_issue_types(*, source_ids: list[str], target_id: str) -> IssueType:
    """Fold sources into target: reassign codings/examples/counterexamples, then deactivate sources."""
    with get_session() as session:
        target = _require_active(session, target_id)
        reassigned_codings = []
        reassigned_examples = []
        deleted_examples = []
        reassigned_counters = []
        reparented_children = []
        types = session.find(IssueType)
        target_is_leaf = not active_children(types, target_id)
        will_gain_children = any(
            source_id != target_id and active_children(types, source_id)
            for source_id in source_ids
        )
        parked = {}
        label_dest = target_id
        if target_is_leaf and will_gain_children:
            parked = _park_own_labels_on_ungrouped(session, target_id)
            label_dest = parked["ungrouped_id"]
        for source_id in source_ids:
            if source_id == target_id:
                continue
            source = _require_active(session, source_id)
            if is_under(types, child=target_id, ancestor=source_id):
                raise BadInput("Cannot merge a type into itself or a descendant")
            for child in active_children(types, source_id):
                if child.id == target_id:
                    continue
                reparented_children.append(
                    {
                        "id": child.id,
                        "from_parent_id": source_id,
                        "from_position": child.position,
                    }
                )
                child.parent_id = target_id
                session.add(child)
            compact_positions(session.find(IssueType), target_id)
            for coding in session.find(Coding, issue_type_id=source_id):
                reassigned_codings.append(
                    {"id": coding.id, "comment_id": coding.comment_id, "from_issue_type_id": source_id}
                )
                coding.issue_type_id = label_dest
                session.add(coding)
            for example in list(session.find(IssueExample, issue_type_id=source_id)):
                if example.source_comment_id:
                    existing = session.first(
                        IssueExample,
                        issue_type_id=label_dest,
                        source_comment_id=example.source_comment_id,
                    )
                    if existing is not None:
                        deleted_examples.append(dump_row(example))
                        session.delete(example)
                        continue
                reassigned_examples.append({"id": example.id, "from_issue_type_id": source_id})
                example.issue_type_id = label_dest
                session.add(example)
            for counter in session.find(IssueCounterexample, issue_type_id=source_id):
                reassigned_counters.append({"id": counter.id, "from_issue_type_id": source_id})
                counter.issue_type_id = label_dest
                session.add(counter)
            source.status = ISSUE_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
            compact_positions(session.find(IssueType), source.parent_id)
        _log(
            session,
            "merge",
            {
                "source_ids": source_ids,
                "target_id": target_id,
                "reassigned_codings": list(parked.get("reassigned_codings") or []) + reassigned_codings,
                "reassigned_examples": list(parked.get("reassigned_examples") or []) + reassigned_examples,
                "deleted_examples": deleted_examples,
                "reassigned_counters": list(parked.get("reassigned_counters") or []) + reassigned_counters,
                "reparented_children": reparented_children,
                **{key: parked[key] for key in ("ungrouped_id", "ungrouped_name") if key in parked},
            },
        )
        session.add(target)
        session.commit()
        session.refresh(target)
        return target


def flatten_issue_type(issue_type_id: str) -> IssueType:
    with get_session() as session:
        issue = _require_active(session, issue_type_id)
        types = session.find(IssueType)
        desc = descendant_ids(types, issue_type_id)
        if not desc:
            raise BadInput("Cannot flatten a type with no children")
        reassigned_codings = []
        reassigned_examples = []
        deleted_examples = []
        reassigned_counters = []
        descendant_ids_list = list(desc)
        for source_id in descendant_ids_list:
            source = session.get(IssueType, source_id)
            for coding in session.find(Coding, issue_type_id=source_id):
                reassigned_codings.append(
                    {"id": coding.id, "comment_id": coding.comment_id, "from_issue_type_id": source_id}
                )
                coding.issue_type_id = issue_type_id
                session.add(coding)
            for example in list(session.find(IssueExample, issue_type_id=source_id)):
                if example.source_comment_id:
                    existing = session.first(
                        IssueExample,
                        issue_type_id=issue_type_id,
                        source_comment_id=example.source_comment_id,
                    )
                    if existing is not None:
                        deleted_examples.append(dump_row(example))
                        session.delete(example)
                        continue
                reassigned_examples.append({"id": example.id, "from_issue_type_id": source_id})
                example.issue_type_id = issue_type_id
                session.add(example)
            for counter in session.find(IssueCounterexample, issue_type_id=source_id):
                reassigned_counters.append({"id": counter.id, "from_issue_type_id": source_id})
                counter.issue_type_id = issue_type_id
                session.add(counter)
            source.status = ISSUE_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
        _log(
            session,
            "flatten",
            {
                "issue_type_id": issue_type_id,
                "name": issue.name,
                "descendant_ids": descendant_ids_list,
                "reassigned_codings": reassigned_codings,
                "reassigned_examples": reassigned_examples,
                "deleted_examples": deleted_examples,
                "reassigned_counters": reassigned_counters,
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def remove_issue_type(issue_type_id: str) -> None:
    with get_session() as session:
        issue = _require_active(session, issue_type_id)
        ids = descendant_ids(session.find(IssueType), issue_type_id, active_only=False) | {
            issue_type_id
        }
        dumped_types = [dump_row(session.get(IssueType, i)) for i in ids]
        deleted_codings = _retire_codings_for_types(session, ids)
        dumped_examples = []
        dumped_counters = []
        for type_id in ids:
            for example in list(session.find(IssueExample, issue_type_id=type_id)):
                dumped_examples.append(dump_row(example))
                session.delete(example)
            for counter in list(session.find(IssueCounterexample, issue_type_id=type_id)):
                dumped_counters.append(dump_row(counter))
                session.delete(counter)
            session.delete(session.get(IssueType, type_id))
        compact_positions(session.find(IssueType), issue.parent_id)
        for row in session.find(IssueType):
            session.add(row)
        _log(
            session,
            "remove",
            {
                "issue_type_id": issue_type_id,
                "name": issue.name,
                "types": dumped_types,
                "deleted_codings": deleted_codings,
                "examples": dumped_examples,
                "counters": dumped_counters,
            },
        )
        session.commit()


def apply_split(*, source_id: str | None, plan) -> list[IssueType]:
    from reviewdistill.coding.split import SplitPlan

    if not isinstance(plan, SplitPlan):
        raise BadInput("Split plan is invalid")
    init_db()
    with get_session() as session:
        source = None
        if source_id is not None:
            source = _require_active(session, source_id)
            if active_children(session.find(IssueType), source_id):
                raise BadInput("Cannot split a type that has children")
        elif any(row.status == ISSUE_ACTIVE for row in session.find(IssueType)):
            raise BadInput("Cannot split unlabeled comments while a taxonomy exists")
        comment_ids = [row["comment_id"] for row in plan.assignments]
        deleted_codings: list[dict] = []
        replaced: list[dict] = []
        if source is not None:
            deleted_codings = _retire_codings_for_types(
                session, {source_id}, comment_ids=set(comment_ids)
            )
        else:
            for comment_id in comment_ids:
                for row in list(session.find(Coding, comment_id=comment_id, status=CODING_PROPOSED)):
                    replaced.append(dump_row(row))
                    session.delete(row)
        created = []
        parent_id = source_id
        for spec in plan.types:
            issue = add_issue_type(
                session,
                name=spec["name"],
                definition=spec["definition"],
                parent_id=parent_id,
                log=False,
            )
            created.append(issue)
        parked: dict = {}
        if source is not None:
            leftover = [
                row
                for row in session.find(Coding, issue_type_id=source_id)
                if row.status == CODING_ACCEPTED
            ]
            if leftover:
                parked = _park_own_labels_on_ungrouped(session, source_id)
        siblings = [
            row
            for row in active_children(session.find(IssueType), parent_id)
            if row.id not in {issue.id for issue in created}
        ]
        for index, issue in enumerate(created):
            siblings.insert(index, issue)
        for index, row in enumerate(siblings):
            row.position = index
            session.add(row)
        created_codings = []
        for row in plan.assignments:
            child = created[row["type_index"]]
            coding = Coding(
                id=str(uuid4()),
                comment_id=row["comment_id"],
                issue_type_id=child.id,
                coder_type="ai",
                status=CODING_PROPOSED,
            )
            session.add(coding)
            created_codings.append(dump_row(coding))
        created_ids = [issue.id for issue in created]
        if parked.get("ungrouped_id"):
            created_ids.append(parked["ungrouped_id"])
        _log(
            session,
            "split",
            {
                "keep_source": True,
                "source_id": source_id,
                "source_name": None if source is None else source.name,
                "created_ids": created_ids,
                "deleted_codings": deleted_codings,
                "created": created_codings,
                "replaced": replaced,
                **parked,
            },
        )
        session.commit()
        for issue in created:
            session.refresh(issue)
        return created
