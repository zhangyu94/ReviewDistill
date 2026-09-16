from __future__ import annotations

from uuid import uuid4

from reviewdistill.db.models import (
    CODING_ACCEPTED,
    CODING_MODIFIED,
    CODING_PROPOSED,
    LABEL_ACTIVE,
    LABEL_INACTIVE,
    Coding,
    LabelExample,
    Label,
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


def _require_active(session, label_id: str) -> Label:
    label = session.get(Label, label_id)
    if label is None or label.status != LABEL_ACTIVE:
        raise NotFound(f"Unknown label {label_id}")
    return label


def _log(session, event_type: str, payload: dict) -> None:
    record(session, event_type, payload)


def _retire_codings_for_labels(
    session, label_ids: set[str], comment_ids: set[str] | None = None
) -> list[dict]:
    deleted = []
    labeled_comments = {
        coding.comment_id
        for label_id in label_ids
        for coding in session.find(Coding, label_id=label_id)
        if coding.status == CODING_ACCEPTED
        and (comment_ids is None or coding.comment_id in comment_ids)
    }
    for comment_id in labeled_comments:
        for row in list(session.find(Coding, comment_id=comment_id)):
            deleted.append(dump_row(row))
            session.delete(row)
    for label_id in label_ids:
        for row in list(session.find(Coding, label_id=label_id, status=CODING_PROPOSED)):
            deleted.append(dump_row(row))
            session.delete(row)
    return deleted


def add_label(
    session,
    *,
    name: str,
    definition: str,
    parent_id: str | None = None,
    detection_guidance: str | None = None,
    log: bool = True,
) -> Label:
    if parent_id is not None:
        parent = session.get(Label, parent_id)
        if parent is None or parent.status != LABEL_ACTIVE:
            raise NotFound(f"Unknown label {parent_id}")
    taken_names = [row.name for row in session.find(Label, status=LABEL_ACTIVE)]
    name = next_unique_name(taken_names, name)
    siblings = [
        row
        for row in session.find(Label, status=LABEL_ACTIVE)
        if row.parent_id == parent_id
    ]
    label = Label(
        id=str(uuid4()),
        name=name,
        parent_id=parent_id,
        position=len(siblings),
        definition=definition,
        detection_guidance=detection_guidance,
        status=LABEL_ACTIVE,
    )
    session.add(label)
    if log:
        record(session, "add", {"label_id": label.id, "name": name})
    return label


def create_label(
    *,
    name: str,
    definition: str,
    parent_id: str | None = None,
    detection_guidance: str | None = None,
) -> Label:
    init_db()
    with get_session() as session:
        label = add_label(
            session,
            name=name,
            definition=definition,
            parent_id=parent_id,
            detection_guidance=detection_guidance,
        )
        session.commit()
        session.refresh(label)
        return label


def _reassign_own_labels(session, from_id: str, to_id: str) -> dict:
    reassigned_codings = []
    for coding in session.find(Coding, label_id=from_id):
        reassigned_codings.append(
            {"id": coding.id, "comment_id": coding.comment_id, "from_label_id": from_id}
        )
        coding.label_id = to_id
        session.add(coding)
    reassigned_examples = []
    for example in list(session.find(LabelExample, label_id=from_id)):
        reassigned_examples.append({"id": example.id, "from_label_id": from_id})
        example.label_id = to_id
        session.add(example)
    return {
        "reassigned_codings": reassigned_codings,
        "reassigned_examples": reassigned_examples,
    }


def _has_own_labels(session, label_id: str) -> bool:
    if session.first(Coding, label_id=label_id) is not None:
        return True
    if session.first(LabelExample, label_id=label_id) is not None:
        return True
    return False


def _park_own_labels_on_ungrouped(session, parent_id: str) -> dict:
    ungrouped = add_label(
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


def add_child_label(
    session,
    *,
    name: str,
    definition: str,
    parent_id: str | None,
    detection_guidance: str | None = None,
) -> Label:
    """Add a label. If parent is a leaf, park its assignments on ungrouped (one add event)."""
    split_leaf = False
    if parent_id is not None:
        _require_active(session, parent_id)
        split_leaf = not active_children(session.find(Label), parent_id)
    label = add_label(
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
                "label_id": label.id,
                "name": label.name,
                **parked,
            },
        )
    return label


def create_empty_label(*, parent_id: str | None) -> Label:
    init_db()
    with get_session() as session:
        label = add_child_label(
            session,
            name="New label",
            definition="",
            parent_id=parent_id,
        )
        session.commit()
        session.refresh(label)
        return label


def _latest_proposed(session, comment_id: str):
    rows = session.find(Coding, comment_id=comment_id, status=CODING_PROPOSED, order_by="created_at")
    return rows[-1] if rows else None


def _assign_working_comment(session, comment: ProofreadingComment, label_id: str) -> dict:
    proposed = _latest_proposed(session, comment.id)
    modified_proposed = []
    if proposed is not None:
        proposed.status = CODING_MODIFIED
        session.add(proposed)
        modified_proposed.append({"id": proposed.id})
    retired_accepted = []
    for row in list(session.find(Coding, comment_id=comment.id, status=CODING_ACCEPTED)):
        retired_accepted.append(dump_row(row))
        row.status = CODING_MODIFIED
        session.add(row)
    deleted_examples = []
    for example in list(session.find(LabelExample, source_comment_id=comment.id)):
        deleted_examples.append(dump_row(example))
        session.delete(example)
    human = Coding(
        id=str(uuid4()),
        comment_id=comment.id,
        label_id=label_id,
        coder_type="human",
        status=CODING_ACCEPTED,
        rationale="Grouped unlabeled comments.",
    )
    session.add(human)
    example, created, _previous = ensure_example(session, label_id, example_text(comment), comment.id)
    return {
        "coding": dump_row(human),
        "example": dump_row(example) if created else None,
        "modified_proposed": modified_proposed,
        "retired_accepted": retired_accepted,
        "deleted_examples": deleted_examples,
    }


def recycle_ungrouped() -> Label:
    """Park leftover unlabeled working-set comments on a new ``ungrouped`` root.

    Header fork only runs on an empty forest. Once a taxonomy exists, recycle
    makes that leftover pile a leaf so leaf-fork can cluster it. Does not call
    the LLM. The new root shares the ``ungrouped`` name family with the parking
    child created by hover-plus on a leaf; they are different nodes.
    """
    from reviewdistill.coding.split import unlabeled_working_comments
    from reviewdistill.db.models import is_labeled

    comments = unlabeled_working_comments()
    init_db()
    with get_session() as session:
        if not any(row.status == LABEL_ACTIVE for row in session.find(Label)):
            raise BadInput("Cannot group unlabeled comments until a taxonomy exists")
        if len(comments) < 2:
            raise BadInput("Need at least two unlabeled comments to group")
        label = add_label(
            session,
            name="ungrouped",
            definition="",
            parent_id=None,
            log=False,
        )
        created = []
        examples = []
        retired_accepted = []
        modified_proposed = []
        deleted_examples = []
        for comment in comments:
            live = session.get(ProofreadingComment, comment.id)
            if live is None or is_labeled(session, live.id):
                continue
            assigned = _assign_working_comment(session, live, label.id)
            created.append(assigned["coding"])
            if assigned["example"]:
                examples.append(assigned["example"])
            retired_accepted.extend(assigned["retired_accepted"])
            modified_proposed.extend(assigned["modified_proposed"])
            deleted_examples.extend(assigned["deleted_examples"])
        record(
            session,
            "recycle",
            {
                "label_id": label.id,
                "name": label.name,
                "created": created,
                "examples": examples,
                "retired_accepted": retired_accepted,
                "modified_proposed": modified_proposed,
                "deleted_examples": deleted_examples,
            },
        )
        session.commit()
        session.refresh(label)
        return label


def list_active_labels() -> list[Label]:
    init_db()
    with get_session() as session:
        return sorted(
            session.find(Label, status=LABEL_ACTIVE),
            key=lambda label: (label.parent_id or "", label.position, label.name),
        )


def get_label(label_id: str) -> Label | None:
    with get_session() as session:
        label = session.get(Label, label_id)
        if label is None or label.status != LABEL_ACTIVE:
            return None
        return label


def example_text(comment) -> str:
    """Passage excerpt stored on the label for Export / spotting.

    The remark stays on the coding row. Copying ``raw_text`` into the example
    makes SKILL.md unusable once that comment is held out. Whitespace is
    collapsed so markdown export stays one list item per example.
    """
    context = (getattr(comment, "context_text", None) or "").strip()
    raw = context if context else (getattr(comment, "raw_text", None) or "").strip()
    return " ".join(raw.split())


def _sourced_example_text(session, example: LabelExample) -> str:
    """Read-time passage for a sourced example. Does not write the store."""
    if not example.source_comment_id:
        return example.text
    comment = session.get(ProofreadingComment, example.source_comment_id)
    if comment is None:
        return example.text
    return example_text(comment) or example.text


def ensure_example(
    session,
    label_id: str,
    text: str,
    source_comment_id: str | None = None,
) -> tuple[LabelExample, bool, str | None]:
    """One example per ``source_comment_id``. Later calls update ``text`` in place.

    Returns ``(row, created, previous_text)``. ``previous_text`` is set when an
    existing row's text changed, so History can invert the write.
    """
    cleaned = " ".join(text.split())
    if source_comment_id:
        existing = session.first(
            LabelExample,
            label_id=label_id,
            source_comment_id=source_comment_id,
        )
        if existing is not None:
            previous = existing.text
            if previous != cleaned:
                existing.text = cleaned
                return existing, False, previous
            return existing, False, None
    row = LabelExample(
        id=str(uuid4()),
        label_id=label_id,
        text=cleaned,
        source_comment_id=source_comment_id,
    )
    session.add(row)
    return row, True, None


def add_example(label_id: str, text: str, source_comment_id: str | None = None) -> LabelExample:
    with get_session() as session:
        row, _created, _previous = ensure_example(session, label_id, text, source_comment_id)
        session.commit()
        session.refresh(row)
        return row


def list_examples(label_id: str) -> list[LabelExample]:
    with get_session() as session:
        rows = session.find(LabelExample, label_id=label_id)
        shown = []
        for row in rows:
            if not _source_in_working_set(session, row.source_comment_id):
                continue
            if not _example_matches_current_label(session, row):
                continue
            shown.append(
                LabelExample(
                    id=row.id,
                    label_id=row.label_id,
                    text=_sourced_example_text(session, row),
                    source_comment_id=row.source_comment_id,
                )
            )
        return shown


def _source_in_working_set(session, source_comment_id: str | None) -> bool:
    if source_comment_id is None:
        return True
    comment = session.get(ProofreadingComment, source_comment_id)
    return comment is not None and in_working_set(comment)


def _example_matches_current_label(session, example: LabelExample) -> bool:
    if example.source_comment_id is None:
        return True
    return any(
        coding.status == CODING_ACCEPTED and coding.label_id == example.label_id
        for coding in session.find(Coding, comment_id=example.source_comment_id)
    )


def accepted_counts_by_label() -> dict[str, int]:
    init_db()
    counts: dict[str, int] = {}
    with get_session() as session:
        for coding in session.find(Coding, status=CODING_ACCEPTED):
            if not coding.label_id:
                continue
            if not _source_in_working_set(session, coding.comment_id):
                continue
            counts[coding.label_id] = counts.get(coding.label_id, 0) + 1
    return counts


def list_working_observations(label_id: str) -> list[ProofreadingComment]:
    init_db()
    with get_session() as session:
        labels = session.find(Label)
        ids = descendant_ids(labels, label_id) | {label_id}
        seen: set[str] = set()
        comments: list[ProofreadingComment] = []
        for coding in session.find(Coding, status=CODING_ACCEPTED):
            if coding.label_id not in ids or coding.comment_id in seen:
                continue
            comment = session.get(ProofreadingComment, coding.comment_id)
            if comment is None or not in_working_set(comment):
                continue
            seen.add(comment.id)
            comments.append(comment)
        return comments


def rename_label(label_id: str, *, name: str) -> Label:
    with get_session() as session:
        label = session.get(Label, label_id)
        if label is None:
            raise NotFound(f"Unknown label {label_id}")
        taken_names = [
            row.name
            for row in session.find(Label, status=LABEL_ACTIVE)
            if row.id != label_id
        ]
        before = {"name": label.name}
        label.name = next_unique_name(taken_names, name)
        label.updated_at = utcnow()
        _log(
            session,
            "rename",
            {
                "label_id": label_id,
                "before": before,
                "after": {"name": label.name},
            },
        )
        session.add(label)
        session.commit()
        session.refresh(label)
        return label


def edit_label(
    label_id: str,
    *,
    definition: str | None = None,
    detection_guidance: str | None = None,
) -> Label:
    with get_session() as session:
        label = session.get(Label, label_id)
        if label is None:
            raise NotFound(f"Unknown label {label_id}")
        before = {
            "definition": label.definition,
            "detection_guidance": label.detection_guidance,
        }
        if definition is not None:
            label.definition = definition
        if detection_guidance is not None:
            label.detection_guidance = detection_guidance
        label.updated_at = utcnow()
        _log(
            session,
            "edit",
            {
                "label_id": label_id,
                "before": before,
                "after": {
                    "definition": label.definition,
                    "detection_guidance": label.detection_guidance,
                },
            },
        )
        session.add(label)
        session.commit()
        session.refresh(label)
        return label


def move_label(label_id: str, *, parent_id: str | None, position: int) -> Label:
    with get_session() as session:
        label = _require_active(session, label_id)
        if parent_id is not None:
            parent = session.get(Label, parent_id)
            if parent is None or parent.status != LABEL_ACTIVE:
                raise NotFound(f"Unknown label {parent_id}")
        labels = session.find(Label)
        if parent_id is not None and is_under(labels, child=parent_id, ancestor=label_id):
            raise BadInput("Cannot move a label under itself or a descendant")
        before_parent = label.parent_id
        before_pos = label.position
        dest_is_leaf = parent_id is not None and not active_children(labels, parent_id)
        place_among_siblings(labels, label, parent_id, position)
        for row in session.find(Label):
            session.add(row)
        if before_parent == parent_id and before_pos == label.position:
            session.commit()
            session.refresh(label)
            return label
        parked = {}
        if dest_is_leaf and _has_own_labels(session, parent_id):
            parked = _park_own_labels_on_ungrouped(session, parent_id)
        label.updated_at = utcnow()
        _log(
            session,
            "move",
            {
                "label_id": label_id,
                "from_parent_id": before_parent,
                "from_position": before_pos,
                "to_parent_id": parent_id,
                "to_position": label.position,
                "name": label.name,
                **parked,
            },
        )
        session.add(label)
        session.commit()
        session.refresh(label)
        return label


def deactivate_label(label_id: str) -> Label:
    """Hide this label. Children become siblings; assignments on this label go Unlabeled."""
    with get_session() as session:
        label = session.get(Label, label_id)
        if label is None:
            raise NotFound(f"Unknown label {label_id}")
        deleted_codings = _retire_codings_for_labels(session, {label_id})
        reparented_children = lift_children(session.find(Label), label)
        for row in session.find(Label):
            session.add(row)
        label.status = LABEL_INACTIVE
        label.updated_at = utcnow()
        _log(
            session,
            "deactivate",
            {
                "label_id": label_id,
                "name": label.name,
                "deleted_codings": deleted_codings,
                "reparented_children": reparented_children,
            },
        )
        session.add(label)
        session.commit()
        session.refresh(label)
        return label


def merge_labels(*, source_ids: list[str], target_id: str) -> Label:
    """Fold sources into target: reassign codings and examples, then deactivate sources."""
    with get_session() as session:
        target = _require_active(session, target_id)
        reassigned_codings = []
        reassigned_examples = []
        deleted_examples = []
        reparented_children = []
        labels = session.find(Label)
        target_is_leaf = not active_children(labels, target_id)
        will_gain_children = any(
            source_id != target_id and active_children(labels, source_id)
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
            if is_under(labels, child=target_id, ancestor=source_id):
                raise BadInput("Cannot merge a label into itself or a descendant")
            for child in active_children(labels, source_id):
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
            compact_positions(session.find(Label), target_id)
            for coding in session.find(Coding, label_id=source_id):
                reassigned_codings.append(
                    {"id": coding.id, "comment_id": coding.comment_id, "from_label_id": source_id}
                )
                coding.label_id = label_dest
                session.add(coding)
            for example in list(session.find(LabelExample, label_id=source_id)):
                if example.source_comment_id:
                    existing = session.first(
                        LabelExample,
                        label_id=label_dest,
                        source_comment_id=example.source_comment_id,
                    )
                    if existing is not None:
                        deleted_examples.append(dump_row(example))
                        session.delete(example)
                        continue
                reassigned_examples.append({"id": example.id, "from_label_id": source_id})
                example.label_id = label_dest
                session.add(example)
            source.status = LABEL_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
            compact_positions(session.find(Label), source.parent_id)
        _log(
            session,
            "merge",
            {
                "source_ids": source_ids,
                "target_id": target_id,
                "reassigned_codings": list(parked.get("reassigned_codings") or []) + reassigned_codings,
                "reassigned_examples": list(parked.get("reassigned_examples") or []) + reassigned_examples,
                "deleted_examples": deleted_examples,
                "reparented_children": reparented_children,
                **{key: parked[key] for key in ("ungrouped_id", "ungrouped_name") if key in parked},
            },
        )
        session.add(target)
        session.commit()
        session.refresh(target)
        return target


def flatten_label(label_id: str) -> Label:
    with get_session() as session:
        label = _require_active(session, label_id)
        labels = session.find(Label)
        desc = descendant_ids(labels, label_id)
        if not desc:
            raise BadInput("Cannot flatten a label with no children")
        reassigned_codings = []
        reassigned_examples = []
        deleted_examples = []
        descendant_ids_list = list(desc)
        for source_id in descendant_ids_list:
            source = session.get(Label, source_id)
            for coding in session.find(Coding, label_id=source_id):
                reassigned_codings.append(
                    {"id": coding.id, "comment_id": coding.comment_id, "from_label_id": source_id}
                )
                coding.label_id = label_id
                session.add(coding)
            for example in list(session.find(LabelExample, label_id=source_id)):
                if example.source_comment_id:
                    existing = session.first(
                        LabelExample,
                        label_id=label_id,
                        source_comment_id=example.source_comment_id,
                    )
                    if existing is not None:
                        deleted_examples.append(dump_row(example))
                        session.delete(example)
                        continue
                reassigned_examples.append({"id": example.id, "from_label_id": source_id})
                example.label_id = label_id
                session.add(example)
            source.status = LABEL_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
        _log(
            session,
            "flatten",
            {
                "label_id": label_id,
                "name": label.name,
                "descendant_ids": descendant_ids_list,
                "reassigned_codings": reassigned_codings,
                "reassigned_examples": reassigned_examples,
                "deleted_examples": deleted_examples,
            },
        )
        session.add(label)
        session.commit()
        session.refresh(label)
        return label


def remove_label(label_id: str) -> None:
    with get_session() as session:
        label = _require_active(session, label_id)
        ids = descendant_ids(session.find(Label), label_id, active_only=False) | {
            label_id
        }
        dumped_labels = [dump_row(session.get(Label, i)) for i in ids]
        deleted_codings = _retire_codings_for_labels(session, ids)
        dumped_examples = []
        for removed_id in ids:
            for example in list(session.find(LabelExample, label_id=removed_id)):
                dumped_examples.append(dump_row(example))
                session.delete(example)
            session.delete(session.get(Label, removed_id))
        compact_positions(session.find(Label), label.parent_id)
        for row in session.find(Label):
            session.add(row)
        _log(
            session,
            "remove",
            {
                "label_id": label_id,
                "name": label.name,
                "types": dumped_labels,
                "deleted_codings": deleted_codings,
                "examples": dumped_examples,
            },
        )
        session.commit()


def apply_split(*, source_id: str | None, plan) -> list[Label]:
    """Header or leaf fork: mint labels and write accepted codings plus examples.

    One ``split`` History event. ``labeled`` on the HTTP body is assignment
    count, not comments parked onto ``ungrouped``.
    """
    from reviewdistill.coding.split import SplitPlan

    if not isinstance(plan, SplitPlan):
        raise BadInput("Split plan is invalid")
    init_db()
    with get_session() as session:
        source = None
        if source_id is not None:
            source = _require_active(session, source_id)
            if active_children(session.find(Label), source_id):
                raise BadInput("Cannot split a label that has children")
        elif any(row.status == LABEL_ACTIVE for row in session.find(Label)):
            raise BadInput("Cannot split unlabeled comments while a taxonomy exists")
        comment_ids = [row["comment_id"] for row in plan.assignments]
        deleted_codings: list[dict] = []
        replaced: list[dict] = []
        if source is not None:
            deleted_codings = _retire_codings_for_labels(
                session, {source_id}, comment_ids=set(comment_ids)
            )
        else:
            for comment_id in comment_ids:
                for row in list(session.find(Coding, comment_id=comment_id, status=CODING_PROPOSED)):
                    replaced.append(dump_row(row))
                    session.delete(row)
        created = []
        parent_id = source_id
        for spec in plan.labels:
            label = add_label(
                session,
                name=spec["name"],
                definition=spec["definition"],
                parent_id=parent_id,
                log=False,
            )
            created.append(label)
        parked: dict = {}
        if source is not None:
            leftover = [
                row
                for row in session.find(Coding, label_id=source_id)
                if row.status == CODING_ACCEPTED
            ]
            if leftover:
                parked = _park_own_labels_on_ungrouped(session, source_id)
        siblings = [
            row
            for row in active_children(session.find(Label), parent_id)
            if row.id not in {label.id for label in created}
        ]
        for index, label in enumerate(created):
            siblings.insert(index, label)
        for index, row in enumerate(siblings):
            row.position = index
            session.add(row)
        created_codings = []
        examples = []
        deleted_examples = []
        for row in plan.assignments:
            child = created[row["label_index"]]
            comment = session.get(ProofreadingComment, row["comment_id"])
            if comment is not None:
                for example in list(session.find(LabelExample, source_comment_id=comment.id)):
                    deleted_examples.append(dump_row(example))
                    session.delete(example)
            coding = Coding(
                id=str(uuid4()),
                comment_id=row["comment_id"],
                label_id=child.id,
                coder_type="ai",
                status=CODING_ACCEPTED,
            )
            session.add(coding)
            created_codings.append(dump_row(coding))
            if comment is not None:
                example, made, _previous = ensure_example(
                    session, child.id, example_text(comment), comment.id
                )
                if made:
                    examples.append(dump_row(example))
        created_ids = [label.id for label in created]
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
                "examples": examples,
                "deleted_examples": deleted_examples,
                **parked,
            },
        )
        session.commit()
        for label in created:
            session.refresh(label)
        return created
