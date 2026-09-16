# CLI

| Command | Role |
| --- | --- |
| `reviewdistill init` | Create `.reviewdistill/` in this paper repo |
| `reviewdistill extract` | Pull comments from `.tex` (`--watch` keeps going) |
| `reviewdistill ui` | Open the workbench at http://127.0.0.1:8765 |
| `reviewdistill export` | Write a skill (`md`); `yaml` / `json` dump the taxonomy |
| `reviewdistill paths` | Print the data folder |
| `reviewdistill paths use DIR` | Use `DIR` from now on |
| `reviewdistill paths move DIR` | Copy the current folder to `DIR` and keep using it |

`init`: `--name`, `--command` (repeatable; default `myremark`).

`ui`: `--host` (default `127.0.0.1`), `--port` (default `8765`).

`export`: `--format` (default `md`), `--output` / `-o` (default `SKILL.md` for `md`, `review-taxonomy.yaml` / `review-taxonomy.json` for those formats), `--id` (repeatable).

`move` needs an empty destination. Quit `ui` and `extract --watch` first; restart them after `use` or `move`.
