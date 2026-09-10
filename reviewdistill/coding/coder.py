from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

import httpx
from sqlmodel import select

from reviewdistill.coding.retrieval import retrieve_candidates
from reviewdistill.db.models import WORKING_COMMENT_STATUSES, Coding, ProofreadingComment
from reviewdistill.db.session import get_session, init_db
from reviewdistill.history import dump_row, record
from reviewdistill.llm.base import LLMProvider, get_provider, privacy_warning


@dataclass
class ModelProposal:
    recommendation: str
    issue_type_id: str | None = None
    issue_code: str | None = None
    issue_name: str | None = None
    category: str | None = None
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
    return ModelProposal(
        recommendation=data.get("recommendation", "new"),
        issue_type_id=data.get("issue_type_id"),
        issue_code=data.get("issue_code"),
        issue_name=data.get("issue_name"),
        category=data.get("category"),
        definition=data.get("definition"),
        confidence=data.get("confidence"),
        rationale=data.get("rationale"),
        suggested_evidence=data.get("suggested_evidence"),
    )


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
        "Existing issue types:",
    ]
    if not candidates:
        lines.append("(none yet)")
    for issue in candidates:
        lines.append(f"- id={issue.id} code={issue.code} name={issue.name} category={issue.category}")
        lines.append(f"  definition: {issue.definition}")
    lines.extend(
        [
            "",
            "Task:",
            "Determine whether this observation is best explained by an existing issue type.",
            "If so, recommend the best match using recommendation=existing and issue_type_id.",
            "If no existing issue type adequately captures the observation, propose a candidate new issue type.",
            "Return JSON with keys:",
            "recommendation, issue_type_id, issue_code, issue_name, category, definition,",
            "confidence, rationale, suggested_evidence",
        ]
    )
    return "\n".join(lines)


_UNSET = object()


def is_placeholder_coding(coding: Coding | None) -> bool:
    if coding is None or coding.status != "proposed":
        return False
    name = (coding.proposed_issue_name or "").strip()
    rationale = coding.rationale or ""
    return name == "Mock issue" or rationale.startswith("Mock provider")


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
        comments = list(
            session.exec(
                select(ProofreadingComment).where(
                    ProofreadingComment.status.in_(WORKING_COMMENT_STATUSES)
                )
            )
        )
        resolved_ids: set[str] = set()
        for coding in session.exec(select(Coding)):
            if coding.status in {"accepted", "rejected", "modified"}:
                resolved_ids.add(coding.comment_id)
            elif coding.status == "proposed" and not hide_placeholder_coding(
                coding, provider_name=resolved
            ):
                resolved_ids.add(coding.comment_id)
        return [comment for comment in comments if comment.id not in resolved_ids]


def code_uncoded_comments(provider: LLMProvider | None = None) -> CodeSummary:
    init_db()
    provider = provider or get_provider()
    comments = uncoded_comments(provider_name=provider.name)
    warning = None
    if provider.name != "mock" and comments:
        warning = privacy_warning(provider_name=provider.name, comment_count=len(comments))
        print(warning)
    coded = 0
    skipped = 0
    created: list[dict] = []
    replaced: list[dict] = []
    for comment in comments:
        ranked = retrieve_candidates(comment)
        prompt = build_prompt(
            raw_text=comment.raw_text,
            context_text=comment.context_text,
            section=comment.section,
            candidates=[item.issue for item in ranked],
        )
        try:
            proposal = parse_model_output(provider.generate(prompt))
        except httpx.HTTPError:
            raise
        except ValueError:
            skipped += 1
            continue
        issue_type_id = proposal.issue_type_id if proposal.recommendation == "existing" else None
        if issue_type_id:
            from reviewdistill.taxonomy.operations import get_issue_type

            if get_issue_type(issue_type_id) is None:
                issue_type_id = None
        with get_session() as session:
            for row in list(
                session.exec(
                    select(Coding).where(
                        Coding.comment_id == comment.id,
                        Coding.status == "proposed",
                    )
                )
            ):
                if hide_placeholder_coding(row, provider_name=provider.name):
                    session.delete(row)
                else:
                    replaced.append(dump_row(row))
                    session.delete(row)
            coding = Coding(
                id=str(uuid4()),
                comment_id=comment.id,
                issue_type_id=issue_type_id,
                coder_type="ai",
                confidence=proposal.confidence,
                rationale=proposal.rationale,
                status="proposed",
                proposed_issue_code=proposal.issue_code,
                proposed_issue_name=proposal.issue_name,
                proposed_issue_category=proposal.category,
                proposed_issue_definition=proposal.definition,
                suggested_evidence=proposal.suggested_evidence,
            )
            session.add(coding)
            session.commit()
            session.refresh(coding)
            created.append(dump_row(coding))
        coded += 1
    if created:
        with get_session() as session:
            record(session, "propose", {"created": created, "replaced": replaced})
            session.commit()
    return CodeSummary(coded=coded, skipped=skipped, privacy_warning=warning)
