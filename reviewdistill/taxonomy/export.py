from __future__ import annotations

import json

import yaml

from reviewdistill.db.session import get_session
from reviewdistill.errors import BadInput
from reviewdistill.taxonomy.operations import (
    list_active_issue_types,
    list_counterexamples,
    list_examples,
)


def export_rubric(fmt: str = "md", issue_ids: list[str] | None = None) -> str:
    with get_session():
        active = list_active_issue_types()
        by_id = {issue.id: issue for issue in active}
        if issue_ids is not None:
            unknown = [row for row in issue_ids if row not in by_id]
            if unknown:
                raise BadInput(f"Unknown issue type {unknown[0]}")
            wanted = set(issue_ids)
            active = [issue for issue in active if issue.id in wanted]
        issues = []
        for issue in active:
            issues.append(
                {
                    "id": issue.id,
                    "name": issue.name,
                    "parent_id": issue.parent_id,
                    "parent_name": (
                        by_id[issue.parent_id].name
                        if issue.parent_id and issue.parent_id in by_id
                        else None
                    ),
                    "definition": issue.definition,
                    "examples": [example.text for example in list_examples(issue.id)],
                    "counterexamples": [item.text for item in list_counterexamples(issue.id)],
                }
            )
    if fmt == "md":
        return _to_markdown(issues)
    if fmt == "yaml":
        return yaml.safe_dump({"issue_types": [_structured(issue) for issue in issues]}, sort_keys=False)
    if fmt == "json":
        return json.dumps({"issue_types": [_structured(issue) for issue in issues]}, indent=2)
    raise BadInput(f"Unknown export format: {fmt}")


def _structured(issue: dict) -> dict:
    return {key: issue[key] for key in (
        "id",
        "name",
        "parent_id",
        "definition",
        "examples",
        "counterexamples",
    )}


_SKILL_FRONTMATTER = """\
---
name: scholarly-review
description: Review a scholarly manuscript against this author's distilled issue taxonomy. Use when proofreading, reviewing, or checking a paper.
---
"""

_SKILL_PROCEDURE = (
    "Review the manuscript against the issue types below. "
    "For each type, flag passages that match the definition and examples. "
    "Do not flag counterexamples."
)


def default_export_filename(fmt: str) -> str:
    if fmt == "md":
        return "SKILL.md"
    if fmt == "yaml":
        return "review-taxonomy.yaml"
    if fmt == "json":
        return "review-taxonomy.json"
    raise BadInput(f"Unknown export format: {fmt}")


def _to_markdown(issues: list[dict]) -> str:
    lines = [
        _SKILL_FRONTMATTER.rstrip(),
        "",
        "# Scholarly Review",
        "",
        _SKILL_PROCEDURE,
        "",
    ]
    for issue in issues:
        lines.append(f"## {issue['name']}")
        if issue["parent_name"]:
            lines.append(f"Parent: {issue['parent_name']}")
        lines.append("### Definition")
        lines.append(issue["definition"])
        lines.append("### Examples")
        if issue["examples"]:
            lines.extend(f"- {text}" for text in issue["examples"])
        else:
            lines.append("- (none yet)")
        lines.append("### Counterexamples")
        if issue["counterexamples"]:
            lines.extend(f"- {text}" for text in issue["counterexamples"])
        else:
            lines.append("- (none yet)")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
