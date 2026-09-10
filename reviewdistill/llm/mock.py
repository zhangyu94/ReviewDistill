from __future__ import annotations


class MockLLMProvider:
    name = "mock"

    def __init__(self, scripted_response: str | None = None):
        self.scripted_response = scripted_response

    def generate(self, prompt: str) -> str:
        if self.scripted_response is not None:
            return self.scripted_response
        return (
            '{"recommendation":"new","issue_code":"MOCKISSUE",'
            '"issue_name":"Mock issue","category":"General",'
            '"definition":"A placeholder issue from the mock provider.",'
            '"confidence":0.5,"rationale":"Mock provider used in tests.",'
            '"suggested_evidence":null}'
        )
