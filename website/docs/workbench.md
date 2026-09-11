# Workbench

`reviewdistill serve` is the labeling UI. It serves the built Vue app plus `/api` on http://127.0.0.1:8765.

The layout is **Issue Taxonomy | Issue Details | Comments**.

## Groups

Issue types in the taxonomy (active groups you can label into). You can rename, edit definitions, merge, split, move, or deactivate a group. **Deactivate** returns that type’s labeled comments to Unlabeled. **Export** in the header downloads the rubric or deactivates a group.

## Entries

Comments for the current selector:

- **Unlabeled** — working-set comments with no issue type, plus comments that left the manuscript and are still unreviewed (so you can Verify or Drop). Rows not in the manuscript are marked.
- **This type** — labeled comments in the working set for the selected group.

**Verify** and **Drop** stamp quality on the observation (independent of the label). Extract never throws observations away and never Verify/Drops, except that a wording revision clears verified back to unreviewed.

Click a row to open it in the inspector. Drag an unlabeled comment onto a group to assign that type.

## Inspector

- **Comment inspector** — wording, manuscript context, location, quality (Verify / Drop), current type when labeled, AI suggestion (if any), Accept / Change. There is no Reject: not accepting a suggestion leaves the comment unlabeled.
- **Issue inspector** — definition, examples, and operations on the selected group.

**Unlabeled** empty state **Configure LLM** opens the same dialog as header **Settings**. Settings has two panels: **Assistant** (provider, model, API key) and **Data** (the folder on this computer, same as `reviewdistill paths`). Copy that whole folder to back up comments and issue types. To store it somewhere else, quit the workbench and run `reviewdistill paths move DIR` (or `reviewdistill paths use DIR` if you already copied it).

## Selectors and pagination

The selectors bar switches Unlabeled vs a type. Long lists paginate; the URL keeps the selected comment.

## Optional hot reload

From a clone, with the API already on `:8765`:

```bash
pnpm --dir client dev
```

Vite on :5173 proxies `/api`. After you finish UI work, rebuild packaged assets (`pip install -e ".[dev]"` or `scripts/build-client-assets.sh`) so `reviewdistill serve` is not stuck on an old build.
