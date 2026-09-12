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


def export_rubric(fmt: str = "md") -> str:
    with get_session():
        active = list_active_issue_types()
        by_id = {issue.id: issue for issue in active}
        issues = []
        for issue in active:
            issues.append(
                {
                    "id": issue.id,
                    "code": issue.code,
                    "name": issue.name,
                    "parent_id": issue.parent_id,
                    "parent_code": by_id[issue.parent_id].code if issue.parent_id else None,
                    "definition": issue.definition,
                    "examples": [example.text for example in list_examples(issue.id)],
                    "counterexamples": [item.text for item in list_counterexamples(issue.id)],
                    "notes": issue.notes,
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
        "code",
        "name",
        "parent_id",
        "definition",
        "examples",
        "counterexamples",
        "notes",
    )}


def _to_markdown(issues: list[dict]) -> str:
    lines = ["# Scholarly Review Rubric"]
    for issue in issues:
        lines.append(f"## {issue['name']}")
        if issue["parent_code"]:
            lines.append(f"Parent: {issue['parent_code']}")
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
