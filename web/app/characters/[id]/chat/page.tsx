"use client";
import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { api, Avatar, Character, Message } from "@/components/api";
export default function Chat({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const base = `/characters/${id}`;
  const [character, setCharacter] = useState<Character | null>(null);
  const [conversations, setConversations] = useState<
    { id: string; created_at: string }[]
  >([]);
  const [conversation, setConversation] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState<{
    content: string;
    request_id: string;
  } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const guard = useRef(false);
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Character>(base),
      api<{ id: string; created_at: string }[]>(`${base}/conversations`),
    ])
      .then(async ([c, cs]) => {
        if (!active) return;
        const conv = sessionStorage.getItem(`echoloom-conversation-${id}`);
        const cid = cs.some((x) => x.id === conv) ? conv! : c.conversation_id;
        const ms = await api<Message[]>(`/conversations/${cid}/messages`);
        if (active) {
          setCharacter(c);
          setConversations(cs);
          setConversation(cid);
          setMessages(ms);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [base, id]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);
  async function send(failed?: { content: string; request_id: string }) {
    if (guard.current || (!failed && !input.trim())) return;
    const body = failed || {
      content: input.trim(),
      request_id: crypto.randomUUID(),
    };
    guard.current = true;
    setBusy(true);
    setError("");
    setRetry(null);
    try {
      const ms = await api<Message[]>(
        `/conversations/${conversation}/messages`,
        body,
      );
      setMessages(ms);
      setInput("");
      setCharacter(await api(base));
    } catch (e) {
      setError((e as Error).message);
      setRetry(body);
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  async function switchConversation(cid: string) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      setMessages(await api(`/conversations/${cid}/messages`));
      setConversation(cid);
      sessionStorage.setItem(`echoloom-conversation-${id}`, cid);
      setRetry(null);
      setInput("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  async function newConversation() {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      const c = await api<{ id: string; created_at: string }>(
        `${base}/conversations`,
        {},
      );
      setConversations((old) => [...old, c]);
      setConversation(c.id);
      setMessages([]);
      setRetry(null);
      setInput("");
      sessionStorage.setItem(`echoloom-conversation-${id}`, c.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  if (loading)
    return (
      <main className="container" role="status">
        正在找回上次的对话…
      </main>
    );
  if (!character)
    return (
      <main className="container">
        <p className="error" role="alert">
          {error}
        </p>
        <button className="button" onClick={() => location.reload()}>
          重新加载
        </button>
      </main>
    );
  return (
    <main className="chat-container">
      <div className="chat-top">
        <Link className="back-link" href="/characters">
          ← 我的角色
        </Link>
        <Link className="button" href={`${base}/edit`}>
          编辑角色 ↗
        </Link>
      </div>
      <section className="chat-shell">
        <aside className="chat-profile">
          <Avatar character={character} large />
          <h1>{character.profile.name}</h1>
          <p>{character.profile.short_description}</p>
          <div className="tags">
            {character.profile.personality.core_traits
              .slice(0, 4)
              .map((t, i) => (
                <span key={i}>{t}</span>
              ))}
          </div>
          <p className="muted small">
            当前设定 v{character.profile_version}
            <br />
            这是虚构 AI 角色。对话保存在本机。
          </p>
          <label htmlFor="conversation">对话记录</label>
          <select
            id="conversation"
            disabled={busy}
            value={conversation}
            onChange={(e) => switchConversation(e.target.value)}
          >
            {conversations.map((c, i) => (
              <option key={c.id} value={c.id}>
                对话 {i + 1} ·{" "}
                {new Date(c.created_at).toLocaleDateString("zh-CN")}
              </option>
            ))}
          </select>
          <button
            className="button full"
            disabled={busy}
            onClick={newConversation}
          >
            ＋ 开始新对话
          </button>
        </aside>
        <div className="chat-main">
          <div className="chat-title">
            <span className="presence" />与 {character.profile.name} 的对话{" "}
            <small>AI CHARACTER</small>
          </div>
          <div className="messages" aria-live="polite">
            {messages.length === 0 && (
              <div className="chat-empty">
                <span>✧</span>
                <h2>故事，从一句「你好」开始。</h2>
                <p>问问 TA 今天在想什么，或者介绍一下自己。</p>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`message ${m.role}`}>
                <small>
                  {m.role === "user" ? "你" : character.profile.name}
                </small>
                <p>{m.content}</p>
              </div>
            ))}
            {busy && (
              <div className="thinking" role="status">
                正在等待回应…
              </div>
            )}
            <div ref={bottom} />
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
              {retry && (
                <button disabled={busy} onClick={() => send(retry)}>
                  重试这条消息
                </button>
              )}
            </div>
          )}
          <form
            className="chat-composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <label className="sr-only" htmlFor="message">
              消息
            </label>
            <textarea
              id="message"
              rows={2}
              maxLength={4000}
              placeholder={`对 ${character.profile.name} 说点什么…`}
              value={input}
              disabled={busy || !!retry}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  if (!retry) void send();
                }
              }}
            />
            <button
              className="button primary"
              disabled={busy || !input.trim() || !!retry}
            >
              发送 ↑
            </button>
          </form>
          {retry && (
            <div className="retry-note">
              <span>未发送成功：{retry.content.slice(0, 80)}</span>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => {
                  setRetry(null);
                  setError("");
                }}
              >
                取消重试，重新编辑
              </button>
            </div>
          )}
          <p className="chat-disclaimer">
            AI 可能生成不准确的内容。Enter 发送 · Shift + Enter 换行
          </p>
        </div>
      </section>
    </main>
  );
}
