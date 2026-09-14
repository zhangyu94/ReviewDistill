# Internals

Contributor-facing specs live in the GitHub repository, not on this site:

- [Product spec](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/spec.md) — goals, UI rules, APIs
- [Data schema](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/data-schema.md) — project and comment columns
- [Comment identity](https://github.com/zhangyu94/ReviewDistill/blob/main/docs/comment-identity.md) — new / revision / move / gone from the source

Client source: [`client/`](https://github.com/zhangyu94/ReviewDistill/tree/main/client). `pip install -e` builds that UI so `reviewdistill serve` can host it; see [`client_build.py`](https://github.com/zhangyu94/ReviewDistill/blob/main/client_build.py).
