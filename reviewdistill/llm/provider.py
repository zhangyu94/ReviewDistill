from __future__ import annotations

import logging

from reviewdistill.llm.base import require_api_key

log = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "deepseek": "deepseek-chat",
}


def litellm_model_id(provider: str, model: str | None) -> str:
    name = (model or DEFAULT_MODELS[provider]).strip()
    if "/" in name:
        return name
    return f"{provider}/{name}"


class LiteLLMProvider:
    def __init__(self, *, name: str, model: str | None):
        self.name = name
        self.model = model or DEFAULT_MODELS[name]

    def generate(self, prompt: str) -> str:
        api_key = require_api_key(self.name)
        import os

        os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
        import litellm

        litellm.drop_params = True
        try:
            response = litellm.completion(
                model=litellm_model_id(self.name, self.model),
                messages=[
                    {"role": "system", "content": "Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=4096,
                api_key=api_key,
                timeout=60.0,
                num_retries=3,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            log.exception("LLM request failed (%s)", self.name)
            raise RuntimeError(f"LLM request failed ({self.name})") from exc
        choices = getattr(response, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message is not None else None
        return content or ""
