# UI

`reviewdistill ui` is the labeling UI. It serves the built Vue app plus `/api` on http://127.0.0.1:8765.

Selectors and Progress span the window. Under Selectors, two cards: **Label Taxonomy** over **Label Details** and **Comments**, equal width. Clicking a label opens Label Details and replaces the label chip; chips AND. × on the label chip keeps Label Details (`labelchip=0`). **Label with AI** in the Comments header whenever unlabeled comments still need proposals, even if the Unlabeled chip is off. The batch accept-assigns those comments; a dismissible snackbar says they appear in Label Taxonomy. Selectors do not change. If the UI cannot reach the ReviewDistill server, that snackbar says so in plain language (not HTTP status names such as Bad Gateway). Label Details does not repeat that sentence; after a selected label fails to load it shows “Couldn't load this label.” Comments and Label Taxonomy stay blank rather than claiming the lists are empty.

The header has **History**, **Settings**, and **Export** as chips on the right. History and Settings open dialogs; they do not leave this screen. **GitHub** and **Docs** sit further right as text links and open the repository and documentation website in a new tab.

## Label Taxonomy

Labels in an indented forest. New labels go on **leaves** only. Active names are unique: a second `New label` becomes `New label (2)`. The tree starts expanded; the chevron expands or collapses, and clicking the **name** selects. Click a label to edit it; Comments and the count are the **subtree**. Header **+** adds a root. Header fork is enabled only when there are no labels yet, at least two unlabeled comments, and an LLM is configured; it creates root labels from those comments (including comments that already have an AI proposal) and accept-assigns them. Selectors do not change. A snackbar says they appear in Label Taxonomy. Header recycle is enabled when there is already at least one label and at least two unlabeled comments to distill; it creates a **root** named `ungrouped` and assigns those comments so you can leaf-fork that node. It does not run the LLM. Hover **+** on a leaf adds `New label` and an `ungrouped` **child**, and moves that leaf’s labels onto `ungrouped`. The recycle root and that parking child share a name family; they are different nodes. Hover **+** on a parent only adds `New label`. Hover fork on a leaf with at least two labeled comments keeps that label as parent and creates more specific children; each old label is accept-assigned onto a child. Selectors stay put. Flatten reassigns descendant comments onto that label. Remove deletes the subtree (undoable). Drag a label before/after a row to reorder siblings, onto the middle to nest, or onto a leaf’s **merge** chip to merge. One **Edit** on the Label Details header changes name and definition (**Save** writes only the fields that changed). **Export** in the header downloads a review skill: choose a format and check which labels to include (each node independent). Markdown is `SKILL.md`; YAML and JSON are taxonomy dumps. Unchecked labels stay in the taxonomy.

## Comments

Comments for the current chips (AND). No chips: comments to distill. The header count is **N to distill** with no chips, or **N matching · M to distill** when chips AND.

- **Unlabeled chip** — inbox queue: comments to distill with no label, plus comments that left the manuscript and are still not verified (so you can Verify or Delete). Those rows show a **Left the manuscript** chip. A label on an inactive label does not count; that comment is Unlabeled.
- **Label chip** — named with the label (for example `Overclaiming (3)`); labeled comments to distill for that label and its descendants.

**Verify** toggles protect on the observation (independent of the label). Click again to unverify. **Delete** removes the observation from the store (undo from History) and is disabled while verified. Extract never Verify/Unverifies, except that a wording revision clears verified to false.

Click a row to open it in the inspector. The list shows each comment’s assigned leaf label(s) when it has them. Drag an unlabeled comment onto a leaf label to assign that label.

## Inspector

- **Comment inspector** — wording, manuscript context (a square marks where the comment command sat when `context_offset` is known; a parenthetical legend beside the heading shows the same square), Label / Assign label, Triage (Verify / Delete), location. When the `.tex` file is still on this computer, **File** is a control that selects it in the file manager (same idea as Settings **Open folder**: not a `file://` link, and not the default editor). If the checkout is gone, File stays plain text. Failures show in a dismissible snackbar. Unlabeled **Assign label** is two rows: a leftover stored proposal (or **No AI suggestion**) then a label menu of **leaves** (a leftover parent label still shows as the current value). The menu shows the current label (or **Choose a label…** if unlabeled). Picking a label assigns it; there is no Change button. **Accept** applies a leftover AI suggestion. Label with AI and fork accept-assign in the batch, so Accept is usually unused after those actions. New leftover proposals are titled `New: {name}`; a new proposal with no name is **No AI suggestion** and stays in the Label with AI queue. There is no Reject: not accepting a leftover suggestion leaves the comment unlabeled.
- **Label inspector** — under the taxonomy tree, a compact strip: the selected label’s name as a title, then the definition. Nothing selected is “Select a label.”; a missing label is “This label was not found.”; a failed load is “Couldn't load this label.” **Edit** on the Label Details header still changes both.

**Unlabeled** empty state **Configure LLM** opens the same dialog as header **Settings**. Settings has two panels: **Assistant** (provider, model, and API key in this computer’s ReviewDistill folder, not a paper) and **Data** (the folder on this computer, same as `reviewdistill paths`). Edit the path or **Choose…** a folder, then **Save** to point ReviewDistill at that folder (`paths use`; it does not copy files). **Open folder** reveals it in the file manager. Backup and `paths move` are in that folder’s `README.md`.

## Selectors and pagination

Selectors are chips on the left (AND). The Unlabeled control on the right adds or removes the Unlabeled chip and has no pressed state. With no chips, Comments lists comments to distill. Clicking a label still selects Label Details. Long lists paginate; the URL keeps the selected comment (`unlabeled=1`, `labelchip=0`).

## Progress

A bottom strip shows **to distill** (in the manuscript or verified), then unlabeled · verified. unlabeled is comments to distill with no label; verified is comments the reviewer has Verified. The Unlabeled chip has no count. With no chips, Comments lists comments to distill; with only Unlabeled, Comments is the inbox queue, which can differ from Progress unlabeled. The strip is not clickable.

## Optional hot reload

From a clone, with the API already on `:8765`:

```bash
pnpm --dir client dev
```

Vite on :5173 proxies `/api`. After you finish UI work, rebuild packaged assets (`pip install -e ".[dev]"` or `python client_build.py`) so `reviewdistill ui` is not stuck on an old build.
