from __future__ import annotations

import json

import yaml

from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import (
    list_active_issue_types,
    list_counterexamples,
    list_examples,
)


def export_rubric(fmt: str = "md") -> str:
    with get_session():
        issues = []
        for issue in list_active_issue_types():
            issues.append(
                {
                    "code": issue.code,
                    "name": issue.name,
                    "category": issue.category,
                    "definition": issue.definition,
                    "examples": [example.text for example in list_examples(issue.id)],
                    "counterexamples": [item.text for item in list_counterexamples(issue.id)],
                    "notes": issue.notes,
                }
            )
    if fmt == "md":
        return _to_markdown(issues)
    if fmt == "yaml":
        return yaml.safe_dump({"issue_types": issues}, sort_keys=False)
    if fmt == "json":
        return json.dumps({"issue_types": issues}, indent=2)
    raise ValueError(f"Unknown export format: {fmt}")


def _to_markdown(issues: list[dict]) -> str:
    lines = ["# Scholarly Review Rubric"]
    for issue in issues:
        lines.append(f"## {issue['name']}")
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
