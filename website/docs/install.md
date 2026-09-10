# Install

Install from this GitHub repository. You get a `reviewdistill` command to run inside paper directories. Next: [Workflow](./workflow.md).

## Prerequisites

- **Python ≥ 3.11**
- **Node ≥ 22**
- [pnpm](https://pnpm.io/)

Node and pnpm are used once during install so `reviewdistill serve` can open the workbench in the browser.

## Install

```sh
git clone https://github.com/zhangyu94/ReviewDistill.git
cd ReviewDistill
pip install -e ".[dev]"
```

Check:

```sh
reviewdistill --help
```

## Where data lives

`$REVIEWDISTILL_HOME` (default `~/.reviewdistill`) holds the shared SQLite database and optional home-level LLM settings. The taxonomy accumulates there across papers.

## If you change the workbench UI

Rebuild, then restart `reviewdistill serve`:

`pip install -e ".[dev]"` or `scripts/build-studio-assets.sh`

Python tests: `python -m pytest`. Studio tests: `pnpm --dir studio test`.
