from copy import deepcopy

import pytest
from echoloom import rehearsal_graph as workflow
from echoloom.rehearsal_domain import (
    bind_role_context,
    role_bindings,
    validate_performance,
)
from echoloom.rehearsal_schema import Performance
from langgraph.checkpoint.sqlite import SqliteSaver
from test_rehearsal import create, quick

CAST = {
    "cast": [
        {"id": "actor-a", "name": "Miyu Takahashi"},
        {"id": "actor-b", "name": "秦彻"},
    ]
}


def performance(kind="action", actor=None):
    return {
        "blocks": [
            {"type": kind, "character_id": actor, "text": "The station falls silent."}
        ],
        "changes": [
            {"after_block": 0, "text": "The station is quiet.", "known_by": []}
        ],
    }


def test_unattributed_stage_direction_becomes_narration_without_mutating_input():
    original = performance()
    before = deepcopy(original)
    result = validate_performance(original, CAST, {"takeover": None})
    assert result.blocks[0].type == "narration"
    assert result.blocks[0].character_id is None
    assert result.blocks[0].text == before["blocks"][0]["text"]
    assert result.changes[0].after_block == 0
    assert original == before


@pytest.mark.parametrize(
    "kind,actor,takeover",
    [
        ("dialogue", None, None),
        ("action", "unknown", None),
        ("action", None, "actor-a"),
        ("action", "actor-a", "actor-a"),
    ],
)
def test_actor_validation_remains_strict(kind, actor, takeover):
    with pytest.raises(ValueError):
        validate_performance(performance(kind, actor), CAST, {"takeover": takeover})


def test_explicit_actor_attribution_is_unchanged():
    result = validate_performance(
        performance(actor="actor-b"), CAST, {"takeover": None}
    )
    assert result.blocks[0].type == "action"
    assert result.blocks[0].character_id == "actor-b"


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("A", "actor-a"),
        ("B", "actor-b"),
        ("角色A", "actor-a"),
        ("角色 B", "actor-b"),
        ("第一个人", "actor-a"),
        ("第二个人", "actor-b"),
        ("第一个角色", "actor-a"),
        ("第二位角色", "actor-b"),
        ("first person", "actor-a"),
        ("second person", "actor-b"),
        ("the first character", "actor-a"),
        ("CHARACTER B", "actor-b"),
    ],
)
def test_author_shorthand_maps_in_blocks_and_knowledge(alias, expected):
    original = performance("dialogue", alias)
    original["changes"][0]["known_by"] = [alias]
    result = validate_performance(original, CAST, {"takeover": None})
    assert result.blocks[0].character_id == expected
    assert result.changes[0].known_by == [expected]


def test_slots_take_precedence_over_list_order():
    cast = [
        {"id": "actor-b", "name": "秦彻", "slot": 1},
        {"id": "actor-a", "name": "Miyu Takahashi", "slot": 0},
    ]
    assert role_bindings(cast)[0]["character_id"] == "actor-a"
    result = validate_performance(
        performance("dialogue", "A"), {"cast": cast}, {"takeover": None}
    )
    assert result.blocks[0].character_id == "actor-a"


def test_alias_does_not_bypass_takeover():
    with pytest.raises(ValueError, match="taken over"):
        validate_performance(
            performance("dialogue", "第一个人"), CAST, {"takeover": "actor-a"}
        )


def test_ambiguous_name_and_role_is_not_guessed():
    cast = deepcopy(CAST)
    cast["cast"][1]["name"] = "A"
    with pytest.raises(ValueError, match="ambiguous"):
        validate_performance(performance("dialogue", "A"), cast, {"takeover": None})


def test_old_checkpoint_context_gets_bindings_without_rewriting_prose():
    import json

    messages = [
        {"role": "system", "content": "Existing rules."},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "cast": CAST["cast"],
                    "setup": {"premise": "A等着B。第一个人知道秘密，第二个人不知道。"},
                },
                ensure_ascii=False,
            ),
        },
    ]
    original = deepcopy(messages)
    enriched = bind_role_context(messages)
    frame = json.loads(enriched[-1]["content"])
    assert frame["role_bindings"][0]["name"] == "Miyu Takahashi"
    assert frame["role_bindings"][1]["name"] == "秦彻"
    assert (
        frame["setup"]["premise"]
        == json.loads(original[-1]["content"])["setup"]["premise"]
    )
    assert messages == original


def test_pending_validation_checkpoint_resumes_without_model_call(
    setup, tmp_path, monkeypatch
):
    c, _base, _, settings, _ = setup
    scene = create(
        c, False, character_ids=[quick(c, "Miyu Takahashi"), quick(c, "秦彻")]
    )
    doc = scene["document"]
    initial = {
        "document": doc,
        "scene_version": doc["versions"][doc["active_version"]],
        "request_event": {"kind": "continue", "text": ""},
    }
    settings = settings.model_copy(update={"rehearsal_consistency_enabled": False})
    calls = 0

    class Provider:
        def rehearsal(self, messages):
            nonlocal calls
            calls += 1
            return Performance.model_validate(performance())

    path = str(tmp_path / "attribution.db")
    config = {"configurable": {"thread_id": "pending-validation"}}

    def old_validator(*args):
        raise ValueError("Unknown or ambiguous actor.")

    with SqliteSaver.from_conn_string(path) as cp, monkeypatch.context() as patch:
        patch.setattr(workflow, "validate_performance", old_validator)
        graph = workflow.build_rehearsal_graph(Provider(), settings, cp)
        with pytest.raises(ValueError):
            graph.invoke(initial, config, durability="sync")
        assert graph.get_state(config).next == ("validate_output",)

    # Rebuild with the corrected validator and reopen the same persisted DB.
    with SqliteSaver.from_conn_string(path) as cp:
        graph = workflow.build_rehearsal_graph(Provider(), settings, cp)
        result = graph.invoke(None, config, durability="sync")
        assert graph.get_state(config).next == ()
    assert calls == 1
    assert result["performance"]["blocks"][0]["type"] == "narration"
