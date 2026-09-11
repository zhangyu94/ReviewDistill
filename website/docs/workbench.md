# Workbench

`reviewdistill serve` is the coding UI. It serves the built Vue app plus `/api` on http://127.0.0.1:8765.

The layout is **Groups | Entries | Inspector**.

## Groups

Issue types in the taxonomy (active groups you can code into). You can rename, edit definitions, merge, split, move, or deactivate a group. **Export** in the header downloads the rubric or deactivates a group.

## Entries

Comments in the **working dataset** for the current selector:

- **Uncoded** — not yet assigned to a type.
- **This type** — comments coded as the selected group.
- Disappeared comments wait for **Keep** or **Retract** (extract never throws observations away).

Click a row to open it in the inspector. Drag a comment onto a group to code it.

## Inspector

- **Comment inspector** — wording, manuscript context, location, AI suggestion (if any), accept / change / reject.
- **Issue inspector** — definition, examples, and operations on the selected group.

**Uncoded** empty state **Configure LLM** opens the same dialog as header **Settings**. Settings has two panels: **Assistant** (provider, model, API key) and **Data** (the folder on this computer, same as `reviewdistill paths`). Copy that whole folder to back up comments and issue types. To store it somewhere else, quit the workbench and run `reviewdistill paths move DIR` (or `reviewdistill paths use DIR` if you already copied it).

## Selectors and pagination

The selectors bar switches Uncoded vs a type. Long lists paginate; the URL keeps the selected comment.

## Optional hot reload

From a clone, with the API already on `:8765`:

```bash
pnpm --dir studio dev
```

Vite on :5173 proxies `/api`. After you finish UI work, rebuild packaged assets (`pip install -e ".[dev]"` or `scripts/build-studio-assets.sh`) so `reviewdistill serve` is not stuck on an old build.
