# Export

Export the accumulated taxonomy as a review rubric:

```bash
reviewdistill export --format md -o review-rubric.md
```

`--format` is `md`, `yaml`, or `json`. `--output` / `-o` sets the path. The default file is `review-rubric.md` (or `review-rubric.yaml` / `.json`). YAML and JSON are a flat list of types with `parent_id` (null for roots). Markdown may include a `Parent:` line.

The workbench header **Export** dialog downloads the same formats and can deactivate a group. Deactivating a group hides it from the live tree; its children become siblings, and labeled comments on that type return to Unlabeled (undo restores the labels).

Give the Markdown file to a coding agent (for example Cursor) as the review standard to apply. Dropped comments and deactivated groups are not treated as live examples.
