from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "skill-eval"))

from lib import (  # noqa: E402
    BASELINE_CONDITION,
    SKILL_CONDITION,
    FixtureError,
    Fold,
    TypeRef,
    distractor_item,
    exact_counts,
    heading_names_from_skill,
    hierarchical_hits,
    load_fixture_pack,
    parse_types,
    parse_types_result,
    passage_at_line,
    prf,
    prompt_for,
    skill_markdown_from_labels,
    unused_paragraphs,
)

SKILL_MD = """\
---
name: scholarly-review
---

# Scholarly Review

Review the manuscript against the labels below.

## Terminology Precision
### Definition
Same concept, two names.
### Examples
- The filter is a gate then a mask.

## Cross-Referencing and Navigation
### Definition
Points at a missing figure.
### Examples
- See the appendix table.
"""


def test_heading_names_from_skill_skips_definition_headings():
    assert heading_names_from_skill(SKILL_MD) == [
        "Terminology Precision",
        "Cross-Referencing and Navigation",
    ]


def test_baseline_prompt_lists_headings_without_definitions():
    prompt = prompt_for(BASELINE_CONDITION, SKILL_MD, "A held-out passage.")
    assert "## Terminology Precision" in prompt
    assert "## Cross-Referencing and Navigation" in prompt
    assert "Same concept, two names." not in prompt
    assert "The filter is a gate then a mask." not in prompt
    assert "### Definition" not in prompt
    assert "### Examples" not in prompt
    assert "A held-out passage." in prompt


def test_skill_prompt_still_includes_definitions():
    prompt = prompt_for(SKILL_CONDITION, SKILL_MD, "A held-out passage.")
    assert "Same concept, two names." in prompt
    assert "The filter is a gate then a mask." in prompt


def test_unused_paragraphs_skips_preamble_and_end_document(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}

\section{Method}

We treat each chorus event as a 200\,ms window.

Peak picking follows the energy rule in the supplement.

\end{document}
""",
        encoding="utf-8",
    )
    found = unused_paragraphs(root=tmp_path, occupied={}, commands=set())
    assert r"\end{document}" not in found
    assert not any(r"\documentclass" in chunk for chunk in found)
    assert any("chorus event" in chunk for chunk in found)
    assert any("Peak picking" in chunk for chunk in found)


def test_distractor_ids_include_project_so_folds_do_not_collide():
    fold = Fold(
        id="comment-fraction",
        test_comment_ids=frozenset(),
        test_project_ids=frozenset({"paper-a", "paper-b"}),
    )
    a = distractor_item(fold, "paper-a", 0, "alpha")
    b = distractor_item(fold, "paper-b", 0, "beta")
    assert a.id != b.id
    assert "paper-a" in a.id
    assert "paper-b" in b.id


def test_fixture_unused_paragraphs_are_prose():
    pack = load_fixture_pack(ROOT / "experiments" / "skill-eval" / "fixtures")
    found = []
    for paper_id, root in pack.roots.items():
        occupied = pack.occupied.get(paper_id, {})
        found.extend(unused_paragraphs(root=root, occupied=occupied, commands=set()))
    assert found
    joined = "\n".join(found)
    assert r"\end{document}" not in joined
    assert r"\documentclass" not in joined


def test_skill_drops_train_examples_that_match_a_held_out_passage():
    labels = [
        {
            "id": "l1",
            "name": "Overclaiming",
            "parent_id": None,
            "parent_name": None,
            "definition": "A claim is too strong.",
            "example_rows": [
                {
                    "text": "The experiment only shows a correlation.",
                    "source_item_id": "train-sibling",
                },
                {
                    "text": "A different paragraph about methods.",
                    "source_item_id": "other",
                },
            ],
        }
    ]
    md = skill_markdown_from_labels(
        labels,
        {"held-out-comment"},
        holdout_passages={"The experiment  only shows a correlation."},
    )
    assert "The experiment only shows a correlation." not in md
    assert "A different paragraph about methods." in md
    assert "Overclaiming" in md


def test_parse_types_uses_last_object_with_a_types_list():
    assert parse_types('Sure. {"types": ["Overclaiming"]} trailing') == {"Overclaiming"}
    assert parse_types('{"note": "hi"} {"types": ["Overclaiming"]}') == {"Overclaiming"}
    assert parse_types('{"types": ["A"]} then {"types": ["B"]}') == {"B"}
    assert parse_types("not json") == set()
    assert parse_types('{"types": "Overclaiming"}') == set()
    assert parse_types('{"types": ["  Overclaiming  ", ""]}') == {"Overclaiming"}
    names, parse_error = parse_types_result('{"note": "hi"}')
    assert names == set()
    assert parse_error is True
    names, parse_error = parse_types_result('{"types": []}')
    assert names == set()
    assert parse_error is False


def test_notebook_miss_table_does_not_embed_passages():
    nb = json.loads((ROOT / "experiments" / "skill-eval" / "analyze.ipynb").read_text())
    misses = next(cell for cell in nb["cells"] if cell.get("id") == "misses")
    source = "".join(misses["source"])
    assert 'item["passage"]' not in source
    assert '"passage"' not in json.dumps(misses.get("outputs", []))


def test_prf_undefined_ratios_are_zero():
    assert prf(0, 0, 0) == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0}
    tp, fp, fn = exact_counts({"A"}, {"A", "B"})
    assert (tp, fp, fn) == (1, 1, 0)
    scores = prf(tp, fp, fn)
    assert scores["precision"] == 0.5
    assert scores["recall"] == 1.0


def test_hierarchical_hits_counts_parent_prediction():
    types = [
        TypeRef(id="p", name="Clarity", parent_id=None),
        TypeRef(id="c", name="Overclaiming", parent_id="p"),
    ]
    assert hierarchical_hits({"Overclaiming"}, {"Clarity"}, types) == {"Overclaiming"}
    assert hierarchical_hits({"Overclaiming"}, {"Unrelated"}, types) == set()
    assert hierarchical_hits({"Overclaiming"}, {"Overclaiming"}, types) == {"Overclaiming"}


def test_passage_at_line_returns_paragraph(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\n"
        "Hello world.\n"
        "\n"
        "\\section{Method}\n"
        "\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    assert passage_at_line(tex, 4) == "Hello world."
    with pytest.raises(FixtureError, match="not a content block"):
        passage_at_line(tex, 6)
    with pytest.raises(FixtureError, match="out of range"):
        passage_at_line(tex, 99)
    with pytest.raises(FixtureError, match="Cannot read"):
        passage_at_line(tmp_path / "missing.tex", 1)


def test_load_fixture_pack_rejects_unknown_gold_name(tmp_path: Path):
    (tmp_path / "papers" / "p").mkdir(parents=True)
    (tmp_path / "papers" / "p" / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\nHello world.\n\n\\end{document}\n",
        encoding="utf-8",
    )
    (tmp_path / "taxonomy.yaml").write_text(
        "labels:\n  - id: a\n    name: Alpha\n    definition: A manuscript pattern.\n",
        encoding="utf-8",
    )
    (tmp_path / "gold.jsonl").write_text(
        json.dumps(
            {
                "id": "g1",
                "paper_id": "p",
                "file_path": "main.tex",
                "line_number": 4,
                "gold_names": ["Nope"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(FixtureError, match="unknown gold name"):
        load_fixture_pack(tmp_path)
