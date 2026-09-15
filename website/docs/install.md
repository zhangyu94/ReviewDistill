# Install

Install from this GitHub repository. You get a `reviewdistill` command to run inside paper directories. Next: [Workflow](./workflow.md).

## Prerequisites

- **Python ≥ 3.11**
- **Node ≥ 22**
- [pnpm](https://pnpm.io/)

Node and pnpm are used once during install so `reviewdistill ui` can open the UI in the browser.

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

Comments and labels are stored in one folder on your computer (not in the paper repo):

- Default: `~/.reviewdistill`
- Comments: `~/.reviewdistill/comments.jsonl` (plus `projects.jsonl`, `codings.jsonl`, `labels.jsonl`, …)

Print the resolved paths:

```sh
reviewdistill paths
```

Header **Settings → Data** shows the same folder. Edit the path or **Choose…** a folder, then **Save** to point ReviewDistill at it (`paths use`; it does not copy files). **Open folder** reveals it in the file manager. Backup and `paths move` are in that folder’s `README.md`. Do not edit JSONL while `ui` or `extract` is running.

To store it in a new folder:

```sh
reviewdistill paths move ~/Documents/reviewdistill
```

That copies the current folder into an empty destination and stores new comments there. If you already copied the folder yourself:

```sh
reviewdistill paths use ~/Documents/reviewdistill
```

Quit `reviewdistill ui` and `extract --watch` before `move`. Restart them afterwards. Do not put the live folder in Dropbox, iCloud, or Google Drive.

## If you change the UI

Rebuild, then restart `reviewdistill ui`:

`pip install -e ".[dev]"` or `python client_build.py`

Python tests: `python -m pytest`. Client tests: `pnpm --dir client test`. Client lint: `pnpm --dir client lint`.
