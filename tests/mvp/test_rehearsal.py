"""Real persistence/jobs with isolated providers. Semantic model quality is evaluated separately."""

import json
import time
from copy import deepcopy
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import select

from echoloom.db import RehearsalOperation, sessions
from echoloom.rehearsal_domain import history


def create(client, demo=True, **fields):
    r = client.post(
        "/api/rehearsal/scenes",
        json={
            "operation_id": str(uuid4()),
            "demo": demo,
            "setup": {
                "premise": "Two old friends meet at the station.",
                "language": "en",
            },
            **fields,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def command(client, s, kind, **fields):
    r = client.post(
        f"/api/rehearsal/scenes/{s['id']}/commands",
        json={
            "operation_id": str(uuid4()),
            "expected_revision": s["revision"],
            "kind": kind,
            **fields,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def wait(client, result):
    jid = result["job_id"]
    for _ in range(250):
        r = client.get("/api/rehearsal/jobs/" + jid)
        assert r.status_code == 200, r.text
        j = r.json()
        if j["status"] not in ("queued", "running", "stopping"):
            return j
        time.sleep(0.01)
    pytest.fail("Generation did not finish")


def completed(client, s, kind="continue", **fields):
    j = wait(client, command(client, s, kind, **fields))
    assert j["status"] == "completed", j
    return j["scene"]


def texts(s, vid=None):
    d = s["document"]
    v = d["versions"][vid or d["active_version"]]
    return "\n".join(b["text"] for n in history(d, v["head"]) for b in n["blocks"])


def quick(client, name):
    body = {
        "operation_id": str(uuid4()),
        "name": name,
        "description": name + " is an observant actor with an unfinished story.",
    }
    r = client.post("/api/rehearsal/characters", json=body)
    assert r.status_code == 201, r.text
    assert client.post("/api/rehearsal/characters", json=body).json() == r.json()
    return r.json()["character_id"]


def test_cast_draft_quick_creation_and_shortest_live_start(setup):
    c, text, *_ = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = create(c, False, character_ids=[], setup={})
    s = command(c, s, "cast", character_ids=[None, b])
    assert s["document"]["cast"][0]["slot"] == 1
    s = command(c, s, "cast", character_ids=[a, b])
    s = command(
        c, s, "setup", setup={"premise": "Two old friends meet in a quiet station."}
    )
    s = completed(c, s)
    assert "moment to talk" in texts(s)
    assert s["document"]["status"] == "rehearsing"
    assert len(c.get("/api/rehearsal/characters").json()) == 2
    assert all(
        not item["current_image_id"]
        for item in c.get("/api/rehearsal/characters").json()
    )
    frame = json.loads(
        next(ctx for kind, ctx in reversed(text.calls) if kind == "rehearsal")[-1][
            "content"
        ]
    )
    assert "private_chat" not in json.dumps(frame)
    assert c.delete("/api/characters/" + a).status_code == 204
    assert (
        c.get("/api/rehearsal/scenes/" + s["id"]).json()["document"]["cast"][0]["name"]
        == "Lin"
    )
    completed(c, s)


def test_idempotent_generation_progress_and_stale_revisions(setup):
    c, *_ = setup
    s = create(c)
    body = {
        "operation_id": str(uuid4()),
        "expected_revision": s["revision"],
        "kind": "continue",
    }
    url = f"/api/rehearsal/scenes/{s['id']}/commands"
    first = c.post(url, json=body).json()
    j = wait(c, first)
    replay = c.post(url, json=body).json()
    assert replay["job_id"] == first["job_id"]
    assert len(replay["document"]["nodes"]) == 1
    assert c.post(url, json={**body, "text": "changed"}).status_code == 409
    assert c.post(url, json={**body, "operation_id": str(uuid4())}).status_code == 409
    events = c.get("/api/rehearsal/jobs/" + first["job_id"] + "?after=1").json()[
        "events"
    ]
    assert all(e["sequence"] > 1 and e["job_id"] == first["job_id"] for e in events)
    s = command(c, j["scene"], "progress", position=344)
    assert s["document"]["versions"][s["document"]["active_version"]]["position"] == 344


def test_branch_state_isolation_saved_result_and_next_scene_dependency(setup):
    c, *_ = setup
    s = completed(c, create(c))
    main = s["document"]["active_version"]
    old = deepcopy(s["document"])
    s = completed(c, s, "branch", text="Let Xu confess the betrayal.")
    other = s["document"]["active_version"]
    assert "I told them" in texts(s)
    head = s["document"]["versions"][other]["head"]
    assert s["document"]["nodes"][head]["state"]["world_facts"]
    s = command(c, s, "result")
    stamp = s["document"]["result"]["stamp"]
    child = create(
        c,
        False,
        source_scene_id=s["id"],
        setup={"premise": "They walk out into the rain."},
    )
    assert child["document"]["initial_state"]["world_facts"]
    assert child["document"]["source"]["version_id"] == other
    original_knowledge = deepcopy(child["document"]["initial_state"]["knowledge"])
    child = command(
        c, child, "setup", setup={"premise": "They walk out into the rain."}
    )
    assert child["document"]["initial_state"]["knowledge"] == original_knowledge
    s = command(c, s, "switch", version_id=main)
    assert texts(s) == texts({"document": old})
    assert not s["document"]["nodes"][s["document"]["versions"][main]["head"]]["state"][
        "world_facts"
    ]
    s = command(c, s, "result")
    assert s["document"]["result"]["stamp"] != stamp
    check = c.get("/api/rehearsal/scenes/" + child["id"]).json()
    assert check["source_updated"]
    assert check["document"]["source"]["head"] == head
    r = c.delete("/api/rehearsal/scenes/" + s["id"])
    assert (
        r.status_code == 409
        and r.json()["detail"]["dependencies"][0]["id"] == child["id"]
    )
    assert c.delete("/api/rehearsal/scenes/" + child["id"]).status_code == 204
    assert c.delete("/api/rehearsal/scenes/" + s["id"]).status_code == 204


def test_takeover_locked_input_failure_retry_and_hand_back(setup):
    c, text, *_ = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = create(c, False, character_ids=[a, b])
    s = completed(c, s)
    s = command(c, s, "takeover", target_id=a)
    text.fail = True
    j = wait(c, command(c, s, "speak", text="Some things, you do remember."))
    assert j["status"] == "failed"
    s = j["scene"]
    assert texts(s).count("Some things, you do remember.") == 1
    text.fail = False
    r = c.post("/api/rehearsal/jobs/" + j["id"] + "/retry", json={}).json()
    j = wait(c, r)
    assert j["status"] == "completed"
    s = j["scene"]
    assert texts(s).count("Some things, you do remember.") == 1
    last = s["document"]["nodes"][
        s["document"]["versions"][s["document"]["active_version"]]["head"]
    ]
    assert not any(x["character_id"] == a for x in last["blocks"])
    old = len(s["document"]["nodes"])
    s = command(c, s, "release")
    assert len(s["document"]["nodes"]) == old
    assert not s["document"]["versions"][s["document"]["active_version"]]["takeover"]


def test_pause_ignores_late_provider_response_and_switch_keeps_target(setup):
    c, text, *_ = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = create(c, False, character_ids=[a, b])
    s = completed(c, s)
    ready, release = Event(), Event()
    original = text.rehearsal

    def delayed(ctx):
        ready.set()
        assert release.wait(5)
        return original(ctx)

    text.rehearsal = delayed
    r = command(c, s, "continue")
    assert ready.wait(3)
    assert (
        c.post("/api/rehearsal/jobs/" + r["job_id"] + "/pause", json={}).json()[
            "status"
        ]
        == "cancelled"
    )
    assert (
        c.post("/api/rehearsal/jobs/" + r["job_id"] + "/pause", json={}).json()[
            "status"
        ]
        == "cancelled"
    )
    release.set()
    j = wait(c, r)
    assert j["status"] == "cancelled"
    assert texts(j["scene"]) == texts(s)


def test_wording_edit_keeps_following_text_plot_edit_forks_and_locks(setup):
    c, *_ = setup
    s = completed(c, create(c))
    s = completed(c, s, "branch", text="Let Xu confess.")
    original = s["document"]["active_version"]
    before = texts(s)
    nodes = history(s["document"], s["document"]["versions"][original]["head"])
    n = nodes[0]
    b = n["blocks"][0]
    s = command(
        c,
        s,
        "edit",
        node_id=n["id"],
        block_id=b["id"],
        text="Rain gilds the platform.",
        edit_type="wording",
    )
    assert "I told them" in texts(s)
    assert texts(s, original) == before
    assert any(
        x.get("state_review")
        for x in history(
            s["document"],
            s["document"]["versions"][s["document"]["active_version"]]["head"],
        )
    )
    current_nodes = history(
        s["document"],
        s["document"]["versions"][s["document"]["active_version"]]["head"],
    )
    n = current_nodes[0]
    b = n["blocks"][0]
    s = completed(
        c,
        s,
        "edit",
        node_id=n["id"],
        block_id=b["id"],
        text="Lin notices the clock.",
        edit_type="plot",
    )
    assert texts(s).startswith("Lin notices the clock.")
    assert texts(s, original) == before
    assert any(
        b["locked"] and b["text"] == "Lin notices the clock."
        for n in history(
            s["document"],
            s["document"]["versions"][s["document"]["active_version"]]["head"],
        )
        for b in n["blocks"]
    )


def test_directions_do_not_perform_until_chosen_export_excludes_notes(setup):
    c, *_ = setup
    s = completed(c, create(c))
    before = deepcopy(s)
    body = {"operation_id": str(uuid4()), "version_id": s["document"]["active_version"]}
    r = c.post("/api/rehearsal/scenes/" + s["id"] + "/directions", json=body)
    assert r.status_code == 200 and len(r.json()["options"]) == 2
    assert (
        c.post("/api/rehearsal/scenes/" + s["id"] + "/directions", json=body).json()
        == r.json()
    )
    assert (
        c.get("/api/rehearsal/scenes/" + s["id"]).json()["document"]
        == before["document"]
    )
    for fmt in ("md", "txt"):
        out = c.get("/api/rehearsal/scenes/" + s["id"] + "/export?format=" + fmt)
        assert out.status_code == 200
        assert (
            "Xu" in out.text
            and "private" not in out.text
            and "knowledge" not in out.text
        )
        assert "filename*=" in out.headers["content-disposition"]


def test_ownership_bootstrap_and_deleted_payloads(setup):
    c, *_ = setup
    s = completed(c, create(c))
    jid = next(n["operation_id"] for n in s["document"]["nodes"].values())
    c.post(
        "/api/account/register",
        json={"username": "owner", "password": "strong-password-123"},
    )
    assert c.get("/api/rehearsal/scenes/" + s["id"]).status_code == 200
    c.post("/api/account/logout")
    assert c.get("/api/rehearsal/scenes/" + s["id"]).status_code == 401
    setup[3].allow_additional_accounts = True
    c.post(
        "/api/account/register",
        json={"username": "second", "password": "strong-password-123"},
    )
    assert c.get("/api/rehearsal/scenes").json() == []
    assert c.get("/api/rehearsal/scenes/" + s["id"]).status_code == 404
    assert c.get("/api/rehearsal/jobs/" + jid).status_code == 404
    assert c.post("/api/rehearsal/jobs/" + jid + "/pause", json={}).status_code == 404
    assert c.get("/api/rehearsal/scenes/" + s["id"] + "/export").status_code == 404


def test_restart_marks_unfinished_jobs_failed_without_regeneration(setup):
    c, _text, _, _, engine = setup
    s = completed(c, create(c))
    factory = sessions(engine)
    with factory() as db:
        job = RehearsalOperation(
            id=str(uuid4()),
            scene_id=s["id"],
            owner_id=None,
            kind="continue",
            payload={},
            status="running",
            result={
                "version_id": s["document"]["active_version"],
                "events": [],
                "generation": {"kind": "continue"},
            },
        )
        db.add(job)
        db.commit()
        jid = job.id
    r = c.get("/api/rehearsal/jobs/" + jid).json()
    assert r["status"] == "failed"
    assert "restarted" in r["events"][-1]["error"]
    assert texts(r["scene"]) == texts(s)


def test_invalid_actor_and_rules_conflict_never_commit_model_blocks(setup):
    from echoloom.rehearsal_schema import Performance

    c, text, *_ = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = create(c, False, character_ids=[a, b])
    s = completed(c, s)
    text.rehearsal = lambda ctx: Performance(
        blocks=[
            {"type": "dialogue", "character_id": "stranger", "text": "Wrong actor."}
        ]
    )
    j = wait(c, command(c, s, "continue"))
    assert j["status"] == "failed" and texts(j["scene"]) == texts(s)
    s = j["scene"]
    text.rehearsal = lambda ctx: Performance(
        conflicts=["The author locked the door; the request opens it without a cause."]
    )
    j = wait(c, command(c, s, "direction", text="Open the locked door immediately."))
    assert j["status"] == "failed" and "locked rule" in j["events"][-1]["error"]
    assert texts(j["scene"]) == texts(s)


def test_event_is_locked_once_and_metrics_do_not_contain_text(setup):
    c, *_ = setup
    s = completed(c, create(c))
    text = "The departure announcement interrupts them."
    result = command(c, s, "event", text=text)
    s = wait(c, result)["scene"]
    assert texts(s).count(text) == 1
    node = s["document"]["nodes"][
        s["document"]["versions"][s["document"]["active_version"]]["head"]
    ]
    assert (
        node["blocks"][0]["locked"] and node["state"]["world_facts"][-1]["text"] == text
    )
    c.get("/api/rehearsal/scenes/" + s["id"] + "/export")
    c.get("/api/rehearsal/scenes/" + s["id"] + "/export")
    metrics = c.get("/api/rehearsal/metrics").json()
    assert metrics["events"]["export_completed"] == 1
    assert text not in json.dumps(metrics)


def test_changed_knowledge_and_persistent_direction_are_branch_local(setup):
    c, text, *_ = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = create(
        c,
        False,
        character_ids=[a, b],
        setup={
            "premise": "Two friends meet at the station.",
            "knowledge_a": "Lin knows the secret.",
            "knowledge_b": "Xu thinks Lin does not know.",
        },
    )
    s = completed(c, s)
    old = s["document"]["active_version"]
    changed = deepcopy(s["document"]["setup"])
    changed["knowledge_b"] = "Xu now knows Lin discovered the truth."
    s = command(c, s, "setup", setup=changed)
    s = completed(c, s, "direction", text="Let them speak quietly.", persistent=True)
    v = s["document"]["versions"][s["document"]["active_version"]]
    assert v["instructions"][0]["active"]
    frame = json.loads(
        next(ctx for kind, ctx in reversed(text.calls) if kind == "rehearsal")[-1][
            "content"
        ]
    )
    assert frame["state"]["knowledge"][b] == "Xu now knows Lin discovered the truth."
    s = command(c, s, "stop_instruction", target_id=v["instructions"][0]["id"])
    assert not s["document"]["versions"][s["document"]["active_version"]][
        "instructions"
    ][0]["active"]
    s = command(c, s, "switch", version_id=old)
    assert not s["document"]["versions"][old]["instructions"]
    s = completed(c, s)
    frame = json.loads(
        next(ctx for kind, ctx in reversed(text.calls) if kind == "rehearsal")[-1][
            "content"
        ]
    )
    assert frame["state"]["knowledge"][b] == "Xu thinks Lin does not know."


def test_switch_during_generation_does_not_redirect_completed_blocks(setup):
    c, text, *_ = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = completed(c, create(c, False, character_ids=[a, b]))
    original = s["document"]["active_version"]
    original_head = s["document"]["versions"][original]["head"]
    entered, release = Event(), Event()
    provider = text.rehearsal

    def delayed(ctx):
        entered.set()
        assert release.wait(5)
        return provider(ctx)

    text.rehearsal = delayed
    result = command(c, s, "branch", text="Tell the truth.")
    assert entered.wait(3)
    target = result["document"]["active_version"]
    command(c, result, "switch", version_id=original)
    release.set()
    j = wait(c, result)
    assert j["status"] == "completed"
    s = j["scene"]
    assert s["document"]["active_version"] == original
    assert s["document"]["versions"][original]["head"] == original_head
    assert s["document"]["versions"][target]["head"] != original_head


def test_retry_and_delete_scrub_content_without_resurrecting_a_scene(setup):
    c, text, _, _, engine = setup
    a, b = quick(c, "Lin"), quick(c, "Xu")
    s = completed(c, create(c, False, character_ids=[a, b]))
    s = command(c, s, "takeover", target_id=a)
    text.fail = True
    failed = wait(c, command(c, s, "speak", text="Keep this private line."))
    text.fail = False
    retry = c.post("/api/rehearsal/jobs/" + failed["id"] + "/retry", json={}).json()
    done = wait(c, retry)
    assert done["status"] == "completed"
    assert (
        c.post("/api/rehearsal/jobs/" + failed["id"] + "/retry", json={}).json()[
            "job_id"
        ]
        == retry["job_id"]
    )
    assert texts(done["scene"]).count("Keep this private line.") == 1
    assert c.delete("/api/rehearsal/scenes/" + s["id"]).status_code == 204
    with sessions(engine)() as db:
        for op in db.scalars(
            select(RehearsalOperation).where(RehearsalOperation.scene_id == s["id"])
        ):
            assert op.payload == {} and op.status == "deleted"
    assert c.get("/api/rehearsal/scenes/" + s["id"]).status_code == 404
