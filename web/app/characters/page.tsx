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
        `Delete ${c.profile.name} and all conversations, profiles and images? This cannot be undone.`,
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
          <h1>Every character has a story.</h1>
          <p className="muted">
            Create someone new, or pick up where your last conversation left
            off.
          </p>
        </div>
        <Link className="button primary" href="/characters/new">
          ＋ Create Character
        </Link>
      </section>
      {error && (
        <div role="alert" className="error">
          {error} <button onClick={load}>Retry</button>
        </div>
      )}
      {loading ? (
        <p role="status">Opening your character library…</p>
      ) : !characters.length && !error ? (
        <section className="empty-state">
          <div className="empty-art">✧</div>
          <p className="eyebrow">A STORY STARTS WITH A SPARK</p>
          <h2>Who will your first character be?</h2>
          <p>
            A stargazing librarian. A sharp-tongued traveler with a gentle
            heart.
            <br />
            Bring someone from your imagination to life in a few words.
          </p>
          <Link className="button primary" href="/characters/new">
            Start creating →
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
              <p>
                {c.profile.short_description ||
                  "A story waiting to be written together."}
              </p>
              <div className="tags">
                {c.profile.personality.core_traits.slice(0, 3).map((t, i) => (
                  <span key={i}>{t}</span>
                ))}
              </div>
              <small className="muted">
                Updated {new Date(c.updated_at).toLocaleDateString("en-US")}
              </small>
              <div className="card-actions">
                <Link
                  href={`/characters/${c.id}/chat`}
                  className="button primary"
                >
                  Continue chat
                </Link>
                <Link href={`/characters/${c.id}/edit`} className="button">
                  Edit
                </Link>
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() => remove(c)}
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
