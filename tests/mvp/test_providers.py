import base64
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from echoloom.config import Settings
from echoloom.providers import (
    OpenAIImages,
    OpenAIText,
    ProviderUnavailable,
    chat_context,
)
from echoloom.schemas import Profile, Refinement, apply_changes


def test_minimal_schema_and_patch_validation():
    profile = Profile(name="A")
    assert profile.backstory == "" and profile.appearance.hair == ""
    result, diff = apply_changes(
        profile,
        Refinement(
            changes=[{"path": "appearance.hair", "value": "blue"}], explanation="hair"
        ),
    )
    assert result.appearance.hair == "blue" and profile.appearance.hair == ""
    assert diff == [{"path": "appearance.hair", "before": "", "after": "blue"}]
    for changes in (
        [{"path": "id", "value": "evil"}],
        [{"path": "personality", "value": "evil"}],
        [{"path": "name", "value": "A"}, {"path": "name", "value": "B"}],
        [{"path": "personality.core_traits", "value": "not an array"}],
    ):
        with pytest.raises(ValueError):
            apply_changes(profile, Refinement(changes=changes, explanation="bad"))
    with pytest.raises(ValidationError):
        Profile(name="A", unexpected="field")


def test_bounded_context_keeps_recent_whole_turns():
    settings = Settings(
        _env_file=None, max_chat_context_tokens=2200, max_output_tokens=300
    )
    history = []
    for i in range(20):
        history.extend(
            [
                {"role": "user", "content": f"{i}:" + "a" * 150},
                {"role": "assistant", "content": "b" * 150},
            ]
        )
    context = chat_context(Profile(name="A"), history, "last", settings)
    assert context[0]["role"] == "system" and context[-1]["content"] == "last"
    assert len(context) < len(history)
    assert context[-2] == history[-1] and context[-3] == history[-2]
    assert sum(len(m["content"].encode()) + 16 for m in context) <= 2200 - 300 - 256
    with pytest.raises(ValueError):
        chat_context(Profile(name="A", backstory="汉" * 2000), [], "hello", settings)


def test_missing_credentials_are_explicit_no_fallback():
    settings = Settings(
        _env_file=None, llm_api_key="", image_api_key="", llm_model="", image_model=""
    )
    with pytest.raises(ProviderUnavailable):
        OpenAIText(settings).generate("anything")
    with pytest.raises(ProviderUnavailable):
        OpenAIImages(settings).render("anything")


def test_adapter_calls_official_sdk_and_uses_source_for_edit(monkeypatch):
    calls = []

    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.complete)
            )
            self.images = SimpleNamespace(generate=self.generate, edit=self.edit)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def complete(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content='{"name":"Vera"}'),
                    )
                ],
                usage=None,
            )

        def generate(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(b"image").decode())]
            )

        def edit(self, **kwargs):
            return self.generate(**kwargs)

    monkeypatch.setattr("echoloom.providers.OpenAI", Client)
    settings = Settings(
        _env_file=None,
        llm_api_key="test-only",
        llm_model="configured-text-model",
        image_model="configured-image-model",
    )
    assert OpenAIText(settings).generate("Vera").name == "Vera"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["model"] == "configured-text-model"
    assert OpenAIImages(settings).render("hair", b"original") == b"image"
    assert calls[-1]["image"] == ("portrait.png", b"original", "image/png")
    assert "response_format" not in calls[-1]  # GPT image models return b64 directly.
