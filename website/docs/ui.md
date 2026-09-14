# UI

`reviewdistill ui` is the labeling UI. It serves the built Vue app plus `/api` on http://127.0.0.1:8765.

Selectors and Progress span the window. Under Selectors, two cards: **Issues** (Issue Taxonomy over Issue Details) and **Comments**, equal width. Clicking a type opens Issue Details and replaces the type chip; chips AND. × on the type chip keeps Issue Details (`typechip=0`). **Label with AI** in the Comments header whenever unlabeled comments still need proposals, even if the Unlabeled chip is off.

The header has **History**, **Settings**, and **Export** as chips on the right. History and Settings open dialogs; they do not leave this screen. **GitHub** and **Docs** sit further right as text links and open the repository and documentation website in a new tab.

## Issue Taxonomy

Issue types in an indented forest. New labels go on **leaves** only. Active names are unique: a second `New type` becomes `New type (2)`. The tree starts expanded; the chevron expands or collapses, and clicking the **name** selects. Click a type to edit it; Comments and the count are the **subtree**. Header **+** adds a root. Header fork is enabled only when there are no types yet, at least two unlabeled comments, and an LLM is configured; it creates root types from those comments (including comments that already have an AI proposal). Hover **+** on a leaf adds `New type` and `ungrouped`, and moves that leaf’s labels onto `ungrouped`. Hover **+** on a parent only adds `New type`. Hover fork on a leaf with at least two labeled comments keeps that type as parent and creates more specific children; each old label becomes an AI proposal on a child. After a split, Unlabeled turns on and the type chip turns off so Comments shows those proposals. Flatten reassigns descendant comments onto that type. Remove deletes the subtree (undoable). Drag a type before/after a row to reorder siblings, onto the middle to nest, or onto a leaf’s **merge** chip to merge. One **Edit** on the Issue Details header changes name and definition (**Save** writes only the fields that changed). **Export** in the header downloads a review skill: choose a format and check which types to include (each node independent). Markdown is `SKILL.md`; YAML and JSON are taxonomy dumps. Unchecked types stay in the taxonomy.

## Comments

Comments for the current chips (AND). No chips: comments to distill. The header count is **N to distill** with no chips, or **N matching · M to distill** when chips AND. It is not dropped + to distill.

- **Unlabeled chip** — inbox queue: comments to distill with no issue type, plus comments that left the manuscript and are still unreviewed (so you can Verify or Drop). Those rows show a **Left the manuscript** chip. A label on an inactive type does not count; that comment is Unlabeled.
- **Type chip** — named with the issue type (for example `Overclaiming (3)`); labeled comments to distill for that type and its descendants.

**Verify** and **Drop** stamp quality on the observation (independent of the label). Extract never throws observations away and never Verify/Drops, except that a wording revision clears verified back to unreviewed.

Click a row to open it in the inspector. The list shows each comment’s assigned leaf issue type(s) when it has them. Drag an unlabeled comment onto a leaf type to assign that type.

## Inspector

- **Comment inspector** — wording, manuscript context, type, quality (Verify / Drop), location. Unlabeled **Assign type** is two rows: a stored proposal (or **No AI suggestion**) then a type menu of **leaves** (a leftover parent label still shows as the current value). The menu shows the current type (or **Choose a type…** if unlabeled). Picking a type assigns it; there is no Change button. **Accept** applies the AI suggestion. New types are titled `New: {name}`; a new proposal with no name is **No AI suggestion** and stays in the Label with AI queue. There is no Reject: not accepting a suggestion leaves the comment unlabeled.
- **Issue inspector** — under the taxonomy tree, a compact strip: the selected type’s name as a title, then the definition. **Edit** on the Issue Details header still changes both.

**Unlabeled** empty state **Configure LLM** opens the same dialog as header **Settings**. Settings has two panels: **Assistant** (provider, model, and API key in this computer’s ReviewDistill folder, not a paper) and **Data** (the folder on this computer, same as `reviewdistill paths`). Edit the path or **Choose…** a folder, then **Save** to point ReviewDistill at that folder (`paths use`; it does not copy files). **Open folder** reveals it in the file manager. Backup and `paths move` are in that folder’s `README.md`.

## Selectors and pagination

Selectors are chips on the left (AND). The Unlabeled control on the right adds or removes the Unlabeled chip and has no pressed state. With no chips, Comments lists comments to distill. Clicking a type still selects Issue Details. Long lists paginate; the URL keeps the selected comment (`unlabeled=1`, `typechip=0`).

## Progress

A bottom strip shows **to distill** (not dropped, and in the manuscript or verified), then unlabeled · verified · dropped. unlabeled is comments to distill with no type; verified is quality-assured. The Unlabeled chip has no count. With no chips, Comments lists comments to distill; with only Unlabeled, Comments is the inbox queue, which can differ from Progress unlabeled. The strip is not clickable.

## Optional hot reload

From a clone, with the API already on `:8765`:

```bash
pnpm --dir client dev
```

Vite on :5173 proxies `/api`. After you finish UI work, rebuild packaged assets (`pip install -e ".[dev]"` or `python client_build.py`) so `reviewdistill ui` is not stuck on an old build.
