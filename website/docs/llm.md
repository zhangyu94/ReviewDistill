# LLM settings

There is no default model. Until `llm.provider` is set, the Uncoded inspector shows **No AI suggestion** and **Get AI suggestions** stays disabled. Mock proposals from older runs are ignored.

Workbench **Settings** (header, next to Export) writes `llm.provider` / `llm.model` to the chosen paper’s `.reviewdistill/config.yaml` and the API key to that paper’s `.reviewdistill/.env` (gitignored). **Configure LLM** in the Uncoded empty state opens the same dialog.

## Config you can commit

```yaml
# paper/.reviewdistill/config.yaml
llm:
  provider: deepseek    # openai | anthropic | deepseek  (mock is tests-only)
  model: deepseek-chat
```

Do not put the key in YAML.

## Key file (gitignored)

```
# paper/.reviewdistill/.env  (copy from .env.example)
DEEPSEEK_API_KEY=sk-...
```

| `provider` | `.env` variable | typical `model` |
| --- | --- | --- |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |

A process environment variable of the same name wins if both are set. Settings **Save** with a blank key field keeps the existing `.env` value.

Calls go through [LiteLLM](https://github.com/BerriAI/litellm).

## Get AI suggestions

The button sends every uncoded working-dataset comment in one request. A paper’s `llm` block and `.env` are used even if you start `reviewdistill serve` from another directory, as long as **exactly one** registered paper has an LLM config. If two papers both have keys, set `llm` in `~/.reviewdistill/config.yaml` (or serve from the paper directory) so the workbench does not pick a key at random.

External providers receive the comment, nearby manuscript context, and candidate issue summaries — not the rest of your disk. After **Get AI suggestions**, the workbench shows that warning.

Key lookup order: process environment, then the paper’s `.reviewdistill/.env`, then leftover `llm.api_key` in YAML.
