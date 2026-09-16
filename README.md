<p align="center">
  <img src="./docs/assets/logo.svg" width="64" height="64" alt="ReviewDistill logo">
</p>

<h1 align="center">ReviewDistill</h1>

<p align="center">
  Distill the comments you write in a LaTeX paper into a reusable agent skill to save your proofreading time.
</p>

<p align="center">
  <a href="https://zhangyu94.github.io/ReviewDistill/">Documentation</a>
  ·
  <a href="https://pypi.org/project/reviewdistill/">PyPI</a>
  ·
  <a href="https://github.com/zhangyu94/ReviewDistill">GitHub</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/reviewdistill/"><img alt="PyPI" src="https://img.shields.io/pypi/v/reviewdistill"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-%3E%3D3.11-3776AB">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

## What is ReviewDistill?

You already write comments in the `.tex` file. Those remarks stay in that paper. ReviewDistill groups them into labels and exports a skill you reuse: an agent applies the same checks on the next paper.

You can add an API key if you want an LLM to suggest labels. Comments and keys stay on your computer.

## Start using it

You need **Python ≥ 3.11**. Then:

`pip install reviewdistill`

That puts the `reviewdistill` command on your `PATH`.

In a LaTeX paper repository:

1. `reviewdistill init --name paper-01 --command myremark`
2. Proofread with `\myremark{...}` (or the commands you passed to `init`). Define `\newcommand{\myremark}[1]{#1}` in the preamble if needed.
3. `reviewdistill extract` (add `--watch` to keep extracting).
4. `reviewdistill ui` → http://127.0.0.1:8765. Pick a leaf label, or **Label with AI** if a key is set. **Verify** stamps the observation; **Delete** removes a bad extract.
5. Repeat on the next paper; the taxonomy is reused.
6. **Export** in the workbench, or `reviewdistill export` (writes `SKILL.md`)
7. Put that file in `.cursor/skills/scholarly-review/` (or the equivalent for another coding agent).

The full guide: [Introduction](./website/docs/intro.md), [Install](./website/docs/install.md), [Your first paper](./website/docs/first-paper.md), [Label comments](./website/docs/labeling.mdx), [Export](./website/docs/export.md).

To see the data folder: `reviewdistill paths`, or header **Settings → Data**. To copy it somewhere else: `reviewdistill paths move ~/Documents/reviewdistill`.

Run the documentation site locally: `pnpm --dir website start`.

## For developers

| Command | Description |
| --- | --- |
| `pip install -e ".[dev]"` | CLI + Python deps + client UI build |
| `python -m pytest` | Python tests |
| `pnpm --dir client test` | Client unit tests |
| `pnpm --dir client lint` | Client ESLint (`--fix` to apply) |
| `pnpm --dir client up` | Bump client npm deps (taze) |
| `pnpm --dir client dev` | Vite on :5173, proxies `/api` |
| `pnpm --dir website start` | Documentation site |
| `pnpm --dir website capture` | Rebuild docs screenshots and CLI GIFs |
| `python client_build.py` | Rebuild packaged UI without reinstalling |

Client source: [`client/`](./client/). Docs site: [`website/`](./website/). Product spec: [`docs/spec/README.md`](./docs/spec/README.md), [`docs/spec/data-schema.md`](./docs/spec/data-schema.md), [`docs/spec/comment-identity.md`](./docs/spec/comment-identity.md).

A GitHub Release whose tag matches `pyproject.toml` (`v0.1.0` or `0.1.0`) publishes to PyPI via Trusted Publishing.

## License

ReviewDistill is released under the [MIT License](./LICENSE).
