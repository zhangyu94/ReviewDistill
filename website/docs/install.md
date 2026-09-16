import useBaseUrl from '@docusaurus/useBaseUrl';

# Install

You need **Python ≥ 3.11**.

```sh
git clone https://github.com/zhangyu94/ReviewDistill.git
cd ReviewDistill
pip install -e .
reviewdistill --help
```

<img
  src={useBaseUrl('/video/install.gif')}
  alt="The CLI printing command help"
/>

From a git clone, that `pip install` compiles the UI from `client/` (the built files are not in git). If it asks for Node ≥ 22 and pnpm, that is only for that compile. After it succeeds, `reviewdistill ui` is Python only.

Labels and comments live in `~/.reviewdistill`, not in the paper repo. How to move that folder: [Data folder](./data.md).

Next: [Your first paper](./first-paper.md).
