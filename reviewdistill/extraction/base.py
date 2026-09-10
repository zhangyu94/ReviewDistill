from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractedComment:
    source_type: str
    source_command: str
    file_path: str
    line_number: int
    raw_text: str


class CommentExtractor(Protocol):
    def extract(self, source: str, file_path: str) -> list[ExtractedComment]:
        ...
