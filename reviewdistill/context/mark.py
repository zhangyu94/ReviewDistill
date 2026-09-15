"""Prompt-only insertion mark. Stored ``context_text`` stays unmarked TeX.

Bounds match client ``splitContextMark``: a true integer in ``0..len(text)``
inclusive. ``True`` is not ``1``.
"""

from __future__ import annotations

REMARK_TOKEN = "\u2039remark\u203a"


def offset_is_valid(text: str, offset: object) -> bool:
    return isinstance(offset, int) and not isinstance(offset, bool) and 0 <= offset <= len(text)


def splice_remark(text: str, offset: object) -> str:
    if not offset_is_valid(text, offset):
        return text
    index = int(offset)
    return f"{text[:index]}{REMARK_TOKEN}{text[index:]}"
