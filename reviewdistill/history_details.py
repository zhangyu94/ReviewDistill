"""Human-readable History dialog details from taxonomy event payloads.

Sentence construction lives here, not on the client. Payload names take
precedence over live rows. Lookups are batched once per list.
"""

from __future__ import annotations

from dataclasses import dataclass

from reviewdistill.db.models import Coding, Label, ProofreadingComment

MISSING_LABEL = "a label that is no longer available"
MISSING_COMMENT = "Comment is no longer available"


@dataclass(frozen=True)
class HistoryLookup:
    comments: dict[str, str]
    labels: dict[str, str]
    coding_comments: dict[str, str]


def collect_ids(payload: dict) -> tuple[set[str], set[str], set[str]]:
    comment_ids: set[str] = set()
    label_ids: set[str] = set()
    coding_ids: set[str] = set()

    def add_comment(value: object) -> None:
        if isinstance(value, str) and value:
            comment_ids.add(value)

    def add_label_id(value: object) -> None:
        if isinstance(value, str) and value:
            label_ids.add(value)

    add_comment(payload.get("comment_id"))
    for key in (
        "label_id",
        "from_parent_id",
        "to_parent_id",
        "ungrouped_id",
        "target_id",
        "source_id",
    ):
        add_label_id(payload.get(key))
    for key in ("source_ids", "created_ids", "descendant_ids"):
        for item in payload.get(key) or []:
            add_label_id(item)
    # Persisted remove dumps keep the wrapper key "types".
    for row in payload.get("types") or []:
        add_label_id(row.get("id"))
    for key in ("created", "replaced", "deleted_codings", "retired_accepted"):
        for row in payload.get(key) or []:
            add_comment(row.get("comment_id"))
            add_label_id(row.get("label_id"))
            add_label_id(row.get("proposed_parent_id"))
    coding = payload.get("coding")
    if isinstance(coding, dict):
        add_comment(coding.get("comment_id"))
        add_label_id(coding.get("label_id"))
    for row in payload.get("reassigned_codings") or []:
        if row.get("id"):
            coding_ids.add(row["id"])
        add_comment(row.get("comment_id"))
        add_label_id(row.get("from_label_id"))
    return comment_ids, label_ids, coding_ids


def build_lookup(session, events: list[tuple[str, dict]]) -> HistoryLookup:
    comment_ids: set[str] = set()
    label_ids: set[str] = set()
    coding_ids: set[str] = set()
    for _event_type, payload in events:
        comments, found_label_ids, codings = collect_ids(payload)
        comment_ids |= comments
        label_ids |= found_label_ids
        coding_ids |= codings
    coding_comments: dict[str, str] = {}
    if coding_ids:
        for row in session.find(Coding, id=coding_ids):
            coding_comments[row.id] = row.comment_id
            comment_ids.add(row.comment_id)
    comments: dict[str, str] = {}
    if comment_ids:
        for row in session.find(ProofreadingComment, id=comment_ids):
            comments[row.id] = row.raw_text
    labels: dict[str, str] = {}
    if label_ids:
        for row in session.find(Label, id=label_ids):
            labels[row.id] = row.name
    return HistoryLookup(comments=comments, labels=labels, coding_comments=coding_comments)


def event_details(event_type: str, payload: dict, lookup: HistoryLookup, *, summary: str) -> dict:
    handler = HANDLERS.get(event_type)
    try:
        if handler is None:
            details = {"explanation": event_type, "comments": [], "quotes": []}
        else:
            details = handler(payload, lookup)
    except Exception:
        # A details failure must not fail list_history.
        return {"explanation": summary, "comments": [], "quotes": []}
    return {
        "explanation": details["explanation"],
        "comments": list(details.get("comments") or []),
        "quotes": list(details.get("quotes") or []),
    }


def _name(lookup: HistoryLookup, label_id: str | None, stored: str | None = None) -> str:
    # Payload names win so rename/add/remove stay accurate without a live row.
    if stored:
        return stored
    if label_id and lookup.labels.get(label_id):
        return lookup.labels[label_id]
    return MISSING_LABEL


def _join(names: list[str]) -> str:
    return ", ".join(names)


def _join_and(names: list[str]) -> str:
    if not names:
        return MISSING_LABEL
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _from_codings(
    payload: dict, lookup: HistoryLookup, label_name: str | None, *, skip_missing: bool
) -> list[dict]:
    items = []
    seen: set[str] = set()
    for row in payload.get("reassigned_codings") or []:
        comment_id = row.get("comment_id") or lookup.coding_comments.get(row.get("id"))
        if not comment_id or comment_id in seen:
            continue
        seen.add(comment_id)
        text = lookup.comments.get(comment_id)
        if text is None:
            if skip_missing:
                continue
            text = MISSING_COMMENT
        items.append({"text": text, "label_name": label_name})
    return items


def _rename(payload: dict, lookup: HistoryLookup) -> dict:
    before = (payload.get("before") or {}).get("name")
    after = (payload.get("after") or {}).get("name")
    return {
        "explanation": f"Renamed {_name(lookup, None, before)} to {_name(lookup, None, after)}.",
        "comments": [],
        "quotes": [],
    }


def _add(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"), payload.get("name"))
    explanation = f"Added the label {name}."
    comments: list[dict] = []
    if payload.get("ungrouped_id"):
        ungrouped = _name(lookup, payload.get("ungrouped_id"), payload.get("ungrouped_name"))
        explanation += f" Existing label assignments on the parent were moved onto {ungrouped}."
        comments = _from_codings(payload, lookup, ungrouped, skip_missing=True)
    return {"explanation": explanation, "comments": comments, "quotes": []}


def _edit(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"))
    before = payload.get("before") or {}
    after = payload.get("after") or {}
    quotes = [{"heading": "Definition", "body": after.get("definition") or ""}]
    if after.get("detection_guidance") != before.get("detection_guidance"):
        quotes.append({"heading": "Detection guidance", "body": after.get("detection_guidance") or ""})
    # Legacy edit payloads may still contain notes; never quote that key.
    return {"explanation": f"Edited the definition of {name}.", "comments": [], "quotes": quotes}


def _move(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"), payload.get("name"))
    parent_id = payload.get("to_parent_id")
    if parent_id:
        explanation = f"Moved {name} under {_name(lookup, parent_id)}."
    else:
        explanation = f"Moved {name} to the top of the taxonomy."
    return {"explanation": explanation, "comments": [], "quotes": []}


def _from_dumps(
    rows: list, lookup: HistoryLookup, label_name: str | None, *, skip_missing: bool
) -> list[dict]:
    items = []
    seen: set[str] = set()
    for row in rows or []:
        comment_id = row.get("comment_id")
        if not comment_id or comment_id in seen:
            continue
        seen.add(comment_id)
        text = lookup.comments.get(comment_id)
        if text is None:
            if skip_missing:
                continue
            text = MISSING_COMMENT
        items.append({"text": text, "label_name": label_name})
    return items


def _flatten(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"), payload.get("name"))
    descendants = [_name(lookup, item) for item in (payload.get("descendant_ids") or [])]
    extra = f": {_join(descendants)}" if descendants else ""
    return {
        "explanation": (
            f"Flattened {name}. These descendant labels were retired, "
            f"and their comments were assigned to {name}{extra}."
        ),
        "comments": _from_codings(payload, lookup, name, skip_missing=True),
        "quotes": [],
    }


def _remove(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"), payload.get("name"))
    root_id = payload.get("label_id")
    child_names = []
    for row in payload.get("types") or []:
        if row.get("id") == root_id:
            continue
        child_names.append(row.get("name") or _name(lookup, row.get("id")))
    if child_names:
        explanation = (
            f"Removed {name} and its subtree ({_join(child_names)}). "
            "Labeled comments on those labels returned to Unlabeled."
        )
    else:
        explanation = f"Removed {name}. Labeled comments on those labels returned to Unlabeled."
    return {
        "explanation": explanation,
        "comments": _from_dumps(payload.get("deleted_codings") or [], lookup, None, skip_missing=True),
        "quotes": [],
    }


def _deactivate(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"), payload.get("name"))
    return {
        "explanation": (
            f"Deactivated {name}. Its children became siblings, "
            "and labeled comments on this label returned to Unlabeled."
        ),
        "comments": _from_dumps(payload.get("deleted_codings") or [], lookup, None, skip_missing=True),
        "quotes": [],
    }


def _merge(payload: dict, lookup: HistoryLookup) -> dict:
    target_id = payload.get("target_id")
    target = _name(lookup, target_id)
    sources = [_name(lookup, item) for item in (payload.get("source_ids") or []) if item != target_id]
    joined = _join(sources) if sources else MISSING_LABEL
    return {
        "explanation": f"Merged {joined} into {target}.",
        "comments": _from_codings(payload, lookup, target, skip_missing=True),
        "quotes": [],
    }


def _split(payload: dict, lookup: HistoryLookup) -> dict:
    created_ids = payload.get("created_ids") or []
    created_names = [_name(lookup, item) for item in created_ids]
    joined = _join_and(created_names)
    if payload.get("keep_source"):
        source_id = payload.get("source_id")
        if source_id:
            explanation = f"Split {_name(lookup, source_id)} into {joined}."
        else:
            explanation = f"Split unlabeled comments into {joined}."
        comments = []
        seen: set[str] = set()
        for row in payload.get("created") or []:
            comment_id = row.get("comment_id")
            if not comment_id or comment_id in seen:
                continue
            seen.add(comment_id)
            text = lookup.comments.get(comment_id)
            if text is None:
                continue
            comments.append(
                {
                    "text": text,
                    "label_name": _name(lookup, row.get("label_id")),
                }
            )
        return {"explanation": explanation, "comments": comments, "quotes": []}
    source = _name(lookup, payload.get("source_id"))
    if len(created_names) >= 2:
        explanation = (
            f"Split {source} into {created_names[0]} and {created_names[1]}. "
            f"Labeled comments on {source} returned to Unlabeled."
        )
    else:
        explanation = f"Split {source}. Labeled comments on {source} returned to Unlabeled."
    return {
        "explanation": explanation,
        "comments": _from_dumps(payload.get("deleted_codings") or [], lookup, None, skip_missing=True),
        "quotes": [],
    }


def _one_comment(payload: dict, lookup: HistoryLookup, label_name: str | None) -> list[dict]:
    comment_id = payload.get("comment_id")
    if not comment_id:
        return [{"text": MISSING_COMMENT, "label_name": label_name}]
    text = lookup.comments.get(comment_id)
    if text is None:
        text = MISSING_COMMENT
    return [{"text": text, "label_name": label_name}]


def _propose(payload: dict, lookup: HistoryLookup) -> dict:
    created = payload.get("created") or []
    comments = []
    seen: set[str] = set()
    for row in created:
        comment_id = row.get("comment_id")
        if not comment_id or comment_id in seen:
            continue
        seen.add(comment_id)
        text = lookup.comments.get(comment_id)
        if text is None:
            continue
        if row.get("label_id"):
            label_name = _name(lookup, row.get("label_id"))
        else:
            label_name = row.get("proposed_label_name")
        comments.append({"text": text, "label_name": label_name})
    return {
        "explanation": f"Labeled {len(created)} comments with AI.",
        "comments": comments,
        "quotes": [],
    }


def _accept(payload: dict, lookup: HistoryLookup) -> dict:
    label_name = _name(lookup, payload.get("label_id"))
    return {
        "explanation": f"Accepted the label {label_name} for this comment.",
        "comments": _one_comment(payload, lookup, label_name),
        "quotes": [],
    }


def _change(payload: dict, lookup: HistoryLookup) -> dict:
    new_id = (payload.get("coding") or {}).get("label_id")
    new_name = _name(lookup, new_id)
    old_name = None
    for row in payload.get("retired_accepted") or []:
        if row.get("label_id"):
            old_name = _name(lookup, row.get("label_id"))
            break
    if old_name:
        explanation = f"Changed the label from {old_name} to {new_name}."
    else:
        explanation = f"Assigned this comment to {new_name}."
    return {
        "explanation": explanation,
        "comments": _one_comment(payload, lookup, new_name),
        "quotes": [],
    }


def _verify(payload: dict, lookup: HistoryLookup) -> dict:
    return {
        "explanation": "Verified this comment.",
        "comments": _one_comment(payload, lookup, None),
        "quotes": [],
    }


def _unverify(payload: dict, lookup: HistoryLookup) -> dict:
    return {
        "explanation": "Unverified this comment.",
        "comments": _one_comment(payload, lookup, None),
        "quotes": [],
    }


def _drop(payload: dict, lookup: HistoryLookup) -> dict:
    return {
        "explanation": "Dropped this comment.",
        "comments": _one_comment(payload, lookup, None),
        "quotes": [],
    }


def _delete(payload: dict, lookup: HistoryLookup) -> dict:
    dumped = payload.get("comment") or {}
    text = dumped.get("raw_text")
    if text:
        comments = [{"text": text, "label_name": None}]
    else:
        comments = _one_comment(payload, lookup, None)
    return {
        "explanation": "Deleted this comment.",
        "comments": comments,
        "quotes": [],
    }


def _recycle(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("label_id"), payload.get("name"))
    created = payload.get("created") or []
    comments = []
    seen: set[str] = set()
    for row in created:
        comment_id = row.get("comment_id")
        if not comment_id or comment_id in seen:
            continue
        seen.add(comment_id)
        text = lookup.comments.get(comment_id)
        if text is None:
            continue
        comments.append({"text": text, "label_name": name})
    return {
        "explanation": (
            f"Added the label {name} and assigned {len(created)} unlabeled comments to it."
        ),
        "comments": comments,
        "quotes": [],
    }


HANDLERS = {
    "rename": _rename,
    "add": _add,
    "edit": _edit,
    "move": _move,
    "flatten": _flatten,
    "remove": _remove,
    "deactivate": _deactivate,
    "merge": _merge,
    "split": _split,
    "propose": _propose,
    "accept": _accept,
    "change": _change,
    "verify": _verify,
    "unverify": _unverify,
    "drop": _drop,
    "delete": _delete,
    "recycle": _recycle,
}
