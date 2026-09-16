# CLI and export

```
reviewdistill init             Create `.reviewdistill/` in this paper repo
reviewdistill extract          Pull comments from `.tex` (`--watch` keeps going)
reviewdistill ui               Workbench at http://127.0.0.1:8765
reviewdistill export           Write a skill (`md`); `yaml` / `json` dump the taxonomy
reviewdistill paths            Print the data folder
reviewdistill paths use DIR    Point at DIR (does not copy files)
reviewdistill paths move DIR   Copy the current home into an empty DIR, then use it
```

`init`: `--name`, `--command` (repeatable; default `myremark`).

`ui`: `--host` (default `127.0.0.1`), `--port` (default `8765`).

`export`: `--format` (default `md`), `--output` / `-o` (default `SKILL.md` for `md`, `review-taxonomy.yaml` / `review-taxonomy.json` for those formats), `--id` (repeatable).

`move` needs an empty destination. Quit `ui` and `extract --watch` first; restart them after `use` or `move`.

A later `reviewdistill review` that applies the skill to a new manuscript is out of scope.

## Skill format

Markdown is the agent skill (`SKILL.md`): YAML frontmatter, a short review procedure, then the labels:

```markdown
---
name: scholarly-review
description: Review a scholarly manuscript against this author's distilled label taxonomy. Use when proofreading, reviewing, or checking a paper.
---

# Scholarly Review

Review the manuscript against the labels below. For each label, flag passages that match the definition and examples.

## Overclaiming
### Definition
Flag claims whose strength exceeds the evidence presented.
### Examples
- "The results demonstrate..." when evidence is correlational.
- "This proves..." when the experiment does not establish causality.
```

YAML/JSON are taxonomy dumps: a flat list of labels with `parent_id` (null for roots), not a nested `children` blob. Markdown may show a `Parent:` line by parent name.

Put `SKILL.md` in `.cursor/skills/scholarly-review/` (or the equivalent for another agent). The file should say when to apply the skill, how to apply it, and each issue with a definition and examples.
