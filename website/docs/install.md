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

Comments and issue types are stored in one folder on your computer (not in the paper repo):

- Default: `~/.reviewdistill`
- Database file: `~/.reviewdistill/reviewdistill.db`

Print the resolved paths:

```sh
reviewdistill paths
```

Workbench **Settings → Data** shows the same folder. Copy the **whole folder** to back up — not only the `.db` file — especially if ReviewDistill is running.

To store it in a new folder:

```sh
reviewdistill paths move ~/Documents/reviewdistill
```

That copies the current folder into an empty destination and stores new comments there. If you already copied the folder yourself:

```sh
reviewdistill paths use ~/Documents/reviewdistill
```

Quit `reviewdistill serve` and `extract --watch` before `move`. Restart them afterwards. Do not put the live folder in Dropbox, iCloud, or Google Drive.

## If you change the workbench UI

Rebuild, then restart `reviewdistill serve`:

`pip install -e ".[dev]"` or `scripts/build-studio-assets.sh`

Python tests: `python -m pytest`. Studio tests: `pnpm --dir studio test`.
