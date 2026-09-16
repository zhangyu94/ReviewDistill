# Data schema

Stored shape of a **project** (paper), a proofreading **observation**, and a **label** in the ReviewDistill store.

Identity (when a source comment is new, a revision, a move, or gone) is defined in [`comment-identity.md`](comment-identity.md). Product spec: [`spec.md`](spec.md). This file is the schema of the rows that identity acts on.

Implementation: one JSONL file per collection in the ReviewDistill home folder (default `~/.reviewdistill`): `projects.jsonl`, `comments.jsonl`, `codings.jsonl`, `labels.jsonl`, `label_examples.jsonl`, `taxonomy_events.jsonl`. One JSON object per line, sorted by `id`. `reviewdistill paths use` / `move` choose that folder. `comments.project_id` is the `projects.id` of the paper.

The JSON object under `comment` in `GET /api/inbox` is the comment row (`created_at` as ISO-8601). `items` is the Unlabeled queue; `working_items` is every comment to distill (labeled included) so the UI can AND selectors without extra fetches. Each item has `in_working_set`. `progress.working_set` is the **to distill** headline. `progress` has no `absent` key; presence is `in_manuscript` on the item. Response extras (`project_name`, `permalink`, `guess`, `in_manuscript`, `labeled`, `label`, `coding`, `in_working_set`, `local_file`) are not columns on `comments`; `project_name` is `projects.name`. `in_manuscript` is `status == "active"`. `local_file` is true when `{projects.root_path}/{file_path}` resolves to a file that stays under that root (`..` does not count). The absolute path is not in the JSON. `POST /api/inbox/{comment_id}/reveal` (empty body) re-checks that path and selects the file in the OS file manager. Unknown comment is 404 (`Unknown comment {id}`); missing project, missing file, or path escape is 404 (`This file is not on this computer.`); file-manager failure is 400. Reveal does not write store rows or History.

---

## Project

A paper repository registered with ReviewDistill. One shared database holds many projects so the taxonomy accumulates across papers.

On-disk companion (not this table): `{root}/.reviewdistill/config.yaml` stores `project.id`, `project.name`, and `comments.latex_commands`. Comment-command names live only in that YAML; they are not columns on `projects`.

### Table

| Column | Type | Null | Default | Indexed |
| --- | --- | --- | --- | --- |
| `id` | string (UUID) | no | — | primary key |
| `name` | string | no | — | no |
| `root_path` | string | no | — | no |
| `created_at` | datetime (UTC) | no | now | no |

### Fields

#### `id`

Stable identity of the paper. Assigned once by `reviewdistill init` (`uuid4`) and written to `.reviewdistill/config.yaml`. Extract looks up this id; it does not mint a new one for an already-initialized repo.

#### `name`

Display name (Location “Project”, CLI). Taken from `--name` at init, or the directory name if omitted. Extract copies the current YAML `project.name` onto the row, so a later YAML rename is reflected after extract.

#### `root_path`

Absolute resolved path of the paper checkout. Set at init. Extract overwrites it with the directory you ran extract from, so a moved clone still resolves `file_path` (context rebuild, disappearance guessing).

#### `created_at`

Time the row was first inserted. Not updated when `name` or `root_path` change.

### How the row is written

- **Init:** inserts `id`, `name`, `root_path` if the repo is not already initialized.
- **Extract:** if the YAML id is missing from `projects`, inserts the same three fields; if present, refreshes `name` and `root_path` only.

---

## Comment

### Table

| Column | Type | Null | Default | Indexed |
| --- | --- | --- | --- | --- |
| `id` | string (UUID) | no | — | primary key |
| `project_id` | string | no | — | yes |
| `source_type` | string | no | — | no |
| `source_command` | string | no | — | no |
| `file_path` | string | no | — | no |
| `line_number` | integer | no | — | no |
| `raw_text` | string | no | — | no |
| `context_text` | string | no | `""` | no |
| `context_offset` | integer | yes | `null` | no |
| `section` | string | yes | `null` | no |
| `git_commit` | string | yes | `null` | no |
| `git_url` | string | yes | `null` | no |
| `status` | string | no | `"active"` | yes |
| `verified` | bool | no | `false` | no |
| `supersedes_id` | string | yes | `null` | no |
| `created_at` | datetime (UTC) | no | now | no |

`supersedes_id` is reserved for another `comments.id`; extract currently never sets it (revisions update the same row in place).

### Fields

#### `id`

Stable identity of the observation. Assigned once on insert (`uuid4`). Survives revision, move, absence from the source, and Verify.

#### `project_id`

Owning paper. Matches `.reviewdistill/config.yaml` `project.id` and `projects.id`.

#### `source_type`

How the comment was found in the manuscript. Current extractor always writes `latex_command`.

#### `source_command`

LaTeX macro name **without** the leading backslash (for example `myremark` for `\myremark{...}`). Taken from the project’s configured comment commands. It is a marker, not a label.

#### `file_path`

Path of the `.tex` file relative to the project root, using the extractor’s path (typically POSIX-style, e.g. `sections/03_formative_study.tex`). Resolved against `projects.root_path`.

#### `line_number`

1-based line of the opening `\<command>{` in that file. Not identity: a different remark on the same line is a different observation.

#### `raw_text`

What the reviewer wrote, after extract-time normalization: strip the command body, drop empty lines, join remaining lines with a single space.

The AI never writes this field. Source-driven **revision** of a still-present comment updates it in place (same `id`). Coding reads it; Export / Label Details / skill-eval examples use `context_text` when `label_examples.source_comment_id` points at this comment.

#### `context_text`

Nearby manuscript text at last extract, **not** the comment body.

Built as source TeX of the insertion neighborhood:

1. Find complete configured macros on the raw file (same brace rule as harvest; a `}` after `%` still closes).
2. Strip those macros (optional space before `{`; do not drop the rest of the line). A blank line inside `{...}` does not split the outer paragraph.
3. Drop unescaped `%` tails (line count unchanged).
4. Take the blank-line block that contains the opening command line.
5. If the span is empty, walk **up**, skipping blocks that are also empty after strip: consecutive heading / `\label` blocks (sectioning commands `\chapter` through `\subparagraph`, optional `*`), or the previous prose paragraph. Never a block below the comment.
6. Keep line breaks. Trim edge blanks. Do not append `Citations:` / `Refs:`.

When the comment is not in the manuscript, a non-binding guess compares stored `context_text` to a fresh extract of `{root_path}/{file_path}` at `line_number`.

#### `context_offset`

Character index into `context_text` of the hole left by this comment’s macro after strip / `%` tails / join, or `null`. The mark sits before that index, or at the end when the index equals the length. Walk-up (remark after a blank line, or only headings above) uses the length. Empty context is `null`. Missing key on an old row is `null` until the next extract that rebuilds context.

The hole is this remark, not another macro on the same line: extract matches harvest on `line_number`, `source_command`, and normalized `raw_text`, and takes the earlier file `start` if more than one still qualifies. `extract_context` needs those identity fields for an offset; omit them and the offset is `null`.

Not a sentinel inside `context_text`. Disappearance matching ignores this field. Retrieval, export, and skill-eval passages use unmarked `context_text`. History dumps and restores the field with the rest of the row (no new event type); an older payload without the key restores as `null`.

#### `section`

Nearest `\section` / `\subsection` titles at extract time, or `null`. Format when both exist: `{section} / {subsection}`.

#### `git_commit`

`HEAD` of the paper repo at last extract (`git rev-parse HEAD`), or `null` if the project is not a git checkout.

#### `git_url`

`origin` remote as git reports it (`git remote get-url origin`), or `null`. HTTP(S) and `ssh://` userinfo is stripped before storage, JSON, and permalinks, except a password-less `git` username (`https://git@git.overleaf.com/...`). This is a clone URL, not a web permalink. GitHub/GitLab file+line links are derived at read time from `git_url` + `git_commit` + `file_path` + `line_number`.

Exact same-wording pairing (within a file, across files, resurrect after a comment left the manuscript) is computed at extract time from `source_command` and `raw_text` (`fingerprint_for`). It is not a stored column. On load, a leftover `fingerprint` key is dropped and the store is rewritten.

#### `status`

Presence of the observation in the manuscript source. See [Presence](#presence).

#### `verified`

Human Verify stamp on the observation itself, independent of the label. See [Verified](#verified).

#### `supersedes_id`

Unused by current extract. Do not infer identity from it.

#### `created_at`

Time the row was first inserted. Not updated on revision, move, presence change, or Verify.

### Presence

`status` is extract-managed presence, not a UI queue.

| Status | Still in the manuscript source? | How it is set |
| --- | --- | --- |
| `active` | yes | New extract; resurrect when the same wording (same command + text) returns |
| `pending_disappeared` | no | Extract: present comment unmatched as revision/move |

Extract never Verify/Deletes. Exception: a wording revision clears verified to false. A deleted comment is gone; the same wording still in the file is a new observation (new `id`).

### Verified

| `verified` | Meaning | How it is set |
| --- | --- | --- |
| `false` | Default after extract; wording revision also clears a Verify stamp | Extract (new / revision) |
| `true` | Observation is verified. Does not confirm the label assignment | **Verify** |

On load, leftover `quality` strings map to this bool (`verified`/`unreviewed`); leftover `quality=dropped` rows are purged (comment plus dependents, no History event). Unknown `quality` still fails (`Unknown comment quality`). A leftover `fingerprint` key is dropped. A non-boolean `verified` fails (`Unknown comment verified`). After a mapping, purge, or fingerprint drop, the store is rewritten so later loads see only `verified`.

### Comments to distill

A comment is **to distill** (`in_working_set`) when it is in the manuscript (`status=active`) or `verified`. Progress shows this count as **to distill**; the JSON key remains `working_set`.

AI suggestions, taxonomy examples, label-chip counts, recent observations, and export use only comments to distill.

Selector views:

- **Unlabeled** — comments to distill with no **active** label, plus absent + not verified (so you can Verify or Delete). No Reject: not accepting a suggestion leaves the comment unlabeled. An accepted label on an inactive label does not count.
- **Label chip** — that label’s labeled comments to distill.

### What extract updates in place

On unchanged, revised, moved, or resurrected rows, extract refreshes location and git, and rebuilds `context_text` / `context_offset` / `section`. On revision it also updates `raw_text`, `source_command`, and `source_type`, and clears verified to false. It does not change `id`, `project_id`, `created_at`, or `supersedes_id`.

---

## Label

Live taxonomy node (`labels.jsonl`). The store is a forest: `parent_id` is null for a root, otherwise another label’s `id`. `position` is order among siblings (`0..n-1` after each sibling-list rewrite). A label may have children and its own accepted comments.

A **label** is a category in the scheme. Whether a comment is **labeled** lives on `codings.label_id`, not on this row. YAML/JSON **export** dumps wrap the list in `labels` and default to `review-taxonomy.yaml` / `.json` (taxonomy = the scheme).

| Column | Type | Null | Default |
| --- | --- | --- | --- |
| `id` | string | no | — |
| `name` | string | no | — |
| `parent_id` | string | yes | null (root) |
| `position` | int | no | 0 |
| `definition` | string | no | — |
| `detection_guidance` | string | yes | null |
| `status` | `active` / `inactive` | no | `active` |

An active label’s `parent_id` must be an active label; missing, inactive, or cyclic parents fail load. Inactive rows keep last `parent_id` / `position` for undo. Leftover `category` and `notes` keys in old files are ignored; they are not rewritten and `category` is not promoted into parent labels. `notes` is not a field. `detection_guidance` is used in retrieval and is not shown in Label Details.

`codings.proposed_parent_id` is the parent for a proposed **new** label (`null` = root). Unknown or inactive ids are treated as root.

---

## Related tables

| Table | Relationship |
| --- | --- |
| `codings` | many `codings.comment_id` → one comment; AI/human interpretation lives here |
| `label_examples` | optional `source_comment_id`; `text` is the passage excerpt (`context_text`) when sourced, not the remark |
| `taxonomy_events` | append-only history (`event_type`, `payload_json`, `undone`); Undo/Redo set `undone` rather than inserting a new row |

A comment may have several `codings` over time (`proposed`, `accepted`, `modified`). The observation row stays the evidence; coding rows stay the interpretation. Not accepting a suggestion leaves the comment unlabeled.
