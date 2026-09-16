# Extract

A comment without manuscript context is often ambiguous. Context is the **insertion neighborhood** in the `.tex` file: the paragraph around the command. Remarks that mention other parts of the paper rely on the comment wording. Extract does not call an LLM and does not search the paper for what the remark refers to.

## Harvest

For each command from `reviewdistill init --command` (default `myremark`):

* A match is `\command{...}` or `\command {...}` (spaces or tabs before `{`), including `word\command{...}`.
* Matches inside a TeX `%` comment are ignored. `\%` is not a comment. Harvest skips a macro whose opener sits after a `%` that is not inside a live configured argument: `%` inside `\myremark{...}` (including on the closer line) does not hide a later command; `%` inside `\caption{...}` still comments out `\note{old}`.
* `\notmyremark` is not `\myremark`.
* An unclosed live `{` makes that file unstable: no comments from it this pass. An unclosed `% \command{` does not; harvest continues. `%`-commented macros are still found (`in_comment`) and context still strips that span (including an unclosed `% \command{` through the next configured command) so a commented-out body is not treated as prose.

The stored comment text is the brace body, empty lines dropped, remaining lines joined by spaces.

Stored neighborhood and `context_offset`: [`data-schema.md`](data-schema.md) (`context_text`, `context_offset`).

## Context

For each comment, extract:

* the blank-line paragraph that contains the command, with configured comment macros stripped on the raw file (same brace rule as harvest) then `%` tails removed (a blank line inside `{...}` is not an outer paragraph break);
* a heading after `}` on the closer line (or `\label`) is not neighborhood and ends the block; a heading that shares a block with sentences counts as prose;
* if that paragraph is empty after strip, headings / `\label` immediately above, or the previous prose paragraph, skipping other empty-after-strip remarks (never the next paragraph after a heading);
* section/subsection titles (separate field);
* source file and line number;
* character offset of this remark’s insertion hole in that neighborhood (`context_offset`: opening line + command + normalized body, not a search of words copied from the remark), shown as a square in the inspector (with a parenthetical legend beside the heading that shows the same square) and as `‹remark›` in the labeling prompt when the offset is a true integer in `0..length`.

The inspector and the labeling prompt see that same source TeX.

```
Comment:
"I don't think this follows."
Section:
Results / Accuracy
Context:
"Model A achieved higher accuracy than Model B.
Therefore, Model A is more suitable for real-world applications."
```

## Git

Manuscripts are usually Git repositories. For every extracted comment, record repository, remote URL (if a remote such as origin is configured), commit hash, file, and line.

That is enough to reconstruct, later:

```
Original manuscript
       ↓
Reviewer comment
       ↓
Author revision
       ↓
Final manuscript
```

Example: original “The results demonstrate that…”; reviewer “Too strong.”; revision “The results suggest that…”. That pair can become a review rule: when evidence does not establish a claim conclusively, prefer weaker epistemic language.

Version-to-version revision linkage is not required for v0.1. The data model must not prevent it.

## Extractor interface

The comment-extraction layer is extensible:

```python
class CommentExtractor:
    def extract(self, source) -> list[ProofreadingComment]:
        ...
```

Shipped: `LatexCommandExtractor`. Later: GitHub review, Markdown, Word comments. Normalized output is always `ProofreadingComment`, so the conceptual model is not tied to LaTeX.

## LaTeX

Commands are configurable:

```yaml
comments:
  latex_commands:
    - myremark
```

or several:

```yaml
comments:
  latex_commands:
    - myremark
    - question
    - revise
```

The parser must handle multiline comments, comments containing LaTeX, comments near paragraphs, escaped characters, and nested braces where feasible.

The command name is retained (`source_command = "question"`) and does not become the semantic label. `\question{This argument does not follow.}` can still be assigned as Logical gap.

## Incremental extraction

Extraction is idempotent. Running `reviewdistill extract` twice must not duplicate comments that are still present.

Identity (new, revision, move, gone from the source, Verify vs Delete) is defined in [`comment-identity.md`](comment-identity.md). The stored project and comment rows are [`data-schema.md`](data-schema.md).

`reviewdistill extract --watch` runs the same extraction after LaTeX sources settle. It does not run labeling and does not Verify or Delete.

The AI never overwrites the reviewer’s comment text. Source-driven revision of a still-present comment updates that observation’s wording in place.
