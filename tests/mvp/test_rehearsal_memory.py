"""Memory boundaries use deterministic providers; no paid API calls."""

import json
from copy import deepcopy
from threading import Event
from types import SimpleNamespace

from langgraph.checkpoint.sqlite import SqliteSaver

from echoloom.config import Settings
from echoloom.rehearsal_domain import add_node, new_document, state_change
from echoloom.rehearsal_graph import build_rehearsal_graph
from echoloom.rehearsal_memory import RehearsalMemory, sources
from echoloom.rehearsal_schema import Setup, StateChange


class FakeMemory:
    def __init__(self):
        self.rows = []
        self.adds = []
        self.fail = False
        self.closed = False
        self.vector_store = SimpleNamespace(client=SimpleNamespace(close=lambda: None))

    def add(self, text, **kwargs):
        if self.fail:
            raise RuntimeError("private-sdk-error")
        self.adds.append((json.loads(text), deepcopy(kwargs)))
        self.rows.append(
            {
                **deepcopy(kwargs),
                "memory": json.loads(text)["record"],
                "id": str(len(self.adds)),
                "score": 0.9,
            }
        )
        return {"results": [self.rows[-1]]}

    def delete_all(self, **scope):
        self.rows = [
            r for r in self.rows if not all(r.get(k) == v for k, v in scope.items())
        ]

    def search(self, query, *, filters, top_k, **kwargs):
        return {
            "results": [
                r
                for r in self.rows
                if r["user_id"] == filters["user_id"]
                and r["agent_id"] == filters["agent_id"]
                and r["metadata"]["source_key"] in filters["source_key"]["in"]
            ][:top_k]
        }

    def close(self):
        self.closed = True


def scene():
    doc = new_document(
        Setup(premise="Two actors meet at the station.").model_dump(),
        [{"id": "a", "name": "Lin"}, {"id": "b", "name": "Xu"}],
    )
    v = doc["versions"][doc["active_version"]]
    state = deepcopy(doc["initial_state"])
    state_change(
        state, StateChange(text="Lin knows the secret.", known_by=["a"]), "n1", "b1"
    )
    state_change(
        state,
        StateChange(
            text="Xu suspects a betrayal; unproven.", known_by=["b"], kind="belief"
        ),
        "n1",
        "b1",
    )
    state_change(
        state, StateChange(text="UNSCOPED author-only note.", known_by=[]), "n1", "b1"
    )
    add_node(
        doc,
        v,
        [
            {
                "id": "b1",
                "text": "Lin hides the letter.",
                "type": "action",
                "character_id": "a",
            }
        ],
        state,
        "op1",
        node_id="n1",
    )
    return doc, v


def service(tmp_path, fake=None, **updates):
    settings = Settings(
        _env_file=None,
        memory_directory=tmp_path / "memory",
        memory_enabled=True,
        **updates,
    )
    fake = fake or FakeMemory()
    return RehearsalMemory(settings, lambda: fake), fake


def test_sources_exclude_unknown_knowledge_foreign_nodes_and_owners(tmp_path):
    memory, _ = service(tmp_path)
    try:
        doc, v = scene()
        expected = sources(doc, v, "owner", "scene", memory.settings)
        assert {p["actor"] for p in expected.values()} == {"a", "b"}
        assert len(expected) == 2
        assert not set(expected) & set(
            sources(doc, v, "other", "scene", memory.settings)
        )
        assert not set(expected) & set(
            sources(doc, v, "owner", "other", memory.settings)
        )
        # Even a stale state record cannot authorize another branch's node.
        doc["nodes"]["n1"]["state"]["world_facts"].append(
            {
                "source_node": "sibling",
                "source_block": "other",
                "text": "OTHER BRANCH",
                "known_by": ["a"],
            }
        )
        assert set(expected) == set(sources(doc, v, "owner", "scene", memory.settings))
        doc["nodes"]["n1"]["blocks"][0]["text"] = "Edited wording"
        assert not set(expected) & set(
            sources(doc, v, "owner", "scene", memory.settings)
        )
    finally:
        memory.close()


def test_index_retrieve_deduplicate_and_invalidate(tmp_path):
    memory, fake = service(tmp_path)
    try:
        doc, v = scene()
        result = memory.lookup(doc, v, "owner", "scene", {"kind": "continue"})
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert {tuple(i["known_by"]) for i in result["items"]} == {("a",), ("b",)}
        belief = next(i for i in result["items"] if i["kind"] == "beliefs")
        assert "unproven" in belief["evidence"]
        assert all("UNSCOPED" not in json.dumps(p) for p, _ in fake.adds)
        memory.lookup(doc, v, "owner", "scene", {"kind": "continue"})
        assert len(fake.adds) == 2
        # A branch before n1 sees no future memories, even though vectors remain.
        before = deepcopy(v) | {"head": None}
        assert memory.lookup(doc, before, "owner", "scene", {})["items"] == []
        # Deleting the source block makes the old vectors unreachable too.
        doc["nodes"]["n1"]["blocks"] = []
        assert memory.lookup(doc, v, "owner", "scene", {})["items"] == []
    finally:
        memory.close()


def test_failed_index_retries_after_reopen(tmp_path):
    fake = FakeMemory()
    fake.fail = True
    memory, _ = service(tmp_path, fake)
    doc, v = scene()
    try:
        result = memory.lookup(doc, v, "owner", "scene", {})
        assert result["status"] == "partial"
        assert result["pending_sources"] == 2
    finally:
        memory.close()
        memory.worker.shutdown(wait=True)
    fake = FakeMemory()
    memory, _ = service(tmp_path, fake)
    try:
        assert len(memory.lookup(doc, v, "owner", "scene", {})["items"]) == 2
        assert len(fake.adds) == 2
    finally:
        memory.close()


def test_timeout_falls_back_without_private_error(tmp_path):
    memory, _ = service(tmp_path, memory_timeout_seconds=1)
    release = Event()
    memory.worker.submit(lambda: release.wait(5))
    try:
        doc, v = scene()
        result = memory.lookup(doc, v, "owner", "scene", {})
        assert result["status"] == "degraded"
        assert result["items"] == []
        assert result["error_type"] == "TimeoutError"
        assert "private" not in json.dumps(result)
    finally:
        release.set()
        memory.close()


def test_graph_resume_keeps_memory_snapshot(setup, tmp_path):
    from test_rehearsal_quality import inputs

    base, settings, initial = inputs(setup)
    initial["memory_experiment"] = {"owner": "owner", "scene": "scene"}

    class Lookup:
        calls = 0

        def lookup(self, *args):
            self.calls += 1
            return {
                "status": "ok",
                "items": [
                    {
                        "id": "m1",
                        "text": "Lin promised to return tomorrow, not yet done.",
                        "kind": "goals",
                        "known_by": [initial["document"]["cast"][0]["id"]],
                    }
                ],
            }

    memory = Lookup()
    settings = settings.model_copy(update={"rehearsal_consistency_enabled": False})
    base.fail = True
    import pytest

    from echoloom.providers import ProviderError

    with SqliteSaver.from_conn_string(str(tmp_path / "graph.sqlite")) as cp:
        graph = build_rehearsal_graph(base, settings, cp, memory)
        config = {"configurable": {"thread_id": "memory-retry"}}
        with pytest.raises(ProviderError):
            graph.invoke(initial, config, durability="sync")
        base.fail = False
        result = graph.invoke(None, config, durability="sync")
    assert memory.calls == 1
    assert result["memory_context"]["used_ids"] == ["m1"]
    frame = json.loads(result["messages"][-1]["content"])
    assert frame["memories"][0]["id"] == "m1"


def test_enabled_api_saves_only_committed_sources(setup, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from test_rehearsal import command, completed, create, quick, wait

    from echoloom.api import create_app

    _, base, images, settings, engine = setup
    settings = settings.model_copy(
        update={"memory_enabled": True, "memory_directory": tmp_path / "api-memory"}
    )
    memory = RehearsalMemory(settings, FakeMemory)
    monkeypatch.setattr("echoloom.rehearsal_memory.RehearsalMemory", lambda _: memory)
    original = base.rehearsal

    def with_changes(messages):
        output = original(messages)
        actor = json.loads(messages[-1]["content"])["cast"][0]["id"]
        output.changes = [
            StateChange(
                after_block=0,
                text="Lin promised to return tomorrow.",
                known_by=[actor],
                kind="goal",
            )
        ]
        return output

    base.rehearsal = with_changes
    with TestClient(create_app(settings, base, images, engine)) as c:
        s = create(c, False, character_ids=[quick(c, "Lin"), quick(c, "Xu")])
        s = completed(c, s)
        job = wait(c, command(c, s, "continue"))
        assert job["status"] == "completed"
        assert job["memory"]["status"] == "ok"
        assert job["memory"]["used_ids"]
        assert all(
            i["source_node"] in job["scene"]["document"]["nodes"]
            for i in job["memory"]["items"]
        )


def test_real_mem0_sdk_filters_and_journal_without_network(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setenv("MEM0_TELEMETRY", "false")
    monkeypatch.setenv("MEM0_DIR", str(tmp_path / "internal"))
    sdk = pytest.importorskip("mem0")
    settings = Settings(_env_file=None, memory_directory=tmp_path / "real-sdk")

    def factory():
        client = sdk.Memory.from_config(
            {
                "llm": {
                    "provider": "openai",
                    "config": {"api_key": "test-placeholder", "model": "gpt-4.1-mini"},
                },
                "embedder": {
                    "provider": "openai",
                    "config": {"api_key": "test-placeholder"},
                },
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "path": str(tmp_path / "qdrant"),
                        "collection_name": "sdk-test",
                    },
                },
                "history_db_path": str(tmp_path / "history.sqlite"),
            }
        )
        client.embedding_model.embed = lambda *a, **k: [1.0] + [0.0] * 1535
        client.embedding_model.embed_batch = lambda texts, **k: [
            [1.0] + [0.0] * 1535 for _ in texts
        ]

        def generate(**kwargs):
            return json.dumps(
                {
                    "memory": [
                        {
                            "id": "0",
                            "text": "Fictional sourced record.",
                            "linked_memory_ids": [],
                        }
                    ]
                }
            )

        client.llm.generate_response = generate
        return client

    memory = RehearsalMemory(settings, factory)
    try:
        doc, v = scene()
        result = memory.lookup(doc, v, "owner", "scene", {})
        assert result["status"] == "ok"
        assert len(result["items"]) == 2
        assert {tuple(i["known_by"]) for i in result["items"]} == {("a",), ("b",)}
    finally:
        memory.close()
        memory.worker.shutdown(wait=True)


def test_overbroad_backend_results_are_filtered_again(tmp_path):
    fake = FakeMemory()
    fake.search = lambda *a, **k: {"results": fake.rows}
    memory, _ = service(tmp_path, fake)
    try:
        doc, v = scene()
        result = memory.lookup(doc, v, "owner", "scene", {})
        assert (
            len(result["items"]) == 2
        )  # not four, despite backend ignoring actor filters
        assert len(memory.lookup(doc, v, "another-owner", "scene", {})["items"]) == 2
        assert len(fake.rows) == 4
    finally:
        memory.close()


def test_memory_budget_discards_supplements_before_baseline_history():
    from echoloom.rehearsal_domain import context

    doc, v = scene()
    settings = Settings(_env_file=None)
    baseline = context(doc, v, {"kind": "continue"}, settings)
    payload_bytes = sum(len(m["content"].encode()) for m in baseline)
    tight = settings.model_copy(
        update={
            "story_max_context_tokens": payload_bytes
            + settings.story_max_output_tokens
            + 600
            + 10,
        }
    )
    assert (
        context(
            doc,
            v,
            {"kind": "continue"},
            tight,
            memories=[
                {
                    "id": "large",
                    "text": "x" * 12000,
                }
            ],
        )
        == baseline
    )


def test_disabled_never_imports_mem0_or_creates_store(setup, tmp_path, monkeypatch):
    import builtins

    from fastapi.testclient import TestClient
    from test_rehearsal import completed, create, quick

    from echoloom.api import create_app

    _, base, images, settings, engine = setup
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        assert not name.startswith("mem0"), "Disabled mode imported Mem0"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    directory = tmp_path / "must-not-exist"
    settings = settings.model_copy(
        update={"memory_enabled": False, "memory_directory": directory}
    )
    with TestClient(create_app(settings, base, images, engine)) as c:
        completed(c, create(c, False, character_ids=[quick(c, "Lin"), quick(c, "Xu")]))
    assert not directory.exists()
