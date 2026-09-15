"""Insertion-neighborhood context for a comment. No LLM, no whole-paper search.

Pipeline: scan_macros on the raw harvest buffer → strip those spans
(including ``%``-commented macros and an unclosed ``% \\command{`` through the
next configured command) → drop_percent_tails → blank_line_blocks
(a heading token ends the neighborhood, even mid-line after leftover) →
if the chosen span is empty after strip, walk up while empty → join_source.
Finding macros on the raw file keeps a ``}`` after ``%`` (same as harvest).
``_blocks`` / ``_is_structural_line`` are aliases for skill-eval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from reviewdistill.extraction.latex import scan_macros

SECTION_RE = re.compile(r"\\(?:sub)*section\*?\{([^}]+)\}")


@dataclass
class ManuscriptContext:
    context_text: str
    section: str | None


def extract_context(
    source: str,
    line_number: int,
    *,
    commands: list[str] | None = None,
    command: str | None = None,
) -> ManuscriptContext:
    raw_lines = source.splitlines()
    cmds = list(commands) if commands else ([command] if command else [])
    if not raw_lines:
        return ManuscriptContext("", None)
    idx = max(0, min(line_number - 1, len(raw_lines) - 1))
    glue = _lines_inside_macros(raw_lines, cmds)
    stripped = strip_comment_macros(raw_lines, cmds) if cmds else list(raw_lines)
    neighborhood = drop_percent_tails(stripped)
    stops: set[int] = set()
    if cmds:
        neighborhood, stops = _drop_post_macro_headings(raw_lines, neighborhood, cmds)
    return ManuscriptContext(
        context_text=choose_anchor(neighborhood, idx, glue=glue, stop=stops),
        section=_section_at(neighborhood, idx),
    )


def _section_at(lines: list[str], idx: int) -> str | None:
    section = None
    subsection = None
    for line in lines[: idx + 1]:
        if not is_structural_line(line):
            continue
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


_SECTIONING = (
    r"\chapter",
    r"\part",
    r"\section",
    r"\subsection",
    r"\subsubsection",
    r"\paragraph",
    r"\subparagraph",
)


def drop_percent_tails(lines: list[str]) -> list[str]:
    return [_drop_percent_tail(line) for line in lines]


def _drop_percent_tail(line: str) -> str:
    i = 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            i += 2
            continue
        if line[i] == "%":
            return line[:i]
        i += 1
    return line


def blank_line_blocks(
    lines: list[str],
    *,
    glue: set[int] | frozenset[int] | None = None,
    stop: set[int] | frozenset[int] | None = None,
) -> list[tuple[int, int]]:
    """Consecutive non-blank lines. ``glue`` lines stay in a block even if blank
    (used for empty lines that sit inside a ``\\command{...}`` argument).
    ``stop`` lines end the block (leftover heading after a stripped macro)."""
    sticky = glue or frozenset()
    stops = stop or frozenset()

    def filled(i: int) -> bool:
        return bool(lines[i].strip()) or i in sticky

    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if not filled(i):
            i += 1
            continue
        start = i
        if start in stops:
            blocks.append((start, start))
            i += 1
            continue
        while i + 1 < n and filled(i + 1):
            nxt = i + 1
            if is_structural_line(lines[nxt]) and nxt not in sticky:
                break
            if is_structural_line(lines[start]) and not is_structural_line(lines[nxt]):
                break
            i += 1
            if i in stops:
                break
        blocks.append((start, i))
        i += 1
    return blocks


def _structural_command_index(line: str) -> int | None:
    """Byte index of the first sectioning command or ``\\label``, or None."""
    i = 0
    names = (r"\label",) + _SECTIONING
    while i < len(line):
        if line[i] != "\\":
            i += 1
            continue
        for cmd in names:
            if not line.startswith(cmd, i):
                continue
            rest = line[i + len(cmd) : i + len(cmd) + 1]
            if rest.isalpha():
                continue
            return i
        i += 1
    return None


def is_structural_line(line: str) -> bool:
    """True when the line is a sectioning command or ``\\label`` (optional leading space)."""
    idx = _structural_command_index(line)
    return idx is not None and not line[:idx].strip()


def _drop_post_macro_headings(
    raw: list[str],
    lines: list[str],
    commands: list[str],
) -> tuple[list[str], set[int]]:
    """Blank a heading that sits after ``}`` on the closer line. That line ends the block."""
    text = "\n".join(raw)
    matches, _unstable = scan_macros(text, commands)
    out = list(lines)
    stops: set[int] = set()
    for match in matches:
        if match.in_comment or match.end <= match.start:
            continue
        last = text.count("\n", 0, match.end - 1)
        nl = text.find("\n", match.end)
        leftover = _drop_percent_tail(text[match.end : len(text) if nl < 0 else nl])
        rel = _structural_command_index(leftover)
        if rel is None or last >= len(out):
            continue
        at = match.end + rel
        if any(other.start <= at < other.end for other in matches):
            continue
        stops.add(last)
        heading = _structural_token(leftover, rel)
        pos = out[last].rfind(heading) if heading else -1
        if pos >= 0:
            out[last] = out[last][:pos]
        elif is_structural_line(out[last]):
            out[last] = ""
    return out, stops


def _structural_token(line: str, idx: int) -> str:
    """``\\subsection{B}`` / ``\\label{x}`` starting at ``idx``, not the rest of the line."""
    j = idx + 1
    while j < len(line) and line[j].isalpha():
        j += 1
    if j < len(line) and line[j] == "*":
        j += 1
    while j < len(line) and line[j] in " \t":
        j += 1
    if j >= len(line) or line[j] != "{":
        return line[idx:j]
    depth = 0
    k = j
    while k < len(line):
        if line[k] == "{":
            depth += 1
        elif line[k] == "}":
            depth -= 1
            if depth == 0:
                return line[idx : k + 1]
        k += 1
    return line[idx:]


def strip_comment_macros(lines: list[str], commands: list[str]) -> list[str]:
    """Remove configured ``\\command{...}`` bodies. Keep the rest of each line."""
    text = "\n".join(lines)
    chars = list(text)
    matches, _unstable = scan_macros(text, commands)
    for match in matches:
        for i in range(match.start, match.end):
            if chars[i] != "\n":
                chars[i] = ""
    return "".join(chars).split("\n")


def join_source(lines: list[str], start: int, end: int) -> str:
    parts = [lines[i].rstrip() for i in range(start, end + 1)]
    while parts and not parts[0].strip():
        parts.pop(0)
    while parts and not parts[-1].strip():
        parts.pop()
    return "\n".join(parts)


def _block_is_structural(lines: list[str], start: int, end: int) -> bool:
    """True when every non-blank line is structural. A heading that shares a block with sentences is prose."""
    return all(
        is_structural_line(lines[i])
        for i in range(start, end + 1)
        if lines[i].strip()
    )


def _block_index_at_or_above(blocks: list[tuple[int, int]], idx: int) -> int | None:
    for i, (start, end) in enumerate(blocks):
        if start <= idx <= end:
            return i
    above = [i for i, (_s, end) in enumerate(blocks) if end < idx]
    return above[-1] if above else None


def _lines_inside_macros(lines: list[str], commands: list[str]) -> set[int]:
    """Line indexes that overlap a complete ``\\command{...}`` (argument blanks included)."""
    if not commands:
        return set()
    text = "\n".join(lines)
    matches, _unstable = scan_macros(text, commands)
    stripped = strip_comment_macros(lines, commands)
    inside: set[int] = set()
    for match in matches:
        if match.in_comment or match.end <= match.start:
            continue
        first = text.count("\n", 0, match.start)
        last = text.count("\n", 0, match.end - 1)
        if first == last:
            continue
        # Glue only when the opener still has prose after every configured macro is gone.
        if first < len(stripped) and stripped[first].strip():
            inside.update(range(first, last + 1))
    return inside


def _block_text(lines: list[str], start: int, end: int) -> str:
    return join_source(lines, start, end)


def choose_anchor(
    lines: list[str],
    idx: int,
    *,
    commands: list[str] | None = None,
    glue: set[int] | frozenset[int] | None = None,
    stop: set[int] | frozenset[int] | None = None,
) -> str:
    cmds = list(commands) if commands else []
    if glue is None:
        glue = _lines_inside_macros(lines, cmds)
    if cmds:
        lines = strip_comment_macros(lines, cmds)
    blocks = blank_line_blocks(lines, glue=glue, stop=stop)
    if not blocks:
        return ""
    bi = _block_index_at_or_above(blocks, idx)
    if bi is None:
        return ""

    def text_at(i: int) -> str:
        return _block_text(lines, *blocks[i])

    while bi >= 0 and not text_at(bi):
        bi -= 1
    if bi < 0:
        return ""
    start, end = blocks[bi]
    if start <= idx <= end:
        return text_at(bi)
    if not _block_is_structural(lines, start, end):
        return text_at(bi)
    chosen: list[int] = []
    k = bi
    while k >= 0:
        if not text_at(k):
            k -= 1
            continue
        if not _block_is_structural(lines, *blocks[k]):
            break
        chosen.append(k)
        k -= 1
    if not chosen:
        return ""
    chosen.reverse()
    parts = [text_at(chosen[0])]
    for i in range(1, len(chosen)):
        prev_end = blocks[chosen[i - 1]][1]
        this_start = blocks[chosen[i]][0]
        sep = "\n" if this_start == prev_end + 1 else "\n\n"
        parts.append(sep)
        parts.append(text_at(chosen[i]))
    return "".join(parts)


_blocks = blank_line_blocks
_is_structural_line = is_structural_line

