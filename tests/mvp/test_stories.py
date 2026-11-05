import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from echoloom.api import create_app
from echoloom.config import Settings
from echoloom.db import ChatEvent, Message, Story, StoryRequest, StorySegment, sessions
from echoloom.providers import OpenAIText, ProviderError
from echoloom.story_context import story_context, validate_story_output


def invite(client, c, **kwargs):
    return client.post(
        f"/api/characters/{c['id']}/stories",
        json={
            "conversation_id": c["conversation_id"],
            "request_id": str(uuid4()),
            "description": "We are old friends reuniting in a bookshop on a rainy evening.",
            **kwargs,
        },
    )


def act(client, story, operation, **kwargs):
    return client.post(
        f"/api/stories/{story['id']}/actions",
        json={
            "request_id": str(uuid4()),
            "expected_revision": story["revision"],
            "operation": operation,
            **kwargs,
        },
    )


@pytest.fixture
def story(setup, character):
    response = invite(setup[0], character)
    assert response.status_code == 201, response.text
    return response.json()["story"]


def test_invitation_snapshot_idempotency_timeline_and_chat_isolation(setup, character):
    client, text = setup[:2]
    conv = character["conversation_id"]
    message = {"request_id": str(uuid4()), "content": "ordinary chat only"}
    assert (
        client.post(f"/api/conversations/{conv}/messages", json=message).status_code
        == 200
    )
    rid = str(uuid4())
    result = invite(client, character, request_id=rid)
    assert result.status_code == 201, result.text
    story = result.json()["story"]
    assert story["status"] == "ready" and story["segments"] == []
    assert not [c for c in text.calls if c[0] == "story"]
    assert invite(client, character, request_id=rid).json() == result.json()
    assert (
        invite(client, character, request_id=rid, description="different").status_code
        == 409
    )
    profile = character["profile"] | {"name": "Changed later"}
    client.patch(
        f"/api/characters/{character['id']}",
        json={"profile": profile, "expected_version": 1},
    )
    assert (
        client.get(f"/api/stories/{story['id']}").json()["character_snapshot"]
        == character["profile"]
    )
    client.post(
        f"/api/conversations/{conv}/messages",
        json={"request_id": str(uuid4()), "content": "still ordinary"},
    )
    timeline = client.get(f"/api/conversations/{conv}/timeline").json()
    assert [item["kind"] for item in timeline] == [
        "text",
        "text",
        "story_card",
        "text",
        "text",
    ]
    assert [item["timeline_order"] for item in timeline] == [1, 2, 3, 4, 5]
    assert "rainy" not in json.dumps(text.calls[-1])
    act(client, story, "start")
    frame = json.loads([c for c in text.calls if c[0] == "story"][-1][1][-1]["content"])
    assert "ordinary chat only" not in json.dumps(frame)
    assert frame["profile"]["name"] == character["profile"]["name"]
    other = client.post(f"/api/characters/{character['id']}/conversations").json()["id"]
    assert client.get(f"/api/conversations/{other}/timeline").json() == []


def test_decision_blocks_continue_and_undo_restores_branch_and_idempotent_old_result(
    setup, story
):
    client, text = setup[:2]
    response = act(client, story, "start")
    assert response.status_code == 200, response.text
    started = response.json()["story"]
    assert started["status"] == "awaiting_choice"
    assert act(client, started, "continue").status_code == 422
    ending = started["segments"][-1]["ending"]
    rid = str(uuid4())
    payload = {
        "request_id": rid,
        "expected_revision": started["revision"],
        "operation": "decide",
        "decision_id": ending["id"],
        "option_id": ending["options"][0]["id"],
    }
    result = client.post(f"/api/stories/{story['id']}/actions", json=payload)
    assert result.status_code == 200, result.text
    chosen = result.json()["story"]
    assert "missing letter" in chosen["segments"][-1]["blocks"][0]["text"]
    assert (
        chosen["segments"][0]["ending"]["selected_option_id"]
        == ending["options"][0]["id"]
    )
    undone = act(client, chosen, "undo").json()["story"]
    assert (
        len(undone["segments"]) == 1
        and "selected_option_id" not in undone["segments"][0]["ending"]
    )
    calls = len(text.calls)
    replay = client.post(f"/api/stories/{story['id']}/actions", json=payload).json()
    assert (
        replay["replayed"]
        and replay["story"]["active_segment_id"] == undone["active_segment_id"]
    )
    assert replay["result"]["segment_id"] == chosen["active_segment_id"]
    assert len(text.calls) == calls
    alternative = act(
        client,
        undone,
        "decide",
        decision_id=ending["id"],
        option_id=ending["options"][1]["id"],
    ).json()["story"]
    assert "weather" in alternative["segments"][-1]["blocks"][0]["text"]
    assert "missing letter" not in json.dumps(alternative["segments"])


def test_interjection_discards_unread_suffix_facts_and_decision(setup, story):
    client, text = setup[:2]
    started = act(client, story, "start").json()["story"]
    head = started["segments"][-1]
    result = act(
        client,
        started,
        "interject",
        content="I look at the clock",
        input_type="action",
        revealed_block_id=head["blocks"][1]["id"],
    )
    assert result.status_code == 200, result.text
    updated = result.json()["story"]
    assert len(updated["segments"][0]["blocks"]) == 2
    assert updated["segments"][0]["ending"] == {"type": "continue"}
    frame = json.loads(text.calls[-1][1][-1]["content"])
    assert "UNREAD_DRAWER" not in json.dumps(frame)
    assert head["ending"]["id"] not in json.dumps(frame)
    assert updated["segments"][-1]["blocks"][0]["source"] == "user"
    assert updated["segments"][-1]["blocks"][0]["text"] == "I look at the clock"
    assert (
        act(
            client,
            updated,
            "interject",
            content="x",
            revealed_block_id=head["blocks"][-1]["id"],
        ).status_code
        == 422
    )
    assert act(client, updated, "undo").status_code == 422


def test_rewrite_failure_retry_and_multitab_conflict(setup, story):
    client, text = setup[:2]
    started = act(client, story, "start").json()["story"]
    request = {
        "request_id": str(uuid4()),
        "expected_revision": started["revision"],
        "operation": "rewrite",
        "content": "Keep a slower pace",
    }
    url = f"/api/stories/{story['id']}/actions"
    text.fail = True
    assert client.post(url, json=request).status_code == 502
    saved = client.get(f"/api/stories/{story['id']}").json()
    assert saved["segments"] == started["segments"] and saved["last_error"]
    text.fail = False
    updated = client.post(url, json=request).json()["story"]
    assert updated["active_segment_id"] != started["active_segment_id"]
    assert len(updated["segments"]) == 1
    assert "slower pace" in updated["segments"][0]["blocks"][0]["text"]
    assert act(client, started, "rewrite", content="Stale").status_code == 409
    assert client.post(url, json=request | {"content": "changed"}).status_code == 409
    assert client.post(url, json=request).json()["replayed"]


def test_concurrent_start_only_generates_once(setup, story):
    client, text = setup[:2]
    request = {"request_id": str(uuid4()), "expected_revision": 0, "operation": "start"}
    url = f"/api/stories/{story['id']}/actions"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: client.post(url, json=request), range(2)))
    assert all(r.status_code == 200 for r in results)
    assert len([c for c in text.calls if c[0] == "story"]) == 1
    assert len(results[-1].json()["story"]["segments"]) == 1


def test_progress_restart_recovery_end_delete_placeholder_and_portrait_protection(
    setup, character
):
    client, text, images, settings, engine = setup
    base = f"/api/characters/{character['id']}"
    portrait = client.post(base + "/images/generate", json={}).json()
    client.post(base + f"/images/{portrait['id']}/select")
    story = invite(client, character).json()["story"]
    alternate = client.post(
        base + "/images/generate", json={"expected_image_id": portrait["id"]}
    ).json()
    client.post(base + f"/images/{alternate['id']}/select")
    assert client.delete(base + f"/images/{portrait['id']}").status_code == 409
    started = act(client, story, "start").json()["story"]
    head = started["segments"][-1]
    progress = {
        "expected_revision": started["revision"],
        "segment_id": head["id"],
        "last_revealed_block_id": head["blocks"][1]["id"],
    }
    assert (
        client.patch(f"/api/stories/{story['id']}/progress", json=progress).status_code
        == 200
    )
    with sessions(engine)() as db:
        stored = db.get(Story, story["id"])
        stored.status = "generating"
        stored.stable_status = "awaiting_choice"
        db.add(
            StoryRequest(
                story_id=stored.id,
                request_id=str(uuid4()),
                expected_revision=stored.revision,
                operation="rewrite",
                payload={},
                status="running",
            )
        )
        db.commit()
    with TestClient(create_app(settings, text, images, engine)) as restarted:
        recovered = restarted.get(f"/api/stories/{story['id']}").json()
        assert (
            recovered["status"] == "awaiting_choice"
            and "interrupted" in recovered["last_error"]
        )
        assert (
            recovered["progress"]["last_revealed_block_id"]
            == progress["last_revealed_block_id"]
        )
        text.fail = True
        assert act(restarted, recovered, "end").status_code == 502
        text.fail = False
        finished = act(restarted, recovered, "end", skip_generation=True).json()[
            "story"
        ]
        assert finished["status"] == "completed"
        assert act(restarted, finished, "continue").status_code == 409
        assert restarted.delete(f"/api/stories/{story['id']}").status_code == 204
        timeline = restarted.get(
            f"/api/conversations/{character['conversation_id']}/timeline"
        ).json()
        assert timeline[0]["status"] == "deleted" and timeline[0]["story_id"] is None
        replayed_invitation = invite(
            restarted, character, request_id=story["creation_request_id"]
        )
        assert replayed_invitation.status_code == 201
        assert replayed_invitation.json()["story"] is None
        assert replayed_invitation.json()["card"]["status"] == "deleted"
    assert client.delete(base).status_code == 204
    with sessions(engine)() as db:
        for table in (Story, StorySegment, StoryRequest, ChatEvent, Message):
            assert db.scalar(select(func.count()).select_from(table)) == 0


def test_story_contract_repair_is_bounded_and_budget_keeps_constraints(
    monkeypatch, setup, story
):
    client, text, _, settings, engine = setup
    act(client, story, "start")
    messages = text.calls[-1][1]
    output = text.story(messages)
    from copy import deepcopy

    wrong = deepcopy(output)
    wrong.blocks[0].text = "\u4f60\u597d"
    calls = []
    replies = iter([wrong, output])

    def request(self, context, schema):
        calls.append(context)
        return next(replies)

    monkeypatch.setattr(OpenAIText, "_request", request)
    assert OpenAIText(settings).story(messages) == output
    assert len(calls) == 2
    monkeypatch.setattr(OpenAIText, "_request", lambda *args: wrong)
    with pytest.raises(ProviderError, match="one correction"):
        OpenAIText(settings).story(messages)
    with sessions(engine)() as db:
        stored = db.get(Story, story["id"])
        stored.setup = {"description": "x" * 2000, "constraints": "must remain fixed"}
        stored.snapshot_profile_json = {"name": "A", "backstory": "x" * 15000}
        with pytest.raises(ValueError, match="budget"):
            story_context(
                stored,
                [],
                {"kind": "start"},
                Settings(_env_file=None, story_max_context_tokens=6000),
            )


def test_interject_before_first_consequence_keeps_the_users_explicit_choice(
    setup, story
):
    client = setup[0]
    started = act(client, story, "start").json()["story"]
    decision = started["segments"][-1]["ending"]
    chosen = act(
        client,
        started,
        "decide",
        decision_id=decision["id"],
        option_id=decision["options"][0]["id"],
    ).json()["story"]
    interrupted = act(
        client, chosen, "interject", content="Slow down before answering"
    ).json()["story"]
    assert interrupted["can_undo"]
    assert interrupted["segments"][1]["blocks"] == []
    assert (
        interrupted["segments"][0]["ending"]["selected_option_id"]
        == decision["options"][0]["id"]
    )
    undone = act(client, interrupted, "undo").json()["story"]
    assert len(undone["segments"]) == 1
    assert "selected_option_id" not in undone["segments"][0]["ending"]


@pytest.mark.parametrize(
    "case",
    json.loads(
        (
            Path(__file__).resolve().parents[2] / "docs/mvp/story-evaluation-cases.json"
        ).read_text()
    ),
    ids=lambda case: case["id"],
)
def test_fixed_agency_contract_examples(case, setup, story):
    from copy import deepcopy

    client, text = setup[:2]
    act(client, story, "start")
    context = deepcopy(text.calls[-1][1])
    frame = json.loads(context[-1]["content"])
    frame["setup"]["description"] = case["scene"]
    frame["event"] = case.get("event", {"kind": "start"})
    context[-1]["content"] = json.dumps(frame)
    baseline = text.story(text.calls[-1][1])
    baseline.blocks[3].text = case["candidate"]
    if case["reject"]:
        with pytest.raises(ValueError, match="major player decision"):
            validate_story_output(baseline, context)
    else:
        assert validate_story_output(baseline, context) is baseline


def test_rewrite_keeps_user_authored_contribution(setup, story):
    client = setup[0]
    started = act(client, story, "start").json()["story"]
    updated = act(
        client,
        started,
        "interject",
        content="I am not ready to discuss that.",
        input_type="dialogue",
        revealed_block_id=started["segments"][-1]["blocks"][0]["id"],
    ).json()["story"]
    authored = updated["segments"][-1]["blocks"][0]
    rewritten = act(client, updated, "rewrite", content="Use shorter dialogue").json()[
        "story"
    ]
    assert rewritten["segments"][-1]["blocks"][0] == authored


def test_summary_cannot_turn_an_unselected_choice_into_a_fact(setup, story):
    client, text = setup[:2]
    act(client, story, "start")
    context = text.calls[-1][1]
    candidate = text.story(context)
    candidate.summary = "You agree to date."
    with pytest.raises(ValueError, match="major player decision"):
        validate_story_output(candidate, context)


def test_generating_is_observable_and_get_has_no_model_side_effects(
    setup, story, monkeypatch
):
    from threading import Event

    client, text = setup[:2]
    entered, release = Event(), Event()
    original = text.story

    def slow(context):
        entered.set()
        assert release.wait(10)
        return original(context)

    monkeypatch.setattr(text, "story", slow)
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(lambda: act(client, story, "start"))
        try:
            assert entered.wait(5)
            observed = client.get(f"/api/stories/{story['id']}").json()
            assert observed["status"] == "generating" and observed["segments"] == []
            assert (
                client.get(f"/api/stories/{story['id']}").json()["status"]
                == "generating"
            )
        finally:
            release.set()
        assert pending.result().status_code == 200
    assert len([call for call in text.calls if call[0] == "story"]) == 1


def test_foreign_resources_invalid_options_and_format_failure_do_not_mutate_story(
    setup, character, story, monkeypatch
):
    client, text = setup[:2]
    other = client.post(
        "/api/characters/generate", json={"description": "Another character"}
    ).json()
    assert (
        invite(client, other, conversation_id=character["conversation_id"]).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/characters/{other['id']}/stories",
            params={"conversation_id": character["conversation_id"]},
        ).status_code
        == 404
    )
    started = act(client, story, "start").json()["story"]
    ending = started["segments"][-1]["ending"]
    assert (
        act(
            client, started, "decide", decision_id=ending["id"], option_id=str(uuid4())
        ).status_code
        == 422
    )
    monkeypatch.setattr(
        text, "story", lambda context: {"blocks": [{"speaker": "a stranger"}]}
    )
    failed = act(client, started, "rewrite", content="Keep the scene grounded")
    assert failed.status_code == 502
    saved = client.get(f"/api/stories/{story['id']}").json()
    assert saved["active_segment_id"] == started["active_segment_id"]
    assert saved["segments"] == started["segments"]
    assert saved["retry_action"]["operation"] == "rewrite"


def test_sdk_story_request_uses_its_own_output_budget(setup, story, monkeypatch):
    from types import SimpleNamespace

    client, text, _, _settings, _ = setup
    act(client, story, "start")
    context = text.calls[-1][1]
    expected = text.story(context)
    calls = []

    class SDK:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.complete)
            )

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
                        message=SimpleNamespace(content=expected.model_dump_json()),
                    )
                ],
                usage=None,
            )

    monkeypatch.setattr("echoloom.providers.OpenAI", SDK)
    configured = Settings(
        _env_file=None,
        llm_api_key="test-only",
        llm_model="configured-model",
        story_max_output_tokens=3000,
        max_output_tokens=1000,
    )
    assert OpenAIText(configured).story(context) == expected
    assert calls[0]["max_completion_tokens"] == 3000
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_provider_refusal_is_not_retried_as_a_format_repair(setup, story, monkeypatch):
    from types import SimpleNamespace

    client, text = setup[:2]
    act(client, story, "start")
    context = text.calls[-1][1]
    calls = []

    class SDK:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.complete)
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def complete(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="content_filter",
                        message=SimpleNamespace(content=None),
                    )
                ],
                usage=None,
            )

    monkeypatch.setattr("echoloom.providers.OpenAI", SDK)
    configured = Settings(
        _env_file=None, llm_api_key="test-only", llm_model="configured-model"
    )
    with pytest.raises(ProviderError, match="declined"):
        OpenAIText(configured).story(context)
    assert len(calls) == 1
