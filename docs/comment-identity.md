# Comment identity

How ReviewDistill decides whether a proofreading comment is **new**, a **revision** of an existing observation, a **move**, or **gone from the source** — and what you do when it is gone.

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

Each comment is a lasting observation: the wording you wrote, the manuscript around it, and any coding that followed. The manuscript keeps changing. You edit a comment’s body, cut it, put a different remark where an old one used to be, or save while a comment is only half typed.

**Line number is not identity.** A new comment on the line where an old one used to live is a new observation. The old one is gone from the source and needs a human decision.

## Working dataset

The **working dataset** is the set of comments that count for AI coding, clustering, taxonomy examples, and rubric export.

| State | Still in the manuscript source? | In the working dataset? |
| --- | --- | --- |
| Present | yes | yes |
| Pending disappearance | no | no (waiting on you) |
| Kept | no | yes |
| Retracted | no | no (history is kept; it is not used) |

Extract never discards an observation. It never chooses Keep or Retract for you.

## Events

### New

A comment in the source that does not match an observation already treated as present.

It becomes a new observation and appears in the workbench as Uncoded.

### Revision

The comment **stayed in the source** and its wording changed **similarly**: an edit of the same remark, not a different remark.

That **same observation** is updated to the new wording and surrounding manuscript context. Any coding already attached to it stays attached. The AI never overwrites what you wrote; only your source edits do.

Examples of revisions:

- `\myremark{Too strong.}` → `\myremark{Too strong given the experiment.}`
- Rephrase, add a clause, or fix a typo, while the comment remains in the file

### Move

The same wording is still in the project, but not in the same place:

- **Within a file:** you reorder comments, or surrounding text changes line numbers. Same observation; location and context update.
- **Across files:** the same wording under the same comment command left one file and appeared in another, including a rename of the file. Same observation; location updates.

A *different* remark that happens to sit on the old line is **not** a move.

### Disappeared

A present comment is no longer in the source, and it was not a revision or a move.

The observation is **not** discarded. It leaves the working dataset and waits in the workbench under **Disappeared** until you Keep or Retract it.

Two common meanings of “gone”:

1. **The manuscript was fixed** (or the comment is still a useful teaching example). **Keep** — it stays in the working dataset even though the comment command is gone from the source.
2. **The comment was retracted or wrong.** **Retract** — it leaves the working dataset. The observation and any coding are retained as history; they are not used for future coding, clustering, or export.

Each disappeared item shows a **guess**. The guess is never applied automatically:

- Nearby manuscript text changed a lot → guess **Keep** (likely resolved).
- Nearby manuscript text looks the same → guess **Retract** (likely pulled without fixing the passage).
- The source file itself is gone → guess **Keep**.

### Same line after a gap

If a comment disappears, and later a comment appears on that line (or any line) with different wording, that is **two observations**: the old one stays in Disappeared until you decide; the new one is uncoded.

If you Retract, then later write the same words again, that later comment is **new**. If you have not decided yet, or you Kept it, and the same wording returns in the source, the **same observation** becomes present again.

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

It does not run AI coding. It does not Keep or Retract. It follows the files as you edit them, not only when you commit.

`reviewdistill extract` without `--watch` is the same extraction, run once.

## Workbench

In `reviewdistill serve`, the workbench selector bar has two persistent chips on the right, plus a dismissable type chip on the left when a group is selected:

- **Uncoded** — present and kept comments that still need Accept / Change / Reject.
- **Disappeared** — comments waiting on Keep or Retract. Coding actions are not shown here.
- **Type chip** — named with the issue code (for example `MISSINGINTRODUCT (3)`). Clicking a type in Issue Taxonomy selects this chip and filters Comments to that type’s accepted working-dataset comments. Dismiss it with × to drop the type filter and clear Issue Details. Persistent Uncoded / Disappeared stay.

The Comments panel switches between a list and a single comment. The single-comment view shows manuscript context, location, and record metadata.

Each disappeared item shows the stored comment, its last context and metadata, and the guess.
