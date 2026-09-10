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

4. Extract comments into the local database:

   ```bash
   reviewdistill extract
   ```

   Add `--watch` to extract again whenever `.tex` files settle.

5. Open the workbench:

   ```bash
   reviewdistill serve
   ```

   Then open http://127.0.0.1:8765. Configure an LLM in **Settings** if you want suggestions. Use **Get AI suggestions** on uncoded comments, then accept / change / reject.

6. Repeat on the next paper. The taxonomy in `~/.reviewdistill` is reused.

7. Export a rubric:

   ```bash
   reviewdistill export --format md -o review-rubric.md
   ```

8. Point a coding agent at that file.

Details for the UI: [Workbench](./workbench.md). LLM keys: [LLM settings](./llm.md). Export formats: [Export](./export.md).
