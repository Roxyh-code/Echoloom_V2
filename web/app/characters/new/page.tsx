"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, Character, Health } from "@/components/api";
const example =
  "一位二十多岁的神秘图书管理员，银色长发，蓝色眼睛。她安静、聪明，说话带一点讽刺，喜欢天文学。不擅长直接表达关心，但会默默记住朋友的喜好。";
export default function CreateCharacter() {
  const router = useRouter();
  const guard = useRef(false);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    api<Health>("/health")
      .then(setHealth)
      .catch((e) => setError(e.message));
  }, []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (guard.current || !description.trim()) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      const character = await api<Character>("/characters/generate", {
        description,
      });
      router.push(`/characters/${character.id}/edit`);
    } catch (e) {
      setError((e as Error).message);
      guard.current = false;
      setBusy(false);
    }
  }
  const limit = health?.max_profile_input_chars || 5000;
  return (
    <main className="create-container">
      <Link className="back-link" href="/characters">
        ← 回到我的角色
      </Link>
      <div className="create-heading">
        <span className="spark">✦</span>
        <p className="eyebrow">FROM AN IDEA TO AN IDENTITY</p>
        <h1>让你的角色，鲜活起来。</h1>
        <p className="muted">
          说说 TA 是谁。外貌、性格、经历，或只是一个小小的灵感。
          <br />
          我们会一起把它变成可以交流的角色。
        </p>
      </div>
      <form onSubmit={submit} className="panel create-form">
        <label htmlFor="description">你想遇见怎样的角色？</label>
        <textarea
          id="description"
          autoFocus
          rows={8}
          maxLength={limit}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={busy}
          placeholder="TA 的名字、样子、性格，或某个特别的习惯…"
        />
        <div className="input-footer">
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => setDescription(example)}
          >
            ✧ 试试一个灵感
          </button>
          <small>
            {description.length} / {limit}
          </small>
        </div>
        {health && !health.text_configured && (
          <p className="notice">
            文字模型尚未配置。请在后端 .env
            中填写模型和密钥后重启服务；系统不会用示例回复冒充生成结果。
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button
          className="button primary full"
          disabled={busy || !description.trim()}
        >
          {busy ? "正在赋予角色个性，请稍等…" : "创造我的角色 →"}
        </button>
        <p className="form-note">
          生成后，你可以自由编辑每一个细节。头像由你决定何时生成。
        </p>
      </form>
    </main>
  );
}
