import useBaseUrl from '@docusaurus/useBaseUrl';

# Your first paper

Make a folder and `cd` into it:

```sh
mkdir demo-paper && cd demo-paper
```

Save this exact file as `main.tex`:

```latex
\documentclass{article}
\newcommand{\myremark}[1]{#1}
\begin{document}

The results demonstrate that the method is effective.
\myremark{Demonstrate is too strong here.}

\end{document}
```

You do not need to compile it. Then:

```sh
reviewdistill init --name paper-01 --command myremark
reviewdistill extract
reviewdistill ui
```

The clip is `init` and `extract`:

<img
  src={`${useBaseUrl('/video/first-paper.gif')}?v=paper-01`}
  alt="Initializing a paper and extracting comments"
/>

`extract` does not change the `.tex` file. It finds the macros you passed to `init` and stores each hit as a comment: the text in the braces, plus the manuscript sentence at that spot. For this starter the line should look like:

```
Extracted comments: 1 added, 0 unchanged, 0 revised, 0 moved, 0 disappeared, 0 resurrected, 0 skipped
```

`1 added` is `Demonstrate is too strong here.`, tied to `The results demonstrate that the method is effective.` It has no label yet.

`reviewdistill ui` serves http://127.0.0.1:8765. That unlabeled comment is in the list.

If you already have a paper, run `init` in that repo instead. `--command` is the macro name without the backslash, and you can pass it more than once. Use the commands you already proofread with; `myremark` in the starter is only an example.

`--watch` on `extract` re-runs after `.tex` files settle.

Next: [Label comments](./labeling.mdx).
