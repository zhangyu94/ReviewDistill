# Extract

`reviewdistill extract` finds configured comment macros in `.tex` files and stores each remark with the **manuscript text at the insertion point**. It does not ask an LLM what the remark is about, and it does not search the rest of the paper. If a comment refers elsewhere, that belongs in the remark wording.

`--watch` runs the same extract after sources settle.

## Comments

For each command from `reviewdistill init --command` (default `myremark`):

- A match is `\command{...}` or `\command {...}` (spaces or tabs before `{`), including `word\command{...}`.
- Matches inside a TeX `%` comment are ignored. `\%` is not a comment.
- `\notmyremark` is not `\myremark`.
- An unclosed live `{` makes that file unstable: no comments from it this pass. An unclosed `% \command{` does not; harvest continues, and context strips from that opener through the next configured command.

The stored comment text is the brace body, empty lines dropped, remaining lines joined by spaces.

## Context

Context is the insertion neighborhood — the same text the inspector and the coding prompt show.

1. **Find complete configured macros** on the raw file (same brace rule as harvest, so a `}` after `%` still closes). A blank line *inside* `{...}` is still the argument, not an outer paragraph break. Harvest skips a macro whose opener sits after a `%` that is not inside a live configured argument. Context still strips that span — including an unclosed `% \command{` through the next configured command — so a commented-out body is not treated as prose.
2. **Strip those macros.** Every configured command and its `{...}` body go (including a space before `{`, bodies that span lines, and `%`-commented macros). The rest of the line stays.
3. **Drop `%` tails.** An unescaped `%` starts a comment. Whole-line `%` dividers disappear. Line numbers do not shift.
4. **Take the blank-line block** that contains the opening line of the command. Consecutive non-blank lines are one paragraph. A heading after `}` on the closer line (one-line or multiline) is not neighborhood and ends the block. Empty lines that sit inside a live multiline macro with leftover opener prose stay in that paragraph.
5. **If that span is empty, walk up only**, skipping other blocks that are also empty after strip (a previous standalone remark). Consecutive heading / `\label` blocks above are context. A heading is a sectioning command (`\chapter` through `\subparagraph`, optional `*`) or `\label`. A prose paragraph immediately above (no heading between) is context. Never the next paragraph after a heading. If nothing qualifies, context is empty.
6. **Keep source TeX.** Line breaks stay. No `Citations:` / `Refs:` footer.

A heading that shares a block with sentences counts as prose: that whole block is kept.

## Examples

Inline remark (the paragraph stays; a `%` divider does not):

```latex
% – corpus

We created the evaluation corpus by running the coding agent. \yzc{Where are the tables?}
```

Context: `We created the evaluation corpus by running the coding agent.`

Remark on the next line of the same paragraph:

```latex
The results demonstrate that the intervention caused the improvement.
\myremark{Causal language is not supported by this design.}
```

Context: `The results demonstrate that the intervention caused the improvement.`

Remark after a blank line: the previous paragraph.

Remark between headings: those headings only, not the next subsection’s first paragraph.

## What extract does not do

- It does not call an LLM.
- It does not retrieve tables, figures, or other sections the remark might mention.
- It does not convert TeX to plain prose.
