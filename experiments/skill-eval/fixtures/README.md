# Public fixture pack

Fictional papers and rewritten skill text so `run.py --source fixture` can run
without the author's private store or `*.writing` repos.

Label **names** match the live taxonomy snapshot at authoring
(Terminology Precision, Cross-Referencing and Navigation, Structural Clarity
and Overview). Definitions and examples are invented. Papers are about frog
chorus counting and kitchen timers, not the author's manuscripts.

Gold is `gold.jsonl`, one object per gold item (not distractors):

```json
{"id": "paper-a-term", "paper_id": "paper-a", "file_path": "main.tex", "line_number": 12, "gold_names": ["Terminology Precision"]}
```

`id` is unique. `paper_id` is a directory under `papers/`. `line_number` is
1-based. Passages are read from `.tex` at run time using the same paragraph
blocks as distractors (a blank line starts a new block). Occupied lines are
those gold pointers; unused prose blocks in the same paper become distractors
(preamble and `\end{document}` are skipped).
If you edit a `.tex` file, recompute `line_number`. Taxonomy examples may
set `source_item_id` to a gold `id` so holdout can drop that example from
the skill. Omit it for generic examples that stay in every fold.

Do not add `\remark` / `\yzc` / `\yuzhang` / `\authornote`. Do not copy
sentences from private `*.writing` git history; that history is only a local
authoring hint. Do not store the passage string in `gold.jsonl`.

`--source fixture` never reads the live store. This pack does not import into
the ReviewDistill store.

When the live taxonomy gains a safe-to-publish name, add a heading here and a
rewritten definition. If a name would identify an unpublished paper, omit it
and record the omission in this file.
