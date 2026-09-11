"""Idempotent extract: match source comments to stored observations.

Behavior: ``docs/comment-identity.md``. CLI extract (including ``--watch``) calls ``extract_project``.

Per stable ``.tex`` file: pair exact fingerprints in file order, then
``difflib.SequenceMatcher`` on leftovers (revision if similar and same command,
else absent + new). Then cross-file exact-fingerprint moves, then resurrect
absent rows, then new vs absent. Unclosed comment braces skip
that file only. Never deletes rows; never Verify/Drops (except a wording
revision clears ``verified`` to ``unreviewed``); never AI-labels.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

from reviewdistill.config import load_project_config
from reviewdistill.context.manuscript import extract_context
from reviewdistill.db.models import GitCommitRecord, Project, ProofreadingComment, comment_quality
from reviewdistill.db.session import get_session, init_db
from reviewdistill.extraction.base import ExtractedComment
from reviewdistill.extraction.latex import LatexCommandExtractor
from reviewdistill.gitinfo import GitMetadata, read_git_metadata

SKIP_TEX_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    ".idea",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".hypothesis",
    ".reviewdistill",
    "dist",
    "build",
}


@dataclass
class ExtractSummary:
    added: int = 0
    unchanged: int = 0
    revised: int = 0
    moved: int = 0
    disappeared: int = 0
    resurrected: int = 0
    skipped_unstable: int = 0


@dataclass
class _Pending:
    source_type: str
    source_command: str
    file_path: str
    line_number: int
    raw_text: str
    fingerprint: str


class _NeverEq:
    def __init__(self, index: int):
        self.index = index

    def __eq__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return id(self)


def fingerprint_for(source_command: str, raw_text: str) -> str:
    normalized = " ".join(raw_text.split())
    payload = f"{source_command}\0{normalized}".encode()
    return hashlib.sha256(payload).hexdigest()


# Expansion is the shorter core's tokens as a prefix or suffix of the longer, not a mid-string
# substring ("ok" in "This is ok here."). Short cores need a minimum length so "Too." is not
# a revision of "Too long.". Short distinct remarks often have SequenceMatcher ratio >= 0.5.
# Typos of similar length need a much higher ratio.
SIMILARITY_THRESHOLD = 0.5
TYPO_RATIO_THRESHOLD = 0.9
TYPO_LENGTH_RATIO = 0.8
MIN_CORE_LENGTH = 6
MIN_EXPANSION_TOKENS = 2


def _token_affix(short_tokens: list[str], long_tokens: list[str]) -> bool:
    n = len(short_tokens)
    if n == 0 or n > len(long_tokens):
        return False
    return long_tokens[:n] == short_tokens or long_tokens[-n:] == short_tokens


def similar_text(a: str, b: str) -> bool:
    left = " ".join(a.split())
    right = " ".join(b.split())
    if not left or not right:
        return False
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    core_short = shorter.rstrip(".,;:!?")
    core_long = longer.rstrip(".,;:!?")
    short_tokens = core_short.casefold().split()
    long_tokens = core_long.casefold().split()
    extra = len(long_tokens) - len(short_tokens)
    if _token_affix(short_tokens, long_tokens) and (
        len(core_short) >= MIN_CORE_LENGTH or extra >= MIN_EXPANSION_TOKENS
    ):
        return True
    ratio = SequenceMatcher(None, left.casefold(), right.casefold()).ratio()
    if ratio < SIMILARITY_THRESHOLD:
        return False
    return len(shorter) / len(longer) >= TYPO_LENGTH_RATIO and ratio >= TYPO_RATIO_THRESHOLD


def format_extract_summary(summary: ExtractSummary) -> str:
    return (
        "Extracted comments: "
        f"{summary.added} added, {summary.unchanged} unchanged, "
        f"{summary.revised} revised, {summary.moved} moved, "
        f"{summary.disappeared} disappeared, {summary.resurrected} resurrected, "
        f"{summary.skipped_unstable} skipped"
    )


def extract_project(root: Path) -> ExtractSummary:
    init_db()
    root = root.resolve()
    config = load_project_config(root)
    git = read_git_metadata(root)
    extractor = LatexCommandExtractor(config.latex_commands)
    by_file, skipped = _extract_all_tex(root, extractor)
    skipped_set = set(skipped)
    summary = ExtractSummary(skipped_unstable=len(skipped))

    with get_session() as session:
        project = session.get(Project, config.id)
        if project is None:
            session.add(Project(id=config.id, name=config.name, root_path=str(root)))
        else:
            project.root_path = str(root)
            project.name = config.name

        if git.repository and git.commit_hash:
            exists = session.first(
                GitCommitRecord,
                project_id=config.id,
                commit_hash=git.commit_hash,
            )
            if exists is None:
                session.add(
                    GitCommitRecord(
                        id=str(uuid4()),
                        project_id=config.id,
                        repository=git.repository,
                        commit_hash=git.commit_hash,
                        remote_url=git.remote_url,
                    )
                )

        existing = session.find(ProofreadingComment, project_id=config.id)
        present = [
            row
            for row in existing
            if row.status == "active" and row.file_path not in skipped_set
        ]
        leftover_db: list[ProofreadingComment] = []
        leftover_ex: list[_Pending] = []
        files = sorted(set(by_file) | {row.file_path for row in present})
        for path in files:
            d_rows = [row for row in present if row.file_path == path]
            d_rows.sort(key=lambda row: (row.line_number, row.id))
            e_rows = list(by_file.get(path, []))
            paired, d_left, e_left = _pair_exact_fingerprints(d_rows, e_rows)
            for row, pending in paired:
                _apply_source(row, pending, root, git, update_text=False)
                summary.unchanged += 1
            d_unmatched, e_unmatched = _pass_b(d_left, e_left, root, git, summary)
            leftover_db.extend(d_unmatched)
            leftover_ex.extend(e_unmatched)

        moved, leftover_db, leftover_ex = _pair_cross_file(leftover_db, leftover_ex)
        for row, pending in moved:
            _apply_source(row, pending, root, git, update_text=False)
            summary.moved += 1

        still_ex: list[_Pending] = []
        resurrected_ids: set[str] = set()
        for pending in leftover_ex:
            candidate = _resurrect_candidate(existing, pending.fingerprint, resurrected_ids)
            if candidate is None:
                still_ex.append(pending)
                continue
            candidate.status = "active"
            _apply_source(candidate, pending, root, git, update_text=True)
            resurrected_ids.add(candidate.id)
            summary.resurrected += 1

        for pending in still_ex:
            session.add(_to_row(config.id, pending, root, git))
            summary.added += 1

        for row in leftover_db:
            if row.id in resurrected_ids:
                continue
            row.status = "pending_disappeared"
            summary.disappeared += 1

        session.commit()
    return summary


def _extract_all_tex(
    root: Path, extractor: LatexCommandExtractor
) -> tuple[dict[str, list[_Pending]], list[str]]:
    by_file: dict[str, list[_Pending]] = {}
    skipped: list[str] = []
    for path in sorted(root.rglob("*.tex")):
        if any(part in SKIP_TEX_DIR_NAMES for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        source = path.read_text(errors="replace")
        comments, unstable = extractor.extract_with_status(source, file_path=rel)
        if unstable:
            skipped.append(rel)
            continue
        by_file[rel] = [_pending_from(comment) for comment in comments]
    return by_file, skipped


def _pending_from(comment: ExtractedComment) -> _Pending:
    return _Pending(
        source_type=comment.source_type,
        source_command=comment.source_command,
        file_path=comment.file_path,
        line_number=comment.line_number,
        raw_text=comment.raw_text,
        fingerprint=fingerprint_for(comment.source_command, comment.raw_text),
    )


def _context_fields(root: Path, pending: _Pending) -> tuple[str, str | None]:
    source = (root / pending.file_path).read_text(errors="replace")
    ctx = extract_context(source, pending.line_number, command=pending.source_command)
    extra = []
    if ctx.citations:
        extra.append("Citations: " + ", ".join(ctx.citations))
    if ctx.figure_table_refs:
        extra.append("Refs: " + ", ".join(ctx.figure_table_refs))
    context_text = ctx.context_text
    if extra:
        context_text = context_text + "\n" + " | ".join(extra)
    return context_text, ctx.section


def _apply_source(
    row: ProofreadingComment, pending: _Pending, root: Path, git: GitMetadata, *, update_text: bool
) -> None:
    row.file_path = pending.file_path
    row.line_number = pending.line_number
    row.git_commit = git.commit_hash
    row.git_url = git.remote_url
    row.context_text, row.section = _context_fields(root, pending)
    if update_text:
        text_changed = row.fingerprint != pending.fingerprint
        row.raw_text = pending.raw_text
        row.fingerprint = pending.fingerprint
        row.source_command = pending.source_command
        row.source_type = pending.source_type
        if text_changed and comment_quality(row) == "verified":
            row.quality = "unreviewed"


def _to_row(project_id: str, comment: _Pending, root: Path, git: GitMetadata) -> ProofreadingComment:
    context_text, section = _context_fields(root, comment)
    return ProofreadingComment(
        id=str(uuid4()),
        project_id=project_id,
        source_type=comment.source_type,
        source_command=comment.source_command,
        file_path=comment.file_path,
        line_number=comment.line_number,
        raw_text=comment.raw_text,
        context_text=context_text,
        section=section,
        git_commit=git.commit_hash,
        git_url=git.remote_url,
        fingerprint=comment.fingerprint,
        status="active",
        quality="unreviewed",
    )


def _pair_exact_fingerprints(
    db_rows: list[ProofreadingComment], ex_rows: list[_Pending]
) -> tuple[list[tuple[ProofreadingComment, _Pending]], list[ProofreadingComment], list[_Pending]]:
    db_by: dict[str, list[ProofreadingComment]] = defaultdict(list)
    for row in db_rows:
        db_by[row.fingerprint].append(row)
    ex_by: dict[str, list[_Pending]] = defaultdict(list)
    for pending in ex_rows:
        ex_by[pending.fingerprint].append(pending)
    paired: list[tuple[ProofreadingComment, _Pending]] = []
    leftover_db: list[ProofreadingComment] = []
    leftover_ex: list[_Pending] = []
    for fingerprint in set(db_by) | set(ex_by):
        ds = db_by.get(fingerprint, [])
        es = ex_by.get(fingerprint, [])
        n = min(len(ds), len(es))
        for i in range(n):
            paired.append((ds[i], es[i]))
        leftover_db.extend(ds[n:])
        leftover_ex.extend(es[n:])
    leftover_db.sort(key=lambda row: (row.line_number, row.id))
    leftover_ex.sort(key=lambda pending: (pending.line_number, pending.source_command))
    return paired, leftover_db, leftover_ex


def _pass_b(
    d_left: list[ProofreadingComment],
    e_left: list[_Pending],
    root: Path,
    git: GitMetadata,
    summary: ExtractSummary,
) -> tuple[list[ProofreadingComment], list[_Pending]]:
    unmatched_d: list[ProofreadingComment] = []
    unmatched_e: list[_Pending] = []
    matcher = SequenceMatcher(
        a=[_NeverEq(i) for i in range(len(d_left))],
        b=[_NeverEq(j) for j in range(len(e_left))],
        autojunk=False,
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                row = d_left[i1 + k]
                pending = e_left[j1 + k]
                if row.source_command == pending.source_command and similar_text(row.raw_text, pending.raw_text):
                    _apply_source(row, pending, root, git, update_text=True)
                    summary.revised += 1
                else:
                    unmatched_d.append(row)
                    unmatched_e.append(pending)
            unmatched_d.extend(d_left[i1 + n : i2])
            unmatched_e.extend(e_left[j1 + n : j2])
            continue
        if tag == "delete":
            unmatched_d.extend(d_left[i1:i2])
            continue
        if tag == "insert":
            unmatched_e.extend(e_left[j1:j2])
    return unmatched_d, unmatched_e


def _pair_cross_file(
    leftover_db: list[ProofreadingComment], leftover_ex: list[_Pending]
) -> tuple[list[tuple[ProofreadingComment, _Pending]], list[ProofreadingComment], list[_Pending]]:
    leftover_db = sorted(leftover_db, key=lambda row: (row.fingerprint, row.file_path, row.line_number, row.id))
    leftover_ex = sorted(
        leftover_ex, key=lambda pending: (pending.fingerprint, pending.file_path, pending.line_number, pending.source_command)
    )
    return _pair_exact_fingerprints(leftover_db, leftover_ex)


def _resurrect_candidate(
    existing: list[ProofreadingComment], fingerprint: str, used_ids: set[str]
) -> ProofreadingComment | None:
    candidates = [
        row
        for row in existing
        if row.fingerprint == fingerprint
        and row.status != "active"
        and row.id not in used_ids
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda row: row.id)
    candidates.sort(key=lambda row: row.created_at, reverse=True)
    return candidates[0]
