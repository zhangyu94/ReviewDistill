from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

WORKING_COMMENT_STATUSES = ("active", "kept")  # AI coding, cluster, export; pending_disappeared is workbench Disappeared only

_STATUS_ALIASES = {
    "deleted": "pending_disappeared",
    "modified": "superseded",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def migrate_comment_status(status: str) -> str:
    return _STATUS_ALIASES.get(status, status)


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
