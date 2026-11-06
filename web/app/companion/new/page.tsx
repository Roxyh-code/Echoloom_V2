"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, Character, Health } from "@/components/api";
const example =
  "A mysterious librarian in her twenties with long silver hair and blue eyes. She is reserved, intelligent and slightly sarcastic, and loves astronomy. She rarely expresses affection directly, but quietly remembers her friends' preferences.";
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
      <Link className="back-link" href="/companion">
        ← Back to My Characters
      </Link>
      <div className="create-heading">
        <span className="spark">✦</span>
        <p className="eyebrow">FROM AN IDEA TO AN IDENTITY</p>
        <h1>Bring your character to life.</h1>
        <p className="muted">
          Tell us who they are: their looks, personality, history, or just a
          spark of inspiration.
          <br />
          Together, we will shape someone you can talk to.
        </p>
      </div>
      <form onSubmit={submit} className="panel create-form">
        <label htmlFor="description">Who would you like to meet?</label>
        <textarea
          id="description"
          autoFocus
          rows={8}
          maxLength={limit}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={busy}
          placeholder="Their name, appearance, personality, or a distinctive habit…"
        />
        <div className="input-footer">
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => setDescription(example)}
          >
            ✧ Try an example
          </button>
          <small>
            {description.length} / {limit}
          </small>
        </div>
        {health && !health.text_configured && (
          <p className="notice">
            The text model is not configured. Set the model and API key in the
            server .env file, then restart the backend.
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
          {busy ? "Bringing your character to life…" : "Create my character →"}
        </button>
        <p className="form-note">
          Every detail is editable. Generate a portrait whenever you are ready.
        </p>
      </form>
    </main>
  );
}
