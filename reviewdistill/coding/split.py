from __future__ import annotations

import json
from dataclasses import dataclass

# LLM divide of a leaf or an empty forest into N ≥ 2 types. The parent stays.
# Assignments become proposed codings. Invalid JSON writes nothing.

SPLIT_TASK = "Task: split these comments into more specific issue types."


@dataclass(frozen=True)
class SplitPlan:
    types: list[dict]
    assignments: list[dict]


@dataclass(frozen=True)
class SplitSummary:
    issues: list
    privacy_warning: str | None


def build_split_prompt(
    *,
    source_name: str | None,
    source_definition: str | None,
    comments,
) -> str:
    lines = [
        "You are assisting qualitative coding of scholarly proofreading comments.",
        "Split the given comments into more specific issue types.",
        "Do not rewrite the source type.",
        "",
    ]
    if source_name:
        lines.extend(
            [
                f"Source issue type: {source_name}",
                f"Definition: {source_definition or '(none)'}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "There is no taxonomy yet. Create an initial set of root issue types.",
                "",
            ]
        )
    lines.append("Comments:")
    for comment in comments:
        lines.append(f"- id={comment.id}")
        lines.append(f"  text: {comment.raw_text}")
        lines.append(f"  context: {comment.context_text or '(none)'}")
        lines.append(f"  section: {comment.section or '(unknown)'}")
    lines.extend(
        [
            "",
            SPLIT_TASK,
            "Return JSON with keys types and assignments.",
            "types is a list of {name, definition}. assignments is a list of {comment_id, type_index}.",
            "Every comment id appears exactly once. type_index is 0-based into types.",
            "Create at least two types. Names and definitions are required and non-empty.",
            "Do not include the source type in types.",
        ]
    )
    return "\n".join(lines)


def parse_split_output(text: str, comment_ids: list[str]) -> SplitPlan:
    start = text.find("{")
    if start < 0:
        raise ValueError("Model output did not contain JSON")
    try:
        data, _end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("Model output did not contain JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Model output did not contain JSON")
    raw_types = data.get("types")
    raw_assign = data.get("assignments")
    if not isinstance(raw_types, list) or not isinstance(raw_assign, list):
        raise ValueError("Split JSON must include types and assignments")
    types = []
    for row in raw_types:
        if not isinstance(row, dict):
            raise ValueError("Each type needs a name and definition")
        name = (row.get("name") or "").strip()
        definition = (row.get("definition") or "").strip()
        if not name or not definition:
            raise ValueError("Each type needs a name and definition")
        types.append({"name": name, "definition": definition})
    by_comment: dict[str, int] = {}
    for row in raw_assign:
        if not isinstance(row, dict):
            raise ValueError("Split is missing a comment assignment")
        comment_id = row.get("comment_id")
        index = row.get("type_index")
        if not isinstance(comment_id, str) or not isinstance(index, int):
            raise ValueError("Split is missing a comment assignment")
        if index < 0 or index >= len(types):
            raise ValueError("Split assignment type_index is out of range")
        if comment_id in by_comment:
            raise ValueError("Split assigned a comment more than once")
        by_comment[comment_id] = index
    expected = set(comment_ids)
    if set(by_comment) != expected:
        raise ValueError("Split JSON is missing a comment assignment")
    used = sorted(set(by_comment.values()))
    if len(used) < 2:
        raise ValueError("Split must produce at least two types")
    remap = {old: new for new, old in enumerate(used)}
    kept = [types[old] for old in used]
    assignments = [
        {"comment_id": comment_id, "type_index": remap[by_comment[comment_id]]}
        for comment_id in comment_ids
    ]
    return SplitPlan(types=kept, assignments=assignments)


def unlabeled_working_comments() -> list:
    """Working-set comments with no accepted active type, including those that already have a proposal."""
    from reviewdistill.db.models import ProofreadingComment, in_working_set, is_labeled
    from reviewdistill.db.session import get_session, init_db

    init_db()
    with get_session() as session:
        return [
            comment
            for comment in session.find(ProofreadingComment, order_by="created_at")
            if in_working_set(comment) and not is_labeled(session, comment.id)
        ]


def _generate(provider, prompt: str, comments) -> tuple[SplitPlan, str | None]:
    import httpx

    from reviewdistill.llm.base import privacy_warning

    warning = None
    if provider.name != "mock" and comments:
        warning = privacy_warning(provider_name=provider.name, comment_count=len(comments))
    try:
        text = provider.generate(prompt)
    except httpx.HTTPError:
        raise
    return parse_split_output(text, [comment.id for comment in comments]), warning


def run_leaf_split(source_id: str, provider=None):
    from reviewdistill.db.models import ISSUE_ACTIVE, IssueType
    from reviewdistill.db.session import get_session, init_db
    from reviewdistill.errors import BadInput, NotFound
    from reviewdistill.llm.base import get_provider
    from reviewdistill.taxonomy.operations import apply_split, list_working_observations
    from reviewdistill.taxonomy.tree import active_children

    init_db()
    with get_session() as session:
        source = session.get(IssueType, source_id)
        if source is None or source.status != ISSUE_ACTIVE:
            raise NotFound(f"Unknown issue type {source_id}")
        if active_children(session.find(IssueType), source_id):
            raise BadInput("Cannot split a type that has children")
        name = source.name
        definition = source.definition
    comments = list_working_observations(source_id)
    if len(comments) < 2:
        raise BadInput("Need at least two labeled comments to split")
    provider = provider or get_provider()
    prompt = build_split_prompt(
        source_name=name,
        source_definition=definition,
        comments=comments,
    )
    plan, warning = _generate(provider, prompt, comments)
    return SplitSummary(
        issues=apply_split(source_id=source_id, plan=plan),
        privacy_warning=warning,
    )


def run_header_split(provider=None):
    from reviewdistill.db.models import ISSUE_ACTIVE, IssueType
    from reviewdistill.db.session import get_session, init_db
    from reviewdistill.errors import BadInput
    from reviewdistill.llm.base import get_provider
    from reviewdistill.taxonomy.operations import apply_split

    init_db()
    with get_session() as session:
        if any(row.status == ISSUE_ACTIVE for row in session.find(IssueType)):
            raise BadInput("Cannot split unlabeled comments while a taxonomy exists")
    comments = unlabeled_working_comments()
    if len(comments) < 2:
        raise BadInput("Need at least two unlabeled comments to split")
    provider = provider or get_provider()
    prompt = build_split_prompt(source_name=None, source_definition=None, comments=comments)
    plan, warning = _generate(provider, prompt, comments)
    return SplitSummary(
        issues=apply_split(source_id=None, plan=plan),
        privacy_warning=warning,
    )
