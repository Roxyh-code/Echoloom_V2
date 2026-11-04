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
