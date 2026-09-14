# Workflow

Proofread as usual. ReviewDistill watches the comments, not a separate review file.

1. Clone or open a paper repository (LaTeX).
2. Initialize ReviewDistill in that directory:

   ```bash
   reviewdistill init --name paper-01 --command myremark
   ```

   Repeat `--command` for each comment macro. The default is `myremark` (`\myremark{...}`). Define it in the preamble if it does not already exist, for example `\newcommand{\myremark}[1]{#1}`.

3. Proofread in the manuscript:

   ```latex
   The results demonstrate that the intervention caused the improvement.
   \myremark{Causal language is not supported by this design.}
   ```

4. Extract comments into the local JSONL store:

   ```bash
   reviewdistill extract
   ```

   Add `--watch` to extract again whenever `.tex` files settle.

5. Open the UI:

   ```bash
   reviewdistill ui
   ```

   Then open http://127.0.0.1:8765. Configure an LLM in **Settings** if you want suggestions. Use **Label with AI** on unlabeled comments, then Accept a suggestion or pick a type in the menu. **Verify** or **Drop** stamps quality; there is no Reject.

6. Repeat on the next paper. The taxonomy (Settings → **Data**, or `reviewdistill paths`) is reused.

7. Export a review skill:

   ```bash
   reviewdistill export --format md -o SKILL.md
   ```

8. Put `SKILL.md` in `.cursor/skills/scholarly-review/` (or the equivalent for another coding agent).

Details for the UI: [UI](./ui.md). LLM keys: [LLM settings](./llm.md). Export formats: [Export](./export.md).
