# Export

Export the accumulated taxonomy as a review rubric:

```bash
reviewdistill export --format md -o review-rubric.md
```

`--format` is `md`, `yaml`, or `json`. `--output` / `-o` sets the path. The default file is `review-rubric.md` (or `review-rubric.yaml` / `.json`).

The workbench header **Export** dialog downloads the same formats and can deactivate a group. Deactivating a group returns its labeled comments to Unlabeled (undo restores the labels).

Give the Markdown file to a coding agent (for example Cursor) as the review standard to apply. Dropped comments and deactivated groups are not treated as live examples.
