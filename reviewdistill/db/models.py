from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from reviewdistill.errors import CorruptStore

# Presence: ``active`` = in the manuscript, ``pending_disappeared`` = not.
# To distill (working_set) = in the manuscript or verified.

STATUS_ACTIVE = "active"
STATUS_PENDING_DISAPPEARED = "pending_disappeared"

CODING_PROPOSED = "proposed"
CODING_ACCEPTED = "accepted"
CODING_MODIFIED = "modified"

LABEL_ACTIVE = "active"
LABEL_INACTIVE = "inactive"


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_comment_record(data: dict, *, purge_dropped: bool = True) -> dict | None:
    """Map a raw comment dict onto ``verified``. None means purge (dropped)."""
    data = dict(data)
    data.pop("fingerprint", None)
    quality = data.pop("quality", None)
    if quality == "dropped" and purge_dropped:
        return None
    verified = data.get("verified")
    if isinstance(verified, bool):
        return data
    if "verified" in data:
        raise CorruptStore(f"Unknown comment verified {verified!r}")
    if quality == "verified":
        data["verified"] = True
        return data
    if quality in {"unreviewed", "dropped", None}:
        data["verified"] = False
        return data
    raise CorruptStore(f"Unknown comment quality {quality!r}")


def in_manuscript(comment: ProofreadingComment) -> bool:
    return comment.status == STATUS_ACTIVE


def in_working_set(comment: ProofreadingComment) -> bool:
    return in_manuscript(comment) or comment.verified


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
    status: str = "active"
    verified: bool = False
    supersedes_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Coding(SQLModel):
    id: str
    comment_id: str
    label_id: str | None = None
    coder_type: str
    confidence: float | None = None
    rationale: str | None = None
    status: str
    proposed_label_name: str | None = None
    proposed_parent_id: str | None = None  # new-label parent; unknown/inactive → root
    proposed_label_definition: str | None = None
    suggested_evidence: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


def is_labeled(session, comment_id: str) -> bool:
    return any(
        row.status == CODING_ACCEPTED
        and row.label_id
        and (label := session.get(Label, row.label_id)) is not None
        and label.status == LABEL_ACTIVE
        for row in session.find(Coding, comment_id=comment_id)
    )


class Label(SQLModel):
    """Category in the taxonomy. Assignment lives on Coding.label_id."""
    id: str
    name: str
    parent_id: str | None = None  # null = root; must be active when this row is active
    position: int = 0  # sibling order; compacted to 0..n-1
    definition: str
    detection_guidance: str | None = None  # retrieval only; not shown in Label Details
    status: str = "active"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LabelExample(SQLModel):
    id: str
    label_id: str
    text: str
    source_comment_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class TaxonomyEvent(SQLModel):
    """Scheme mutation log (add/rename/move/merge/split/…). Not a Label row."""
    id: str
    event_type: str
    payload_json: str
    undone: bool = False
    created_at: datetime = Field(default_factory=utcnow)
