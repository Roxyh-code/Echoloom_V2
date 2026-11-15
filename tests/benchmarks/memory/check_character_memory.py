"""Standalone Mem0 semantic smoke test for fictional character knowledge.

Run from the Echoloom_V2 repository root (using the memory-enabled venv):
    .\\.venv-memory\\Scripts\\python.exe .\\tests\\benchmarks\\memory\\check_character_memory.py
    .\\.venv-memory\\Scripts\\python.exe .\\tests\\benchmarks\\memory\\check_character_memory.py --read

Reads the project's root .env. Stores only isolated smoke-test data under
work/character-memory-smoke/. Uses paid OpenAI embedding/model calls.
A PASS indicates SDK/storage success, not semantic correctness: review the
five questions printed at the end.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# This file lives in tests/benchmarks/memory; resolve the original repo root.
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

STORAGE = ROOT / "work" / "character-memory-smoke"
STORAGE.mkdir(parents=True, exist_ok=True)

os.environ["MEM0_TELEMETRY"] = "false"
os.environ["MEM0_DIR"] = str(STORAGE / "internal")
logging.disable(logging.CRITICAL)

RULES = """
Extract memories ONLY about the fictional scene, never about the real user.
Use explicit character names Lin and Xu; never replace them with User or Assistant.

Story time is scene-relative. No absolute calendar date is provided.
Keep tomorrow as tomorrow relative to scene S1; never resolve it using
Observation Date or Current Date.

Distinguish FACT, PROMISE, BELIEF and KNOWLEDGE.
A promise is not a completed event.
A belief is not a proven world fact.

Preserve who knows each secret and who does not.
Do not infer shared knowledge.
Knowing a plan does not mean the plan has already happened.

For every memory, retain scene S1 and source N1 and all necessary qualifiers.
Return memory text in Chinese. Keep the normal Mem0 JSON output schema.
"""

SCENE = """
以下是虚构故事的正式场景记录，不是真实用户的个人信息。

场景：S1。来源节点：N1。
故事没有提供公历日期。

1. Lin 承诺明天在车站把信归还给 Xu。
   归还尚未发生。

2. Lin 私下看过信，知道 Xu 打算离开。
   Xu 不知道 Lin 看过信。
   Lin 尚未向 Xu 透露自己看过信。

3. Xu 怀疑 Lin 把信交给了第三个人。
   这只是 Xu 的猜测，没有证据证明信被交给别人。
"""


def main():
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        print("FAIL: 没有找到 API key，请检查本地 .env")
        return 1

    endpoint = "https://api.openai.com/v1"

    for name in ("OPENAI_BASE_URL", "OPENAI_API_BASE"):
        configured = os.getenv(name, "").rstrip("/")
        if configured and configured != endpoint:
            print("FAIL: 检测到自定义接口地址，需要先核对本地配置")
            return 1

    from mem0 import Memory
    from openai import OpenAI

    model = os.getenv("LLM_MODEL") or "gpt-4.1-mini"
    read_only = "--read" in sys.argv

    print("文本模型：", model)
    print("测试模式：", "重新读取已保存记忆" if read_only else "提取并保存记忆")

    if not read_only:
        with OpenAI(
            api_key=key,
            base_url=endpoint,
            timeout=30,
            max_retries=0,
        ) as client:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="Fictional scene memory connection test.",
            )

        dimensions = len(response.data[0].embedding)
        if dimensions != 1536:
            raise RuntimeError("Unexpected embedding dimensions")

        print("PASS: OpenAI embedding，1536 维", flush=True)

    common = {
        "api_key": key,
        "openai_base_url": endpoint,
    }

    memory = Memory.from_config({
        "custom_instructions": RULES,
        "llm": {
            "provider": "openai",
            "config": {
                **common,
                "model": model,
                "temperature": 0.1,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                **common,
                "model": "text-embedding-3-small",
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "path": str(STORAGE / "qdrant"),
                "collection_name": "echoloom_character_smoke",
                "embedding_model_dims": 1536,
            },
        },
        "history_db_path": str(STORAGE / "history.db"),
    })

    try:
        if not read_only:
            result = memory.add(
                SCENE,
                user_id="echoloom-character-smoke",
                metadata={
                    "scene_id": "S1",
                    "source_node_id": "N1",
                },
                infer=True,
            )

            if not result.get("results"):
                raise RuntimeError("No memories extracted")

            print("PASS: 角色记忆提取与保存", flush=True)

        results = memory.search(
            "场景 S1 中，Lin 和 Xu 的信件约定、秘密知情范围和猜测是什么？",
            filters={
                "user_id": "echoloom-character-smoke",
                "scene_id": "S1",
                "source_node_id": "N1",
            },
            top_k=20,
            threshold=0,
        ).get("results", [])

        if not results:
            raise RuntimeError("No search results")

        print(
            "PASS: 重启后检索" if read_only else "PASS: 角色记忆检索",
            flush=True,
        )

        print("\n提取出的记忆：")
        for index, item in enumerate(results, start=1):
            print(f"{index}. {item['memory']}")

        print("\n请人工核对：")
        print("1. Lin、Xu 是否仍是角色，没有被写成真实用户？")
        print("2. 明天是否保留为故事相对时间，没有补入现实日期？")
        print("3. 归还是否仍是承诺，没有被记成已经完成？")
        print("4. 是否保留 Xu 不知道 Lin 看过信？")
        print("5. 转交信件是否仍是 Xu 的猜测，没有被记成事实？")
        print("\n注意：PASS 仅表示调用成功，不代表语义检查通过。")

    finally:
        memory.close()
        memory.vector_store.client.close()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(
            "FAIL:",
            type(exc).__name__,
            "HTTP状态:",
            getattr(exc, "status_code", None),
        )
        print("未打印原始错误，以避免暴露密钥。")
        sys.exit(1)
