# Data folder

Comments and labels live in one folder on your computer:

- Default: `~/.reviewdistill`
- `reviewdistill paths` prints the resolved folder

**Settings → Data** shows the same path. **Save** points ReviewDistill at a folder (`paths use`; it does not copy files). **Open folder** reveals it in the file manager.

```sh
reviewdistill paths move ~/Documents/reviewdistill
```

That copies into an empty destination. If you already copied the folder:

```sh
reviewdistill paths use ~/Documents/reviewdistill
```

Quit `ui` and `extract --watch` before `move`. Do not put the live folder in Dropbox, iCloud, or Google Drive. Do not edit JSONL while `ui` or `extract` is running. Backup notes are in that folder’s `README.md`.
