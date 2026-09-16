# Internals

Contributor specs live in the GitHub repository, not on these pages:

- [Product spec](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/spec/README.md)
- [Data schema](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/spec/data-schema.md)
- [Comment identity](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/spec/comment-identity.md)

Client source: [`client/`](https://github.com/zhangyu94/ReviewDistill/tree/main/client). A git clone’s `pip install -e .` (or `python client_build.py`) compiles that Vue app into `reviewdistill/web/static/`. That compile needs **Node ≥ 22** and [pnpm](https://pnpm.io/). `reviewdistill ui` then serves the files; it does not run Node.

After UI work, `pnpm --dir client dev` proxies `/api` from Vite on :5173 while the API is already on `:8765`. Rebuild packaged assets before relying on `reviewdistill ui` again. Tests and linters: `pip install -e ".[dev]"`.
