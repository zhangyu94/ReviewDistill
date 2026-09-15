from __future__ import annotations

from dataclasses import dataclass

from reviewdistill.extraction.base import ExtractedComment


@dataclass(frozen=True)
class MacroMatch:
    command: str
    start: int
    end: int
    body: str
    in_comment: bool = False


def scan_macros(source: str, commands: list[str]) -> tuple[list[MacroMatch], bool]:
    """Harvest-buffer scan. ``True`` if a live configured command is unclosed."""
    matches: list[MacroMatch] = []
    for command in commands:
        pos = 0
        while True:
            found = find_command_brace(source, command, pos, commands=commands)
            if found is None:
                break
            idx, brace = found
            commented = _in_tex_comment(source, idx, commands)
            body, end = _read_braced(source, brace)
            if body is None:
                if commented:
                    nxt = _next_macro_start(source, idx + 1, commands)
                    end = len(source) if nxt is None else nxt
                    matches.append(MacroMatch(command, idx, end, "", True))
                    pos = end
                    continue
                return [], True
            matches.append(MacroMatch(command, idx, end, body, commented))
            pos = end
    return matches, False


class LatexCommandExtractor:
    def __init__(self, commands: list[str]):
        self.commands = list(commands)

    def extract(self, source: str, file_path: str) -> list[ExtractedComment]:
        comments, _unstable = self.extract_with_status(source, file_path)
        return comments

    def extract_with_status(self, source: str, file_path: str) -> tuple[list[ExtractedComment], bool]:
        """Return comments, or ([], True) if a configured command is unclosed (unstable file)."""
        matches, unstable = scan_macros(source, self.commands)
        if unstable:
            return [], True
        comments = [
            ExtractedComment(
                source_type="latex_command",
                source_command=match.command,
                file_path=file_path,
                line_number=source.count("\n", 0, match.start) + 1,
                raw_text=_normalize_comment_text(match.body),
            )
            for match in sorted(matches, key=lambda match: match.start)
            if not match.in_comment
        ]
        return comments, False


def find_command_brace(
    source: str,
    command: str,
    start: int = 0,
    *,
    commands: list[str] | None = None,
) -> tuple[int, int] | None:
    """Return (backslash index, opening-brace index), or None."""
    needle = "\\" + command
    idx = start
    while True:
        idx = source.find(needle, idx)
        if idx < 0:
            return None
        j = idx + len(needle)
        while j < len(source) and source[j] in " \t":
            j += 1
        if j < len(source) and source[j] == "{":
            return idx, j
        idx += 1


def _opens_configured_command(source: str, brace: int, commands: list[str]) -> bool:
    """True when ``source[brace]`` is ``{`` of a configured ``\\command`` / ``\\command {``."""
    j = brace
    while j > 0 and source[j - 1] in " \t":
        j -= 1
    for command in commands:
        needle = "\\" + command
        start = j - len(needle)
        if start < 0 or source[start:j] != needle:
            continue
        return True
    return False


def _next_macro_start(source: str, start: int, commands: list[str]) -> int | None:
    best: int | None = None
    for command in commands:
        found = find_command_brace(source, command, start, commands=commands)
        if found is None:
            continue
        idx = found[0]
        if best is None or idx < best:
            best = idx
    return best


def _in_tex_comment(source: str, idx: int, commands: list[str]) -> bool:
    """True when ``idx`` sits after a ``%`` that is not inside a configured argument.

    ``%`` inside ``\\yzc{...}`` does not hide a later command, including when the
    argument spans lines and the ``%`` sits on the closer line. ``%`` inside
    ``\\caption{...}`` still comments out ``\\note{old}``.
    """
    i = 0
    stack: list[bool] = []
    while i < idx:
        ch = source[i]
        if ch == "\\" and i + 1 < idx:
            i += 2
            continue
        if ch == "{":
            stack.append(_opens_configured_command(source, i, commands))
            i += 1
            continue
        if ch == "}" and stack:
            stack.pop()
            i += 1
            continue
        if ch == "%" and not any(stack):
            nl = source.find("\n", i)
            if nl < 0 or nl >= idx:
                return True
            i = nl + 1
            continue
        i += 1
    return False


def _read_braced(source: str, open_idx: int) -> tuple[str | None, int]:
    if open_idx >= len(source) or source[open_idx] != "{":
        return None, open_idx
    depth = 0
    i = open_idx
    chars: list[str] = []
    while i < len(source):
        ch = source[i]
        if ch == "\\" and i + 1 < len(source):
            nxt = source[i + 1]
            if nxt in "{}":
                chars.append(nxt)
            else:
                chars.append(ch)
                chars.append(nxt)
            i += 2
            continue
        if ch == "{":
            depth += 1
            if depth > 1:
                chars.append(ch)
            i += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(chars), i + 1
            chars.append(ch)
            i += 1
            continue
        chars.append(ch)
        i += 1
    return None, i


def _normalize_comment_text(text: str) -> str:
    lines = [line.strip() for line in text.strip().splitlines()]
    return " ".join(line for line in lines if line)
