import useBaseUrl from '@docusaurus/useBaseUrl';

# Export a skill

The skill is how you reuse the labels. Your coding agent applies the same checks on later papers.

There are two ways to export, and they write the same Markdown skill. YAML and JSON are taxonomy dumps, not a skill.

## From the UI

In the workbench header, click **Export**. Uncheck labels you do not want, then download.

<img
  src={useBaseUrl('/img/export-dialog.png')}
  alt="Export dialog with Markdown selected"
/>

## From the terminal

```sh
reviewdistill export
```

That writes `SKILL.md` in the current directory. `--id` (repeatable) keeps only those labels; omit it to export the whole tree.

Put the file in `.cursor/skills/scholarly-review/` (or the equivalent for another coding agent).
