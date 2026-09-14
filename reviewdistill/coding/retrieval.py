from __future__ import annotations

import re
from dataclasses import dataclass

from reviewdistill.db.models import IssueType, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import list_active_issue_types, list_examples
from reviewdistill.taxonomy.tree import active_children

TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class RankedIssue:
    id: str
    issue: IssueType
    score: float


def retrieve_candidates(comment: ProofreadingComment, limit: int = 5) -> list[RankedIssue]:
    """Rank active issue types by lexical token overlap. No embeddings."""
    query_tokens = _tokens(f"{comment.raw_text} {comment.context_text}")
    if not query_tokens:
        return []
    ranked: list[RankedIssue] = []
    with get_session():
        active = list_active_issue_types()
        for issue in active:
            if active_children(active, issue.id):
                continue
            example_text = " ".join(example.text for example in list_examples(issue.id))
            doc_tokens = _tokens(
                f"{issue.name} {issue.definition} {issue.detection_guidance or ''} {example_text}"
            )
            score = _overlap(query_tokens, doc_tokens)
            if score > 0:
                ranked.append(RankedIssue(id=issue.id, issue=issue, score=score))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def _tokens(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(text.lower()) if len(token) > 2}


def _overlap(query: set[str], doc: set[str]) -> float:
    if not query or not doc:
        return 0.0
    inter = len(query & doc)
    union = len(query | doc)
    return inter / union
