# Docs media capture

There is no `REVIEWDISTILL_HOME` override. Scripts set `HOME` to a temp directory so both `~/.reviewdistill` and `~/.config/reviewdistill/home` stay inside it. They must not read or write your real store. A `sitecustomize.py` on `PYTHONPATH` also filters pyenv blake2 hashlib noise out of CLI GIFs.

Do not call a real LLM. After extract, seed labels and assignments through the local HTTP API (`seed.py`). Assign only leaf labels.

```sh
pip install playwright
playwright install chromium
# optional: brew install vhs  (needs ttyd and ffmpeg)
pnpm --dir website capture
```

`pnpm --dir website capture` rebuilds the Vue client first so stills match the current workbench (list / tree / one). Playwright uses `fixtures/paper/` (several remarks, initialized before the UI). VHS `first-paper.gif` uses `fixtures/starter/` (the one-remark `main.tex` from Your first paper) and must not run `reviewdistill ui`. Keep `tapes/first-paper.tape` in sync with that starter (`--name paper-01`, `1 added`).

The runner rewrites each tape’s `Output` to an absolute path under `website/static/video/` because the first-paper tape’s cwd is the paper copy, not `website/captures/tapes/`.

| Asset | Pages |
| --- | --- |
| `workbench.png` | Homepage hero, Label comments |
| `inspector.png` | Label comments, Workbench |
| `export-dialog.png` | Export a skill |
| `assign-label.webm` | Label comments (slow row-menu assign of the leftover unlabeled remark) |
| `install.gif` | Install |
| `first-paper.gif` | Your first paper |

Playwright writes the PNGs and `assign-label.webm`. VHS writes the GIFs when `vhs` is on `PATH`. `pnpm --dir website build` does not run this.
