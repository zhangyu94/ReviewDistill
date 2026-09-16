import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "website" / "docs"


def _sidebar_ids() -> list[str]:
    text = (ROOT / "website" / "sidebars.ts").read_text(encoding="utf-8")
    ids: list[str] = []
    for block in re.findall(r"items:\s*\[(.*?)\]", text, re.DOTALL):
        ids.extend(re.findall(r"'([a-z0-9-]+)'", block))
    return ids


def test_sidebar_ids_match_doc_files():
    ids = _sidebar_ids()
    stems = {path.stem for path in DOCS.iterdir() if path.suffix in {".md", ".mdx"}}
    assert ids
    assert set(ids) == stems
    assert len(ids) == len(set(ids))
