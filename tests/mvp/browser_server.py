"""Ephemeral test server for Playwright. Not a runtime provider mode."""

import os
import tempfile
from pathlib import Path

import uvicorn
from conftest import FakeImages, FakeText

from echoloom.api import create_app
from echoloom.config import Settings
from echoloom.db import Base, make_engine

if __name__ == "__main__":
    if os.environ.get("ECHOLOOM_TEST_SERVER") != "1":
        raise SystemExit("Test server only: invoke through npm run test:e2e.")
    with tempfile.TemporaryDirectory(prefix="echoloom-e2e-") as directory:
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite:///{directory}/test.db",
            image_directory=Path(directory) / "images",
            llm_api_key="test-only",
            llm_model="test-only",
            image_api_key="test-only",
            image_model="test-only",
        )
        engine = make_engine(settings.database_url)
        Base.metadata.create_all(engine)
        print("TEST ONLY: AI providers mocked; data is temporary.", flush=True)
        uvicorn.run(
            create_app(settings, FakeText(), FakeImages(), engine),
            host="127.0.0.1",
            port=8001,
        )
        engine.dispose()
