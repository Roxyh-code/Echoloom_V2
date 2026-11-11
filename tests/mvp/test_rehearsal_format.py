import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from echoloom.config import Settings
from echoloom.providers import InvalidModelOutput, OpenAIText, ProviderError
from echoloom.rehearsal_schema import Performance


def test_one_correction_then_success_preserves_original_messages(monkeypatch):
    provider = OpenAIText(Settings(_env_file=None))
    messages = [
        {"role": "system", "content": "Rules"},
        {"role": "user", "content": "Scene"},
    ]
    original = deepcopy(messages)
    calls = []

    def request(m, schema, **kwargs):
        calls.append((m, schema, kwargs))
        if len(calls) == 1:
            raise InvalidModelOutput(
                "bad", [{"loc": ["blocks", 0, "text"], "type": "string_too_long"}]
            )
        return Performance(blocks=[{"type": "narration", "text": "A quiet station."}])

    monkeypatch.setattr(provider, "_request", request)
    result = provider.rehearsal_once(messages)
    assert len(calls) == 2
    assert all(call[2] == {"max_retries": 0} for call in calls)
    assert "string_too_long" in calls[1][0][-1]["content"]
    assert result.blocks[0].text == "A quiet station."
    assert messages == original


def test_second_bad_output_stops(monkeypatch):
    provider = OpenAIText(Settings(_env_file=None))
    calls = 0

    def request(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise InvalidModelOutput("bad")

    monkeypatch.setattr(provider, "_request", request)
    with pytest.raises(InvalidModelOutput, match="after one format correction"):
        provider.rehearsal_once([])
    assert calls == 2


def test_network_or_refusal_error_not_corrected(monkeypatch):
    provider = OpenAIText(Settings(_env_file=None))
    calls = 0

    def request(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise ProviderError("Request failed or declined")

    monkeypatch.setattr(provider, "_request", request)
    with pytest.raises(ProviderError):
        provider.rehearsal_once([])
    assert calls == 1


def test_actual_schema_failure_logs_codes_not_generated_content(monkeypatch, caplog):
    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content=json.dumps(
                                {
                                    "blocks": [
                                        {
                                            "type": "dialogue",
                                            "text": {
                                                "secret": "PRIVATE_GENERATED_TEXT"
                                            },
                                        }
                                    ]
                                }
                            )
                        ),
                    )
                ],
                usage=None,
            )

    monkeypatch.setattr("echoloom.providers.OpenAI", Client)
    provider = OpenAIText(
        Settings(_env_file=None, llm_api_key="test-only", llm_model="test-model")
    )
    with pytest.raises(InvalidModelOutput) as error:
        provider._request([], Performance, max_retries=0)
    assert error.value.validation_errors[0]["loc"] == ["blocks", 0, "text"]
    assert error.value.validation_errors[0]["type"] == "string_type"
    assert "PRIVATE_GENERATED_TEXT" not in caplog.text
    assert "test-only" not in caplog.text
    assert "schema_errors=" in caplog.text
