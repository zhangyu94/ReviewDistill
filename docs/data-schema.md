# Data schema

Stored shape of a **project** (paper), a proofreading **observation**, and an **issue type** in the ReviewDistill store.

Identity (when a source comment is new, a revision, a move, or gone) is defined in [`comment-identity.md`](comment-identity.md). Product spec: [`spec.md`](spec.md). This file is the schema of the rows that identity acts on.

Implementation: one JSONL file per collection in the ReviewDistill home folder (default `~/.reviewdistill`): `projects.jsonl`, `comments.jsonl`, `codings.jsonl`, `issue_types.jsonl`, `issue_examples.jsonl`, `issue_counterexamples.jsonl`, `taxonomy_events.jsonl`, `git_commits.jsonl`. One JSON object per line, sorted by `id`. `reviewdistill paths use` / `move` choose that folder. `comments.project_id` is the `projects.id` of the paper.

The JSON object under `comment` in `GET /api/inbox` is the comment row (`created_at` as ISO-8601). `items` is the Unlabeled queue; `working_items` is every comment to distill (labeled included) so the UI can AND selectors without extra fetches. Each item has `in_working_set`. `progress.working_set` is the **to distill** headline. `progress` has no `absent` key; presence is `in_manuscript` on the item. Response extras (`project_name`, `permalink`, `guess`, `in_manuscript`, `labeled`, `issue`, `coding`, `in_working_set`, `local_file`) are not columns on `comments`; `project_name` is `projects.name`. `in_manuscript` is `status == "active"`. `local_file` is true when `{projects.root_path}/{file_path}` resolves to a file that stays under that root (`..` does not count). The absolute path is not in the JSON. `POST /api/inbox/{comment_id}/reveal` (empty body) re-checks that path and selects the file in the OS file manager. Unknown comment is 404 (`Unknown comment {id}`); missing project, missing file, or path escape is 404 (`This file is not on this computer.`); file-manager failure is 400. Reveal does not write store rows or History.

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
| `section` | string | yes | `null` | no |
| `git_commit` | string | yes | `null` | no |
| `git_url` | string | yes | `null` | no |
| `fingerprint` | string | no | — | yes |
| `status` | string | no | `"active"` | yes |
| `quality` | string | no | `"unreviewed"` | no |
| `supersedes_id` | string | yes | `null` | no |
| `created_at` | datetime (UTC) | no | now | no |

`supersedes_id` is reserved for another `comments.id`; extract currently never sets it (revisions update the same row in place).

### Fields

#### `id`

Stable identity of the observation. Assigned once on insert (`uuid4`). Survives revision, move, absence from the source, Verify, and Drop.

#### `project_id`

Owning paper. Matches `.reviewdistill/config.yaml` `project.id` and `projects.id`.

#### `source_type`

How the comment was found in the manuscript. Current extractor always writes `latex_command`.

#### `source_command`

LaTeX macro name **without** the leading backslash (for example `myremark` for `\myremark{...}`). Taken from the project’s configured comment commands. It is a marker, not an issue type.

#### `file_path`

Path of the `.tex` file relative to the project root, using the extractor’s path (typically POSIX-style, e.g. `sections/03_formative_study.tex`). Resolved against `projects.root_path`.

#### `line_number`

1-based line of the opening `\<command>{` in that file. Not identity: a different remark on the same line is a different observation.

#### `raw_text`

What the reviewer wrote, after extract-time normalization: strip the command body, drop empty lines, join remaining lines with a single space.

The AI never writes this field. Source-driven **revision** of a still-present comment updates it in place (same `id`). Coding and export read it; they do not invent a replacement.

#### `context_text`

Nearby manuscript text at last extract, **not** the comment body.

Built as:

1. Local prose around the comment (headings and following paragraph when the comment sits alone between sectioning commands; comment-command lines themselves are omitted). Line breaks match the source: consecutive TeX lines stay on separate lines; a blank line in the source becomes a blank line in `context_text`.
2. Optional last line of harvested keys from that same local text: `Citations: …` and/or `Refs: …`, joined with ` | `.

Citations and refs are **not** separate columns. When the comment is not in the manuscript, a non-binding guess compares the prose (everything except that last extras line) to a fresh extract of `{root_path}/{file_path}` at `line_number`.

#### `section`

Nearest `\section` / `\subsection` titles at extract time, or `null`. Format when both exist: `{section} / {subsection}`.

#### `git_commit`

`HEAD` of the paper repo at last extract (`git rev-parse HEAD`), or `null` if the project is not a git checkout.

#### `git_url`

`origin` remote as git reports it (`git remote get-url origin`), or `null`. HTTP(S) and `ssh://` userinfo is stripped before storage, JSON, and permalinks, except a password-less `git` username (`https://git@git.overleaf.com/...`). This is a clone URL, not a web permalink. GitHub/GitLab file+line links are derived at read time from `git_url` + `git_commit` + `file_path` + `line_number`.

#### `fingerprint`

SHA-256 hex of `source_command + NUL + normalized raw_text`, UTF-8. Normalization for the hash is `" ".join(raw_text.split())` (whitespace collapse). Used to pair exact same-wording comments within and across files. Not a primary key: two copies of the same wording are two rows with the same fingerprint.

#### `status`

Presence of the observation in the manuscript source. See [Presence](#presence).

#### `quality`

Human stamp on the observation itself, independent of the issue type. See [Quality](#quality).

#### `supersedes_id`

Unused by current extract. Do not infer identity from it.

#### `created_at`

Time the row was first inserted. Not updated on revision, move, presence change, or quality stamp.

### Presence

`status` is extract-managed presence, not a UI queue.

| Status | Still in the manuscript source? | How it is set |
| --- | --- | --- |
| `active` | yes | New extract; resurrect when the same fingerprint returns |
| `pending_disappeared` | no | Extract: present comment unmatched as revision/move |

Extract never Verify/Drops. Exception: a wording revision clears `verified` to `unreviewed`. Dropped rows with the same wording still in the file keep the same `id` (no new row).

### Quality

| Quality | Meaning | How it is set |
| --- | --- | --- |
| `unreviewed` | Default after extract; revision of wording also clears `verified` back to this | Extract (new / revision) |
| `verified` | Observation is quality-assured. Does not confirm the issue type | **Verify** |
| `dropped` | Do not distill (too local or bad extract). History is kept | **Drop** |

Unknown values are rejected on `add`, `commit`, and load (`Unknown comment quality`). Corrupt `comments.jsonl` fails fast; rows are not skipped.

### Comments to distill

A comment is **to distill** (`in_working_set`) when it is not `dropped`, and either in the manuscript (`status=active`) or `verified`. Progress shows this count as **to distill**; the JSON key remains `working_set`.

AI suggestions, taxonomy examples, type-chip counts, recent observations, and export use only comments to distill.

Selector views:

- **Unlabeled** — comments to distill with no **active** issue type, plus absent + `unreviewed` (so you can Verify or Drop). No Reject: not accepting a suggestion leaves the comment unlabeled. An accepted label on an inactive type does not count.
- **Type chip** — that type’s labeled comments to distill.

### What extract updates in place

On unchanged, revised, moved, or resurrected rows, extract refreshes location and git, and rebuilds `context_text` / `section`. On revision it also updates `raw_text`, `fingerprint`, `source_command`, and `source_type`, and clears `verified` to `unreviewed`. It does not change `id`, `project_id`, `created_at`, `supersedes_id`, or `dropped`.

---

## Issue type

Live taxonomy node (`issue_types.jsonl`). The store is a forest: `parent_id` is null for a root, otherwise another type’s `id`. `position` is order among siblings (`0..n-1` after each sibling-list rewrite). A type may have children and its own accepted comments.

| Column | Type | Null | Default |
| --- | --- | --- | --- |
| `id` | string | no | — |
| `name` | string | no | — |
| `parent_id` | string | yes | null (root) |
| `position` | int | no | 0 |
| `definition` | string | no | — |
| `detection_guidance` | string | yes | null |
| `status` | `active` / `inactive` | no | `active` |

An active type’s `parent_id` must be an active type; missing, inactive, or cyclic parents fail load. Inactive rows keep last `parent_id` / `position` for undo. Leftover `category` and `notes` keys in old files are ignored; they are not rewritten and `category` is not promoted into parent types. `notes` is not a field. `detection_guidance` is used in retrieval and is not shown in Issue Details.

`codings.proposed_parent_id` is the parent for a proposed **new** type (`null` = root). Unknown or inactive ids are treated as root.

---

## Related tables

| Table | Relationship |
| --- | --- |
| `codings` | many `codings.comment_id` → one comment; AI/human interpretation lives here |
| `issue_examples` / `issue_counterexamples` | optional `source_comment_id` |
| `taxonomy_events` | append-only history (`event_type`, `payload_json`, `undone`); Undo/Redo set `undone` rather than inserting a new row |
| `git_commits` | per-project commit log (`git_commits.project_id`); not a foreign key from `comments` |

A comment may have several `codings` over time (`proposed`, `accepted`, `modified`). The observation row stays the evidence; coding rows stay the interpretation. Not accepting a suggestion leaves the comment unlabeled.
