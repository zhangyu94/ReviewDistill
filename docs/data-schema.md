# Data schema

Stored shape of a **project** (paper) and a proofreading **observation** in the ReviewDistill database.

Identity (when a source comment is new, a revision, a move, or gone) is defined in [`comment-identity.md`](comment-identity.md). Product spec: [`spec.md`](spec.md). This file is the schema of the rows that identity acts on.

Implementation: SQLModel `Project` → table `projects`, SQLModel `ProofreadingComment` → table `comments`, in `$REVIEWDISTILL_HOME/reviewdistill.db` (default `~/.reviewdistill/reviewdistill.db`).

There is no declared SQL foreign key. `comments.project_id` is the `projects.id` of the paper.

The JSON object under `comment` in `GET /api/inbox` (workbench Uncoded / Disappeared) is the comment row (`created_at` as ISO-8601). Response extras (`project_name`, `permalink`, `guess`, `coding`) are not columns on `comments`; `project_name` is `projects.name`.

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
| `supersedes_id` | string | yes | `null` | no |
| `created_at` | datetime (UTC) | no | now | no |

`supersedes_id` is reserved for another `comments.id`; extract currently never sets it (revisions update the same row in place).

### Fields

#### `id`

Stable identity of the observation. Assigned once on insert (`uuid4`). Survives revision, move, disappearance, Keep, and Retract.

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

The AI never writes this field. Source-driven **revision** of a still-present comment updates it in place (same `id`). Coding, clustering, and export read it; they do not invent a replacement.

#### `context_text`

Nearby manuscript text at last extract, **not** the comment body.

Built as:

1. Local prose around the comment (headings and following paragraph when the comment sits alone between sectioning commands; comment-command lines themselves are omitted). Line breaks match the source: consecutive TeX lines stay on separate lines; a blank line in the source becomes a blank line in `context_text`.
2. Optional last line of harvested keys from that same local text: `Citations: …` and/or `Refs: …`, joined with ` | `.

Citations and refs are **not** separate columns. Disappearance guessing compares the prose (everything except that last extras line) to a fresh extract of `{root_path}/{file_path}` at `line_number`.

#### `section`

Nearest `\section` / `\subsection` titles at extract time, or `null`. Format when both exist: `{section} / {subsection}`.

#### `git_commit`

`HEAD` of the paper repo at last extract (`git rev-parse HEAD`), or `null` if the project is not a git checkout.

#### `git_url`

`origin` remote as git reports it (`git remote get-url origin`), or `null`. HTTP(S) and `ssh://` userinfo is stripped before storage, JSON, and permalinks, except a password-less `git` username (`https://git@git.overleaf.com/...`). This is a clone URL, not a web permalink. GitHub/GitLab file+line links are derived at read time from `git_url` + `git_commit` + `file_path` + `line_number`.

#### `fingerprint`

SHA-256 hex of `source_command + NUL + normalized raw_text`, UTF-8. Normalization for the hash is `" ".join(raw_text.split())` (whitespace collapse). Used to pair exact same-wording comments within and across files. Not a primary key: two copies of the same wording are two rows with the same fingerprint.

#### `status`

Lifecycle of the observation. See [Statuses](#statuses).

#### `supersedes_id`

Unused by current extract. Kept on the row for older data and possible future chaining. Do not infer identity from it.

#### `created_at`

Time the row was first inserted. Not updated on revision, move, or status change.

### Statuses

| Status | Still in the manuscript source? | Working dataset? | How it is set |
| --- | --- | --- | --- |
| `active` | yes | yes | New extract; resurrect of `pending_disappeared` or `kept` when the same fingerprint returns |
| `pending_disappeared` | no | no | Extract: present comment unmatched as revision/move |
| `kept` | no | yes | Human Keep in the workbench (Disappeared) |
| `retracted` | no | no | Human Retract in the workbench (Disappeared) |
| `superseded` | n/a | no | One-time migration of legacy `modified` rows only |

**Working dataset** (`WORKING_COMMENT_STATUSES`): `active` and `kept`. Coding, clustering, taxonomy examples, taxonomy counts, recent observations, and rubric export use only these. `pending_disappeared`, `retracted`, and `superseded` are retained as history.

Workbench views:

- **Uncoded** — working-dataset comments that still need Accept / Change / Reject.
- **Disappeared** — `pending_disappeared` only (Keep / Retract).

Extract never chooses Keep or Retract. It never resurrects `retracted` or `superseded`.

Legacy values rewritten on `init_db`: `deleted` → `pending_disappeared`, `modified` → `superseded`.

### What extract updates in place

On unchanged, revised, moved, or resurrected rows, extract refreshes location and git, and rebuilds `context_text` / `section`. On revision it also updates `raw_text`, `fingerprint`, `source_command`, and `source_type`. It does not change `id`, `project_id`, `created_at`, or `supersedes_id`.

---

## Related tables

| Table | Relationship |
| --- | --- |
| `codings` | many `codings.comment_id` → one comment; AI/human interpretation lives here |
| `issue_examples` / `issue_counterexamples` | optional `source_comment_id` |
| `taxonomy_events` | append-only history (`event_type`, `payload_json`, `undone`); Undo/Redo set `undone` rather than inserting a new row |
| `git_commits` | per-project commit log (`git_commits.project_id`); not a foreign key from `comments` |

A comment may have several `codings` over time (`proposed`, `accepted`, `rejected`, `modified`). The observation row stays the evidence; coding rows stay the interpretation.
