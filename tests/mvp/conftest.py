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
            raise ProviderError("测试中的提供商故障")
        return Profile(
            name="伊芙琳",
            short_description="喜欢天文学的图书管理员",
            appearance={"hair": "银色长发", "eyes": "蓝色"},
            personality={"core_traits": ["聪明", "安静", "关心朋友"]},
            backstory="在山城的图书馆工作。",
            speech_style={"tone": "冷静，略带讽刺"},
        )

    def refine(self, profile, instruction):
        self.calls.append(("refine", instruction))
        return Refinement(
            changes=[
                {
                    "path": "personality.core_traits",
                    "value": ["聪明", "冷淡", "关心朋友"],
                }
            ],
            explanation="仅调整核心性格，保留其他设定。",
        )

    def chat(self, messages):
        self.calls.append(("chat", messages))
        if self.fail:
            raise ProviderError("测试中的提供商故障")
        return "一本关于垂死恒星的书。听起来是不是很振奋？"


class FakeImages:
    def __init__(self):
        self.sources = []
        self.fail = False

    def render(self, prompt, source=None):
        self.sources.append(source)
        if self.fail:
            raise ProviderError("测试中的图片故障")
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
        json={"description": "银发蓝眼，安静聪明的图书管理员。"},
    )
    assert response.status_code == 201, response.text
    return response.json()
