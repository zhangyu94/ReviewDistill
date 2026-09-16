# UI

The workbench is a local web app. The central screen is Label Taxonomy, Label Details, and Comments.

```
ReviewDistill                          History · Settings · Export    GitHub  Docs
────────────────────────────────────────
Selectors  [Unlabeled ×]  ∩  [Missing introduction (17) ×]          [Unlabeled]
────────────────────────────────────────
[ Label Taxonomy          ]     [ Comments ]
  Argumentation                  17 matching · 42 to distill
    Overclaiming
      Causal lang
  Clarity
[ Label Details           ]
  Definition
────────────────────────────────────────
Progress  42 to distill    unlabeled 8 · verified 40
```

The top bar stays on this screen. **History**, **Settings**, and **Export** are chips on the right; History and Settings open dialogs. Export opens a format picker plus a checkbox tree of labels to include. **GitHub** and **Docs** sit further right as text links and open the repository and documentation website in a new tab.

## Selectors and URLs

Selectors are chips on the left. The right-hand Unlabeled control toggles a left-hand Unlabeled chip and is never pressed. Present chips AND. No chips: Comments lists comments to distill.

Clicking a label opens Label Details and does not clear Unlabeled. If Unlabeled is off, the label chip is that label. If Unlabeled is on, the label chip stays off (`labelchip=0`) so Comments stays the unlabeled queue (Unlabeled ∧ label is almost always empty). Hover **+** and merge use the same rule. × on the label chip sets `labelchip=0` and keeps `/labels/:id`. Toggling Unlabeled keeps the current label-chip state. Unlabeled and labels share this one screen.

| URL | Label Details | Unlabeled chip | Label chip |
| --- | --- | --- | --- |
| `/` | empty | off | none |
| `/?unlabeled=1` | empty | on | none |
| `/labels/:id` | that label | off | that label |
| `/labels/:id?unlabeled=1` | that label | on | that label |
| `/labels/:id?labelchip=0` | that label | off | none |
| `/labels/:id?unlabeled=1&labelchip=0` | that label | on | none |

`labelchip=0` means Label Details is open and the label chip is off. Selecting a label (click, hover **+**, merge) writes it when Unlabeled is on; × on the label chip always writes it. Split and Label with AI do not change selectors. Clicking a label while Unlabeled is off omits `labelchip=0` (label chip on). `?id=` still names the open comment.

Sure/Unsure confidence chips are not in this product. **Remove** (undoable) is how a label leaves the live taxonomy. There is no Deactivate control.

## Layout

Selectors and Progress span the window. Under Selectors, two cards: Label Taxonomy over Label Details, and Comments, equal width.

The Comments header shows **N to distill** with no chips, or **N matching · M to distill** when chips AND. **Label with AI** appears whenever unlabeled comments still need proposals. The open comment is the highlighted row (list or tree) or the inspector plus pager (one-at-a-time); it is not a second count.

A bottom Progress strip is display-only. The headline is the count of comments to distill. unlabeled is comments to distill with no label (labeled is the rest of those comments). verified is comments to distill that have been Verified (the rest of those comments are still not verified). The Unlabeled chip has no count. With no chips, Comments lists comments to distill. With only Unlabeled, Comments is the inbox queue (unlabeled comments to distill plus left-the-manuscript + not verified), not `progress.unlabeled`. The strip is not clickable.

## Comments

The Comments panel can switch between a list of comments, a project file tree, and a single comment. The Comments header has those three controls. The list is for scanning in incoming order; it shows truncated text. The tree nests the same comments under **project / file path**, in path then line order; grouping rows collapse and are not comments (no select, drag, or assign). Collapsing a group hides its remarks even when the open comment is inside; selection moves to the next visible comment when there is one. Tree comment rows omit the repeated project · file path and show **line N**. The file row is the reveal control when the file is on this computer. List and tree scroll the full matching set; only one-at-a-time paginates. **j** / **k** follow tree order while the tree is showing. One comment shows context and metadata, with prev / pager / next at the bottom (one comment per page).

Each row is a card (not a wrapping button, so the menu and file control can be nested): click the text to select (`?id=`); unlabeled text still drags onto a leaf. Every row has the same leaf label menu as the inspector on its own line under location (compact chrome, sized to the label, with a muted **Label** prefix; current label, or **Choose a label…**; a leftover parent still shows as the current value; picking a leaf assigns it). Assign and reveal use that **row’s** comment id. After assign, if the acted comment is still in the list it becomes selected; if it left, keep the current selection when that id is still present; otherwise the same advance as labeling the open comment. Reveal does not change selection.

List location is **project · file path · line N**; tree comment rows omit project and path. Project name and **line N** stay text. When `{projects.root_path}/{file_path}` is still a file, **file path** is the same reveal control as Location **File** (same blue as Remote; title **Show this file on this computer**; not a `file://` link; `POST /api/inbox/{comment_id}/reveal`). If the checkout is gone, the location line stays plain text. A **Left the manuscript** chip still appears when the remark is no longer in the `.tex` file.

The single-comment view shows the full text, manuscript context, location, and record metadata. When `{projects.root_path}/{file_path}` is still a file, Location **File** is a control (same blue as Remote; title **Show this file on this computer**; not a `file://` link). Click `POST /api/inbox/{comment_id}/reveal` with no body: the server selects that file in the OS file manager (`open -R` on macOS; it does not open the default editor). If the checkout is gone, File stays plain text. A comment that left the manuscript can still reveal if the `.tex` file exists. Reveal does not write the store or History. Unknown comment is 404 (`Unknown comment {id}`); missing or escaped path is 404 (`This file is not on this computer.`); file-manager failure is 400. Failures show in a dismissible snackbar, not in Comments or Label Details. If the UI cannot reach the ReviewDistill server (proxy 502/503/504 or a failed fetch), that snackbar says the server is not running, not HTTP status names such as Bad Gateway.

**Accept** applies the AI suggestion. Picking a label in the menu assigns or changes it (there is no Change button and no Reject: not accepting a suggestion leaves the comment unlabeled). **Verify** stamps quality, independent of the label. **Delete** removes the observation (undo from History).

## Taxonomy

Label Taxonomy and Label Details are the same screen as Comments. Label Taxonomy is the top of the taxonomy card; Label Details is a compact strip under the tree. Clicking a label selects it: Label Details shows the name and definition. Unlabeled stays on if it was on. If Unlabeled is off, a label chip named with that label (for example `Missing introduction (17)`) replaces any previous label chip and Comments is that subtree. If Unlabeled is on, the label chip stays off so Comments stays the unlabeled queue.

```
Selectors  [Unlabeled ×]  ∩  [Missing introduction (17) ×]          [Unlabeled]
[ Label Taxonomy          ]     [ Comments ]
  Argumentation     17            17 matching · 42 to distill
    Overclaiming    12
      Causal lang    5
[ Label Details           ]
  Overclaiming
  A claim is stronger than the evidence supports.
────────────────────────────────────────
Progress  42 to distill    unlabeled 8 · verified 40
```

The taxonomy tree is full width of the taxonomy card and takes leftover height (names still `truncate` if they overflow). Label Details is a compact `shrink-0` strip under the tree; a long definition scrolls inside the strip (`max-h-40`) so the forest keeps most of the card. View is the name as a title line, then the definition as prose, with no **Name** / **Definition** / **Label** kickers. The strip stays when nothing is selected (“Select a label.”), when the open label is gone (“This label was not found.”), or when a selected label failed to load (“Couldn't load this label.”) so the card does not jump. While a label fetch is in flight the strip is blank. If the UI cannot reach the ReviewDistill server, the snackbar says so; Label Details does not repeat that sentence.

Label Details does not repeat comment text. Labeled comments in the Comments panel are the examples. A comment is labeled only when its accepted label is still active. Export lives in the header: format plus an indented checkbox tree of active labels (each node independent; all checked to start). Download writes only the checked ids. Unchecked labels stay in the taxonomy. `GET /api/labels/export?id=` (repeatable) and `reviewdistill export --id` are the same filter.

Drag an unlabeled comment onto a **leaf**: same as picking that label in the menu. Dropping onto a parent is ignored. The label menu lists leaves only (Accept and Label with AI the same).

Drag a label onto the top or bottom of another row: reorder as a sibling (`before` / `after`). Drag onto the middle of a row: nest as a child (`inner`). On a leaf, a **merge** chip appears while dragging a label; dropping on the chip merges (source into target; source children are reparented onto the target).

Header **+** adds a root label. Header fork (enabled only when the forest is empty, at least two unlabeled working-set comments exist, and an LLM is configured) creates root labels from those comments and **accept-assigns** them. Header fork includes unlabeled comments that already have an AI proposal (unlike Label with AI, which skips those). Selectors do not change. A dismissible snackbar says they appear in Label Taxonomy (`POST` returns `labeled`). Header recycle (enabled only when the forest is non-empty and at least two unlabeled working-set comments exist; no LLM) adds a root named `ungrouped` (or `ungrouped (2)` if taken) and accept-assigns those comments onto it. After recycle, Unlabeled is off and the label chip is on so Comments shows that pile; leaf fork then clusters it. `POST /api/labels/recycle` is registered next to merge/split so `recycle` is not parsed as an id.

Hover **+** on a **leaf** adds `New label` and an `ungrouped` child, and reassigns that leaf’s labels onto `ungrouped` (one history event). The recycle root and that parking child share a name family; they are different nodes. Hover **+** on a parent only adds `New label`. Hover fork on a leaf with at least two labeled comments keeps that label as parent and creates N ≥ 2 children. The model names and defines each label and assigns a child per comment; it does not rewrite the parent. One prompt per split; invalid or incomplete JSON writes nothing. Drop unused model labels; fail the whole call if fewer than two assigned labels remain. The leaf split also accept-assigns; selectors stay put. Change in Comments reviews those placements. `POST /api/labels/split` is header bootstrap (registered next to merge so `split` is not parsed as an id); `POST /api/labels/{id}/split` is leaf split with no body.

Flatten reassigns descendant comments onto the node and deactivates descendants. Remove deletes the subtree (undoable). One **Edit** on the Label Details header edits name and definition together. **Edit** shows labeled Name and Definition; **Save** is disabled when either is blank after trim; **Cancel** restores both. Save calls `POST /api/labels/{id}/rename` and/or `POST /api/labels/{id}/edit` only for fields that changed (two requests, not one transaction). Label Details does not show `detection_guidance` (retrieval still concatenates it). Label Details does not repeat the taxonomy path. There is no Deactivate control; flatten / split / merge may still retire labels as part of those actions.

The tree defaults to expanded. The chevron expands or collapses; clicking the **name** selects (it does not expand). Drag uses native HTML5 only.

## History

History is a chronological log of taxonomy mutations and labeling verdicts (`history.jsonl`). The History dialog lists each event with a short summary. Rows that have extra information (comment text, a saved definition, merge/split names, a move destination) show a chevron that expands those details in place. **Undo** and **Redo** invert or reapply the tip of the log. They also dismiss the assignment snackbar (it is session UI, not a History event). They mark the row undone (`undone` column) rather than appending a new event. A new forward action deletes the redo tail. Undo/Redo act on the tip, not on a selected row. Jump-to-event restore is out of scope.

Label with AI is one `propose` event for the batch (accepted rows; new labels in `created_label_ids`). Accept of a leftover stored proposal that mints a label is `add` then `accept`; Undo Accept first. Old `merge`/`split` rows without invert payload fields cannot be undone (Undo disabled while they are the tip).

| Type | When | Undo |
|------|------|------|
| `add` | Added the label | Deactivate that label |
| `recycle` | Group unlabeled comments onto a new `ungrouped` root | Deactivate that label; restore assignments |
| `rename` | Name change | Restore `before` |
| `edit` | Definition (`before`/`after` have `definition` and `detection_guidance`; leftover `notes` ignored) | Restore `before` |
| `move` | Parent/position change (`from_parent_id` / `to_parent_id`) | Move back |
| `flatten` | Descendants deactivated; their comments reassigned to this label | Reactivate descendants; restore labels |
| `remove` | Delete subtree (payload includes label/assignment dumps) | Restore the dump |
| `deactivate` | Leftover only (no UI control). Children became siblings; labeled comments on this label returned to Unlabeled | Reactivate; restore child parents and labels |
| `merge` | Merge (payload includes reassigned ids; source children reparented) | Reactivate sources; move rows back |
| `split` | LLM split (`keep_source: true`): parent stays; `source_id` is the leaf (omitted for header bootstrap); `created_ids` stay in the store (deactivated on undo); restore `deleted_assignments`; delete `created` accepted rows and `examples`; restore `replaced` and `deleted_examples`. Legacy rows without `keep_source`: reactivate source; deactivate created labels; restore deleted assignments |
| `propose` | Label with AI | Delete created accepted rows and examples; deactivate `created_label_ids`; restore any it replaced |
| `accept` | Accept | Assignment back to proposed; delete example if this accept created it |
| `change` | Change | Delete human assignment; restore proposal; delete example if created |
| `verify` | Verify | Set `verified=false` |
| `unverify` | Unverify (toggle protect off) | Set `verified=true` |
| `delete` | Delete (payload dumps the comment plus its assignments and sourced examples/counters) | Restore the dump |

`GET /api/history`: events newest first, each with `undone`, `summary`, and `details`: `{ explanation, comments: [{ text, label_name }], quotes: [{ heading, body }] }`. `payload` remains on the API for undo internals and is not shown in the UI. Top-level `can_undo`, `can_redo`. `POST /api/history/undo` and `POST /api/history/redo`: `{ ok: true }` or 400 if nothing to do / cannot invert.

`details` is built on the server at list time (`reviewdistill/history_details.py`) from the payload plus batched lookups. The client does not construct sentences or join rows. Payload names (`name`, `ungrouped_name`, `before`/`after`, label dumps on `remove`) take precedence over live rows so rename/add/remove stay accurate without a live label. Names are not snapshotted onto newly recorded events; a later rename can change the name shown for an old event that did not store one. `explanation` has no UUIDs. `quotes` are used for `edit` (saved definition; detection guidance only if it changed). History details caption comments with `label_name` (`null` when there is no label to caption: Verify, Unverify, Delete, unlabeled after remove, legacy sibling split). Failure to build `details` for one event falls back to `{ explanation: summary, comments: [], quotes: [] }` and does not fail the list.

Missing comment: skip it in batch lists (`propose`, flatten, merge, `keep_source` split); for a single-comment event (`accept`, `change`, `verify`, `unverify`, `delete`) show “Comment is no longer available.” Missing label: a payload name if any, otherwise “a label that is no longer available.” Unknown event types use `event_type` as the explanation.

A sophisticated visualization of splits and merges is not required for v0.1.
