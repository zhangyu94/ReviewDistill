# LLM

There is no default model. Until you set a provider, **Label with AI** stays off.

**Settings → Assistant** writes `llm.provider` / `llm.model` to the home `config.yaml` and the API key to that folder’s `.env` (gitignored). **Configure LLM** in the empty unlabeled state opens the same dialog.

```yaml
# ~/.reviewdistill/config.yaml  (or Settings → Data)
llm:
  provider: deepseek    # openai | anthropic | deepseek
  model: deepseek-chat
```

```
# ~/.reviewdistill/.env
DEEPSEEK_API_KEY=sk-...
```

| `provider` | `.env` variable | typical `model` |
| --- | --- | --- |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |

A process environment variable of the same name wins if both are set. **Save** with a blank key field keeps the existing `.env` value.

**Label with AI** sends every unlabeled comment in one request (comment, nearby manuscript, candidate label summaries) and assigns them. Taxonomy **fork** uses the same provider. Nothing else on disk is sent.

`REVIEWDISTILL_LLM_PROVIDER` / `REVIEWDISTILL_LLM_MODEL` override YAML. Settings shows the home files, not those overrides.
