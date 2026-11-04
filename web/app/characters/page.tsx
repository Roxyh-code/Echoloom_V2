"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Avatar, Character } from "@/components/api";
export default function Library() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  async function load() {
    setLoading(true);
    setError("");
    try {
      setCharacters(await api("/characters"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function remove(c: Character) {
    if (
      !confirm(
        `删除「${c.profile.name}」及全部对话、设定与图片？此操作无法撤销。`,
      )
    )
      return;
    setBusy(true);
    try {
      await api(`/characters/${c.id}`, undefined, "DELETE");
      setCharacters((old) => old.filter((x) => x.id !== c.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="container">
      <section className="page-intro">
        <div>
          <p className="eyebrow">YOUR LITTLE UNIVERSE</p>
          <h1>每个角色，都有故事。</h1>
          <p className="muted">创造一个新朋友，或继续上一次未完的对话。</p>
        </div>
        <Link className="button primary" href="/characters/new">
          ＋ 创造角色
        </Link>
      </section>
      {error && (
        <div role="alert" className="error">
          {error} <button onClick={load}>重试</button>
        </div>
      )}
      {loading ? (
        <p role="status">正在打开你的角色库…</p>
      ) : !characters.length && !error ? (
        <section className="empty-state">
          <div className="empty-art">✧</div>
          <p className="eyebrow">A STORY STARTS WITH A SPARK</p>
          <h2>你的第一个角色，会是谁？</h2>
          <p>
            一位仰望星空的图书管理员，一位嘴硬心软的旅人。
            <br />
            用几句话，让想象中的 TA 来到这里。
          </p>
          <Link className="button primary" href="/characters/new">
            开始创造 →
          </Link>
        </section>
      ) : (
        <section className="character-grid">
          {characters.map((c) => (
            <article className="character-card" key={c.id}>
              <Link href={`/characters/${c.id}/chat`}>
                <Avatar character={c} large />
                <h2>{c.profile.name}</h2>
              </Link>
              <p>{c.profile.short_description || "故事，等你一起书写。"}</p>
              <div className="tags">
                {c.profile.personality.core_traits.slice(0, 3).map((t, i) => (
                  <span key={i}>{t}</span>
                ))}
              </div>
              <small className="muted">
                更新于 {new Date(c.updated_at).toLocaleDateString("zh-CN")}
              </small>
              <div className="card-actions">
                <Link
                  href={`/characters/${c.id}/chat`}
                  className="button primary"
                >
                  继续对话
                </Link>
                <Link href={`/characters/${c.id}/edit`} className="button">
                  编辑
                </Link>
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() => remove(c)}
                >
                  删除
                </button>
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
