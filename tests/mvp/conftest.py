from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from echoloom.api import create_app
from echoloom.config import Settings
from echoloom.db import Base, make_engine
from echoloom.providers import ProviderError
from echoloom.schemas import Profile, Refinement


class FakeText:
    """Test-only deterministic provider. Never registered in production."""

    def __init__(self):
        self.calls = []
        self.fail = False

    def generate(self, description):
        self.calls.append(("generate", description))
        if self.fail:
            raise ProviderError("Simulated provider failure")
        return Profile(
            name="Evelyn",
            short_description="A librarian who loves astronomy",
            appearance={"hair": "Long silver hair", "eyes": "Blue"},
            personality={
                "core_traits": ["Intelligent", "Reserved", "Caring toward friends"]
            },
            backstory="Works at a library in a mountain town.",
            speech_style={"tone": "Calm and slightly sarcastic"},
        )

    def refine(self, profile, instruction):
        self.calls.append(("refine", instruction))
        return Refinement(
            changes=[
                {
                    "path": "personality.core_traits",
                    "value": ["Intelligent", "Distant", "Caring toward friends"],
                }
            ],
            explanation="Adjust only the core traits and preserve all other details.",
        )

    def story(self, context):
        import json

        from echoloom.story_context import validate_story_output
        from echoloom.story_schemas import StoryOutput

        self.calls.append(("story", context))
        if self.fail:
            raise ProviderError("Simulated story failure")
        frame = json.loads(context[-1]["content"])
        event = frame["event"]
        kind = event["kind"]
        if kind == "start":
            first = "Rain traces the bookshop window as two old friends meet again."
            ending = {
                "type": "decision",
                "question": "How would you like to respond?",
                "options": [
                    {"intent": "Ask what happened"},
                    {"intent": "Change the subject"},
                ],
            }
        elif kind == "end":
            first = (
                "The bookshop lights soften as the conversation comes to a quiet close."
            )
            ending = {"type": "ending"}
        else:
            first = (
                "She explains the missing letter."
                if "Ask what happened" in event.get("content", "")
                else "She turns to the weather."
                if "Change the subject" in event.get("content", "")
                else "She responds to your contribution: "
                + event.get("content", "The evening continues.")
            )
            if event.get("rewrite_instruction"):
                first = "Revised scene: " + event["rewrite_instruction"]
            ending = {"type": "continue"}
        if event.get("rewrite_instruction"):
            first = "Revised scene: " + event["rewrite_instruction"]
        output = StoryOutput.model_validate(
            {
                "title": "A Rainy Reunion",
                "blocks": [
                    {"type": "narration", "speaker": None, "text": first},
                    {
                        "type": "action",
                        "speaker": "character",
                        "text": "She sets a book on the table.",
                    },
                    {
                        "type": "dialogue",
                        "speaker": "character",
                        "text": "It has been a while. Would you like to talk?",
                    },
                    {
                        "type": "dialogue",
                        "speaker": "player",
                        "text": "It has been a long time.",
                    },
                    {
                        "type": "action",
                        "speaker": "player",
                        "text": "You glance at the window.",
                    },
                    {
                        "type": "narration",
                        "speaker": None,
                        "text": "UNREAD_DRAWER: A sealed drawer catches the lamplight.",
                    },
                ],
                "ending": ending,
                "summary": "The effective scene includes UNREAD_DRAWER.",
                "confirmed_facts": ["The scene is in a bookshop", "UNREAD_DRAWER"],
            }
        )
        return validate_story_output(output, context)

    def chat(self, messages):
        self.calls.append(("chat", messages))
        if self.fail:
            raise ProviderError("Simulated provider failure")
        return "A book about dying stars. Surprisingly cheerful material, isn't it?"


class FakeImages:
    def __init__(self):
        self.sources = []
        self.fail = False

    def render(self, prompt, source=None):
        self.sources.append(source)
        if self.fail:
            raise ProviderError("Simulated image failure")
        stream = BytesIO()
        Image.new("RGB", (32, 32), "navy" if source else "lavender").save(stream, "PNG")
        return stream.getvalue()


@pytest.fixture
def setup(tmp_path):
    settings = Settings(
        _env_file=None,
        companion_worker_enabled=False,
        calendar_key_file=tmp_path / "calendar.key",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        image_directory=tmp_path / "images",
    )
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    text, images = FakeText(), FakeImages()
    app = create_app(settings, text, images, engine)
    with TestClient(app) as client:
        yield client, text, images, settings, engine
    engine.dispose()


@pytest.fixture
def character(setup):
    client = setup[0]
    response = client.post(
        "/api/characters/generate",
        json={
            "description": "A quiet, intelligent librarian with silver hair and blue eyes."
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
