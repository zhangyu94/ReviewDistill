from __future__ import annotations

import json

import yaml

from reviewdistill.db.session import get_session
from reviewdistill.errors import BadInput
from reviewdistill.taxonomy.operations import (
    list_active_labels,
    list_examples,
)


def export_rubric(fmt: str = "md", label_ids: list[str] | None = None) -> str:
    with get_session():
        active = list_active_labels()
        by_id = {label.id: label for label in active}
        if label_ids is not None:
            unknown = [row for row in label_ids if row not in by_id]
            if unknown:
                raise BadInput(f"Unknown label {unknown[0]}")
            wanted = set(label_ids)
            active = [label for label in active if label.id in wanted]
        labels = []
        for label in active:
            labels.append(
                {
                    "id": label.id,
                    "name": label.name,
                    "parent_id": label.parent_id,
                    "parent_name": (
                        by_id[label.parent_id].name
                        if label.parent_id and label.parent_id in by_id
                        else None
                    ),
                    "definition": label.definition,
                    "examples": [example.text for example in list_examples(label.id)],
                }
            )
    if fmt == "md":
        return _to_markdown(labels)
    if fmt == "yaml":
        return yaml.safe_dump({"labels": [_structured(label) for label in labels]}, sort_keys=False)
    if fmt == "json":
        return json.dumps({"labels": [_structured(label) for label in labels]}, indent=2)
    raise BadInput(f"Unknown export format: {fmt}")


def _structured(label: dict) -> dict:
    return {key: label[key] for key in (
        "id",
        "name",
        "parent_id",
        "definition",
        "examples",
    )}


_SKILL_FRONTMATTER = """\
---
name: scholarly-review
description: Review a scholarly manuscript against this author's distilled label taxonomy. Use when proofreading, reviewing, or checking a paper.
---
"""

_SKILL_PROCEDURE = (
    "Review the manuscript against the labels below. "
    "For each label, flag passages that match the definition and examples."
)


def default_export_filename(fmt: str) -> str:
    if fmt == "md":
        return "SKILL.md"
    if fmt == "yaml":
        return "review-taxonomy.yaml"
    if fmt == "json":
        return "review-taxonomy.json"
    raise BadInput(f"Unknown export format: {fmt}")


def _to_markdown(labels: list[dict]) -> str:
    lines = [
        _SKILL_FRONTMATTER.rstrip(),
        "",
        "# Scholarly Review",
        "",
        _SKILL_PROCEDURE,
        "",
    ]
    for label in labels:
        lines.append(f"## {label['name']}")
        if label["parent_name"]:
            lines.append(f"Parent: {label['parent_name']}")
        lines.append("### Definition")
        lines.append(label["definition"])
        lines.append("### Examples")
        if label["examples"]:
            lines.extend(f"- {text}" for text in label["examples"])
        else:
            lines.append("- (none yet)")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
