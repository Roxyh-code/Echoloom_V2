"""Ephemeral test server for Playwright. Not a runtime provider mode."""

import os
import tempfile
from datetime import timedelta
from pathlib import Path

import uvicorn
from conftest import FakeImages, FakeText
from fastapi import HTTPException
from sqlalchemy import delete
from test_companion import Clock, FakeGoogle, event

from echoloom.api import create_app
from echoloom.config import Settings
from echoloom.db import Base, make_engine

if __name__ == "__main__":
    if os.environ.get("ECHOLOOM_TEST_SERVER") != "1":
        raise SystemExit("Test server only: invoke through npm run test:e2e.")
    with tempfile.TemporaryDirectory(prefix="echoloom-e2e-") as directory:
        settings = Settings(
            _env_file=None,
            companion_worker_enabled=False,
            app_origin="http://127.0.0.1:3001",
            google_client_id="test-client",
            google_client_secret="test-secret",
            calendar_key_file=Path(directory) / "calendar.key",
            google_redirect_uri="http://127.0.0.1:3001/api/integrations/google-calendar/callback",
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
        clock = Clock()
        google = FakeGoogle(clock)
        app = create_app(
            settings,
            FakeText(),
            FakeImages(),
            engine,
            calendar_provider=google,
            clock=clock,
        )

        @app.post("/__test/reset")
        def reset():
            # Only this isolated executable registers these endpoints. Never part
            # of the production application or a runtime fake-provider setting.
            with engine.begin() as connection:
                for table in reversed(Base.metadata.sorted_tables):
                    connection.execute(delete(table))
            clock.value = Clock()()
            google.items = [event(clock, offset=60)]
            return {"reset": True}

        @app.post("/__test/advance/{minutes}")
        def advance(minutes: int):
            if minutes < 0 or minutes > 1440:
                raise HTTPException(422)
            clock.value += timedelta(minutes=minutes)
            app.state.companion.tick()
            return {"current": clock().isoformat()}

        @app.post("/__test/cancel")
        def cancel():
            google.items[0]["status"] = "cancelled"
            return {"cancelled": True}

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8001,
        )
        engine.dispose()
