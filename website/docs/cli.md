# CLI

Visible commands:

| Command | Role |
| --- | --- |
| `reviewdistill init` | Create `.reviewdistill/` in the current paper repo |
| `reviewdistill extract` | Pull comments from `.tex` (`--watch` keeps going) |
| `reviewdistill serve` | Workbench + API on `:8765` |
| `reviewdistill export` | Write the rubric (`--format`, `--output`) |
| `reviewdistill paths` | Print the data folder and database file |
| `reviewdistill paths use DIR` | Use `DIR` for comments and issue types from now on |
| `reviewdistill paths move DIR` | Copy the current data folder to `DIR` and keep using it |

`init` options: `--name`, `--command` (repeatable; default `myremark`).

`serve` options: `--host` (default `127.0.0.1`), `--port` (default `8765`).

`move` copies the whole current folder into an empty `DIR` and leaves the old folder in place. Quit `serve` and `extract --watch` first; restart them after `use` or `move`.

Hidden aliases still work for old scripts: `watch` (same as `extract --watch`), `cluster`, `taxonomy export`. They are not listed in `--help`.
