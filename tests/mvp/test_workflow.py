from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from echoloom.api import create_app
from echoloom.db import (
    ImageRequest,
    Message,
    Portrait,
    ProfileRevision,
    Proposal,
    make_engine,
    sessions,
)


def send(client, conv, text="Hello", request_id=None):
    return client.post(
        f"/api/conversations/{conv}/messages",
        json={"content": text, "request_id": request_id or str(uuid4())},
    )


def test_create_edit_persist_across_app_restart(setup, character):
    client, text, images, settings, _engine = setup
    c = character
    assert c["profile_version"] == 1
    assert client.get("/api/characters").json()[0]["id"] == c["id"]
    c["profile"]["name"] = "Vera"
    result = client.patch(
        f"/api/characters/{c['id']}",
        json={"profile": c["profile"], "expected_version": 1},
    )
    assert result.status_code == 200
    assert result.json()["profile_version"] == 2
    assert len(text.calls) == 1  # Manual edit makes no paid request.
    restarted_engine = make_engine(settings.database_url)
    with TestClient(create_app(settings, text, images, restarted_engine)) as restarted:
        saved = restarted.get(f"/api/characters/{c['id']}").json()
        assert saved["profile"]["name"] == "Vera"
        assert saved["conversation_id"] == c["conversation_id"]
        assert len(restarted.get(f"/api/characters/{c['id']}/versions").json()) == 2
    restarted_engine.dispose()


def test_invalid_description_and_profile(setup, character):
    client = setup[0]
    for description in ("", "  ", "x" * 5001):
        assert (
            client.post(
                "/api/characters/generate", json={"description": description}
            ).status_code
            == 422
        )
    profile = character["profile"] | {"name": ""}
    assert (
        client.patch(
            f"/api/characters/{character['id']}",
            json={"profile": profile, "expected_version": 1},
        ).status_code
        == 422
    )
    assert client.get("/api/characters/not-a-uuid").status_code == 422
    assert client.get(f"/api/characters/{uuid4()}").status_code == 404


def test_chat_refine_restore_preserves_identity_history_and_portrait(setup, character):
    client, text = setup[:2]
    cid, conv = character["id"], character["conversation_id"]
    base = f"/api/characters/{cid}"
    image = client.post(base + "/images/generate", json={}).json()
    assert client.get(base).json()["current_image_id"] is None
    client.post(base + f"/images/{image['id']}/select")
    assert send(client, conv).status_code == 200
    old_messages = client.get(f"/api/conversations/{conv}/messages").json()
    preview = client.post(
        base + "/refine",
        json={"instruction": "Make her more distant", "expected_version": 1},
    ).json()
    assert preview["changes"][0]["path"] == "personality.core_traits"
    assert client.get(base).json()["profile_version"] == 1
    changed = client.post(
        base + "/refine/confirm", json={"proposal_id": preview["proposal_id"]}
    ).json()
    assert changed["id"] == cid and changed["profile_version"] == 2
    assert changed["profile"]["appearance"] == character["profile"]["appearance"]
    assert changed["profile"]["backstory"] == character["profile"]["backstory"]
    assert changed["current_image_id"] == image["id"]
    # Double confirmation is idempotent.
    assert (
        client.post(
            base + "/refine/confirm", json={"proposal_id": preview["proposal_id"]}
        ).json()["profile_version"]
        == 2
    )
    result = send(client, conv, "What are you thinking about today?").json()
    assert result[:2] == old_messages
    assert result[-1]["profile_version"] == 2
    assert "Distant" in text.calls[-1][1][0]["content"]
    assert len(text.calls[-1][1]) == 4  # system + prior turn + new user
    restored = client.post(
        base + "/restore", json={"version": 1, "expected_version": 2}
    ).json()
    assert restored["profile_version"] == 3
    assert restored["profile"] == character["profile"]
    assert client.get(f"/api/conversations/{conv}/messages").json() == result
    assert restored["current_image_id"] == image["id"]


def test_stale_profile_and_proposal_do_not_overwrite(setup, character):
    client = setup[0]
    base = f"/api/characters/{character['id']}"
    proposal = client.post(
        base + "/refine", json={"instruction": "Distant", "expected_version": 1}
    ).json()
    profile = character["profile"] | {"name": "New name"}
    assert (
        client.patch(base, json={"profile": profile, "expected_version": 1}).status_code
        == 200
    )
    assert (
        client.post(
            base + "/refine/confirm", json={"proposal_id": proposal["proposal_id"]}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            base, json={"profile": character["profile"], "expected_version": 1}
        ).status_code
        == 409
    )
    assert client.get(base).json()["profile"]["name"] == "New name"


def test_failed_chat_retry_and_repeated_request_are_atomic(setup, character):
    client, text = setup[:2]
    conv = character["conversation_id"]
    request_id = str(uuid4())
    text.fail = True
    assert send(client, conv, request_id=request_id).status_code == 502
    assert client.get(f"/api/conversations/{conv}/messages").json() == []
    text.fail = False
    result = send(client, conv, request_id=request_id)
    assert result.status_code == 200 and len(result.json()) == 2
    calls = len(text.calls)
    assert send(client, conv, request_id=request_id).json() == result.json()
    assert len(text.calls) == calls
    assert send(client, conv, "different message", request_id).status_code == 409


def test_concurrent_chat_retry_only_calls_provider_once(setup, character):
    client, text = setup[:2]
    conv = character["conversation_id"]
    request_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: send(client, conv, request_id=request_id), range(2))
        )
    assert all(r.status_code == 200 for r in results)
    assert results[0].json() == results[1].json()
    assert len([c for c in text.calls if c[0] == "chat"]) == 1


def test_image_candidate_edit_restore_ownership_and_cleanup(setup, character):
    client, _, images, settings, engine = setup
    cid = character["id"]
    base = f"/api/characters/{cid}"
    initial = client.post(base + "/images/generate", json={})
    assert initial.status_code == 201, initial.text
    image = initial.json()
    original_bytes = client.get(image["url"]).content
    assert client.get(base).json()["current_image_id"] is None
    client.post(base + f"/images/{image['id']}/select")
    edited = client.post(
        base + "/images/edit",
        json={
            "instruction": "Change the hair to blue",
            "expected_image_id": image["id"],
        },
    ).json()
    assert images.sources[-1] == original_bytes
    assert edited["parent_image_id"] == image["id"]
    assert edited["version"] == 2
    assert client.get(base).json()["current_image_id"] == image["id"]
    assert client.get(image["url"]).content == original_bytes
    client.post(base + f"/images/{edited['id']}/select")
    client.post(base + f"/images/{image['id']}/select")
    other = client.post(
        "/api/characters/generate", json={"description": "other"}
    ).json()
    assert (
        client.post(
            f"/api/characters/{other['id']}/images/{image['id']}/select"
        ).status_code
        == 404
    )
    assert client.delete(base + f"/images/{image['id']}").status_code == 409
    assert client.delete(base + f"/images/{edited['id']}").status_code == 204
    assert client.get(edited["url"]).status_code == 404
    assert client.delete(base).status_code == 204
    assert (
        client.get(
            f"/api/conversations/{character['conversation_id']}/messages"
        ).status_code
        == 404
    )
    assert not list(settings.image_directory.iterdir())
    with sessions(engine)() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ProfileRevision)
                .where(ProfileRevision.character_id == cid)
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(ProfileRevision)
                .where(ProfileRevision.character_id == other["id"])
            )
            == 1
        )
        for model in (Message, Portrait, Proposal, ImageRequest):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_image_failure_does_not_damage_character_or_chat_and_budget_persists(
    setup, character
):
    client, text, images, settings, engine = setup
    base = f"/api/characters/{character['id']}"
    images.fail = True
    for _ in range(settings.image_requests_per_hour):
        assert client.post(base + "/images/generate", json={}).status_code == 502
    assert client.post(base + "/images/generate", json={}).status_code == 429
    assert client.get(base).json()["profile"] == character["profile"]
    assert send(client, character["conversation_id"]).status_code == 200
    with TestClient(create_app(settings, text, images, engine)) as restarted:
        assert restarted.post(base + "/images/generate", json={}).status_code == 429


def test_multiple_conversations_are_separate(setup, character):
    client = setup[0]
    old = character["conversation_id"]
    new = client.post(f"/api/characters/{character['id']}/conversations").json()["id"]
    send(client, old, "Old conversation")
    assert client.get(f"/api/conversations/{new}/messages").json() == []
    send(client, new, "New conversation")
    assert (
        client.get(f"/api/conversations/{old}/messages").json()[0]["content"]
        == "Old conversation"
    )


def test_english_display_preserves_legacy_records_and_portrait(setup, character):
    import copy

    client, text, images, settings, engine = setup
    cid = character["id"]
    base = f"/api/characters/{cid}"
    legacy_name = "\u79e6\u5f7b"
    legacy_summary = "\u521b\u5efa\u89d2\u8272"
    with sessions(engine)() as db:
        stored = db.scalar(
            select(ProfileRevision).where(ProfileRevision.character_id == cid)
        )
        profile = copy.deepcopy(stored.profile_json)
        profile["name"] = legacy_name
        stored.profile_json = profile
        stored.change_summary = legacy_summary
        db.commit()
    portrait = client.post(base + "/images/generate", json={}).json()
    client.post(base + f"/images/{portrait['id']}/select")
    old_turn = send(client, character["conversation_id"], "\u4f60\u597d").json()
    before = client.get(base).json()
    image_bytes = client.get(portrait["url"]).content
    restarted_engine = make_engine(settings.database_url)
    with TestClient(create_app(settings, text, images, restarted_engine)) as restarted:
        assert restarted.get(base).json() == before
        assert restarted.get(base).json()["profile"]["name"] == legacy_name
        assert (
            restarted.get(
                f"/api/conversations/{character['conversation_id']}/messages"
            ).json()
            == old_turn
        )
        assert restarted.get(portrait["url"]).content == image_bytes
        assert (
            restarted.get(base + "/versions").json()[0]["change_summary"]
            == "Create Character"
        )
    with sessions(engine)() as db:
        stored = db.scalar(
            select(ProfileRevision).where(ProfileRevision.character_id == cid)
        )
        assert stored.change_summary == legacy_summary
    restarted_engine.dispose()
