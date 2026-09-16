# Storage

Comments, labels, assignments, examples, projects, and History are JSONL files in the ReviewDistill home folder (default `~/.reviewdistill`): one object per line, sorted by `id`. Columns: [`data-schema.md`](data-schema.md). There is no database server. SQLModel / Pydantic records in process are fine.

```
projects.jsonl
comments.jsonl
assignments.jsonl
labels.jsonl
label_examples.jsonl
history.jsonl
```

## Local-first and privacy

Manuscript and comments stay on this computer unless the reviewer configures an external LLM. When a request goes out, send the comment, nearby manuscript, and relevant label summaries, not the whole repository. The UI should make it obvious that text is leaving the machine.

Providers: OpenAI, Anthropic, DeepSeek, and (later) local models, behind one interface:

```python
class LLMProvider:
    def generate(...)
```
