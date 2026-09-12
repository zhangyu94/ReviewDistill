from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from reviewdistill.errors import CorruptStore

# Presence: ``active`` = in the manuscript, ``pending_disappeared`` = not.
# Quality is a separate field. Working set = not dropped, and (present or verified).

QUALITY_UNREVIEWED = "unreviewed"
QUALITY_VERIFIED = "verified"
QUALITY_DROPPED = "dropped"

STATUS_ACTIVE = "active"
STATUS_PENDING_DISAPPEARED = "pending_disappeared"

CODING_PROPOSED = "proposed"
CODING_ACCEPTED = "accepted"
CODING_MODIFIED = "modified"

ISSUE_ACTIVE = "active"
ISSUE_INACTIVE = "inactive"


def utcnow() -> datetime:
    return datetime.now(UTC)


def comment_quality(comment: ProofreadingComment) -> str:
    quality = comment.quality
    if quality not in {QUALITY_UNREVIEWED, QUALITY_VERIFIED, QUALITY_DROPPED}:
        raise CorruptStore(f"Unknown comment quality {quality!r}")
    return quality


def in_manuscript(comment: ProofreadingComment) -> bool:
    return comment.status == STATUS_ACTIVE


def in_working_set(comment: ProofreadingComment) -> bool:
    if comment_quality(comment) == QUALITY_DROPPED:
        return False
    return in_manuscript(comment) or comment_quality(comment) == QUALITY_VERIFIED


class Project(SQLModel):
    id: str
    name: str
    root_path: str
    created_at: datetime = Field(default_factory=utcnow)


class ProofreadingComment(SQLModel):
    id: str
    project_id: str
    source_type: str
    source_command: str
    file_path: str
    line_number: int
    raw_text: str
    context_text: str = ""
    section: str | None = None
    git_commit: str | None = None
    git_url: str | None = None
    fingerprint: str
    status: str = "active"
    quality: str = "unreviewed"
    supersedes_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Coding(SQLModel):
    id: str
    comment_id: str
    issue_type_id: str | None = None
    coder_type: str
    confidence: float | None = None
    rationale: str | None = None
    status: str
    proposed_issue_code: str | None = None
    proposed_issue_name: str | None = None
    proposed_issue_category: str | None = None
    proposed_issue_definition: str | None = None
    suggested_evidence: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


def is_labeled(session, comment_id: str) -> bool:
    return any(
        row.status == CODING_ACCEPTED and row.issue_type_id
        for row in session.find(Coding, comment_id=comment_id)
    )


class IssueType(SQLModel):
    id: str
    code: str
    name: str
    category: str
    definition: str
    notes: str | None = None
    detection_guidance: str | None = None
    status: str = "active"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class IssueExample(SQLModel):
    id: str
    issue_type_id: str
    text: str
    source_comment_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class IssueCounterexample(SQLModel):
    id: str
    issue_type_id: str
    text: str
    source_comment_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class TaxonomyEvent(SQLModel):
    id: str
    event_type: str
    payload_json: str
    undone: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class GitCommitRecord(SQLModel):
    id: str
    project_id: str
    repository: str
    commit_hash: str
    remote_url: str | None = None
    recorded_at: datetime = Field(default_factory=utcnow)
