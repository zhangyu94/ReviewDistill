from __future__ import annotations

from reviewdistill.extraction.base import ExtractedComment


class LatexCommandExtractor:
    def __init__(self, commands: list[str]):
        self.commands = list(commands)

    def extract(self, source: str, file_path: str) -> list[ExtractedComment]:
        comments, _unstable = self.extract_with_status(source, file_path)
        return comments

    def extract_with_status(self, source: str, file_path: str) -> tuple[list[ExtractedComment], bool]:
        """Return comments, or ([], True) if a configured command is unclosed (unstable file)."""
        comments: list[ExtractedComment] = []
        for command in self.commands:
            needle = "\\" + command + "{"
            start = 0
            while True:
                idx = source.find(needle, start)
                if idx < 0:
                    break
                if idx > 0 and source[idx - 1].isalpha():
                    start = idx + 1
                    continue
                if _in_tex_comment(source, idx):
                    start = idx + 1
                    continue
                body, end = _read_braced(source, idx + len(needle) - 1)
                if body is None:
                    return [], True
                line_number = source.count("\n", 0, idx) + 1
                comments.append(
                    ExtractedComment(
                        source_type="latex_command",
                        source_command=command,
                        file_path=file_path,
                        line_number=line_number,
                        raw_text=_normalize_comment_text(body),
                    )
                )
                start = end
        comments.sort(key=lambda c: (c.line_number, c.source_command))
        return comments, False


def _in_tex_comment(source: str, idx: int) -> bool:
    line_start = source.rfind("\n", 0, idx) + 1
    i = line_start
    while i < idx:
        if source[i] == "\\" and i + 1 < idx:
            i += 2
            continue
        if source[i] == "%":
            return True
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
