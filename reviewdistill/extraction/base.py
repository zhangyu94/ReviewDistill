from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedComment:
    source_type: str
    source_command: str
    file_path: str
    line_number: int
    raw_text: str
