# Extract

`reviewdistill extract` finds the comment macros from `init --command` and stores each remark with the **manuscript text at the insertion point**. It does not call an LLM. `--watch` runs the same extract after sources settle.

A match is `\command{...}` or `\command {...}` (spaces or tabs before `{`), including `word\command{...}`. Matches inside a TeX `%` comment are ignored. The stored remark is the brace body, empty lines dropped, remaining lines joined by spaces.

Context is the insertion neighborhood, the same text the inspector shows.

Inline remark (the paragraph stays):

```latex
We created the evaluation corpus by running the coding agent. \myremark{Where are the tables?}
```

Context: `We created the evaluation corpus by running the coding agent.`

Remark on the next line of the same paragraph:

```latex
The results demonstrate that the method is effective.
\myremark{Demonstrate is too strong here.}
```

Context: `The results demonstrate that the method is effective.`

A remark after a blank line uses the previous paragraph. Extract does not retrieve tables or other sections the remark might mention.

Brace-matching and offset rules: [product spec, extract](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/spec/extract.md). Stored columns: [data schema](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/spec/data-schema.md) (`context_text`, `context_offset`).
