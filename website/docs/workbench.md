# Workbench

`reviewdistill serve` is the labeling UI. It serves the built Vue app plus `/api` on http://127.0.0.1:8765.

The layout is **Issue Taxonomy | Issue Details | Comments**.

## Groups

Issue types in an indented forest (active groups you can label into). Every node is a real type: it can have children and its own labels. The tree starts expanded; the chevron expands or collapses, and clicking the **name** selects. Click a type to edit it; Comments and the count are the **subtree**. Header **+** adds a root; hover **+** adds a child. Flatten reassigns descendant comments onto that type. Remove deletes the subtree (undoable). Drag a type before/after a row to reorder siblings, onto the middle to nest, or onto a leaf’s **merge** chip to merge. Drag an unlabeled comment onto a leaf to Change. You can rename, edit definitions, split, or deactivate a group. **Deactivate** hides that type; its children become siblings, and labeled comments on that type return to Unlabeled. **Export** in the header downloads the rubric or deactivates a group.

## Entries

Comments for the current selector:

- **Unlabeled** — working-set comments with no issue type, plus comments that left the manuscript and are still unreviewed (so you can Verify or Drop). Rows not in the manuscript are marked.
- **This type** — labeled comments in the working set for the selected group and its descendants.

**Verify** and **Drop** stamp quality on the observation (independent of the label). Extract never throws observations away and never Verify/Drops, except that a wording revision clears verified back to unreviewed.

Click a row to open it in the inspector. Drag an unlabeled comment onto a leaf type to assign that type.

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
