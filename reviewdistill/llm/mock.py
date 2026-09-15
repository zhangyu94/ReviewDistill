from __future__ import annotations

import json
import re


class MockLLMProvider:
    name = "mock"

    def __init__(self, scripted_response: str | None = None):
        self.scripted_response = scripted_response

    def generate(self, prompt: str) -> str:
        if self.scripted_response is not None:
            return self.scripted_response
        from reviewdistill.coding.split import SPLIT_TASK

        if SPLIT_TASK in prompt:
            # Split prompts need labels+assignments JSON; coding prompts keep the recommendation object.
            ids = re.findall(r"^- id=(\S+)", prompt, re.M)
            labels = [
                {
                    "name": "Split type A",
                    "definition": "First partition from the mock provider.",
                },
                {
                    "name": "Split type B",
                    "definition": "Second partition from the mock provider.",
                },
            ]
            assignments = [
                {"comment_id": comment_id, "label_index": index % 2}
                for index, comment_id in enumerate(ids)
            ]
            return json.dumps({"labels": labels, "assignments": assignments})
        return (
            '{"recommendation":"new",'
            '"label_name":"Mock label","parent_id":null,'
            '"definition":"A placeholder label from the mock provider.",'
            '"confidence":0.5,"rationale":"Mock provider used in tests.",'
            '"suggested_evidence":null}'
        )
