"""Human-readable History dialog details from taxonomy event payloads.

Sentence construction lives here, not on the client. Payload names take
precedence over live rows. Lookups are batched once per list.
"""

from __future__ import annotations

from dataclasses import dataclass

from reviewdistill.db.models import Coding, IssueType, ProofreadingComment

MISSING_TYPE = "a type that is no longer available"
MISSING_COMMENT = "Comment is no longer available"


@dataclass(frozen=True)
class HistoryLookup:
    comments: dict[str, str]
    types: dict[str, str]
    coding_comments: dict[str, str]


def collect_ids(payload: dict) -> tuple[set[str], set[str], set[str]]:
    comment_ids: set[str] = set()
    type_ids: set[str] = set()
    coding_ids: set[str] = set()

    def add_comment(value: object) -> None:
        if isinstance(value, str) and value:
            comment_ids.add(value)

    def add_type(value: object) -> None:
        if isinstance(value, str) and value:
            type_ids.add(value)

    add_comment(payload.get("comment_id"))
    for key in (
        "issue_type_id",
        "from_parent_id",
        "to_parent_id",
        "ungrouped_id",
        "target_id",
        "source_id",
    ):
        add_type(payload.get(key))
    for key in ("source_ids", "created_ids", "descendant_ids"):
        for item in payload.get(key) or []:
            add_type(item)
    for row in payload.get("types") or []:
        add_type(row.get("id"))
    for key in ("created", "replaced", "deleted_codings", "retired_accepted"):
        for row in payload.get(key) or []:
            add_comment(row.get("comment_id"))
            add_type(row.get("issue_type_id"))
            add_type(row.get("proposed_parent_id"))
    coding = payload.get("coding")
    if isinstance(coding, dict):
        add_comment(coding.get("comment_id"))
        add_type(coding.get("issue_type_id"))
    for row in payload.get("reassigned_codings") or []:
        if row.get("id"):
            coding_ids.add(row["id"])
        add_comment(row.get("comment_id"))
        add_type(row.get("from_issue_type_id"))
    return comment_ids, type_ids, coding_ids


def build_lookup(session, events: list[tuple[str, dict]]) -> HistoryLookup:
    comment_ids: set[str] = set()
    type_ids: set[str] = set()
    coding_ids: set[str] = set()
    for _event_type, payload in events:
        comments, types, codings = collect_ids(payload)
        comment_ids |= comments
        type_ids |= types
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
    types: dict[str, str] = {}
    if type_ids:
        for row in session.find(IssueType, id=type_ids):
            types[row.id] = row.name
    return HistoryLookup(comments=comments, types=types, coding_comments=coding_comments)


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


def _name(lookup: HistoryLookup, type_id: str | None, stored: str | None = None) -> str:
    # Payload names win so rename/add/remove stay accurate without a live row.
    if stored:
        return stored
    if type_id and lookup.types.get(type_id):
        return lookup.types[type_id]
    return MISSING_TYPE


def _join(names: list[str]) -> str:
    return ", ".join(names)


def _join_and(names: list[str]) -> str:
    if not names:
        return MISSING_TYPE
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _from_codings(
    payload: dict, lookup: HistoryLookup, type_name: str | None, *, skip_missing: bool
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
        items.append({"text": text, "type_name": type_name})
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
    name = _name(lookup, payload.get("issue_type_id"), payload.get("name"))
    explanation = f"Added the issue type {name}."
    comments: list[dict] = []
    if payload.get("ungrouped_id"):
        ungrouped = _name(lookup, payload.get("ungrouped_id"), payload.get("ungrouped_name"))
        explanation += f" Existing labels on the parent were moved onto {ungrouped}."
        comments = _from_codings(payload, lookup, ungrouped, skip_missing=True)
    return {"explanation": explanation, "comments": comments, "quotes": []}


def _edit(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("issue_type_id"))
    before = payload.get("before") or {}
    after = payload.get("after") or {}
    quotes = [{"heading": "Definition", "body": after.get("definition") or ""}]
    if after.get("detection_guidance") != before.get("detection_guidance"):
        quotes.append({"heading": "Detection guidance", "body": after.get("detection_guidance") or ""})
    # Legacy edit payloads may still contain notes; never quote that key.
    return {"explanation": f"Edited the definition of {name}.", "comments": [], "quotes": quotes}


def _move(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("issue_type_id"), payload.get("name"))
    parent_id = payload.get("to_parent_id")
    if parent_id:
        explanation = f"Moved {name} under {_name(lookup, parent_id)}."
    else:
        explanation = f"Moved {name} to the top of the taxonomy."
    return {"explanation": explanation, "comments": [], "quotes": []}


def _from_dumps(
    rows: list, lookup: HistoryLookup, type_name: str | None, *, skip_missing: bool
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
        items.append({"text": text, "type_name": type_name})
    return items


def _flatten(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("issue_type_id"), payload.get("name"))
    descendants = [_name(lookup, item) for item in (payload.get("descendant_ids") or [])]
    extra = f": {_join(descendants)}" if descendants else ""
    return {
        "explanation": (
            f"Flattened {name}. These descendant types were retired, "
            f"and their comments were assigned to {name}{extra}."
        ),
        "comments": _from_codings(payload, lookup, name, skip_missing=True),
        "quotes": [],
    }


def _remove(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("issue_type_id"), payload.get("name"))
    root_id = payload.get("issue_type_id")
    child_names = []
    for row in payload.get("types") or []:
        if row.get("id") == root_id:
            continue
        child_names.append(row.get("name") or _name(lookup, row.get("id")))
    if child_names:
        explanation = (
            f"Removed {name} and its subtree ({_join(child_names)}). "
            "Labeled comments on those types returned to Unlabeled."
        )
    else:
        explanation = f"Removed {name}. Labeled comments on those types returned to Unlabeled."
    return {
        "explanation": explanation,
        "comments": _from_dumps(payload.get("deleted_codings") or [], lookup, None, skip_missing=True),
        "quotes": [],
    }


def _deactivate(payload: dict, lookup: HistoryLookup) -> dict:
    name = _name(lookup, payload.get("issue_type_id"), payload.get("name"))
    return {
        "explanation": (
            f"Deactivated {name}. Its children became siblings, "
            "and labeled comments on this type returned to Unlabeled."
        ),
        "comments": _from_dumps(payload.get("deleted_codings") or [], lookup, None, skip_missing=True),
        "quotes": [],
    }


def _merge(payload: dict, lookup: HistoryLookup) -> dict:
    target_id = payload.get("target_id")
    target = _name(lookup, target_id)
    sources = [_name(lookup, item) for item in (payload.get("source_ids") or []) if item != target_id]
    joined = _join(sources) if sources else MISSING_TYPE
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
                    "type_name": _name(lookup, row.get("issue_type_id")),
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


def _one_comment(payload: dict, lookup: HistoryLookup, type_name: str | None) -> list[dict]:
    comment_id = payload.get("comment_id")
    if not comment_id:
        return [{"text": MISSING_COMMENT, "type_name": type_name}]
    text = lookup.comments.get(comment_id)
    if text is None:
        text = MISSING_COMMENT
    return [{"text": text, "type_name": type_name}]


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
        if row.get("issue_type_id"):
            type_name = _name(lookup, row.get("issue_type_id"))
        else:
            type_name = row.get("proposed_issue_name")
        comments.append({"text": text, "type_name": type_name})
    return {
        "explanation": f"Labeled {len(created)} comments with AI.",
        "comments": comments,
        "quotes": [],
    }


def _accept(payload: dict, lookup: HistoryLookup) -> dict:
    type_name = _name(lookup, payload.get("issue_type_id"))
    return {
        "explanation": f"Accepted the label {type_name} for this comment.",
        "comments": _one_comment(payload, lookup, type_name),
        "quotes": [],
    }


def _change(payload: dict, lookup: HistoryLookup) -> dict:
    new_id = (payload.get("coding") or {}).get("issue_type_id")
    new_name = _name(lookup, new_id)
    old_name = None
    for row in payload.get("retired_accepted") or []:
        if row.get("issue_type_id"):
            old_name = _name(lookup, row.get("issue_type_id"))
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


def _drop(payload: dict, lookup: HistoryLookup) -> dict:
    return {
        "explanation": "Dropped this comment.",
        "comments": _one_comment(payload, lookup, None),
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
    "drop": _drop,
}
