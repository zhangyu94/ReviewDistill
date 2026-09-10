# CLI

Visible commands:

| Command | Role |
| --- | --- |
| `reviewdistill init` | Create `.reviewdistill/` in the current paper repo |
| `reviewdistill extract` | Pull comments from `.tex` (`--watch` keeps going) |
| `reviewdistill serve` | Workbench + API on `:8765` |
| `reviewdistill export` | Write the rubric (`--format`, `--output`) |

`init` options: `--name`, `--command` (repeatable; default `myremark`).

`serve` options: `--host` (default `127.0.0.1`), `--port` (default `8765`).

Hidden aliases still work for old scripts: `watch` (same as `extract --watch`), `cluster`, `taxonomy export`. They are not listed in `--help`.
