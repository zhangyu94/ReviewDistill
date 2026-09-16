import useBaseUrl from '@docusaurus/useBaseUrl';

# Install

You need **Python ≥ 3.11**.

```sh
pip install reviewdistill
reviewdistill --help
```

<img
  src={useBaseUrl('/video/install.gif')}
  alt="The CLI printing command help"
/>

The wheel includes the workbench. You do not need Node. `reviewdistill ui` is Python only.

Labels and comments live in `~/.reviewdistill`, not in the paper repo. How to move that folder: [Data folder](./data.md).

To work on the source, clone the repository and see [Internals](./internals.md).

Next: [Your first paper](./first-paper.md).
