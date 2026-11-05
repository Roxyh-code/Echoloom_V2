"""Calendar network and AI are deterministic fakes; no paid calls or Google data."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from conftest import FakeImages, FakeText
from fastapi.testclient import TestClient
from sqlalchemy import select

from echoloom.api import create_app
from echoloom.calendar_auth import (
    CalendarFailure,
    CalendarRevoked,
    SyncExpired,
    challenge,
)
from echoloom.calendar_context import instant, next_allowed, normalize, quiet
from echoloom.companion_models import (
    CalendarConnection,
    CalendarEvent,
    CompanionSettings,
    CompanionTask,
    EventMemory,
)
from echoloom.config import Settings
from echoloom.db import Base, Character, Message, make_engine, sessions


class Clock:
    def __init__(self):
        self.value = datetime(2026, 11, 4, 14, 0, tzinfo=UTC)

    def __call__(self):
        return self.value


class FakeGoogle:
    def __init__(self, clock):
        self.clock = clock
        self.items = []
        self.calls = []
        self.fail = False
        self.revoked = False
        self.expired = False
        self.refreshes = 0

    def authorization_url(self, state, verifier):
        self.calls.append((state, verifier))
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}&code_challenge={challenge(verifier)}&code_challenge_method=S256"

    def exchange(self, code, verifier):
        assert code == "test-code" and verifier == self.calls[-1][1]
        return {
            "access_token": "private-access",
            "refresh_token": "private-refresh",
            "expires_at": (self.clock() + timedelta(hours=1)).isoformat(),
        }

    def email(self, credentials):
        return "test@example.test"

    def refresh(self, credentials):
        self.refreshes += 1
        if self.revoked:
            raise CalendarRevoked()
        return {
            **credentials,
            "expires_at": (self.clock() + timedelta(hours=1)).isoformat(),
        }

    def events(self, credentials, token, start, end):
        if self.fail:
            raise CalendarFailure()
        if token and self.expired:
            self.expired = False
            raise SyncExpired()
        return self.items, "sync-token", "America/New_York"

    def event(self, credentials, key):
        return next(i for i in self.items if i["id"] == key)

    def revoke(self, credentials):
        self.revoked = True


def event(clock, key="exam", offset=30, title="Physics exam"):
    return {
        "id": key,
        "summary": title,
        "status": "confirmed",
        "start": {"dateTime": (clock() + timedelta(minutes=offset)).isoformat()},
        "end": {"dateTime": (clock() + timedelta(minutes=offset + 60)).isoformat()},
    }


@pytest.fixture
def companion(tmp_path):
    clock = Clock()
    google = FakeGoogle(clock)
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/test.db",
        image_directory=tmp_path / "portraits",
        calendar_key_file=tmp_path / "key",
        google_client_id="test-client",
        google_client_secret="test-secret",
        allow_additional_accounts=True,
        companion_worker_enabled=False,
    )
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    text = FakeText()
    app = create_app(
        settings, text, FakeImages(), engine, calendar_provider=google, clock=clock
    )
    with TestClient(app) as client:
        yield client, app.state.companion, google, clock, sessions(engine), text
    engine.dispose()


def register(client, name="owner"):
    result = client.post(
        "/api/account/register",
        json={"username": name, "password": "a-strong-test-password"},
    )
    assert result.status_code == 200, result.text


def character(client):
    result = client.post(
        "/api/characters/generate",
        json={
            "description": "A thoughtful astronomer with a warm, dry sense of humor."
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def connect(client, char):
    result = client.post(
        "/api/integrations/google-calendar/connect",
        json={
            "character_id": char["id"],
            "conversation_id": char["conversation_id"],
            "timezone": "America/New_York",
        },
    )
    assert result.status_code == 200, result.text
    state = parse_qs(urlparse(result.json()["authorization_url"]).query)["state"][0]
    response = client.get(
        "/api/integrations/google-calendar/callback",
        params={"state": state, "code": "test-code"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response, state


def timeline(client, char):
    return client.get(f"/api/conversations/{char['conversation_id']}/timeline").json()


def test_legacy_claim_login_and_two_user_isolation(companion):
    client, _service, _google, _clock, factory, _text = companion
    legacy = character(client)
    register(client)
    assert client.get(f"/api/characters/{legacy['id']}").status_code == 200
    with factory() as db:
        assert db.get(Character, legacy["id"]).owner_id
    client.post("/api/account/logout")
    assert client.get("/api/characters").status_code == 401
    register(client, "second")
    assert client.get("/api/characters").json() == []
    for path in (
        f"/api/characters/{legacy['id']}",
        f"/api/conversations/{legacy['conversation_id']}/timeline",
    ):
        assert client.get(path).status_code == 404
    bad = client.post(
        "/api/companion/activate",
        json={
            "character_id": legacy["id"],
            "conversation_id": legacy["conversation_id"],
        },
    )
    assert bad.status_code == 404
    assert (
        client.post(
            "/api/account/logout", headers={"Origin": "https://evil.test"}
        ).status_code
        == 403
    )
    client.post("/api/account/logout")
    assert (
        client.post(
            "/api/account/login",
            json={"username": "owner", "password": "a-strong-test-password"},
        ).status_code
        == 200
    )
    assert len(client.get("/api/characters").json()) == 1


def test_oauth_encrypted_single_use_and_disconnect_preserves_chat(companion):
    client, service, google, clock, factory, _text = companion
    register(client)
    char = character(client)
    google.items = [event(clock)]
    response, state = connect(client, char)
    assert "calendar=connected" in response.headers["location"]
    assert (
        "calendar=invalid"
        in client.get(
            "/api/integrations/google-calendar/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        ).headers["location"]
    )
    status = client.get("/api/companion/settings").json()
    assert status["status"] == "ready" and status["email"] == "test@example.test"
    assert "private-access" not in str(status) and "private-refresh" not in str(status)
    with factory() as db:
        connection = db.scalar(select(CalendarConnection))
        assert "private-refresh" not in connection.credentials
        assert (
            service.vault.open(connection.credentials)["refresh_token"]
            == "private-refresh"
        )
    service.tick()
    service.tick()
    rows = timeline(client, char)
    assert len(rows) == 2  # introduction and due pre-event
    assert all(
        r["source_type"] == "calendar_companion" and r["role"] == "assistant"
        for r in rows
    )
    assert len({r["timeline_order"] for r in rows}) == len(rows)
    client.delete("/api/integrations/google-calendar/connection")
    assert len(timeline(client, char)) == 2
    with factory() as db:
        assert db.scalar(select(CalendarConnection)) is None
        assert db.scalar(select(CalendarEvent)) is None
        assert db.scalar(select(CompanionTask)) is None
    service.tick()
    assert len(timeline(client, char)) == 2


def test_cancel_and_update_rechecked_before_delivery(companion):
    client, service, google, clock, factory, _text = companion
    register(client)
    char = character(client)
    google.items = [event(clock)]
    connect(client, char)
    google.items[0]["status"] = "cancelled"
    service.tick()
    assert len(timeline(client, char)) == 1  # no stale encouragement
    clock.value += timedelta(minutes=20)
    service.tick()
    with factory() as db:
        assert db.scalar(select(CalendarEvent)).status == "cancelled"


def test_quiet_hours_daily_cap_and_followup_restart_dedupe(companion):
    client, service, google, clock, factory, _text = companion
    register(client)
    char = character(client)
    google.items = [event(clock)]
    connect(client, char)
    service.tick()
    assert len(timeline(client, char)) == 2
    clock.value += timedelta(hours=3)
    service.tick()
    assert len(timeline(client, char)) == 3
    service.tick()
    with factory() as db:
        tasks = list(db.scalars(select(CompanionTask)))
        assert sum(t.status == "delivered" for t in tasks) == 3
    # A new task on the same local day is capped even after worker restarts.
    google.items.append(event(clock, "second", 30, "Job interview"))
    with factory() as db:
        service.sync(db, db.scalar(select(CalendarConnection)))
    service.tick()
    assert len(timeline(client, char)) == 3
    with factory() as db:
        task = db.scalar(
            select(CompanionTask).where(
                CompanionTask.event_key == "second", CompanionTask.kind == "before"
            )
        )
        assert task.status == "expired"


def test_switch_pause_delete_active_and_private_filter(companion):
    client, service, google, clock, _factory, _text = companion
    register(client)
    a, b = character(client), character(client)
    google.items = [
        event(clock, offset=60),
        event(clock, "private", 60, "Doctor appointment"),
    ]
    connect(client, a)
    service.tick()
    assert len(timeline(client, a)) == 1
    payload = {
        "character_id": b["id"],
        "conversation_id": b["conversation_id"],
        "timezone": "America/New_York",
    }
    assert client.post("/api/companion/activate", json=payload).status_code == 200
    clock.value += timedelta(minutes=30)
    service.tick()
    assert len(timeline(client, a)) == 1
    assert len(timeline(client, b)) == 1
    assert client.get("/api/companion/upcoming").json()[1]["title"] == "Private event"
    client.post("/api/companion/deactivate")
    clock.value += timedelta(hours=3)
    service.tick()
    assert len(timeline(client, b)) == 1
    client.delete(f"/api/characters/{b['id']}")
    status = client.get("/api/companion/settings").json()
    assert (
        status["connected"] and not status["enabled"] and status["character_id"] is None
    )


def test_sync_failure_refresh_and_410(companion):
    client, service, google, clock, _factory, _text = companion
    register(client)
    char = character(client)
    google.fail = True
    response, _ = connect(client, char)
    assert "calendar=error" in response.headers["location"]
    assert client.get("/api/companion/settings").json()["status"] == "sync_error"
    service.tick()
    assert timeline(client, char) == []
    google.fail = False
    clock.value += timedelta(minutes=16)
    service.tick()
    google.expired = True
    clock.value += timedelta(hours=1)
    service.tick()
    assert google.refreshes == 1
    assert client.get("/api/companion/settings").json()["status"] == "ready"
    google.revoked = True
    clock.value += timedelta(hours=1)
    service.tick()
    assert (
        client.get("/api/companion/settings").json()["status"] == "reconnect_required"
    )


def test_chat_relevance_user_confirmed_memory_and_standalone_history(companion):
    client, service, google, clock, factory, text = companion
    register(client)
    char = character(client)
    google.items = [event(clock)]
    connect(client, char)
    service.tick()

    def send(content):
        result = client.post(
            f"/api/conversations/{char['conversation_id']}/messages",
            json={"content": content, "request_id": str(uuid4())},
        )
        assert result.status_code == 200, result.text
        return text.calls[-1][1]

    ctx = send("Tell me about astronomy")
    assert not any("CALENDAR PRIVACY RULE" in m["content"] for m in ctx)
    assert any(m["role"] == "assistant" for m in ctx[:-1])  # standalone intro retained
    ctx = send("What is on my calendar today?")
    assert any("CALENDAR PRIVACY RULE" in m["content"] for m in ctx)
    send("I might have passed the Physics exam")
    with factory() as db:
        assert db.scalar(select(EventMemory)) is None
    send("I passed the Physics exam")
    with factory() as db:
        assert db.scalar(select(EventMemory)).user_quote == "I passed the Physics exam"
    client.delete("/api/integrations/google-calendar/connection")
    with factory() as db:
        assert db.scalar(select(EventMemory)) is None


def test_dst_all_day_sensitive_and_keyword_conservatism():
    pref = CompanionSettings(
        timezone="America/New_York", quiet_start="22:00", quiet_end="08:00"
    )
    current = instant("2026-03-08T06:30:00+00:00")
    assert quiet(pref, current)
    assert next_allowed(pref, current) == instant("2026-03-08T12:00:00+00:00")
    birthday = normalize(
        {
            "summary": "Birthday",
            "start": {"date": "2026-11-01"},
            "end": {"date": "2026-11-02"},
        },
        "America/New_York",
    )
    assert instant(birthday["ends_at"]) - instant(birthday["starts_at"]) == timedelta(
        hours=25
    )
    item = event(Clock(), title="Interview")
    item["recurringEventId"] = "weekly-series"
    assert normalize(item, "UTC")["status"] == "context_only"
    item["summary"] = "Therapy exam"
    assert normalize(item, "UTC")["private"]


def test_google_wire_contract_uses_pkce_read_only_fields_and_token_body(monkeypatch):
    import httpx

    from echoloom.calendar_auth import SCOPES, GoogleCalendar

    settings = Settings(
        _env_file=None, google_client_id="client", google_client_secret="secret"
    )
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "a",
                    "refresh_token": "r",
                    "expires_in": 3600,
                    "scope": SCOPES,
                },
            )
        if request.url.path == "/revoke":
            return httpx.Response(200)
        if request.url.path.endswith("/events"):
            return httpx.Response(
                200, json={"items": [], "nextSyncToken": "next", "timeZone": "UTC"}
            )
        return httpx.Response(200, json={"email": "owner@example.test"})

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    adapter = GoogleCalendar(settings)
    url = parse_qs(urlparse(adapter.authorization_url("state", "verifier")).query)
    assert url["code_challenge"] == [challenge("verifier")]
    assert url["code_challenge_method"] == ["S256"]
    assert (
        "calendar.events.readonly" in url["scope"][0]
        and "calendar.events " not in url["scope"][0]
    )
    credentials = adapter.exchange("code", "verifier")
    body = parse_qs(calls[-1].content.decode())
    assert body["code_verifier"] == ["verifier"] and body["client_secret"] == ["secret"]
    assert "secret" not in str(calls[-1].url)
    assert adapter.email(credentials) == "owner@example.test"
    adapter.events(credentials, "previous", "start", "end")
    query = calls[-1].url.params
    assert (
        query["syncToken"] == "previous"
        and "timeMin" not in query
        and "timeMax" not in query
    )
    for forbidden in (
        "description",
        "attendees",
        "location",
        "conferenceData",
        "attachments",
    ):
        assert forbidden not in query["fields"]
    adapter.events(credentials, None, "start", "end")
    assert calls[-1].url.params["timeMin"] == "start"
    adapter.refresh(credentials)
    assert parse_qs(calls[-1].content.decode())["grant_type"] == ["refresh_token"]
    adapter.revoke(credentials)
    assert calls[-1].method == "POST" and "token" not in calls[-1].url.params


def test_oauth_expired_cross_account_and_cancelled_states(companion):
    client, _service, _google, clock, _factory, _text = companion
    register(client)
    char = character(client)

    def begin():
        response = client.post(
            "/api/integrations/google-calendar/connect",
            json={
                "character_id": char["id"],
                "conversation_id": char["conversation_id"],
            },
        )
        return parse_qs(urlparse(response.json()["authorization_url"]).query)["state"][
            0
        ]

    state = begin()
    client.post("/api/account/logout")
    register(client, "intruder")
    response = client.get(
        "/api/integrations/google-calendar/callback",
        params={"state": state, "code": "test-code"},
        follow_redirects=False,
    )
    assert "calendar=invalid" in response.headers["location"]
    assert client.get("/api/companion/settings").json()["connected"] is False
    client.post("/api/account/logout")
    client.post(
        "/api/account/login",
        json={"username": "owner", "password": "a-strong-test-password"},
    )
    clock.value += timedelta(minutes=11)
    assert (
        "calendar=invalid"
        in client.get(
            "/api/integrations/google-calendar/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        ).headers["location"]
    )
    state = begin()
    response = client.get(
        "/api/integrations/google-calendar/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert "calendar=cancelled" in response.headers["location"]
    assert client.get("/api/companion/settings").json()["connected"] is False
    assert (
        "calendar=invalid"
        in client.get(
            "/api/integrations/google-calendar/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        ).headers["location"]
    )


def test_failed_generation_bounded_retry_no_false_delivery_and_durable_restart(
    companion,
):
    client, service, google, clock, factory, text = companion
    register(client)
    char = character(client)
    connect(client, char)
    text.fail = True
    for _ in range(3):
        service.tick()
        clock.value += timedelta(minutes=16)
    assert timeline(client, char) == []
    with factory() as db:
        task = db.scalar(select(CompanionTask))
        assert task.status == "failed" and task.attempts == 3
    # A real new app instance against the same file recovers an interrupted task.
    with factory() as db:
        task = db.scalar(select(CompanionTask))
        task.status = "running"
        task.attempts = 1
        task.due_at = clock().isoformat()
        db.commit()
    text.fail = False
    settings = service.settings.model_copy(update={"companion_worker_enabled": True})
    restarted = create_app(
        settings,
        text,
        FakeImages(),
        factory.kw["bind"],
        calendar_provider=google,
        clock=clock,
    )
    import time

    with TestClient(restarted):
        for _ in range(40):
            with factory() as db:
                if db.scalar(select(Message.id)):
                    break
            time.sleep(0.025)
        with factory() as db:
            assert len(list(db.scalars(select(Message)))) == 1
    service.tick()
    assert len(timeline(client, char)) == 1


def test_connected_calendar_cannot_be_read_or_disconnected_by_second_account(companion):
    client, _service, google, clock, factory, _text = companion
    register(client)
    char = character(client)
    google.items = [event(clock)]
    connect(client, char)
    client.post("/api/account/logout")
    register(client, "second-owner")
    assert (
        client.get("/api/integrations/google-calendar/status?user_id=owner").json()[
            "connected"
        ]
        is False
    )
    assert client.get("/api/companion/upcoming").json() == []
    assert client.post("/api/integrations/google-calendar/sync").status_code == 409
    assert (
        client.post(
            "/api/integrations/google-calendar/connect",
            json={
                "character_id": char["id"],
                "conversation_id": char["conversation_id"],
            },
        ).status_code
        == 404
    )
    client.delete("/api/integrations/google-calendar/connection")
    with factory() as db:
        assert db.scalar(select(CalendarConnection)).email == "test@example.test"
        assert len(list(db.scalars(select(CalendarEvent)))) == 1


def test_quiet_event_checkins_expire_instead_of_morning_backlog(companion):
    client, service, google, clock, factory, _text = companion
    clock.value = datetime(2026, 11, 4, 3, 0, tzinfo=UTC)  # 22:00 New York
    register(client)
    char = character(client)
    google.items = [event(clock)]
    connect(client, char)
    service.tick()
    assert len(timeline(client, char)) == 1  # only user-initiated introduction
    clock.value += timedelta(hours=3)
    service.tick()
    clock.value += timedelta(hours=9)
    service.tick()
    assert len(timeline(client, char)) == 1
    with factory() as db:
        tasks = list(
            db.scalars(
                select(CompanionTask).where(CompanionTask.kind != "introduction")
            )
        )
        assert tasks and all(t.status == "expired" for t in tasks)


def test_welcome_immediate_personal_context_and_idempotent_without_worker(companion):
    client, service, google, clock, _factory, text = companion
    register(client)
    char = character(client)
    google.items = [event(clock, offset=6 * 24 * 60, title="Exam")]
    connect(client, char)
    assert timeline(client, char) == []
    response = client.post("/api/companion/welcome", json={})
    assert response.status_code == 200
    messages = timeline(client, char)
    assert len(messages) == 1 and "Exam coming up" in messages[0]["content"]
    import json

    context = text.calls[-1][1]
    frame = json.loads(context[-1]["content"])
    assert frame["upcoming_plan"]["title"] == "Exam"
    assert "ask what subject" in context[0]["content"]
    assert frame["profile"]["name"] == char["profile"]["name"]
    assert client.post("/api/companion/welcome", json={}).status_code == 200
    service.tick()
    assert len(timeline(client, char)) == 1

    # An explicit sync starts a fresh conversation once per synced snapshot.
    assert (
        client.post("/api/companion/welcome", json={"refresh": True}).status_code == 200
    )
    assert len(timeline(client, char)) == 2
    assert json.loads(text.calls[-1][1][-1]["content"])["trigger"] == "calendar_refresh"
    assert (
        client.post("/api/companion/welcome", json={"refresh": True}).status_code == 200
    )
    assert len(timeline(client, char)) == 2

    google.items.append(event(clock, "new-plan", offset=24 * 60, title="Job interview"))
    # Explicit sync must fetch new plans even seconds after the first connection.
    assert client.post("/api/integrations/google-calendar/sync").status_code == 200
    assert len(client.get("/api/companion/upcoming").json()) == 2
    assert (
        client.post("/api/companion/welcome", json={"refresh": True}).status_code == 200
    )
    assert len(timeline(client, char)) == 3


def test_welcome_no_private_or_cancelled_plan_and_no_fake_success(companion):
    client, _service, google, clock, _factory, text = companion
    register(client)
    char = character(client)
    google.items = [event(clock, title="Doctor appointment")]
    connect(client, char)
    text.fail = True
    assert client.post("/api/companion/welcome", json={}).status_code == 503
    assert timeline(client, char) == []
    text.fail = False
    clock.value += timedelta(minutes=6)
    assert client.post("/api/companion/welcome", json={}).status_code == 200
    import json

    assert json.loads(text.calls[-1][1][-1]["content"])["upcoming_plan"] is None
    client.delete("/api/integrations/google-calendar/connection")
    google.items = [event(clock, title="Exam")]
    connect(client, char)
    google.items[0]["status"] = "cancelled"
    assert client.post("/api/companion/welcome", json={}).status_code == 200
    assert json.loads(text.calls[-1][1][-1]["content"])["upcoming_plan"] is None
