# Export

Export the accumulated taxonomy as a review skill (Markdown) or a taxonomy dump (YAML/JSON):

```bash
reviewdistill export --format md -o SKILL.md
```

`--format` is `md`, `yaml`, or `json`. `--output` / `-o` sets the path. The default file is `SKILL.md` (or `review-taxonomy.yaml` / `.json`). YAML and JSON are a flat list of labels with `parent_id` (null for roots), wrapped in `labels`. Markdown is an agent skill: YAML frontmatter, a short review procedure, then the labels. It may include a `Parent:` line by parent name.

`--id` (repeatable) keeps only those labels in the file. Omit it to export every active label. This does not hide labels or change label assignments in the UI.

The header **Export** dialog is the same: format chips, then an indented checkbox tree of active labels (all checked to start; checking a parent does not check its children). **Download** writes the checked ids only. The tooltip is **Download a review skill**.

Put `SKILL.md` in `.cursor/skills/scholarly-review/` (or the equivalent for another coding agent).
