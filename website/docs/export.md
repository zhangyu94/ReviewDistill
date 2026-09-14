# Export

Export the accumulated taxonomy as a review skill (Markdown) or a taxonomy dump (YAML/JSON):

```bash
reviewdistill export --format md -o SKILL.md
```

`--format` is `md`, `yaml`, or `json`. `--output` / `-o` sets the path. The default file is `SKILL.md` (or `review-taxonomy.yaml` / `.json`). YAML and JSON are a flat list of types with `parent_id` (null for roots). Markdown is an agent skill: YAML frontmatter, a short review procedure, then the issue types. It may include a `Parent:` line by parent name.

`--id` (repeatable) keeps only those types in the file. Omit it to export every active type. This does not hide types or change labels in the UI.

The header **Export** dialog is the same: format chips, then an indented checkbox tree of active types (all checked to start; checking a parent does not check its children). **Download** writes the checked ids only. The tooltip is **Download a review skill**.

Put `SKILL.md` in `.cursor/skills/scholarly-review/` (or the equivalent for another coding agent). Dropped comments are not treated as live examples.
