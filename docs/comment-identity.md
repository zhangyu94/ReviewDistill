# Comment identity

How ReviewDistill decides whether a proofreading comment is **new**, a **revision** of an existing observation, a **move**, or **gone from the source** — and how presence and quality combine.

The stored columns of a project and observation are in [`data-schema.md`](data-schema.md). Product spec: [`spec.md`](spec.md).

## Comments in the manuscript

Reviewers leave informal notes in the LaTeX source using a **comment command**: a macro whose only job is to mark “the reviewer wrote this.” It is not an issue type and not a verdict. The body of the command is the comment.

This spec writes that marker as `\myremark{...}` (the default `init` command). Define it in the preamble if needed: `\newcommand{\myremark}[1]{#1}`.

```latex
The results demonstrate that ...
\myremark{I think "demonstrate" is too strong here.}
```

A project may use a different command name, or several. ReviewDistill treats all configured comment commands the same way. A command that sits in a TeX line comment (`% ...`) is not in the source as a live remark and is not extracted.

## Why this exists

Each comment is a lasting **observation**: the wording you wrote, the manuscript around it, and its location. The observation is not the issue type. The manuscript keeps changing. You edit a comment’s body, cut it, put a different remark where an old one used to be, or save while a comment is only half typed.

**Line number is not identity.** A new comment on the line where an old one used to live is a new observation. The old one is gone from the source.

Presence and quality are independent. Extract only updates presence (and wording on revision). It never stamps quality and never assigns an issue type.

## Working set

The **working set** is the set of comments that count for AI suggestions, clustering, taxonomy examples, type chips, and rubric export.

A comment is **in the working set** when it is not `dropped`, and it is either **in the manuscript** or **verified**.

| Quality | In the working set? |
| --- | --- |
| `unreviewed` (default after extract) | only while the comment is still in the manuscript. If it has left the `.tex` file, it is not in the working set, but Unlabeled still lists it so you can Verify or Drop |
| `verified` | yes, whether or not it is still in the manuscript |
| `dropped` | no (history is kept; same wording in the file does not mint a new row) |

`verified` means the observation itself is quality-assured (wording, context, worth keeping as evidence). It does **not** confirm the issue type. A verified comment that later leaves the `.tex` file stays in the working set: the passage was fixed, and the problem was real.

`dropped` means do not distill (too local, or a bad extract). Undo Drop from History if you need the row back in the workbench.

## Events

### New

A comment in the source that does not match an observation already treated as present.

It becomes a new observation (`quality=unreviewed`) and appears in the workbench as Unlabeled.

### Revision

The comment **stayed in the source** and its wording changed **similarly**: an edit of the same remark, not a different remark.

That **same observation** is updated to the new wording and surrounding manuscript context. Any label already attached to it stays attached. A `verified` stamp is cleared back to `unreviewed` (the wording changed). A move that does not change wording keeps the stamp. The AI never overwrites what you wrote; only your source edits do.

Examples of revisions:

- `\myremark{Too strong.}` → `\myremark{Too strong given the experiment.}`
- Rephrase, add a clause, or fix a typo, while the comment remains in the file

### Move

The same wording is still in the project, but not in the same place:

- **Within a file:** you reorder comments, or surrounding text changes line numbers. Same observation; location and context update.
- **Across files:** the same wording under the same comment command left one file and appeared in another, including a rename of the file. Same observation; location updates.

A *different* remark that happens to sit on the old line is **not** a move.

### Gone from the source

A present comment is no longer in the source, and it was not a revision or a move.

The observation is **not** discarded. Presence becomes “not in the manuscript” (`status=pending_disappeared`). Extract does not set quality.

- If the comment was already **verified**, it stays in the working set (fixed passage; the problem was real).
- If it is still **unreviewed**, it stays on the **Unlabeled** chip (same Comments list) with a **not in manuscript** mark so you can **Verify** or **Drop**. There is no Disappeared queue.
- If it is **dropped**, it stays out of the working set.

Two common meanings of “gone”:

1. **The manuscript was fixed** (or the comment is still useful evidence). **Verify** — quality-assured; it stays in the working set even though the comment command is gone.
2. **Too local, or a bad extract.** **Drop** — it leaves the working set. History is kept.

Each absent unreviewed item can show a **guess**. The guess is never applied automatically:

- Nearby manuscript text changed a lot → guess **Verify** (likely resolved).
- Nearby manuscript text looks the same → guess **Drop** (likely pulled without fixing the passage).
- The source file itself is gone → guess **Verify**.

### Same line after a gap

If a comment leaves the source, and later a comment appears on that line (or any line) with different wording, that is **two observations**: the old one is not in the manuscript; the new one is unlabeled.

If the **same wording** returns in the source, the **same observation** becomes present again (including a dropped row: no new id). A revision of the text (fingerprint change) clears `verified` back to `unreviewed`.

## One save, no observed gap

You may replace a comment in a single save without ReviewDistill seeing an empty file in between.

- **Similar** wording → revision (same observation).
- **Dissimilar** wording → the old observation disappeared, and a new one appeared.

Examples:

| Before | After | Outcome |
| --- | --- | --- |
| Too strong. | Too strong given the experiment. | revision |
| too strong. | Too strong given the experiment. | revision |
| Why? | Why this method? | revision |
| Too strong. | Too long. | disappeared + new |
| Too strong. | This citation is missing. | disappeared + new |
| Too. | Too long. | disappeared + new |
| ok | This is ok here. | disappeared + new |

Extra spaces and line breaks in the comment body do not make two wordings different.

When several comments change at once, ReviewDistill compares them **in the order they appear in the file**. It does not search the rest of the file for a “better” similar partner. Two copies of the same wording in one file remain two observations; they are paired in that order.

## Incomplete comments are not disappearances

If a comment is not finished (for example `\myremark{` without a closing `}`), ReviewDistill must not treat other comments in that file as gone, must not record a partial comment, and must not revise existing observations from that file. It waits until the file’s comments are complete.

This avoids treating a half-typed brace as “the comment vanished.”

## Watch

`reviewdistill extract --watch` stays in the project and watches its LaTeX sources. After you pause editing, it extracts the same way a one-shot `reviewdistill extract` does.

It does not run AI labeling. It does not Verify or Drop. It follows the files as you edit them, not only when you commit.

`reviewdistill extract` without `--watch` is the same extraction, run once.

## Workbench

In `reviewdistill serve`, the workbench selector bar has a persistent **Unlabeled** chip on the right, plus a dismissable type chip on the left when a group is selected:

- **Unlabeled** — working-set comments with no issue type, **plus** absent + unreviewed comments so you can Verify or Drop. There is no Reject button: not accepting a suggestion leaves the comment unlabeled.
- **Type chip** — named with the issue code (for example `MISSINGINTRODUCT (3)`). Clicking a type in Issue Taxonomy selects this chip and filters Comments to that type’s **labeled** working-set comments. Dismiss it with × to drop the type filter and clear Issue Details.

**Verify** and **Drop** are quality stamps on the comment inspector (every comment). They are independent of the label. **Accept** / **Change** assign or change the issue type.

The Comments panel switches between a list and a single comment. The list marks rows that are not in the manuscript. The single-comment view shows manuscript context, location, record metadata (including quality), and the guess when the comment is absent.
