# Export

Export the accumulated taxonomy as a review rubric:

```bash
reviewdistill export --format md -o review-rubric.md
```

`--format` is `md`, `yaml`, or `json`. `--output` / `-o` sets the path. The default file is `review-rubric.md` (or `review-rubric.yaml` / `.json`). YAML and JSON are a flat list of types with `parent_id` (null for roots). Markdown may include a `Parent:` line by parent name.

`--id` (repeatable) keeps only those types in the file. Omit it to export every active type. This does not hide types or change labels in the UI.

The header **Export** dialog is the same: format chips, then an indented checkbox tree of active types (all checked to start; checking a parent does not check its children). **Download** writes the checked ids only.

Give the Markdown file to a coding agent (for example Cursor) as the review standard to apply. Dropped comments are not treated as live examples.
