# Introduction

If you proofread in LaTeX, you already leave a remark on the sentence that is wrong:

```latex
The results demonstrate that the method is effective.
\myremark{Demonstrate is too strong here.}
```

That note helps this draft. A week later you open another paper and type the same kind of comment, because the last round never left that file.

ReviewDistill is for that loop. It pulls the remarks out with the sentence they sit in. You group the ones that keep coming back into labels, then export a skill (`SKILL.md`) into the folder your coding agent already reads. On the next paper the agent can reuse those checks, so you spend less time catching the same issues by hand.

Comments and API keys stay on your computer.

Next: [Install](./install.md).
