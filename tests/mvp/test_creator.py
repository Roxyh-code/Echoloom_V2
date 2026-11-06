"""Creator graph integrity, ownership, partial creation and recoverable saves."""

import json
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select

from echoloom.db import sessions


def demo(client):
    r = client.post(
        "/api/creator/works",
        json={
            "request_id": str(uuid4()),
            "demo": True,
            "mode": "direct",
            "premise": "Rainy station. A one-way ticket.",
            "title": "The Last Train",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def action(client, w, op, **kwargs):
    r = client.post(
        f"/api/creator/works/{w['id']}/actions",
        json={
            "request_id": str(uuid4()),
            "expected_revision": w["revision"],
            "operation": op,
            **kwargs,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_demo_branch_checkpoint_restore_and_source_facts(setup):
    client, *_ = setup
    w = action(client, demo(client), "continue")
    main = w["document"]["active_line"]
    opening = w["document"]["lines"][main]["head"]
    w = action(client, w, "direct", content="Let Mira deflect")
    w = action(client, w, "checkpoint", name="Before the departure")
    frozen = deepcopy(w["document"]["checkpoints"][0])
    oldhead = w["document"]["lines"][main]["head"]
    w = action(
        client,
        w,
        "fork",
        node_id=opening,
        name="The truth",
        content="Let Mira admit the residency offer",
    )
    other = w["document"]["active_line"]
    assert other != main
    w = action(
        client, w, "fact", content="Leo knows about the residency.", known_by=["leo"]
    )
    assert w["document"]["facts"][0]["line_id"] == other
    w = action(client, w, "switch", target_id=main)
    assert w["document"]["lines"][main]["head"] == oldhead
    assert not any(f["line_id"] == main for f in w["document"]["facts"])
    assert w["document"]["checkpoints"][0] == frozen
    w = action(client, w, "restore", target_id=frozen["id"])
    assert w["document"]["active_line"] not in (main, other)
    assert w["document"]["lines"][w["document"]["active_line"]]["head"] == oldhead
    assert w["document"]["checkpoints"][0] == frozen
    invalid = deepcopy(w["document"])
    invalid["checkpoints"][0]["facts"] = [
        {
            "id": "invalid",
            "line_id": frozen["line"]["id"],
            "text": "Invalid saved source",
            "source": "missing-moment",
            "known_by": [],
        }
    ]
    assert (
        client.post(
            "/api/creator/import",
            json={
                "request_id": str(uuid4()),
                "document": invalid,
            },
        ).status_code
        == 422
    )


def test_historical_edit_keeps_original_and_frozen_save(setup):
    client, *_ = setup
    w = action(client, demo(client), "continue")
    main = w["document"]["active_line"]
    first = w["document"]["lines"][main]["head"]
    w = action(client, w, "checkpoint", name="Opening")
    w = action(client, w, "continue")
    head = w["document"]["lines"][main]["head"]
    w = action(
        client,
        w,
        "edit",
        node_id=first,
        blocks=[
            {
                "type": "dialogue",
                "speaker": "leo",
                "text": "Please tell me before you leave.",
            }
        ],
    )
    assert w["document"]["active_line"] != main
    assert w["document"]["lines"][main]["head"] == head
    assert w["document"]["checkpoints"][0]["line"]["head"] == first
    assert w["document"]["nodes"][first]["blocks"][0]["type"] == "narration"


def test_requests_dedupe_conflicts_and_failure_keep_draft(setup):
    client, *_ = setup
    w = demo(client)
    body = {
        "request_id": str(uuid4()),
        "expected_revision": w["revision"],
        "operation": "continue",
    }
    url = f"/api/creator/works/{w['id']}/actions"
    a = client.post(url, json=body)
    b = client.post(url, json=body)
    assert a.status_code == b.status_code == 200
    assert len(b.json()["document"]["nodes"]) == 1
    assert client.post(url, json={**body, "operation": "checkpoint"}).status_code == 409
    old = a.json()
    bad = client.post(
        url,
        json={
            "request_id": str(uuid4()),
            "expected_revision": old["revision"],
            "operation": "direct",
            "content": "Perform an unsupported magical cartwheel.",
        },
    )
    assert bad.status_code == 503
    current = client.get(f"/api/creator/works/{w['id']}").json()
    assert current == old
    stale = client.post(url, json={**body, "request_id": str(uuid4())})
    assert stale.status_code == 409


def test_export_import_paths_and_invalid_cycles(setup):
    client, *_ = setup
    w = action(client, demo(client), "continue")
    main = w["document"]["active_line"]
    w = action(
        client,
        w,
        "fork",
        content="Let Mira admit the residency offer",
        name="The truth",
    )
    script = client.get(
        f"/api/creator/works/{w['id']}/export?format=script&line_id={main}"
    ).text
    assert (
        "A one-way ticket?" in script
        and "I was offered a restoration residency" not in script
    )
    backup = client.get(f"/api/creator/works/{w['id']}/export?format=json").json()
    imported = client.post(
        "/api/creator/import", json={"request_id": str(uuid4()), "document": backup}
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] != w["id"]
    assert set(imported.json()["document"]["nodes"]).isdisjoint(backup["nodes"])
    corrupt = deepcopy(backup)
    node = next(iter(corrupt["nodes"]))
    corrupt["nodes"][node]["parent"] = node
    assert (
        client.post(
            "/api/creator/import",
            json={"request_id": str(uuid4()), "document": corrupt},
        ).status_code
        == 422
    )
    assert client.get("/api/creator/works").status_code == 200


def test_new_scene_and_manual_opening(setup):
    client, *_ = setup
    w = demo(client)
    w = action(
        client,
        w,
        "edit",
        blocks=[
            {"type": "narration", "speaker": None, "text": "The empty platform waits."}
        ],
    )
    w = action(
        client, w, "scene", name="On the train", content="Next scene, on the train."
    )
    d = w["document"]
    head = d["nodes"][d["lines"][d["active_line"]]["head"]]
    assert d["scenes"][head["scene_id"]]["title"] == "On the train"
    assert len(d["scenes"]) == 2


def test_partial_character_generation_and_image_only_retry(setup):
    client, text, images, _settings, _engine = setup
    images.fail = True
    body = {
        "request_id": str(uuid4()),
        "description": "A quiet silver-haired librarian with dry humor.",
    }
    result = client.post("/api/creator/characters", json=body)
    assert result.status_code == 201, result.text
    assert result.json()["phase"] == "portrait_failed"
    cid = result.json()["character_id"]
    assert client.get(f"/api/characters/{cid}").status_code == 200
    assert client.post("/api/creator/characters", json=body).json() == result.json()
    assert sum(k == "generate" for k, _ in text.calls) == 1
    images.fail = False
    image = client.post(
        f"/api/creator/characters/{cid}/portrait",
        json={"request_id": str(uuid4()), "editing": False, "expected_image_id": None},
    )
    assert image.status_code == 200, image.text
    assert sum(k == "generate" for k, _ in text.calls) == 1


def test_one_step_character_selects_initial_portrait_and_idempotent(setup):
    client, _text, images, *_ = setup
    body = {
        "request_id": str(uuid4()),
        "description": "A librarian with silver hair and a warm, dry voice.",
    }
    r = client.post("/api/creator/characters", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["phase"] == "ready"
    c = client.get("/api/characters/" + r.json()["character_id"]).json()
    assert c["current_image_id"]
    again = client.post("/api/creator/characters", json=body)
    assert again.json() == r.json() and len(images.sources) == 1


def test_live_context_is_scoped_snapshot_and_assets_pinned(setup):
    client, text, _images, *_ = setup
    c = client.post(
        "/api/creator/characters",
        json={
            "request_id": str(uuid4()),
            "description": "An observant librarian who values honesty.",
        },
    ).json()
    cid = c["character_id"]
    profile = client.get(f"/api/characters/{cid}").json()
    w = client.post(
        "/api/creator/works",
        json={
            "request_id": str(uuid4()),
            "character_ids": [cid],
            "mode": "play",
            "player_name": "Alex",
            "premise": "Rainy platform.",
        },
    ).json()
    w = action(client, w, "continue")
    ctx = next(v for k, v in reversed(text.calls) if k == "creator")
    assert json.loads(ctx[-1]["content"])["cast"][0]["profile"]["name"] == "Evelyn"
    assert client.delete(f"/api/characters/{cid}").status_code == 409
    assert client.patch(f"/api/creator/characters/{cid}/archive").json()["archived"]
    assert client.get("/api/creator/characters").json() == []
    assert client.get(f"/api/creator/works/{w['id']}").status_code == 200
    assert (
        w["document"]["casts"][next(iter(w["document"]["casts"]))][0]["portrait_id"]
        == profile["current_image_id"]
    )


def test_unknown_speaker_rejected_and_notes_need_review(setup):
    client, *_ = setup
    w = action(client, demo(client), "continue")
    w = action(
        client, w, "fact", content="They meet at the station.", known_by=["mira", "leo"]
    )
    old = w["document"]["lines"][w["document"]["active_line"]]["head"]
    w = action(
        client,
        w,
        "edit",
        node_id=old,
        blocks=[
            {"type": "narration", "speaker": None, "text": "They meet at the café."}
        ],
    )
    assert w["document"]["facts"][0]["status"] == "needs_review"
    url = f"/api/creator/works/{w['id']}/actions"
    r = client.post(
        url,
        json={
            "request_id": str(uuid4()),
            "expected_revision": w["revision"],
            "operation": "edit",
            "blocks": [{"type": "dialogue", "speaker": "intruder", "text": "Hello."}],
        },
    )
    assert r.status_code == 502
    assert client.get(f"/api/creator/works/{w['id']}").json() == w


def test_two_accounts_cannot_access_creator_records_or_assets(setup):
    client, *_ = setup
    w = action(client, demo(client), "continue")
    client.post(
        "/api/account/register",
        json={"username": "owner", "password": "strong-password-123"},
    )
    assert client.get(f"/api/creator/works/{w['id']}").status_code == 200
    client.post("/api/account/logout")
    assert client.get("/api/creator/works").status_code == 401
    # Additional local accounts are only enabled in this isolated test.
    setup[3].allow_additional_accounts = True
    client.post(
        "/api/account/register",
        json={"username": "second", "password": "strong-password-123"},
    )
    assert client.get("/api/creator/works").json() == []
    for suffix in ("", "/export"):
        assert client.get(f"/api/creator/works/{w['id']}{suffix}").status_code == 404
    assert client.delete(f"/api/creator/works/{w['id']}").status_code == 404


def test_completed_path_is_immutable_and_restore_forks(setup):
    client, *_ = setup
    w = action(client, demo(client), "continue")
    main = w["document"]["active_line"]
    w = action(client, w, "finish")
    frozen = deepcopy(w["document"]["checkpoints"][0])
    assert w["document"]["finished"] and w["document"]["lines"][main]["finished"]
    w = action(
        client,
        w,
        "fork",
        name="Another ending",
        content="Let Mira admit the residency offer",
    )
    assert not w["document"]["finished"]
    w = action(client, w, "switch", target_id=main)
    assert w["document"]["finished"]
    bad = client.post(
        f"/api/creator/works/{w['id']}/actions",
        json={
            "request_id": str(uuid4()),
            "expected_revision": w["revision"],
            "operation": "continue",
        },
    )
    assert bad.status_code == 409
    w = action(client, w, "restore", target_id=frozen["id"])
    assert not w["document"]["finished"] and w["document"]["checkpoints"][0] == frozen


def test_player_dialogue_is_verbatim_and_model_cannot_write_player(setup):
    from echoloom.creator_schemas import CreatorOutput

    client, text, *_ = setup
    c = client.post(
        "/api/creator/characters",
        json={
            "request_id": str(uuid4()),
            "description": "A quiet librarian with silver hair.",
        },
    ).json()
    w = client.post(
        "/api/creator/works",
        json={
            "request_id": str(uuid4()),
            "character_ids": [c["character_id"]],
            "mode": "play",
            "premise": "At a rainy bookshop.",
            "player_name": "Alex",
        },
    ).json()
    w = action(client, w, "continue")
    w = action(
        client,
        w,
        "direct",
        content="I came back to hear your side.",
        input_type="dialogue",
    )
    node = w["document"]["nodes"][
        w["document"]["lines"][w["document"]["active_line"]]["head"]
    ]
    assert node["blocks"][0] == {
        "type": "dialogue",
        "speaker": "player",
        "text": "I came back to hear your side.",
        "source": "author",
    }
    text.creator = lambda _: CreatorOutput(
        blocks=[
            {
                "type": "dialogue",
                "speaker": "player",
                "text": "I promise to stay forever.",
            }
        ]
    )
    bad = client.post(
        f"/api/creator/works/{w['id']}/actions",
        json={
            "request_id": str(uuid4()),
            "expected_revision": w["revision"],
            "operation": "continue",
        },
    )
    assert bad.status_code == 502
    assert client.get(f"/api/creator/works/{w['id']}").json() == w


def test_duplicate_character_and_snapshot_refresh_keep_old_saved_setup(setup):
    client, *_ = setup
    c = client.post(
        "/api/creator/characters",
        json={
            "request_id": str(uuid4()),
            "description": "A determined librarian who loves the night sky.",
        },
    ).json()
    original = client.get("/api/characters/" + c["character_id"]).json()
    copied = client.post(
        f"/api/creator/characters/{original['id']}/duplicate",
        json={"request_id": str(uuid4())},
    )
    assert copied.status_code == 201, copied.text
    assert (
        copied.json()["id"] != original["id"]
        and copied.json()["current_image_id"] != original["current_image_id"]
    )
    w = client.post(
        "/api/creator/works",
        json={
            "request_id": str(uuid4()),
            "character_ids": [original["id"]],
            "mode": "play",
            "premise": "A bookshop in the rain.",
        },
    ).json()
    w = action(client, w, "continue")
    w = action(client, w, "checkpoint", name="Original character")
    cast_id = w["document"]["lines"][w["document"]["active_line"]]["cast_id"]
    old = deepcopy(w["document"]["casts"][cast_id])
    p = original["profile"]
    p["name"] = "Vera"
    assert (
        client.patch(
            "/api/characters/" + original["id"],
            json={"profile": p, "expected_version": 1},
        ).status_code
        == 200
    )
    w = action(client, w, "update_cast", name="A different voice")
    assert w["document"]["casts"][cast_id] == old
    current = w["document"]["casts"][
        w["document"]["lines"][w["document"]["active_line"]]["cast_id"]
    ]
    assert current[0]["profile"]["name"] == "Vera"
    checkpoint = w["document"]["checkpoints"][0]
    assert checkpoint["line"]["cast_id"] == cast_id


def test_world_rule_changes_and_new_scenes_reach_live_context(setup):
    client, text, *_ = setup
    c = client.post(
        "/api/creator/characters",
        json={
            "request_id": str(uuid4()),
            "description": "A quiet librarian with a strong sense of responsibility.",
        },
    ).json()
    w = client.post(
        "/api/creator/works",
        json={
            "request_id": str(uuid4()),
            "character_ids": [c["character_id"]],
            "mode": "play",
            "premise": "A rainy shop.",
            "location": "Bookshop",
            "time": "Evening",
            "world_rules": "The shop closes at ten.",
        },
    ).json()
    main = w["document"]["active_line"]
    w = action(client, w, "continue")
    w = action(
        client,
        w,
        "setup",
        content="The shop stays open all night.",
        name="A longer evening",
    )
    assert w["document"]["lines"][main]["world_rules"] == "The shop closes at ten."
    w = action(
        client, w, "scene", content="Next morning on the train.", name="The train"
    )
    frame = json.loads(
        next(v for k, v in reversed(text.calls) if k == "creator")[-1]["content"]
    )
    assert frame["scene"]["title"] == "The train"
    assert frame["world_rules"] == "The shop stays open all night."


def test_deleted_story_removes_private_request_payloads(setup):
    client, *rest = setup
    engine = rest[-1]
    w = action(client, demo(client), "continue")
    w = action(client, w, "direct", content="Let Mira admit the residency offer")
    assert client.delete(f"/api/creator/works/{w['id']}").status_code == 204
    from echoloom.db import CreatorRequest

    with sessions(engine)() as db:
        rows = list(db.scalars(select(CreatorRequest)))
        assert rows and all(r.status == "deleted" and r.payload == {} for r in rows)
    assert client.get(f"/api/creator/works/{w['id']}").status_code == 404


def test_migration_0004_preserves_populated_legacy_database(tmp_path, monkeypatch):
    import sqlite3

    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext

    from alembic import command
    from echoloom.db import Base, make_engine

    location = tmp_path / "upgrade.db"
    url = f"sqlite:///{location}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0003")
    with sqlite3.connect(location) as db:
        db.execute(
            "INSERT INTO characters (id, original_description, current_profile_version, created_at, updated_at) VALUES ('original', 'An existing character', 1, 'now', 'now')"
        )
        db.execute(
            "INSERT INTO character_profiles (id, character_id, version, profile_json, change_summary, created_at) VALUES ('profile', 'original', 1, '{\"name\":\"Original\"}', 'Created', 'now')"
        )
        db.execute(
            "INSERT INTO conversations (id, character_id, created_at, updated_at) VALUES ('conversation', 'original', 'now', 'now')"
        )
        db.execute(
            "INSERT INTO messages (id, conversation_id, request_id, role, content, profile_version, created_at) VALUES ('message', 'conversation', 'request', 'assistant', 'Keep this conversation.', 1, 'now')"
        )
        names = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('sqlite_sequence', 'alembic_version')"
            )
        ]
        columns = {
            n: [r[1] for r in db.execute(f'PRAGMA table_info("{n}")')] for n in names
        }

        def legacy_rows():
            return {
                n: db.execute(
                    "SELECT "
                    + ",".join('"' + c + '"' for c in columns[n])
                    + f' FROM "{n}"'
                ).fetchall()
                for n in names
            }

        before = legacy_rows()
        db.commit()
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        assert legacy_rows() == before
        assert db.execute("SELECT archived FROM characters").fetchone() == (0,)
    engine = make_engine(url)
    with engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
    engine.dispose()
    command.downgrade(config, "0003")
    with sqlite3.connect(location) as db:
        assert db.execute("SELECT content FROM messages").fetchone() == (
            "Keep this conversation.",
        )
    command.upgrade(config, "head")
