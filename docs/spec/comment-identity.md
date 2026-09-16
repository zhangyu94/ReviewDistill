# Comment identity

How ReviewDistill decides whether a proofreading comment is **new**, a **revision** of an existing observation, a **move**, or **gone from the source**, and how presence and Verify combine.

The stored columns of a project and observation are in [`data-schema.md`](data-schema.md). Product spec: [`README.md`](README.md).

## Comments in the manuscript

Reviewers leave informal notes in the LaTeX source using a **comment command**: a macro whose only job is to mark “the reviewer wrote this.” It is not a label and not a verdict. The body of the command is the comment.

This spec writes that marker as `\myremark{...}` (the default `init` command). Define it in the preamble if needed: `\newcommand{\myremark}[1]{#1}`.

```latex
The results demonstrate that ...
\myremark{I think "demonstrate" is too strong here.}
```

A project may use a different command name, or several. ReviewDistill treats all configured comment commands the same way. A command that sits in a TeX line comment (`% ...`) is not in the source as a live remark and is not extracted.

## Why this exists

Each comment is a lasting **observation**: the wording you wrote, the manuscript around it, and its location. The observation is not the label. The manuscript keeps changing. You edit a comment’s body, cut it, put a different remark where an old one used to be, or save while a comment is only half typed.

**Line number is not identity.** A new comment on the line where an old one used to live is a new observation. The old one is gone from the source.

Presence and Verify are independent. Extract only updates presence (and wording on revision). It never Verifies and never assigns a label.

## Comments to distill

**Comments to distill** are the comments that count for AI suggestions, taxonomy examples, label chips, and export. Progress shows this count as **to distill**.

A comment is **to distill** when it is **in the manuscript** or **verified**.

| Verified | To distill? |
| --- | --- |
| `false` (default after extract) | only while the comment is still in the manuscript. If it has left the `.tex` file, it is not to distill, but Unlabeled still lists it so you can Verify or Delete |
| `true` | yes, whether or not it is still in the manuscript |

`verified` means the observation itself is verified (wording, context, worth keeping as evidence). It does **not** confirm the label. A verified comment that later leaves the `.tex` file is still to distill: the passage was fixed, and the problem was real.

**Delete** removes the observation from the store (comment, labels, sourced examples). Undo from History. A later extract that still sees the same wording mints a **new** id. Too-local comments you still want in the dataset stay labeled; exclude their label at export.

## Events

### New

A comment in the source that does not match an observation already treated as present.

It becomes a new observation (`verified=false`) and appears as Unlabeled.

### Revision

The comment **stayed in the source** and its wording changed **similarly**: an edit of the same remark, not a different remark.

That **same observation** is updated to the new wording and surrounding manuscript context. Any label already attached to it stays attached. A Verify stamp is cleared back to `verified=false` (the wording changed). A move that does not change wording keeps the stamp. The AI never overwrites what you wrote; only your source edits do.

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

The observation is **not** discarded. Presence becomes “not in the manuscript” (`status=pending_disappeared`). Extract does not set verified.

- If the comment was already **verified**, it is still to distill (fixed passage; the problem was real).
- If it is still **not verified**, it stays on the **Unlabeled** chip (same Comments list) with a **Left the manuscript** chip so you can **Verify** or **Delete**. There is no Disappeared queue.

Two common meanings of “gone”:

1. **The manuscript was fixed** (or the comment is still useful evidence). **Verify**: it is still to distill even though the comment command is gone.
2. **A bad extract.** **Delete**: the observation is removed. Undo from History.

Each comment that left the manuscript and is not verified can show a **guess**. The guess is never applied automatically:

- Nearby manuscript text changed a lot → guess **Verify** (likely resolved).
- Nearby manuscript text looks the same → guess **Delete** (likely a bad extract).
- The source file itself is gone → guess **Verify**.

### Same line after a gap

If a comment leaves the source, and later a comment appears on that line (or any line) with different wording, that is **two observations**: the old one left the manuscript; the new one is unlabeled.

If the **same wording** returns in the source, the **same observation** becomes present again **if the row still exists**. A deleted comment is a new observation (new id). A revision of the text (same observation, new wording) clears verified back to false.

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

It does not run AI labeling. It does not Verify or Delete. It follows the files as you edit them, not only when you commit.

`reviewdistill extract` without `--watch` is the same extraction, run once.

## UI

In `reviewdistill ui`, Selectors chips AND. The right-hand **Unlabeled** control toggles a left-hand Unlabeled chip and is never pressed. No chips: Comments lists comments to distill.

- **Unlabeled**: inbox queue: comments to distill with no **active** label, plus comments that left the manuscript and are still not verified so you can Verify or Delete. Those rows show a **Left the manuscript** chip. There is no Reject button: not accepting a suggestion leaves the comment unlabeled.
- **Label chip**: named with the label (for example `Missing introduction (3)`). Clicking a label opens Label Details and replaces the label chip; it does not clear Unlabeled. × on the label chip sets `labelchip=0` and keeps `/labels/:id` (Label Details stays). Comments then lists comments to distill, or the inbox if Unlabeled is still on.

**Verify** stamps the observation on the comment inspector. **Delete** removes the observation (undo from History). They are independent of the label. **Accept** applies the AI suggestion. Picking a label in the menu assigns it.

The Comments panel switches between a list, a project file tree, and a single comment. Each list row is a card with the inspector’s leaf label menu (own line, compact) and, when the `.tex` file is on this computer, a **file path** control that shows that file in the file manager. Assign and reveal use that row’s comment. The tree nests the same comments under project / file path; grouping rows collapse. Tree comment rows show **line N** instead of repeating the path. The list and the inspector Comment header show a **Left the manuscript** chip when the remark is no longer in the `.tex` file. The single-comment view shows manuscript context, the current label, Triage (Verify / Delete), location, record metadata, and the guess under Triage when present. Location **File** can still show the `.tex` file in the file manager if that path exists on this computer.
