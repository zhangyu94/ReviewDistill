from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_RE = re.compile(r"\\(?:sub)*section\*?\{([^}]+)\}")
CITE_RE = re.compile(r"\\cite[t]?(?:\[[^\]]*\])?\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:auto)?ref\{([^}]+)\}")


@dataclass
class ManuscriptContext:
    context_text: str
    section: str | None
    citations: list[str] = field(default_factory=list)
    figure_table_refs: list[str] = field(default_factory=list)


def split_stored_context(context_text: str) -> tuple[str, str]:
    if not context_text:
        return "", ""
    lines = context_text.split("\n")
    last = lines[-1]
    if last.startswith(("Citations:", "Refs:")):
        return "\n".join(lines[:-1]), last
    return context_text, ""


def extract_context(
    source: str, line_number: int, *, command: str | None = None
) -> ManuscriptContext:
    lines = source.splitlines()
    idx = max(0, min(line_number - 1, len(lines) - 1)) if lines else 0
    section = _section_at(lines, idx)
    paragraph = _paragraph_at(lines, idx, command)
    citations = _split_keys(CITE_RE.findall(paragraph))
    refs = _split_keys(REF_RE.findall(paragraph))
    return ManuscriptContext(
        context_text=paragraph,
        section=section,
        citations=citations,
        figure_table_refs=refs,
    )


def _section_at(lines: list[str], idx: int) -> str | None:
    section = None
    subsection = None
    for line in lines[: idx + 1]:
        match = SECTION_RE.search(line)
        if not match:
            continue
        title = match.group(1).strip()
        stripped = line.lstrip()
        if stripped.startswith(r"\subsection"):
            subsection = title
        elif stripped.startswith(r"\section"):
            section = title
            subsection = None
    if section and subsection:
        return f"{section} / {subsection}"
    return section or subsection


def _is_comment_line(line: str, command: str | None) -> bool:
    if not command:
        return False
    return f"\\{command}{{" in line


def _is_structural_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith((r"\section", r"\subsection", r"\label"))


def _blocks(lines: list[str]) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if not lines[i].strip():
            i += 1
            continue
        start = i
        while i + 1 < n and lines[i + 1].strip():
            i += 1
        blocks.append((start, i))
        i += 1
    return blocks


def _section_bounds(lines: list[str], idx: int) -> tuple[int, int]:
    start = 0
    for i, line in enumerate(lines[: idx + 1]):
        if line.lstrip().startswith(r"\section"):
            start = i
    end = len(lines)
    for i, line in enumerate(lines[idx + 1 :], start=idx + 1):
        if line.lstrip().startswith(r"\section"):
            end = i
            break
    return start, end


def _join_lines(lines: list[str], start: int, end: int, command: str | None) -> str:
    parts = [
        line.rstrip()
        for line in lines[start : end + 1]
        if not _is_comment_line(line, command)
    ]
    while parts and not parts[0].strip():
        parts.pop(0)
    while parts and not parts[-1].strip():
        parts.pop()
    return "\n".join(parts)


def _block_has_prose(lines: list[str], start: int, end: int, command: str | None) -> bool:
    for i in range(start, end + 1):
        if not lines[i].strip() or _is_comment_line(lines[i], command):
            continue
        if not _is_structural_line(lines[i]):
            return True
    return False


def _paragraph_at(lines: list[str], idx: int, command: str | None) -> str:
    if not lines:
        return ""
    sec_start, sec_end = _section_bounds(lines, idx)
    blocks = [(s, e) for s, e in _blocks(lines) if e >= sec_start and s < sec_end]
    if not blocks:
        return ""
    bi = 0
    for i, (start, end) in enumerate(blocks):
        if start <= idx <= end:
            bi = i
            break
        if idx < start:
            bi = i
            break
    else:
        bi = len(blocks) - 1
    start, end = blocks[bi]
    own = _join_lines(lines, start, end, command)
    if _block_has_prose(lines, start, end, command):
        return own
    chunks: list[str] = []
    if bi > 0:
        ps, pe = blocks[bi - 1]
        chunks.append(_join_lines(lines, ps, pe, command))
    if own:
        chunks.append(own)
    for k in range(1, 3):
        if bi + k >= len(blocks):
            break
        ns, ne = blocks[bi + k]
        chunks.append(_join_lines(lines, ns, ne, command))
        if _block_has_prose(lines, ns, ne, command):
            break
    return "\n\n".join(chunk for chunk in chunks if chunk)


def _split_keys(groups: list[str]) -> list[str]:
    keys: list[str] = []
    for group in groups:
        for key in group.split(","):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
    return keys

