from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

import httpx

from reviewdistill.coding.retrieval import retrieve_candidates
from reviewdistill.db.models import (
    CODING_PROPOSED,
    LABEL_ACTIVE,
    Coding,
    Label,
    ProofreadingComment,
    in_working_set,
    is_labeled,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.history import dump_row, record
from reviewdistill.llm.base import LLMProvider, get_provider, privacy_warning
from reviewdistill.taxonomy.tree import active_children


@dataclass
class ModelProposal:
    recommendation: str
    label_id: str | None = None
    label_name: str | None = None
    parent_id: str | None = None
    definition: str | None = None
    confidence: float | None = None
    rationale: str | None = None
    suggested_evidence: str | None = None


@dataclass
class CodeSummary:
    coded: int
    skipped: int
    privacy_warning: str | None = None


def parse_model_output(text: str) -> ModelProposal:
    start = text.find("{")
    if start < 0:
        raise ValueError("Model output did not contain JSON")
    try:
        data, _end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("Model output did not contain JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Model output did not contain JSON")
    label_name = _first_text(data.get("label_name"), data.get("name"), data.get("title"))
    nested = data.get("new_label") or data.get("label")
    if isinstance(nested, dict) and not label_name:
        label_name = _first_text(nested.get("label_name"), nested.get("name"), nested.get("title"))
    definition = _first_text(data.get("definition"), data.get("label_definition"))
    if isinstance(nested, dict) and not definition:
        definition = _first_text(nested.get("definition"))
    return ModelProposal(
        recommendation=data.get("recommendation", "new"),
        label_id=data.get("label_id"),
        label_name=label_name,
        parent_id=data.get("parent_id"),
        definition=definition,
        confidence=data.get("confidence"),
        rationale=data.get("rationale"),
        suggested_evidence=data.get("suggested_evidence"),
    )


def _first_text(*values) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def proposal_has_new_label(proposal: ModelProposal) -> bool:
    return bool((proposal.label_name or "").strip())


def build_prompt(*, raw_text: str, context_text: str, section: str | None, candidates) -> str:
    lines = [
        "You are assisting qualitative coding of scholarly proofreading comments.",
        "Distinguish the reviewer's observation from your interpretation.",
        "Do not modify the taxonomy automatically.",
        "",
        "Reviewer observation:",
        raw_text,
        "",
        "Manuscript context:",
        context_text or "(none)",
        "",
        f"Section: {section or '(unknown)'}",
        "",
        "Existing labels:",
    ]
    if not candidates:
        lines.append("(none yet)")
    for label in candidates:
        lines.append(
            f"- id={label.id} name={label.name} parent_id={label.parent_id}"
        )
        lines.append(f"  definition: {label.definition}")
    lines.extend(
        [
            "",
            "Task:",
            "Determine whether this observation is best explained by an existing label.",
            "If so, recommend the best match using recommendation=existing and label_id.",
            "If no existing label adequately captures the observation, propose a candidate new label.",
            "If recommendation is new, label_name and definition are required. Do not omit them.",
            "Return JSON with keys:",
            "recommendation, label_id, label_name, parent_id, definition,",
            "confidence, rationale, suggested_evidence",
        ]
    )
    return "\n".join(lines)


def _proposal_parent_id(session, parent_id: str | None) -> str | None:
    """Keep only an existing active type id. Unknown or omitted → root (None)."""
    if not parent_id:
        return None
    parent = session.get(Label, parent_id)
    if parent is None or parent.status != LABEL_ACTIVE:
        return None
    return parent.id


_UNSET = object()


def is_placeholder_coding(coding: Coding | None) -> bool:
    if coding is None or coding.status != CODING_PROPOSED:
        return False
    name = (coding.proposed_label_name or "").strip()
    rationale = coding.rationale or ""
    return name == "Mock label" or rationale.startswith("Mock provider")


def effective_provider_name() -> str | None:
    try:
        return get_provider().name
    except RuntimeError:
        return None


def hide_placeholder_coding(coding: Coding | None, *, provider_name: str | None) -> bool:
    return is_placeholder_coding(coding) and provider_name != "mock"


def uncoded_comments(*, provider_name: str | None | object = _UNSET) -> list[ProofreadingComment]:
    if provider_name is _UNSET:
        resolved: str | None = effective_provider_name()
    elif isinstance(provider_name, str):
        resolved = provider_name
    else:
        resolved = None
    init_db()
    with get_session() as session:
        comments = [
            comment
            for comment in session.find(ProofreadingComment, order_by="created_at")
            if in_working_set(comment)
        ]
        resolved_ids: set[str] = {
            comment.id for comment in comments if is_labeled(session, comment.id)
        }
        for coding in session.find(Coding):
            if (
                coding.status == CODING_PROPOSED
                and not hide_placeholder_coding(coding, provider_name=resolved)
                and (coding.label_id or (coding.proposed_label_name or "").strip())
            ):
                resolved_ids.add(coding.comment_id)
        return [comment for comment in comments if comment.id not in resolved_ids]


def code_uncoded_comments(provider: LLMProvider | None = None) -> CodeSummary:
    init_db()
    provider = provider or get_provider()
    coded = 0
    skipped = 0
    created: list[dict] = []
    replaced: list[dict] = []
    with get_session():
        comments = uncoded_comments(provider_name=provider.name)
        ranked_by_id = {comment.id: retrieve_candidates(comment) for comment in comments}
    warning = None
    if provider.name != "mock" and comments:
        warning = privacy_warning(provider_name=provider.name, comment_count=len(comments))
        print(warning)
    pending: list[tuple[ProofreadingComment, ModelProposal, str | None]] = []
    for comment in comments:
        ranked = ranked_by_id[comment.id]
        prompt = build_prompt(
            raw_text=comment.raw_text,
            context_text=comment.context_text,
            section=comment.section,
            candidates=[item.label for item in ranked],
        )
        try:
            proposal = parse_model_output(provider.generate(prompt))
        except httpx.HTTPError:
            raise
        except ValueError:
            skipped += 1
            continue
        label_id = proposal.label_id if proposal.recommendation == "existing" else None
        if not label_id and not proposal_has_new_label(proposal):
            skipped += 1
            continue
        pending.append((comment, proposal, label_id))
        coded += 1
    if pending:
        with get_session() as session:
            for comment, proposal, label_id in pending:
                if label_id:
                    label = session.get(Label, label_id)
                    if (
                        label is None
                        or label.status != LABEL_ACTIVE
                        or active_children(session.find(Label), label.id)
                    ):
                        label_id = None
                if not label_id and not proposal_has_new_label(proposal):
                    skipped += 1
                    coded -= 1
                    continue
                for row in list(session.find(Coding, comment_id=comment.id, status=CODING_PROPOSED)):
                    if hide_placeholder_coding(row, provider_name=provider.name):
                        session.delete(row)
                    else:
                        replaced.append(dump_row(row))
                        session.delete(row)
                coding = Coding(
                    id=str(uuid4()),
                    comment_id=comment.id,
                    label_id=label_id,
                    coder_type="ai",
                    confidence=proposal.confidence,
                    rationale=proposal.rationale,
                    status=CODING_PROPOSED,
                    proposed_label_name=proposal.label_name,
                    proposed_parent_id=_proposal_parent_id(session, proposal.parent_id),
                    proposed_label_definition=proposal.definition,
                    suggested_evidence=proposal.suggested_evidence,
                )
                session.add(coding)
                created.append(dump_row(coding))
            record(session, "propose", {"created": created, "replaced": replaced})
            session.commit()
    return CodeSummary(coded=coded, skipped=skipped, privacy_warning=warning)
