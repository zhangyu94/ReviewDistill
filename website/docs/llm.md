# LLM settings

There is no default model. Until `llm.provider` is set, the Unlabeled inspector shows **No AI suggestion** and **Label with AI** stays disabled. Mock proposals from older runs are ignored.

Header **Settings** (next to History and Export) **Assistant** panel writes `llm.provider` / `llm.model` to the ReviewDistill home `config.yaml` and the API key to that folder’s `.env` (gitignored). **Configure LLM** in the Unlabeled empty state opens the same dialog. There is no paper picker.

## Config you can commit

```yaml
# ReviewDistill home config.yaml  (Settings → Data / `reviewdistill paths`)
llm:
  provider: deepseek    # openai | anthropic | deepseek  (mock is tests-only)
  model: deepseek-chat
```

Do not put the key in YAML. Paper `.reviewdistill/config.yaml` is comments-only (`project` and latex commands). Leftover paper `llm:` / `.env` are ignored.

## Key file (gitignored)

```
# ReviewDistill home .env
DEEPSEEK_API_KEY=sk-...
```

| `provider` | `.env` variable | typical `model` |
| --- | --- | --- |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |

A process environment variable of the same name wins if both are set. Settings loads the saved key into the API key field (password until **Show**). **Save** with a blank key field keeps the existing `.env` value.

Calls go through [LiteLLM](https://github.com/BerriAI/litellm).

## Label with AI

The button sends every unlabeled comment to distill in one request. A thin progress bar at the top of the window runs until that request and the UI refresh finish. Label with AI is store-wide: the assistant is the home folder’s `llm` block and `.env`, not a paper.

Taxonomy **fork** (header on an empty forest, or hover on a leaf with at least two labels) uses the same provider in one prompt. Invalid JSON writes nothing. Header fork includes unlabeled comments that already have a proposal; Label with AI skips those.

External providers receive the comment, nearby manuscript context, and candidate issue summaries — not the rest of your disk. The CLI prints that warning; the UI does not.

Lookup: process environment `REVIEWDISTILL_LLM_PROVIDER` / `REVIEWDISTILL_LLM_MODEL` if set, else home `config.yaml`. Key: process environment for that provider, then the home folder’s `.env`. Settings shows the home files, not those process-env overrides.
