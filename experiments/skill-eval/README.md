# Skill spotting eval

Exported `SKILL.md` is a static dump of this author’s labels (definitions and examples). Nothing in the product runs that file against manuscript text, so there is no way to know whether an agent can *spot* the same issues the author labeled. Polishing the template by inspection is unfalsifiable.

This folder is a **local developer experiment** that answers one question:

> On held-out passages, does the current exported skill beat a **names-only** baseline at **naming** the author’s labels?

It is diagnostic, not a product command and not a CI gate. Scores need not be 100%. Live calls spend API tokens and send manuscript passages to the configured LLM.

Public scholarly-writing datasets use other taxonomies, so they cannot score this author’s headings without a remap. The committed `fixtures/` pack uses the **same label names** with invented papers instead. `--source store` is the real personal check; a perfect fixture score is a smoke test, not evidence the skill works on the author’s writing.

## What happens in one run

1. **Gold** comes from the local store: working-set comments that have at least one **accepted** coding on an **active** label. Gold names are those **label** names.
2. **Holdout** splits gold so the skill under test never includes the test comment’s examples, or any other example whose text is the same passage (two comments can share a block). Default is leave-one-paper-out if two or more projects are labeled; otherwise leave-one-comment-out.
3. Each test item is a **passage** = the comment’s `context_text` with Citations/Refs stripped. The model never sees `raw_text` (that would leak the author’s wording of the issue).
4. **Distractors** are unused **prose** paragraphs from the same paper (no working-set comment on them). Gold for those is `[]`. Command-only blocks such as `\end{document}` are skipped. They catch a skill that flags everything.
5. Two **conditions** see the same items:
   - **skill** — current `SKILL.md` shape (examples from *train* comments only), then the passage, then “return JSON `{"types": [...]}` using heading names from the skill”. The key `types` is this eval protocol, not product JSON. A label with no remaining train examples still appears (same as Export). The runner does not write the ReviewDistill store.
   - **baseline** — same `##` heading names, no definitions or examples. A lift means the skill body is doing work, not that the prompt listed the taxonomy. Invented names that are not heading names never count as hits.
6. **Scoring** is exact label-name match (micro P/R/F1). Extra names = false positives; `[]` on a gold passage = miss. Hierarchical recall (gold name *or an ancestor*) is secondary; precision stays exact.

Then `analyze.ipynb` plots the run. It does not call the LLM.

```
lib.py      holdout, items, skill text, prompts, parse, scores, cache
run.py      batch against the store or fixtures + configured LLM; writes runs/<utc>/
analyze.ipynb   load a run; P/R/F1, per-label, misses
fixtures/   public fictional papers + rewritten skill (see fixtures/README.md)
runs/       gitignored outputs
```

## Setup

From the repo root, with ReviewDistill installed editable and an LLM configured the same way as **Settings → Assistant** (home `config.yaml` + `.env`).

Notebook extras (not part of the package):

```bash
pip install jupyter pandas matplotlib
```

## Run

Personal (default; uses the live store; do not commit `runs/` or notebook outputs):

```bash
python experiments/skill-eval/run.py
```

Public fixture (committed pack; still spends LLM tokens on fictional passages):

```bash
python experiments/skill-eval/run.py --source fixture
```

Writes `experiments/skill-eval/runs/<utc-timestamp>/`:

| File | Contents |
|------|----------|
| `meta.json` | `source` (`store` or `fixture`), holdout mode, provider/model, fold sizes, privacy warning |
| `items.jsonl` | One row per passage: gold names, whether it is a distractor |
| `predictions.jsonl` | Predicted names + raw LLM text, per condition |
| `metrics.json` | Exact P/R/F1, hierarchical recall, per-label confusion |
| `cache.jsonl` | Keyed by `(condition, item_id, prompt_hash)` so retries do not re-spend tokens |

- Default holdout: leave-one-paper-out if two or more projects have gold labels; otherwise leave-one-comment-out.
- `--holdout paper` or `--holdout comment` forces a mode.
- `--comment-fraction 0.2` (with `--holdout comment`) tests a stratified random fraction instead of true leave-one-out.
- `--resume runs/<dir>` reuses `cache.jsonl` so a retry does not re-spend tokens for unchanged prompts.
- `--source store|fixture` (default `store`). Fixture files live in `experiments/skill-eval/fixtures/` (see that folder’s README). `--source fixture` does not open the store. It fails fast on missing files, empty gold, unknown label names, or a gold line that is not a content block.
- `--fixture-dir` overrides the fixture pack path.

The runner prints a privacy warning: manuscript passages go to the configured provider.

## Plot

Open `analyze.ipynb` and run all cells. It plots the latest **fixture** run (`meta.source` is `fixture`) and skips store runs. It does not call the LLM.

To inspect a personal store run, set `SOURCE = "store"` in the first code cell and **do not commit** the notebook. A store run contains private passages.

How to read zeros: a bar of height 0.00 is a real score (no exact name matches), not a failed load. Look at `tp` / `fp` / `fn` in the table. The names-only baseline can now score above 0 if the model picks headings from the list. A fixture F1 of 1.0 is the toy pack being easy, not a pass.

## What this is not

- Not `reviewdistill eval`
- Not a pytest suite
- Does not change Export / `SKILL.md` template
- Does not rewrite definitions with an LLM
- Does not search a full manuscript in Cursor; that smoke check is later
