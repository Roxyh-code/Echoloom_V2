"""Opt-in, source-bound rehearsal memory. Business history is authoritative.

Only committed state records with explicit known_by are indexed. Each record /
actor has its own Mem0 run, so extraction never sees another branch or actor's
records. A durable local journal makes partial writes retryable. Old vectors are
unreachable after edits/deletion; this is logical invalidation, not erasure.
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager
from threading import Lock

from .rehearsal_domain import history, state_at

log = logging.getLogger("echoloom.ai")
RULES_VERSION = "fiction-v1"
RULES = """Extract ONLY fictional character memories, never real user details.
Keep exact character names and IDs. Do not call a character User or Assistant.
Preserve source kind: a belief is not fact, a goal is not completed action,
and a promise is not its fulfilment. Preserve uncertainty and negation.
Use story-relative time. Do NOT resolve tomorrow/yesterday using Observation
Date or Current Date. No calendar date exists unless explicitly in source text.
Do not infer shared knowledge, additional events or offscreen actions.
Only summarize the supplied record; preserve its meaning and qualifications.
Use the input language. Keep the standard Mem0 JSON output schema.
"""
KINDS = ("world_facts", "beliefs", "goals", "relationships", "threads")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def sources(doc, version, owner, scene, settings):
    """Recompute admissible scopes from current history, not vector metadata."""
    path = {n["id"]: n for n in history(doc, version["head"])}
    cast = {c["id"]: c["name"] for c in doc["cast"]}
    user = digest([owner, scene])
    result = {}
    for kind in KINDS:
        for record in state_at(doc, version)[kind]:
            node = path.get(record.get("source_node"))
            if not node:
                continue
            block = next(
                (b for b in node["blocks"] if b["id"] == record.get("source_block")),
                None,
            )
            if not block:
                continue
            for actor in sorted(set(record.get("known_by", [])) & cast.keys()):
                payload = {
                    "user": user,
                    "actor": actor,
                    "cast": cast,
                    "scene": scene,
                    "source_node": node["id"],
                    "source_block": block["id"],
                    "source_hash": digest(block),
                    "kind": kind,
                    "text": record["text"],
                    "rules": RULES_VERSION,
                    "model": settings.memory_llm_model,
                    "embedding": settings.memory_embedding_model,
                }
                result[digest(payload)] = payload
    return result


class RehearsalMemory:
    """One serialized worker owns Mem0/Qdrant; never share a local store process."""

    def __init__(self, settings, client_factory=None):
        self.settings = settings
        self.directory = settings.memory_directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.journal = self.directory / "index.sqlite"
        self.client_factory = client_factory
        self.client = None
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem0")
        self.guard = Lock()
        self.closed = False
        self.index_pending = False
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS sources "
                "(scope TEXT PRIMARY KEY, payload TEXT NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'pending')"
            )

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.journal, timeout=5)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _client(self):
        if self.client is None:
            if self.client_factory:
                self.client = self.client_factory()
                return self.client
            key = self.settings.llm_api_key.get_secret_value()
            if not key:
                raise ValueError("Memory requires LLM_API_KEY")
            # Set before importing Mem0. No telemetry or home/tmp storage.
            os.environ["MEM0_TELEMETRY"] = "false"
            os.environ["MEM0_DIR"] = str(self.directory / "internal")
            from mem0 import Memory

            # Mem0 can log full extraction prompts and provider errors. Keep those
            # out of server logs; our boundary emits only status/type/counts.
            for name in list(logging.Logger.manager.loggerDict):
                if name == "mem0" or name.startswith("mem0."):
                    logging.getLogger(name).setLevel(logging.CRITICAL)

            common = {"api_key": key, "openai_base_url": "https://api.openai.com/v1"}
            self.client = Memory.from_config(
                {
                    "custom_instructions": RULES,
                    "llm": {
                        "provider": "openai",
                        "config": {
                            **common,
                            "model": self.settings.memory_llm_model,
                            "temperature": 0.1,
                        },
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            **common,
                            "model": self.settings.memory_embedding_model,
                        },
                    },
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "path": str(self.directory / "qdrant"),
                            "collection_name": "rehearsal_"
                            + digest(self.settings.memory_embedding_model)[:12],
                            "embedding_model_dims": 1536,
                        },
                    },
                    "history_db_path": str(self.directory / "history.sqlite"),
                }
            )
            # Bound individual network calls; disable hidden SDK retries.
            for adapter in (self.client.llm, self.client.embedding_model):
                adapter.client = adapter.client.with_options(timeout=20, max_retries=0)
        return self.client

    def _queue(self, admissible):
        with self.connect() as db:
            db.executemany(
                "INSERT OR IGNORE INTO sources(scope, payload) VALUES (?, ?)",
                [
                    (scope, json.dumps(p, ensure_ascii=False))
                    for scope, p in admissible.items()
                ],
            )

    def _index(self, scopes):
        """Retry only currently admissible scopes. No blanket replay of deleted data."""
        client = self._client()
        attempted = 0
        for scope in scopes:
            with self.connect() as db:
                row = db.execute(
                    "SELECT payload, status FROM sources WHERE scope=?", (scope,)
                ).fetchone()
            if not row or row[1] == "ready":
                continue
            if attempted >= self.settings.memory_index_batch_size:
                break
            attempted += 1
            payload = json.loads(row[0])
            try:
                # A crash may have left vectors but no ready journal entry.
                client.delete_all(
                    user_id=payload["user"], agent_id=payload["actor"], run_id=scope
                )
                client.add(
                    json.dumps(
                        {
                            "fictional_characters": payload["cast"],
                            "source_kind": payload["kind"],
                            "record": payload["text"],
                            "known_by": [payload["actor"]],
                        },
                        ensure_ascii=False,
                    ),
                    user_id=payload["user"],
                    agent_id=payload["actor"],
                    run_id=scope,
                    metadata={"source_key": scope},
                    infer=True,
                )
                with self.connect() as db:
                    db.execute(
                        "UPDATE sources SET status='ready' WHERE scope=?", (scope,)
                    )
            except Exception as exc:  # noqa: BLE001 - memory failure must not break a saved scene
                log.warning(
                    "kind=memory_index status=failed error_type=%s", type(exc).__name__
                )
                # Keep pending; retry on the next scene operation.

    def schedule(self, doc, version, owner, scene):
        """Called only after a business commit. Failed indexing cannot roll it back."""
        try:
            admissible = sources(doc, version, owner, scene, self.settings)
            self._queue(admissible)
            with self.guard:
                if not self.closed and admissible and not self.index_pending:
                    self.index_pending = True
                    self.worker.submit(self._background_index, list(admissible))
        except Exception as exc:  # noqa: BLE001 - optional service boundary
            log.warning(
                "kind=memory_queue status=failed error_type=%s", type(exc).__name__
            )

    def _background_index(self, scopes):
        try:
            self._index(scopes)
        except Exception as exc:  # noqa: BLE001 - background worker boundary
            log.warning(
                "kind=memory_index status=failed error_type=%s", type(exc).__name__
            )
        finally:
            with self.guard:
                self.index_pending = False

    def lookup(self, doc, version, owner, scene, event):
        started = time.monotonic()
        try:
            admissible = sources(doc, version, owner, scene, self.settings)
            self._queue(admissible)
            query = json.dumps(
                {
                    "operation": event,
                    "premise": version["setup"]["premise"],
                    "recent": [
                        b["text"][:300]
                        for n in history(doc, version["head"])[-2:]
                        for b in n["blocks"]
                    ],
                },
                ensure_ascii=False,
            )[:6000]
            # All Qdrant/SQLite client work stays on its owning worker.
            with self.guard:
                if self.closed:
                    raise RuntimeError("Memory closed")
                future = self.worker.submit(self._lookup, admissible, query)
            result = future.result(timeout=self.settings.memory_timeout_seconds)
        except Exception as exc:  # noqa: BLE001 - fall back to baseline without exposing SDK errors
            if isinstance(exc, TimeoutError):
                future.cancel()
            result = {
                "status": "degraded",
                "items": [],
                "error_type": type(exc).__name__,
            }
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        log.info(
            "kind=memory_lookup status=%s count=%s elapsed_ms=%s",
            result["status"],
            len(result["items"]),
            result["elapsed_ms"],
        )
        return result

    def _lookup(self, admissible, query):
        if not admissible:
            return {"status": "empty", "items": []}
        self._index(admissible)
        client = self._client()
        grouped = {}
        for scope, payload in admissible.items():
            grouped.setdefault((payload["user"], payload["actor"]), []).append(scope)
        candidates = []
        with self.connect() as db:
            ready = {
                row[0]
                for row in db.execute("SELECT scope FROM sources WHERE status='ready'")
            }
        for (user, actor), scopes in grouped.items():
            scopes = [s for s in scopes if s in ready]
            if not scopes:
                continue
            found = client.search(
                query,
                filters={
                    "user_id": user,
                    "agent_id": actor,
                    "source_key": {"in": scopes},
                },
                top_k=self.settings.memory_top_k,
                rerank=False,
            ).get("results", [])
            for item in found:
                scope = (item.get("metadata") or {}).get("source_key")
                if (
                    scope not in scopes
                    or item.get("user_id") != user
                    or item.get("agent_id") != actor
                    or item.get("run_id") != scope
                ):
                    continue
                source = admissible[scope]
                # The writer also gets original evidence/type, not only an LLM summary.
                candidates.append(
                    {
                        "id": item["id"],
                        "text": item["memory"],
                        "known_by": [actor],
                        "kind": source["kind"],
                        "source_node": source["source_node"],
                        "source_block": source["source_block"],
                        "evidence": source["text"],
                        "score": float(item.get("score", 0)),
                    }
                )
        candidates.sort(key=lambda x: x["score"], reverse=True)
        items, used = [], 0
        for item in candidates:
            size = len(json.dumps(item, ensure_ascii=False).encode())
            if (
                used + size <= self.settings.memory_context_bytes
                and len(items) < self.settings.memory_top_k
            ):
                items.append(item)
                used += size
        pending = bool(set(admissible) - ready)
        return {
            "status": "partial" if pending else "ok",
            "items": items,
            "pending_sources": len(set(admissible) - ready),
        }

    def close(self):
        with self.guard:
            if self.closed:
                return
            self.closed = True
            self.worker.submit(self._close_client)
            self.worker.shutdown(wait=False)

    def _close_client(self):
        if self.client is not None:
            self.client.close()
            self.client.vector_store.client.close()
