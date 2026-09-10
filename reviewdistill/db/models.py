from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

WORKING_COMMENT_STATUSES = ("active", "kept")  # AI coding, cluster, export; pending_disappeared is workbench Disappeared only


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(primary_key=True)
    name: str
    root_path: str
    created_at: datetime = Field(default_factory=utcnow)


class ProofreadingComment(SQLModel, table=True):
    __tablename__ = "comments"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True)
    source_type: str
    source_command: str
    file_path: str
    line_number: int
    raw_text: str
    context_text: str = ""
    section: str | None = None
    git_commit: str | None = None
    git_url: str | None = None
    fingerprint: str = Field(index=True)
    status: str = Field(default="active", index=True)
    supersedes_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Coding(SQLModel, table=True):
    __tablename__ = "codings"

    id: str = Field(primary_key=True)
    comment_id: str = Field(index=True)
    issue_type_id: str | None = Field(default=None, index=True)
    coder_type: str
    confidence: float | None = None
    rationale: str | None = None
    status: str = Field(index=True)
    proposed_issue_code: str | None = None
    proposed_issue_name: str | None = None
    proposed_issue_category: str | None = None
    proposed_issue_definition: str | None = None
    suggested_evidence: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class IssueType(SQLModel, table=True):
    __tablename__ = "issue_types"

    id: str = Field(primary_key=True)
    code: str = Field(index=True)
    name: str
    category: str
    definition: str
    notes: str | None = None
    detection_guidance: str | None = None
    status: str = Field(default="active", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class IssueExample(SQLModel, table=True):
    __tablename__ = "issue_examples"

    id: str = Field(primary_key=True)
    issue_type_id: str = Field(index=True)
    text: str
    source_comment_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class IssueCounterexample(SQLModel, table=True):
    __tablename__ = "issue_counterexamples"

    id: str = Field(primary_key=True)
    issue_type_id: str = Field(index=True)
    text: str
    source_comment_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class TaxonomyEvent(SQLModel, table=True):
    __tablename__ = "taxonomy_events"

    id: str = Field(primary_key=True)
    event_type: str
    payload_json: str
    undone: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)


class GitCommitRecord(SQLModel, table=True):
    __tablename__ = "git_commits"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True)
    repository: str
    commit_hash: str
    remote_url: str | None = None
    recorded_at: datetime = Field(default_factory=utcnow)
