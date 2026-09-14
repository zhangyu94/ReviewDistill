<p align="center">
  <img src="./docs/assets/logo.svg" width="64" height="64" alt="ReviewDistill logo">
</p>

<h1 align="center">ReviewDistill</h1>

<p align="center">
  Turn the comments you already write in a LaTeX paper into a reusable guide — for you, and for an AI assistant.
</p>

<p align="center">
  <a href="https://zhangyu94.github.io/ReviewDistill/">Documentation</a>
  ·
  <a href="https://github.com/zhangyu94/ReviewDistill">GitHub</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-%3E%3D3.11-3776AB">
  <img alt="Node" src="https://img.shields.io/badge/node-%3E%3D22-5FA04E">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

## What is ReviewDistill?

When you proofread, comments usually stay buried in the `.tex` file. The next paper, you start over. An AI assistant that edits the text has no idea what you usually flag.

ReviewDistill reads those comments and the sentences around them. You group similar comments into types of problems (for example, “this claim is too strong”). Then you save that list as a file you can reuse — yourself, or by handing it to an assistant.

If you add an API key, an LLM can suggest a group. You still choose. Comments and keys stay on your computer.

## Start using it

Clone this repository. You need **Python ≥ 3.11**, **Node ≥ 22**, and [pnpm](https://pnpm.io/). Then:

`pip install -e ".[dev]"`

That puts the `reviewdistill` command on your `PATH`. In a paper repository:

1. `reviewdistill init --name paper-01 --command myremark`
2. Proofread with `\myremark{...}` (or the commands you passed to `init`). Define `\newcommand{\myremark}[1]{#1}` in the preamble if needed.
3. `reviewdistill extract` (add `--watch` to keep extracting).
4. `reviewdistill ui` → http://127.0.0.1:8765 — **Label with AI**, then Accept a suggestion or pick a type in the menu. **Verify** or **Drop** stamps quality.
5. Repeat on the next paper; the taxonomy is reused.
6. `reviewdistill export --format md -o SKILL.md`
7. Put that file in `.cursor/skills/scholarly-review/` (or the equivalent for another coding agent).

The full guide: [Install](./website/docs/install.md), [Workflow](./website/docs/workflow.md), [UI](./website/docs/ui.md), [LLM settings](./website/docs/llm.md), [Export](./website/docs/export.md).

To see the data folder: `reviewdistill paths`, or header **Settings → Data** (Open folder, or Save a new path). To copy it somewhere else: `reviewdistill paths move ~/Documents/reviewdistill`.

Run the documentation site locally: `pnpm --dir website start`. GitHub Pages will serve it at `https://zhangyu94.github.io/ReviewDistill/` when you enable Pages.

## Who it is for

Researchers and authors who proofread their own (or others’) manuscripts in LaTeX and want those comments to become a reusable review skill for coding agents.

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
| `python client_build.py` | Rebuild packaged UI without reinstalling |

Client source: [`client/`](./client/). Docs site: [`website/`](./website/). Product spec and schema: [`docs/spec.md`](./docs/spec.md), [`docs/data-schema.md`](./docs/data-schema.md), [`docs/comment-identity.md`](./docs/comment-identity.md).

## License

ReviewDistill is released under the [MIT License](./LICENSE).
