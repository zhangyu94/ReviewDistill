ReviewDistill

AI-Assisted Continuous Distillation of Expert Review Practices

1. Overview

ReviewDistill is a local-first tool for continuously distilling an expert’s informal scholarly proofreading comments into a structured, evolving body of reusable review knowledge.

The user should be able to proofread papers naturally, using whatever commenting mechanism they already use. ReviewDistill then extracts those comments, associates them with manuscript context, and uses AI-assisted qualitative coding to identify recurring issues and patterns.

Over multiple papers and multiple review sessions, these observations are progressively distilled into an evolving taxonomy of review issues, including:

* nested labels (`parent_id`)
* definitions
* examples
* severity or importance
* contextual cues
* relationships between labels
* eventually, machine-detectable review rules

Classification uses one family with three roles:

| Role | Meaning | Word |
|---|---|---|
| Collection | the scheme / tree | **taxonomy** |
| Category | an abstract class in that scheme | **label** |
| Assignment | a comment classified with a category | **labeled** / **unlabeled**; a **label assignment** |

The tree header is **Label Taxonomy**, not **Labels** (that would read as a bag of assignments). Keep **taxonomy** only where it names the scheme: dump filenames `review-taxonomy.yaml` / `.json`, package `reviewdistill/taxonomy/`, History log `taxonomy_events.jsonl`, client `taxonomyTree.ts`. Product copy, HTTP, JSON, and store files use **label**, not **type** / **issue type**.

Unchanged: `Coding` rows, parking name **ungrouped**, inbox **Unlabeled**, **Label with AI**, Verify / unreviewed / to distill. YAML/JSON export wraps the list in `labels`. Skill-eval still scores `{"types": [...]}`.

The resulting knowledge can be exported as a review skill for coding agents such as Cursor.

2. Core Concept

The central workflow is:

Natural Expert Review
        │
        ▼
Informal Review Comments
        │
        ▼
Comment Extraction
        │
        ▼
Contextualized Observations
        │
        ▼
AI-Assisted Qualitative Coding
        │
        ▼
Recurring Labels
        │
        ▼
Evolving Review Taxonomy
        │
        ▼
Operational Definitions + Examples
        │
        ▼
Reusable Review Knowledge
        │
        ├──────────────► Coding-agent review skill
        │
        └──────────────► Future AI-assisted coding

The system should be incremental rather than a one-shot clustering tool.

Each new proofreading session should have the potential to:

1. reinforce an existing label;
2. provide new examples of an existing issue;
3. reveal a previously unseen issue;
4. suggest that an existing issue should be split;
5. suggest that multiple issues should be merged;
6. refine the definition or boundaries of an issue.

The taxonomy is therefore an evolving representation of the reviewer’s practice.

⸻

3. Goals

Primary goals

1. Allow the user to continue proofreading using their existing workflow.
2. Automatically collect review comments from the manuscript/repository.
3. Preserve the original comments and manuscript context.
4. Use AI to inductively code comments into recurring labels.
5. Maintain an evolving taxonomy of review issues.
6. Allow the expert to quickly validate, modify, merge, and split AI-generated labels.
7. Accumulate examples for each label.
8. Export the resulting review knowledge in a format usable by coding agents.

Secondary goals

* Track how the taxonomy evolves over time.
* Associate comments with Git commits.
* Eventually connect comments to the revisions made by paper authors.
* Support multiple projects/papers.
* Support multiple LaTeX commenting syntaxes.
* Make the underlying representation independent of LaTeX so other review sources can be added later.

⸻

4. Non-Goals for v0.1

Do not attempt to build:

* a general-purpose LaTeX editor;
* a full Overleaf replacement;
* a fully autonomous paper reviewer;
* automatic modification of manuscript text;
* a cloud-based collaborative review platform;
* a complex multi-user permission system;
* a general-purpose annotation platform;
* a sophisticated vector database infrastructure;
* a large autonomous multi-agent architecture.

The prototype should demonstrate the distillation loop, not solve every aspect of scholarly reviewing.

⸻

5. Primary User Workflow

The intended workflow should require minimal behavioral change from the reviewer.

Step 1 — Initialize a project

reviewdistill init

This creates a project configuration such as:

project:
  name: paper-01
comments:
  latex_commands:
    - myremark

Multiple commands should be supported:

comments:
  latex_commands:
    - myremark
    - note
    - review

The exact commands are project-specific.

The system must not assume that all projects use \myremark.

Step 2 — Proofread normally

The user continues to annotate the LaTeX source using their existing commands.

For example:

The results demonstrate that ...
\myremark{I think "demonstrate" is too strong here. The experiment only provides evidence for this claim.}

Another project might use:

\note{This paragraph does not explain why this design decision was necessary.}

The extraction layer should treat the syntax as an input mechanism, not as a semantic label.

Step 3 — Extract comments

reviewdistill extract

ReviewDistill identifies new comments and extracts:

* comment text
* source file
* line number
* source command
* surrounding manuscript text
* section/subsection
* Git commit
* other available contextual information

Step 4 — AI-assisted coding

In `reviewdistill ui`, **Label with AI** in the Comments header (shown whenever unlabeled comments still need proposals, even if the Unlabeled chip is off). A thin progress bar at the top of the window runs until the batch finishes.

Header **Settings** (next to History and Export) has two panels. **Assistant** writes `llm.provider` / `llm.model` to the ReviewDistill home `config.yaml` and the matching API key to that folder’s `.env` (gitignored). **Data** shows the home folder (same as `reviewdistill paths`) in an editable field, or **Choose…** to pick a folder; **Save** is `paths use` (points at that folder, does not copy files). **Open folder** reveals it in the file manager. Backup and `paths move` are in that folder’s `README.md`. Opening Settings always lands on Assistant. The Unlabeled empty state **Configure LLM** opens the same dialog. GET `/api/llm-settings` returns the saved key (`api_key`) so Settings can show it (password + show/hide); it reads home files only (not `REVIEWDISTILL_LLM_*`). File editing still works. Label with AI is store-wide, so leftover paper `llm:` / `.env` are ignored. Process environment still wins over `.env`. `REVIEWDISTILL_LLM_PROVIDER` / `REVIEWDISTILL_LLM_MODEL` override home YAML at run time. Do not write `llm.api_key` into YAML; do not store keys in the JSONL store.

`reviewdistill paths use DIR` persists `DIR` in `~/.config/reviewdistill/home` so later CLI commands use that folder. `reviewdistill paths move DIR` copies the current home (JSONL files, `config.yaml`, `.env`) into an empty `DIR`, then uses it; it leaves the old folder in place and refuses if the store is busy.

Assistant fields: Provider (DeepSeek / OpenAI / Anthropic), Model (filled with that provider’s default), API key (password + show/hide, filled from home `.env` when set). There is no paper picker. Save is disabled until a provider is chosen. An empty key field on Save keeps the existing `.env` value. `POST /api/llm-settings` with `api_key` omitted or `""` means keep; unknown provider 400; new provider with no key 400. This dialog does not probe the key live or offer mock / Ollama / custom base URL.

For each new observation, AI considers:

* the raw comment;
* manuscript context;
* existing labels;
* previous similar comments;
* examples associated with those labels.

It proposes:

Existing label:
  Overclaiming
Confidence:
  0.91
Rationale:
  The reviewer objects to "demonstrate" because the evidence
  only supports a weaker claim.
Suggested evidence:
  "demonstrate" → "suggest"

Alternatively, it may propose:

Added the label:
  Insufficient justification of methodological choice
Definition:
  The manuscript describes a methodological or design decision
  without explaining why that decision was made.

Step 5 — Human validation

The reviewer sees Label Taxonomy, Label Details, and Comments.

For each comment:

────────────────────────────────────────
Comment
"This paragraph does not explain why this design
decision was necessary."
Context
"We designed the interface using ..."
────────────────────────────────────────
Assign label
New: Insufficient methodological justification  Why?  [Accept]
[Choose a label… ▾]
Triage
[lock Verify] [bin Delete]
Location
file (click shows it on this computer when the `.tex` file still exists), line, heading, …
────────────────────────────────────────

A stored proposal stays until Accept or a label is picked in the menu. Selecting a label assigns it; there is no Change button. The menu shows the current label when the comment is labeled. Label with AI does not have to be clicked again this session. An existing-label id that is not in the active taxonomy is **No AI suggestion**, not a fake title. A new proposal without `proposed_label_name` is also **No AI suggestion**, is not stored, and stays in the Label with AI queue. An accepted coding on an inactive label is unlabeled and stays in that queue too.

The user should be able to validate a suggestion with minimal interaction.

Step 6 — Continuous accumulation

After multiple reviews, the system may have:

Overclaiming
  17 observations
Missing methodological justification
  9 observations
Ambiguous terminology
  14 observations
Unsupported causal claim
  7 observations
Weak motivation
  12 observations

The system should continuously use these accumulated observations to improve future coding.

⸻

6. Core Data Model

The system should explicitly separate raw observations from AI interpretations.

6.1 ProofreadingComment

Represents what the reviewer actually wrote. Field definitions, statuses, and extract pairing: `docs/data-schema.md`.

ProofreadingComment(
    id,
    project_id,
    source_type,
    source_command,
    file_path,
    line_number,
    raw_text,
    context_text,
    section,
    git_commit,
    git_url,
    status,
    verified,
    supersedes_id,
    created_at
)

Important principle:

raw_text must never be overwritten by AI interpretation.

The original observation is the primary evidence.

⸻

6.2 Coding

Represents an AI or human interpretation of a comment.

Coding(
    id,
    comment_id,
    label_id,
    coder_type,
    confidence,
    rationale,
    status,
    created_at
)

Possible coder_type:

ai
human

Possible status:

proposed
accepted
modified

A comment may eventually have multiple codings.

⸻

7. Label Taxonomy

The taxonomy represents the reviewer’s evolving conceptualization of common problems.

A label should contain approximately:

Label(
    id,
    name,
    parent_id,
    position,
    definition,
    status,
    created_at,
    updated_at
)

The live taxonomy is a forest of arbitrary depth. `parent_id` is null for a root, otherwise another label’s id. `position` is order among siblings and is rewritten to `0..n-1` whenever that sibling list changes. Every node is a real label: it can have children and its own labeled comments. There are no folder-only nodes.

Invariants: `parent_id` is null or an **active** label; there are no cycles. Inactive labels keep their last parent and position so undo can restore them; they are omitted from the live tree. Active `name` stays unique the same way as image-taxonomy-labeler: if `Overclaiming` is taken, the next is `Overclaiming (2)`, filling gaps. Create uses name `New label`, `New label (2)`, …. Rename and Accept of a new label use the same name suffix. Inactive names do not block a live name.

Load does not rewrite leftover `category` or `proposed_issue_category` fields. Missing `parent_id` is a root. An active label whose parent is missing, inactive, or cyclic fails fast. Do not promote old category strings into parent labels.

A proposal for a **new** label stores `proposed_parent_id`: an existing active label id, or null for a root. Unknown or omitted parent becomes a root. Do not mint an intermediate parent from a free-text name.

Example:

name: Overclaiming
parent_id: null
definition: >
  A claim is stated more strongly than the evidence or analysis
  presented in the manuscript supports.

Each label should additionally support:

Examples

"The results demonstrate..."
→ evidence only supports "suggest"

Notes

Additional observations from the reviewer.

⸻

8. Taxonomy as an Evolving Object

The taxonomy must not be treated as a static list generated once.

ReviewDistill should support:

Add

Create a new label.

Rename

"Overly strong claim"
→
"Overclaiming"

Edit

Refine the definition.

Merge

"Unsupported claim"
+
"Overly strong claim"
→
"Overclaiming"

Split

"Insufficient explanation"
→
"Missing motivation"
+
"Missing methodological justification"

Move

Nest a label under another, or reorder it among siblings (before / after).

Flatten

Reassign descendant comments onto this label and deactivate the descendants.

Remove

Delete this label and its subtree. Undo restores the dump.

Deactivate

There is no Deactivate button and no HTTP deactivate route. Flatten, split, and merge still retire labels this way: the group leaves the live taxonomy, children become siblings, and labeled comments on that label return to Unlabeled. Codings are stored on the history event so undo restores them. A leftover accepted assignment on an inactive label does not count as labeled. Export unchecking a label is a one-shot filter (`--id`); it does not deactivate the row.

Historical data must never be silently deleted when the taxonomy changes.

⸻

9. AI Coding Strategy

The coding process should be inductive, inspired by qualitative coding rather than predetermined classification.

For every new comment:

Stage 1 — Retrieve potentially relevant existing issues

Search the existing taxonomy and previously coded comments.

Possible approaches:

* lexical similarity;
* embeddings;
* LLM semantic comparison;
* simple database queries.

For v0.1, embeddings are optional.

A vector database is not required.

Stage 2 — Generate coding candidates

The model should consider:

Existing label A
Existing label B
Existing label C
New label

and produce a ranked recommendation.

Stage 3 — Explain the recommendation

The AI should explain:

Why does this comment belong to this label?

The explanation should refer to the actual observation and manuscript context.

Stage 4 — Allow disagreement

The AI must not silently modify the taxonomy.

The human reviewer remains the authority.

⸻

10. Important Distinction: Observation vs Interpretation

The system should explicitly preserve the distinction between:

Observation

“I think ‘demonstrate’ is too strong here.”

and:

Interpretation

“Overclaiming”

and:

Operational rule

Flag strong evidential verbs such as “demonstrate” when the cited evidence is observational rather than causal.

This progression is fundamental to ReviewDistill:

Observation
    ↓
Code
    ↓
Label
    ↓
Definition
    ↓
Examples / Counterexamples
    ↓
Operational Review Rule

The system should not prematurely collapse these levels.

⸻

11. Context Extraction

A comment without manuscript context is often ambiguous.

Context is the **insertion neighborhood** in the `.tex` file — not a search of the paper and not an LLM judgment of what the remark refers to. Remarks that point elsewhere rely on the comment wording.

For each comment, extract:

* the blank-line paragraph that contains the command, with configured comment macros stripped on the raw file (same brace rule as harvest) then `%` tails removed (a blank line inside `{...}` is not an outer paragraph break);
* if that paragraph is empty after strip, headings / `\label` immediately above, or the previous prose paragraph, skipping other empty-after-strip remarks (never the next paragraph after a heading);
* section/subsection titles (separate field);
* source file and line number.

The inspector and the coding prompt see that same source TeX. Details: website `docs/extract.md`.

Example:

Comment:
"I don't think this follows."
Section:
Results / Accuracy
Context:
"Model A achieved higher accuracy than Model B.
Therefore, Model A is more suitable for real-world applications."

⸻

12. Git Integration

Because the manuscripts are likely Git repositories, Git should be integrated from the beginning.

For every extracted comment, record:

repository
remote URL (if a git remote such as origin is configured)
commit hash
file
line

This makes it possible to later reconstruct:

Original manuscript
       ↓
Reviewer comment
       ↓
Author revision
       ↓
Final manuscript

This is particularly valuable for future versions of ReviewDistill.

For example:

Original:
"The results demonstrate that..."
Reviewer:
"Too strong."
Revision:
"The results suggest that..."

This could eventually become a high-quality example of the review rule:

When evidence does not establish a claim conclusively,
prefer weaker epistemic language.

Version-to-version revision linkage is not required for v0.1, but the data model should not prevent it.

⸻

13. Continuous Distillation

This is the defining feature of ReviewDistill.

The system should maintain a distinction between:

Current review corpus

All raw comments accumulated across papers.

Current coding state

The latest accepted coding of those comments.

Current taxonomy

The reviewer’s current conceptualization of recurring issues.

Review knowledge

The operationalized knowledge derived from the taxonomy.

Conceptually:

                 New Review
                     │
                     ▼
             New Observations
                     │
                     ▼
        ┌────────────────────────┐
        │ Existing Review Corpus │
        └────────────┬───────────┘
                     │
                     ▼
              AI Re-coding /
             Pattern Discovery
                     │
                     ▼
          Evolving Taxonomy
                     │
                     ▼
         Refined Review Knowledge
                     │
                     ▼
           Future Review Coding

The prototype should make this accumulation visible.

For example:

ReviewDistill has processed 184 comments across 7 papers.

12 recurring labels have been identified.

3 labels were introduced this month.

2 labels were merged after additional evidence.

⸻

14. UI

The primary UI should be a local web application.

The central screen is Label Taxonomy, Label Details, and Comments on one screen — not a generic dashboard.

Example:

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

The top bar stays on this screen. **History**, **Settings**, and **Export** are chips on the right; History and Settings open dialogs. Export opens a format picker plus a checkbox tree of labels to include. **GitHub** and **Docs** sit further right as text links and open the repository and documentation website in a new tab. Selectors are chips on the left. The right-hand Unlabeled control toggles a left-hand Unlabeled chip and is never pressed. Present chips AND. No chips: Comments lists comments to distill. Clicking a label opens Label Details and does not clear Unlabeled. If Unlabeled is off, the label chip is that label. If Unlabeled is on, the label chip stays off (`labelchip=0`) so Comments stays the unlabeled queue (Unlabeled ∧ label is almost always empty). Hover **+** and merge use the same rule. × on the label chip sets `labelchip=0` and keeps `/labels/:id`. Toggling Unlabeled keeps the current label-chip state. Unlabeled and labels share this one screen.

| URL | Label Details | Unlabeled chip | Label chip |
| --- | --- | --- | --- |
| `/` | empty | off | none |
| `/?unlabeled=1` | empty | on | none |
| `/labels/:id` | that label | off | that label |
| `/labels/:id?unlabeled=1` | that label | on | that label |
| `/labels/:id?labelchip=0` | that label | off | none |
| `/labels/:id?unlabeled=1&labelchip=0` | that label | on | none |

`labelchip=0` means Label Details is open and the label chip is off. Selecting a label (click, hover **+**, merge) writes it when Unlabeled is on; × on the label chip always writes it; split always lands Unlabeled on and the label chip off. Clicking a label while Unlabeled is off omits `labelchip=0` (label chip on). `?id=` still names the open comment.

Selectors and Progress span the window. Under Selectors, two cards: Label Taxonomy over Label Details, and Comments, equal width. Clicking a label opens Label Details. The label chip turns on only when Unlabeled is off; with Unlabeled on it stays off so the unlabeled queue is not ANDed empty. The Comments header shows **N to distill** with no chips, or **N matching · M to distill** when chips AND. **Label with AI** appears whenever unlabeled comments still need proposals. The open comment is the highlighted row (list) or the inspector plus pager (one-at-a-time); it is not a second count.

A bottom Progress strip is display-only. The headline is the count of comments to distill. unlabeled is comments to distill with no label (labeled is the rest of those comments). verified is comments to distill that have been Verified (the rest of those comments are still not verified). The Unlabeled chip has no count. With no chips, Comments lists comments to distill. With only Unlabeled, Comments is the inbox queue (unlabeled comments to distill plus left-the-manuscript + not verified), not `progress.unlabeled`. The strip is not clickable.

The Comments panel can switch between a list of comments and a single comment. The list shows truncated text so you can scan, the assigned **leaf label(s)** when the comment has them, and a **Left the manuscript** chip when the remark is no longer in the `.tex` file. The single-comment view shows the full text, manuscript context, location, and record metadata. When `{projects.root_path}/{file_path}` is still a file, Location **File** is a control (same blue as Remote; title **Show this file on this computer**; not a `file://` link). Click `POST /api/inbox/{comment_id}/reveal` with no body: the server selects that file in the OS file manager (`open -R` on macOS — it does not open the default editor). If the checkout is gone, File stays plain text. A comment that left the manuscript can still reveal if the `.tex` file exists. Reveal does not write the store or History. Unknown comment is 404 (`Unknown comment {id}`); missing or escaped path is 404 (`This file is not on this computer.`); file-manager failure is 400. Failures show in the Comments error slot. **Accept** applies the AI suggestion. Picking a label in the menu assigns or changes it (there is no Change button and no Reject: not accepting a suggestion leaves the comment unlabeled). **Verify** stamps quality, independent of the label. **Delete** removes the observation (undo from History).

Present chips AND. Sure/Unsure confidence chips are not in this product. **Remove** (undoable) is how a label leaves the live taxonomy. There is no Deactivate control.

⸻

15. Taxonomy View

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

The taxonomy tree is full width of the taxonomy card and takes leftover height (names still `truncate` if they overflow). Label Details is a compact `shrink-0` strip under the tree; a long definition scrolls inside the strip (`max-h-40`) so the forest keeps most of the card. View is the name as a title line, then the definition as prose — no **Name** / **Definition** / **Label** kickers. The strip stays when nothing is selected (“Select a label.” / “This label was not found.”) so the card does not jump.

Label Details does not repeat comment text. Labeled comments in the Comments panel are the examples. A comment is labeled only when its accepted label is still active. Export lives in the header: format plus an indented checkbox tree of active labels (each node independent; all checked to start). Download writes only the checked ids. Unchecked labels stay in the taxonomy. `GET /api/labels/export?id=` (repeatable) and `reviewdistill export --id` are the same filter.

Drag an unlabeled comment onto a **leaf**: same as picking that label in the menu. Dropping onto a parent is ignored. The label menu lists leaves only (Accept and Label with AI the same).
Drag a label onto the top or bottom of another row: reorder as a sibling (`before` / `after`).
Drag onto the middle of a row: nest as a child (`inner`).
On a leaf, a **merge** chip appears while dragging a label; dropping on the chip merges (source into target; source children are reparented onto the target).
Header **+** adds a root label. Header fork (enabled only when the forest is empty, at least two unlabeled working-set comments exist, and an LLM is configured) creates root labels from those comments. Header fork includes unlabeled comments that already have an AI proposal (unlike Label with AI, which skips those). Header recycle (enabled only when the forest is non-empty and at least two unlabeled working-set comments exist; no LLM) adds a root named `ungrouped` (or `ungrouped (2)` if taken) and accept-assigns those comments onto it. After recycle, Unlabeled is off and the label chip is on so Comments shows that pile; leaf fork then clusters it. `POST /api/labels/recycle` is registered next to merge/split so `recycle` is not parsed as an id. Hover **+** on a **leaf** adds `New label` and an `ungrouped` child, and reassigns that leaf’s labels onto `ungrouped` (one history event). The recycle root and that parking child share a name family; they are different nodes. Hover **+** on a parent only adds `New label`. Hover fork on a leaf with at least two labeled comments keeps that label as parent and creates N ≥ 2 children. The model names and defines each label and proposes a child per comment; it does not rewrite the parent. One prompt per split; invalid or incomplete JSON writes nothing. Drop unused model labels; fail the whole call if fewer than two assigned labels remain. Accept / Change in Comments review those placements. After a successful split, Unlabeled is on and the label chip is off (`labelchip=0`) so Comments lists proposals (a label chip only shows accepted labels). `POST /api/labels/split` is header bootstrap (registered next to merge so `split` is not parsed as an id); `POST /api/labels/{id}/split` is leaf split with no body. Flatten reassigns descendant comments onto the node and deactivates descendants. Remove deletes the subtree (undoable). One **Edit** on the Label Details header edits name and definition together. **Edit** shows labeled Name and Definition; **Save** is disabled when either is blank after trim; **Cancel** restores both. Save calls `POST /api/labels/{id}/rename` and/or `POST /api/labels/{id}/edit` only for fields that changed (two requests, not one transaction). Label Details does not show `detection_guidance` (retrieval still concatenates it). Label Details does not repeat the taxonomy path. There is no Deactivate control; flatten / split / merge may still retire types as part of those actions.
The tree defaults to expanded. The chevron expands or collapses; clicking the **name** selects (it does not expand).
Drag uses native HTML5 only.

The Comments header has list / one-comment controls. The list is for scanning. One comment shows context and metadata, with prev / pager / next at the bottom (one comment per page).

Overclaiming
A claim is stronger than the evidence supports.

⸻

16. Taxonomy Evolution View

History is a chronological log of taxonomy mutations and labeling verdicts (the `taxonomy_events` table). The History dialog lists each event with a short summary. Rows that have extra information (comment text, a saved definition, merge/split names, a move destination) show a chevron that expands those details in place. **Undo** and **Redo** invert or reapply the tip of the log. They mark the row undone (`undone` column) rather than appending a new event. A new forward action deletes the redo tail. Undo/Redo act on the tip, not on a selected row. Jump-to-event restore is out of scope.

Label with AI is one `propose` event for the batch. Accept of a newly created label is `add` then `accept`; Undo Accept first. Old `merge`/`split` rows without invert payload fields cannot be undone (Undo disabled while they are the tip).

| Type | When | Undo |
|------|------|------|
| `add` | Added the label | Deactivate that label |
| `recycle` | Group unlabeled comments onto a new `ungrouped` root | Deactivate that label; restore assignments |
| `rename` | Name change | Restore `before` |
| `edit` | Definition (`before`/`after` have `definition` and `detection_guidance`; leftover `notes` ignored) | Restore `before` |
| `move` | Parent/position change (`from_parent_id` / `to_parent_id`) | Move back |
| `flatten` | Descendants deactivated; their comments reassigned to this label | Reactivate descendants; restore labels |
| `remove` | Delete subtree (payload includes label/coding dumps) | Restore the dump |
| `deactivate` | Leftover only (no UI control). Children became siblings; labeled comments on this label returned to Unlabeled | Reactivate; restore child parents and labels |
| `merge` | Merge (payload includes reassigned ids; source children reparented) | Reactivate sources; move rows back |
| `split` | LLM split (`keep_source: true`): parent stays; `source_id` is the leaf (omitted for header bootstrap); `created_ids` stay in the store (deactivated on undo); restore `deleted_codings`; delete `created` proposals; restore `replaced`. Legacy rows without `keep_source`: reactivate source; deactivate created labels; restore deleted codings |
| `propose` | Label with AI | Delete created proposed rows; restore any it replaced |
| `accept` | Accept | Coding back to proposed; delete example if this accept created it |
| `change` | Change | Delete human coding; restore proposal; delete example if created |
| `verify` | Verify | Set `verified=false` |
| `unverify` | Unverify (toggle protect off) | Set `verified=true` |
| `delete` | Delete (payload dumps the comment plus its codings and sourced examples/counters) | Restore the dump |
| `drop` | Legacy Drop (no store change) | No-op |

`GET /api/history` — events newest first, each with `undone`, `summary`, and `details`: `{ explanation, comments: [{ text, label_name }], quotes: [{ heading, body }] }`. `payload` remains on the API for undo internals and is not shown in the UI. Top-level `can_undo`, `can_redo`. `POST /api/history/undo` and `POST /api/history/redo` — `{ ok: true }` or 400 if nothing to do / cannot invert.

`details` is built on the server at list time (`reviewdistill/history_details.py`) from the payload plus batched lookups. The client does not construct sentences or join rows. Payload names (`name`, `ungrouped_name`, `before`/`after`, label dumps on `remove`) take precedence over live rows so rename/add/remove stay accurate without a live label. Names are not snapshotted onto newly recorded events; a later rename can change the name shown for an old event that did not store one. `explanation` has no UUIDs. `quotes` are used for `edit` (saved definition; detection guidance only if it changed). History details caption comments with `label_name` (`null` when there is no label to caption: Verify, Unverify, Delete, legacy Drop, unlabeled after remove, legacy sibling split). Failure to build `details` for one event falls back to `{ explanation: summary, comments: [], quotes: [] }` and does not fail the list.

Missing comment: skip it in batch lists (`propose`, flatten, merge, `keep_source` split); for a single-comment event (`accept`, `change`, `verify`, `unverify`, `drop`, `delete`) show “Comment is no longer available.” Missing label: a payload name if any, otherwise “a label that is no longer available.” Unknown event types use `event_type` as the explanation.

A sophisticated visualization of splits and merges is not required for v0.1.

⸻

17. CLI

The initial CLI should be approximately:

reviewdistill init

Initialize a repository.

reviewdistill extract

Extract new proofreading comments.

reviewdistill export

Export reusable review knowledge.

reviewdistill ui

Start the local web UI.

Future:

reviewdistill review

Use the distilled knowledge to review a new manuscript.

⸻

18. Export Format

The exported review knowledge should be human-readable and usable by coding agents.

Markdown is an agent skill (`SKILL.md`): YAML frontmatter, a short review procedure, then the labels. For example:

---
name: scholarly-review
description: Review a scholarly manuscript against this author's distilled label taxonomy. Use when proofreading, reviewing, or checking a paper.
---

# Scholarly Review

Review the manuscript against the labels below. For each label, flag passages that match the definition and examples.

## Overclaiming
### Definition
Flag claims whose strength exceeds the evidence presented.
### Examples
- "The results demonstrate..." when evidence is correlational.
- "This proves..." when the experiment does not establish causality.

A YAML/JSON representation should also be supported for programmatic use. Those formats are a taxonomy dump: a flat list of labels with `parent_id` (null for roots), not a nested `children` blob. Markdown may show a `Parent:` line by parent name.

⸻

19. Coding-Agent Integration

The exported Markdown skill should be usable by tools such as Cursor. Put `SKILL.md` in `.cursor/skills/scholarly-review/` (or the equivalent for another agent).

Conceptually:

ReviewDistill
     │
     │ export
     ▼
SKILL.md
     │
     ▼
Coding Agent
     │
     ▼
New Manuscript
     │
     ▼
Potential Review Issues

The coding agent should not simply receive a list of labels.

It should receive:

When to apply the skill
How to apply it
Issue
Definition
Examples

This transforms qualitative coding results into operational review knowledge.

⸻

20. Source Extraction Architecture

The comment-extraction layer should be extensible.

Define an interface conceptually like:

class CommentExtractor:
    def extract(self, source) -> list[ProofreadingComment]:
        ...

Initial implementation:

LatexCommandExtractor

Future implementations:

GithubReviewExtractor
MarkdownExtractor
WordCommentExtractor

The normalized output should always be ProofreadingComment.

This ensures that the system’s conceptual model is not tied to LaTeX.

⸻

21. LaTeX Extraction

The extractor should support configurable commands.

Example:

comments:
  latex_commands:
    - myremark

or:

comments:
  latex_commands:
    - myremark
    - question
    - revise

The parser should extract comments robustly enough to handle:

* multiline comments;
* comments containing LaTeX;
* comments near paragraphs;
* escaped characters;
* nested braces where feasible.

The command name should be retained:

source_command = "question"

but should not automatically determine the semantic label.

For example:

\question{This argument does not follow.}

could still be coded as:

Logical gap

⸻

22. Incremental Extraction

Extraction must be idempotent.

Running `reviewdistill extract` twice must not duplicate comments that are still present.

Identity (new, revision, move, gone from the source, Verify vs Delete) is defined in [`comment-identity.md`](comment-identity.md). The stored project and comment rows are [`data-schema.md`](data-schema.md).

`reviewdistill extract --watch` runs the same extraction after LaTeX sources settle. It does not run labeling and does not Verify or Delete.

The AI never overwrites the reviewer’s comment text. Source-driven revision of a still-present comment updates that observation’s wording in place.

⸻

23. Storage

Use JSONL files in the home folder (one object per line, sorted by id).

Suggested entities:

projects
comments
codings
labels
label_examples
taxonomy_events

JSONL files in the home folder, one object per line. SQLModel (or Pydantic) records are fine.

No external database server should be required.

⸻

24. Local-First / Privacy

The prototype should be local-first.

The manuscript and review comments should remain on the user’s machine unless the user explicitly configures an external LLM.

LLM access should be abstracted behind a provider interface:

class LLMProvider:
    def generate(...)

Potential providers:

* OpenAI
* Anthropic
* DeepSeek
* local models

The application should make it clear when manuscript content is being sent externally.

Where practical, send only the minimum necessary context:

review comment
+
relevant manuscript context
+
relevant existing issue definitions/examples

Do not send the entire repository unnecessarily.

⸻

25. Suggested Technical Stack

A reasonable prototype stack is:

Backend

* Python
* Typer for CLI
* FastAPI for local API
* JSONL files in the home folder

Frontend

* Vue 3 + TypeScript SPA (`client/`)
* FastAPI JSON under `/api`
* `reviewdistill ui` serves the built SPA (no Node at runtime)

However, simplicity is more important than these specific technologies.

⸻

26. Suggested Project Structure

reviewdistill/
│
├── cli/          init, extract, export, ui
├── extraction/   LaTeX comments + incremental match
├── coding/       AI propose, retrieve, validate
├── taxonomy/     labels, merge/split, export
├── context/      manuscript neighborhood
├── llm/          provider interface
├── db/           JSONL models and session
└── web/          FastAPI `/api` + packaged client static

The exact structure can be simplified for the prototype.

⸻

27. AI Prompting Principles

AI prompts should explicitly distinguish:

What the reviewer observed

from:

What the AI infers

For example:

Reviewer observation:
"I think 'demonstrate' is too strong."
Manuscript context:
"The experiment..."
Existing labels:
id, name, parent_id
...
Task:
Determine whether this observation is best explained by an
existing label. If so, recommend the best match.
If no existing label adequately captures the observation,
propose a candidate new label (parent_id of an existing
label, or omit for a root).
Do not modify the taxonomy automatically.

This helps preserve the qualitative-analysis character of the system.

⸻

28. Human-in-the-Loop Principle

The system should be AI-assisted, not AI-authoritative.

The reviewer is the expert whose practice is being distilled.

Therefore:

AI proposes
      ↓
Human validates
      ↓
Taxonomy changes
      ↓
Future AI proposals improve

Human decisions should themselves become data.

For example:

AI proposed:
Unsupported claim
Human selected:
Overclaiming

This provides evidence that the AI’s conceptualization was incorrect and can improve future suggestions.

⸻

29. Future Research Direction

The prototype should leave room for a stronger research system in which ReviewDistill learns a reviewer’s practice over many papers.

Potential future capabilities include:

Review-pattern discovery

Automatically identify patterns that have not yet been formally coded.

Taxonomy refinement

Detect when an existing label has become too broad.

Reviewer-specific modeling

Learn what particular issues a reviewer tends to identify.

Revision-aware learning

Connect comments to subsequent author revisions.

Agentic review

Use the distilled knowledge to review new manuscripts automatically.

Confidence calibration

Determine which review issues can be reliably detected by an AI and which require human judgment.

Review-practice comparison

Potentially compare the taxonomies of different reviewers.

⸻

30. Prototype Success Criterion

The prototype is successful if the following workflow works end-to-end:

1. Clone a paper repository.
2. Configure its LaTeX comment commands.
3. Proofread normally.
4. Run:
       reviewdistill extract
5. ReviewDistill automatically finds the comments.
6. It extracts manuscript context.
7. In `reviewdistill ui`, Label with AI.
8. AI proposes codes using the accumulated taxonomy.
9. The reviewer rapidly labels comments (Accept or pick a label), uses **Verify**, or uses **Delete** for a bad extract.
10. The taxonomy accumulates examples and definitions.
11. Review a second paper.
12. The accumulated taxonomy improves the coding of its comments.
13. Export:
       SKILL.md
14. Use the skill with a coding agent to review a new paper.

The key demonstration is therefore not merely that AI can classify proofreading comments.

The key demonstration is:

A stream of informal expert review comments can be continuously distilled into an evolving, operationalized representation of the expert’s review practice, which can subsequently be reused by AI systems.

⸻

31. Research Framing

A useful conceptual framing for the project is:

ReviewDistill investigates how AI can continuously distill informal expert review observations into an evolving, reusable representation of scholarly review practice.

The process resembles qualitative analysis:

Open coding
    ↓
Recurring observations
    ↓
Category formation
    ↓
Category refinement
    ↓
Operational definitions
    ↓
Examples
    ↓
Reusable coding/review framework

But the distinctive system contribution is the continuous loop:

             ┌─────────────────────┐
             │                     │
             ▼                     │
       Expert Reviews              │
             │                     │
             ▼                     │
      Informal Comments            │
             │                     │
             ▼                     │
       AI Coding                   │
             │                     │
             ▼                     │
    Evolving Taxonomy              │
             │                     │
             ▼                     │
    Operationalized Rules          │
             │                     │
             ▼                     │
       Future Reviews ─────────────┘

The system thus treats proofreading not simply as annotation, but as a source of continuously accumulating review knowledge.