"""Offline regression coverage for Character Chat Mem0; no OpenAI calls."""

import time
from uuid import uuid4

from echoloom.chat_memory import ChatMemory, scope_id
from echoloom.companion_models import Account
from echoloom.config import Settings
from echoloom.db import Base, Character, Conversation, Message, make_engine, sessions
from echoloom.providers import chat_context
from echoloom.schemas import Profile


class MemoryFake:
    def __init__(self):
        self.entries = []
        self.deleted = []

    def add(self, text, *, user_id, agent_id, run_id, metadata, infer):
        self.entries.append(
            dict(text=text, user_id=user_id, agent_id=agent_id,
                 run_id=run_id, metadata=metadata)
        )
        return {"results": [{"memory": text}]}

    def search(self, query, *, filters, top_k, rerank):
        return {"results": [
            dict(id=str(i), memory=row["text"], user_id=row["user_id"],
                 agent_id=row["agent_id"], run_id=row["run_id"])
            for i, row in enumerate(self.entries)
            if all(row.get(k) == v for k, v in filters.items())
        ][:top_k]}

    def delete_all(self, *, user_id, agent_id, run_id):
        self.deleted.append((user_id, agent_id, run_id))
        self.entries = [
            e for e in self.entries
            if (e["user_id"], e["agent_id"], e["run_id"])
            != (user_id, agent_id, run_id)
        ]

    def close(self):
        pass


def wait_until(predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    assert predicate(), "memory worker did not finish"


def setup_store(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    factory = sessions(engine)
    with factory() as db:
        owner = Account(username="benchmark", password_hash="example")
        other = Account(username="other", password_hash="example")
        db.add_all([owner, other])
        db.flush()
        alice = Character(owner_id=owner.id, original_description="A")
        bob = Character(owner_id=owner.id, original_description="B")
        foreign = Character(owner_id=other.id, original_description="C")
        db.add_all([alice, bob, foreign])
        db.flush()
        a1 = Conversation(character_id=alice.id)
        a2 = Conversation(character_id=alice.id)
        b1 = Conversation(character_id=bob.id)
        c1 = Conversation(character_id=foreign.id)
        db.add_all([a1, a2, b1, c1])
        db.commit()
        ids = (owner.id, other.id, alice.id, bob.id, foreign.id,
               a1.id, a2.id, b1.id, c1.id)
    return engine, factory, ids


def write_user(factory, conversation_id, content):
    with factory() as db:
        msg = Message(
            conversation_id=conversation_id, role="user",
            source_type="user_chat", content=content,
            request_id=str(uuid4()), profile_version=1
        )
        db.add(msg)
        db.commit()
        return msg.id


def memory(tmp_path, factory, fake):
    settings = Settings(
        _env_file=None, chat_memory_enabled=True,
        chat_memory_directory=tmp_path / "mem",
        memory_index_batch_size=4, memory_timeout_seconds=3
    )
    return ChatMemory(settings, factory, client_factory=lambda: fake)


def test_cross_conversation_and_account_character_isolation(tmp_path):
    engine, factory, (owner, other, alice, bob, foreign, a1, a2, b1, c1) = setup_store(tmp_path)
    fake = MemoryFake()
    service = memory(tmp_path, factory, fake)
    try:
        mid = write_user(factory, a1, "My favorite tea is jasmine.")
        service.schedule_ids(owner, alice, [mid, mid])
        wait_until(lambda: service.status(owner, alice)["ready_turns"] == 1)
        # Scope does not include conversation ID: a2 shares a1's memories.
        assert "jasmine" in str(service.lookup(owner, alice, "favorite tea")["items"])
        assert service.lookup(owner, bob, "favorite tea")["items"] == []
        assert service.lookup(other, foreign, "favorite tea")["items"] == []
        assert len(fake.entries) == 1
        assert fake.entries[0]["user_id"] == scope_id(owner, alice)
    finally:
        service.close()
        engine.dispose()


def test_memory_failure_stays_observable_after_restart(tmp_path):
    engine, factory, (owner, _, alice, _, _, a1, *_rest) = setup_store(tmp_path)

    class FailingFake(MemoryFake):
        def add(self, *args, **kwargs):
            raise RuntimeError("simulated network failure")

    service = memory(tmp_path, factory, FailingFake())
    mid = write_user(factory, a1, "I moved to Victoria.")
    service.schedule_ids(owner, alice, [mid])
    wait_until(lambda: service.status(owner, alice)["failed_turns"] == 1)
    assert service.lookup(owner, alice, "where do I live?")["items"] == []
    service.close()

    restarted = memory(tmp_path, factory, MemoryFake())
    assert restarted.status(owner, alice)["failed_turns"] == 1
    restarted.close()
    engine.dispose()


def test_delete_wipes_only_target_character_scope(tmp_path):
    engine, factory, (owner, _, alice, bob, _, a1, _, b1, _) = setup_store(tmp_path)
    fake = MemoryFake()
    service = memory(tmp_path, factory, fake)
    try:
        m1 = write_user(factory, a1, "I like astronomy.")
        m2 = write_user(factory, b1, "I like chess.")
        service.schedule_ids(owner, alice, [m1])
        service.schedule_ids(owner, bob, [m2])
        wait_until(lambda: len(fake.entries) == 2)
        service.forget(owner, alice)
        wait_until(lambda: len(fake.deleted) == 1)
        assert not service.lookup(owner, alice, "hobbies")["items"]
        assert "chess" in str(service.lookup(owner, bob, "hobbies")["items"])
    finally:
        service.close()
        engine.dispose()


def test_memory_context_is_optional_and_bounded():
    profile = Profile(name="Rowan")
    settings = Settings(
        _env_file=None, max_chat_context_tokens=3000, max_output_tokens=300
    )
    regular = chat_context(profile, [], "Do you remember my cat?", settings)
    assert not any("LONG-TERM MEMORY" in m["content"] for m in regular)
    enabled = chat_context(
        profile, [], "Do you remember my cat?", settings,
        memory_frame=["User has a cat named Chestnut."]
    )
    assert any("Chestnut" in m["content"] for m in enabled)
    oversized = chat_context(
        profile, [], "Do you remember my cat?", settings,
        memory_frame=["huge" * 2000]
    )
    assert not any("LONG-TERM MEMORY" in m["content"] for m in oversized)
