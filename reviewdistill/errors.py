"""Domain errors. HTTP maps these by type, not message prefix."""


class ReviewDistillError(ValueError):
    """Base for store and domain failures. Subclasses ``ValueError`` so existing tests still match."""


class NotFound(ReviewDistillError):
    """Missing comment, label, or project."""


class Conflict(ReviewDistillError):
    """Duplicate name, already labeled, or similar."""


class BadInput(ReviewDistillError):
    """Malformed request or impossible command (bad export format, nothing to undo)."""


class CorruptStore(ReviewDistillError):
    """On-disk JSONL cannot be loaded or a row violates an invariant."""
