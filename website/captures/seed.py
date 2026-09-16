from __future__ import annotations

from typing import Any

import httpx

DEMO_LABELS = (
    ("Overclaiming", "The passage claims more than the evidence supports."),
    ("Missing evidence", "The passage points at evidence that is not in the neighborhood."),
    ("Inconsistent terms", "The passage uses two names for one thing."),
    ("Unclear writing", "The passage is hard to parse or a term is never defined."),
    ("Reproducibility", "A reader could not rerun the experiment from the text."),
    ("Related work", "A cited comparison or prior method is missing or misstated."),
)

DEMO_CHILDREN = (
    ("Overclaiming", "Missing comparison", "Compared against too few systems."),
    ("Overclaiming", "Causal language", "Claims cause from a correlational result."),
    ("Missing evidence", "No figure", "A figure is mentioned but not shown."),
    ("Missing evidence", "No table", "A table is mentioned but not shown."),
    ("Unclear writing", "Undefined term", "A term is used before it is defined."),
    ("Unclear writing", "Ambiguous claim", "A sentence can be read two ways."),
    ("Reproducibility", "Missing hardware", "Runtime or hardware is not reported."),
    ("Reproducibility", "Missing seed", "A random seed or config is omitted."),
    ("Related work", "Missing citation", "A relevant comparison is not cited."),
    ("Related work", "Misstated prior work", "A cited method is described incorrectly."),
)

ASSIGNMENTS = {
    "Demonstrate is too strong here.": "Causal language",
    "We evaluated on one corpus.": "Causal language",
    "Where are the tables?": "No table",
    "Point to a figure or drop the claim.": "No figure",
    "No runtime or hardware is reported.": "Missing hardware",
}


def seed_demo(client: Any) -> dict[str, str]:
    """HTTP-only demo taxonomy. No LLM. Assign leaves only. Returns name -> id."""
    ids: dict[str, str] = {}
    for name, definition in DEMO_LABELS:
        created = client.post("/api/labels", json={"parent_id": None})
        created.raise_for_status()
        label_id = created.json()["id"]
        client.post(f"/api/labels/{label_id}/rename", json={"name": name}).raise_for_status()
        client.post(f"/api/labels/{label_id}/edit", json={"definition": definition}).raise_for_status()
        ids[name] = label_id
    for parent_name, name, definition in DEMO_CHILDREN:
        created = client.post("/api/labels", json={"parent_id": ids[parent_name]})
        created.raise_for_status()
        label_id = created.json()["id"]
        client.post(f"/api/labels/{label_id}/rename", json={"name": name}).raise_for_status()
        client.post(f"/api/labels/{label_id}/edit", json={"definition": definition}).raise_for_status()
        ids[name] = label_id
    forest = client.get("/api/labels")
    forest.raise_for_status()

    def _drop_ungrouped(nodes: list[dict]) -> None:
        for node in nodes:
            if node["name"] == "ungrouped" or node["name"].startswith("ungrouped "):
                client.post(f"/api/labels/{node['id']}/remove").raise_for_status()
                continue
            _drop_ungrouped(node.get("children") or [])

    _drop_ungrouped(forest.json()["forest"])
    inbox = client.get("/api/inbox")
    inbox.raise_for_status()
    for row in inbox.json()["working_items"]:
        text = row["comment"]["raw_text"]
        if text not in ASSIGNMENTS:
            continue
        label_id = ids[ASSIGNMENTS[text]]
        comment_id = row["comment"]["id"]
        client.post(
            f"/api/inbox/{comment_id}/change",
            json={"label_id": label_id},
        ).raise_for_status()
    return ids


def seed_demo_http(base_url: str) -> dict[str, str]:
    with httpx.Client(base_url=base_url, timeout=30) as client:
        return seed_demo(client)
