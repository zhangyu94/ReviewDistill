from pathlib import Path

from fastapi.testclient import TestClient

from reviewdistill.cli.init import init_project
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.web.app import create_app

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "website" / "captures"))
from seed import DEMO_LABELS, seed_demo  # noqa: E402

TEX = r"""
The results demonstrate that the method is effective.
\myremark{Demonstrate is too strong here.}

This result holds for any dataset.
\myremark{We evaluated on one corpus.}

We created the evaluation corpus by running the coding agent.
\myremark{Where are the tables?}

The appendix never shows the ablation.
\myremark{Point to a figure or drop the claim.}

The method is easy to run on a laptop.
\myremark{No runtime or hardware is reported.}

Later we call the same unit a vocal bout and a call packet.
\myremark{The same span is called a vocal bout and a call packet.}
"""


def test_seed_demo_assigns_labeled_and_leaves_one(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="demo", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text(TEX)
    extract_project(repo)
    client = TestClient(create_app())
    created = seed_demo(client)
    assert [row[0] for row in DEMO_LABELS] == [
        "Overclaiming",
        "Missing evidence",
        "Inconsistent terms",
        "Unclear writing",
        "Reproducibility",
        "Related work",
    ]
    assert set(created) >= {row[0] for row in DEMO_LABELS}
    forest = client.get("/api/labels").json()["forest"]
    by_name = {node["name"]: node for node in forest}
    assert [node["name"] for node in forest] == [row[0] for row in DEMO_LABELS]
    assert [child["name"] for child in by_name["Overclaiming"]["children"]] == [
        "Missing comparison",
        "Causal language",
    ]
    assert [child["name"] for child in by_name["Missing evidence"]["children"]] == [
        "No figure",
        "No table",
    ]
    assert [child["name"] for child in by_name["Unclear writing"]["children"]] == [
        "Undefined term",
        "Ambiguous claim",
    ]
    assert [child["name"] for child in by_name["Reproducibility"]["children"]] == [
        "Missing hardware",
        "Missing seed",
    ]
    assert [child["name"] for child in by_name["Related work"]["children"]] == [
        "Missing citation",
        "Misstated prior work",
    ]
    body = client.get("/api/inbox").json()
    by_text = {row["comment"]["raw_text"]: row for row in body["working_items"]}
    assert by_text["Demonstrate is too strong here."]["label"]["name"] == "Causal language"
    assert by_text["We evaluated on one corpus."]["label"]["name"] == "Causal language"
    assert by_text["Where are the tables?"]["label"]["name"] == "No table"
    assert by_text["Point to a figure or drop the claim."]["label"]["name"] == "No figure"
    assert by_text["No runtime or hardware is reported."]["label"]["name"] == "Missing hardware"
    assert by_text["The same span is called a vocal bout and a call packet."]["labeled"] is False
