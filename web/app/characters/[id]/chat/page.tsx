"use client";
import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { api, Avatar, Character } from "@/components/api";
import { StoryInvitation } from "@/components/story-invitation";
import { StoryCard } from "@/components/story-card";
import { TimelineItem, StoryCardData } from "@/components/story-api";
export default function Chat({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const base = `/characters/${id}`;
  const [character, setCharacter] = useState<Character | null>(null);
  const [conversations, setConversations] = useState<
    { id: string; created_at: string }[]
  >([]);
  const [conversation, setConversation] = useState("");
  const [messages, setMessages] = useState<TimelineItem[]>([]);
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
  const target = useRef<string | null>(null);
  const [extras, setExtras] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [past, setPast] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Character>(base),
      api<{ id: string; created_at: string }[]>(`${base}/conversations`),
    ])
      .then(async ([c, cs]) => {
        if (!active) return;
        const query = new URLSearchParams(window.location.search);
        const requested = query.get("conversation");
        const conv = sessionStorage.getItem(`echoloom-conversation-${id}`);
        const cid = cs.some((x) => x.id === requested)
          ? requested!
          : cs.some((x) => x.id === conv)
            ? conv!
            : c.conversation_id;
        const ms = await api<TimelineItem[]>(`/conversations/${cid}/timeline`);
        const event = query.get("event");
        if (
          requested === cid &&
          event &&
          ms.some((item) => item.kind === "story_card" && item.id === event)
        )
          target.current = `story-event-${event}`;
        if (active) {
          setCharacter(c);
          setConversations(cs);
          setConversation(cid);
          setMessages(ms);
          if (requested === cid && query.get("invite") === "1")
            setInviting(true);
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
    if (target.current) {
      const element = document.getElementById(target.current);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
        target.current = null;
      }
    } else bottom.current?.scrollIntoView({ behavior: "smooth" });
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
      await api(`/conversations/${conversation}/messages`, body);
      setMessages(
        await api<TimelineItem[]>(`/conversations/${conversation}/timeline`),
      );
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
      setMessages(await api(`/conversations/${cid}/timeline`));
      setInviting(false);
      setPast(false);
      setExtras(false);
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
      setInviting(false);
      setPast(false);
      setExtras(false);
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
        Loading your conversation…
      </main>
    );
  if (!character)
    return (
      <main className="container">
        <p className="error" role="alert">
          {error}
        </p>
        <button className="button" onClick={() => location.reload()}>
          Reload
        </button>
      </main>
    );
  return (
    <main className="chat-container">
      {inviting && (
        <StoryInvitation
          key={conversation}
          character={character}
          conversation={conversation}
          onClose={() => setInviting(false)}
          onCreated={async (card: StoryCardData) => {
            setInviting(false);
            target.current = `story-event-${card.id}`;
            try {
              setMessages(await api(`/conversations/${conversation}/timeline`));
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        />
      )}
      {past && (
        <section className="panel past-activities">
          <div className="dialog-header">
            <h2>Past activities</h2>
            <button className="button" onClick={() => setPast(false)}>
              Close
            </button>
          </div>
          <p className="muted small">Activities in this conversation only.</p>
          {messages
            .filter((m): m is StoryCardData => m.kind === "story_card")
            .map((card) => (
              <StoryCard key={card.id} card={card} />
            ))}
          {!messages.some((m) => m.kind === "story_card") && (
            <p>No activities yet. Send an invitation to begin.</p>
          )}
        </section>
      )}

      <div className="chat-top">
        <Link className="back-link" href="/characters">
          ← My Characters
        </Link>
        <Link className="button" href={`${base}/edit`}>
          Edit character ↗
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
            Current profile v{character.profile_version}
            <br />
            This is a fictional AI character. Conversations are saved locally.
          </p>
          <label htmlFor="conversation">Conversation history</label>
          <select
            id="conversation"
            disabled={busy}
            value={conversation}
            onChange={(e) => switchConversation(e.target.value)}
          >
            {conversations.map((c, i) => (
              <option key={c.id} value={c.id}>
                Conversation {i + 1} ·{" "}
                {new Date(c.created_at).toLocaleDateString("en-US")}
              </option>
            ))}
          </select>
          <button
            className="button full"
            disabled={busy}
            onClick={newConversation}
          >
            ＋ New conversation
          </button>
        </aside>
        <div className="chat-main">
          <div className="chat-title">
            <span className="presence" />
            Chat with {character.profile.name} <small>AI CHARACTER</small>
          </div>
          <div className="messages" aria-live="polite">
            {messages.length === 0 && (
              <div className="chat-empty">
                <span>✧</span>
                <h2>Every story starts with hello.</h2>
                <p>Ask what is on their mind, or introduce yourself.</p>
              </div>
            )}
            {messages.map((m) =>
              m.kind === "story_card" ? (
                <StoryCard key={m.id} card={m} />
              ) : (
                <div key={m.id} className={`message ${m.role}`}>
                  <small>
                    {m.role === "user" ? "You" : character.profile.name}
                  </small>
                  <p>{m.content}</p>
                </div>
              ),
            )}
            {busy && (
              <div className="thinking" role="status">
                Waiting for a reply…
              </div>
            )}
            <div ref={bottom} />
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
              {retry && (
                <button disabled={busy} onClick={() => send(retry)}>
                  Retry this message
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
            <div className="chat-extras">
              <button
                type="button"
                className="button extras-toggle"
                aria-label="Open activities"
                aria-expanded={extras}
                disabled={busy}
                onClick={() => setExtras(!extras)}
              >
                ＋
              </button>
              {extras && (
                <div className="extras-menu">
                  <button
                    type="button"
                    onClick={() => {
                      setExtras(false);
                      setInviting(true);
                    }}
                  >
                    Do something together
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setExtras(false);
                      setPast(!past);
                    }}
                  >
                    Past activities
                  </button>
                </div>
              )}
            </div>
            <label className="sr-only" htmlFor="message">
              Message
            </label>
            <textarea
              id="message"
              rows={2}
              maxLength={4000}
              placeholder={`Say something to ${character.profile.name}…`}
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
              Send ↑
            </button>
          </form>
          {retry && (
            <div className="retry-note">
              <span>Not sent: {retry.content.slice(0, 80)}</span>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => {
                  setRetry(null);
                  setError("");
                }}
              >
                Cancel retry and edit
              </button>
            </div>
          )}
          <p className="chat-disclaimer">
            AI can make mistakes. Enter to send · Shift + Enter for a new line
          </p>
        </div>
      </section>
    </main>
  );
}
