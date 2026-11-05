"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, Avatar, Character } from "./api";
import type { StoryCardData } from "./story-api";
type Draft = {
  description: string;
  player_name: string;
  relationship: string;
  atmosphere: string;
  constraints: string;
};
export function StoryInvitation({
  character,
  conversation,
  onClose,
  onCreated,
}: {
  character: Character;
  conversation: string;
  onClose: () => void;
  onCreated: (card: StoryCardData) => void;
}) {
  const key = `echoloom-invitation-${conversation}`;
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const guard = useRef(false);
  const [draft, setDraft] = useState<Draft>({
    description: "",
    player_name: "You",
    relationship:
      character.profile.interaction_preferences.relationship_context || "",
    atmosphere: "",
    constraints: "",
  });
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    try {
      const saved = sessionStorage.getItem(key);
      if (saved) setDraft(JSON.parse(saved));
    } catch {
      /* Ignore unavailable or invalid local drafts. */
    }
    setLoaded(true);
    dialog.current?.showModal();
    input.current?.focus();
    return () => {
      // Wait until the modal has been removed so outside controls are no longer inert.
      requestAnimationFrame(() => {
        const visibleEntry =
          document.querySelector<HTMLButtonElement>(".activity-invite");
        if (visibleEntry) visibleEntry.focus();
        else if (trigger?.isConnected && trigger.tagName === "BUTTON")
          trigger.focus();
      });
    };
  }, [key]);
  useEffect(() => {
    if (loaded) sessionStorage.setItem(key, JSON.stringify(draft));
  }, [draft, key, loaded]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (guard.current || !draft.description.trim()) return;
    guard.current = true;
    setBusy(true);
    setError("");
    const data = {
      ...draft,
      player_name: draft.player_name.trim() || "You",
      conversation_id: conversation,
    };
    const payload = JSON.stringify(data);
    let request_id = crypto.randomUUID();
    try {
      const saved = JSON.parse(
        sessionStorage.getItem(`${key}-request`) || "null",
      );
      if (saved?.payload === payload) request_id = saved.request_id;
    } catch {
      /* Start a fresh request when no usable pending request exists. */
    }
    sessionStorage.setItem(
      `${key}-request`,
      JSON.stringify({ payload, request_id }),
    );
    try {
      const result = await api<{ card: StoryCardData }>(
        `/characters/${character.id}/stories`,
        { ...data, request_id },
      );
      sessionStorage.removeItem(key);
      sessionStorage.removeItem(`${key}-request`);
      onCreated(result.card);
    } catch (e) {
      setError((e as Error).message);
      guard.current = false;
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="story-dialog"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="invitation-title"
    >
      <div className="dialog-header">
        <div className="actions">
          <Avatar character={character} />
          <span>{character.profile.name}</span>
        </div>
        <button
          className="icon-button"
          type="button"
          aria-label="Close invitation"
          disabled={busy}
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <h2 id="invitation-title">
        What would you like to do with {character.profile.name}?
      </h2>
      <p className="muted small">
        AI helps with everyday dialogue. Important decisions are yours. You can
        speak up or redirect the scene at any time.
      </p>
      <form onSubmit={submit}>
        <label htmlFor="story-description">Your scene</label>
        <textarea
          ref={input}
          id="story-description"
          required
          maxLength={2000}
          rows={4}
          placeholder="We are old friends meeting in a bookshop on a rainy evening…"
          value={draft.description}
          disabled={busy}
          onChange={(e) => setDraft({ ...draft, description: e.target.value })}
        />
        <small className="muted">{draft.description.length} / 2,000</small>
        <label htmlFor="story-player">Your name in the story</label>
        <input
          id="story-player"
          maxLength={100}
          value={draft.player_name}
          disabled={busy}
          onChange={(e) => setDraft({ ...draft, player_name: e.target.value })}
        />
        <label htmlFor="story-relationship">
          Relationship context (optional)
        </label>
        <textarea
          id="story-relationship"
          maxLength={500}
          rows={2}
          value={draft.relationship}
          disabled={busy}
          onChange={(e) => setDraft({ ...draft, relationship: e.target.value })}
        />
        <label htmlFor="story-atmosphere">Atmosphere (optional)</label>
        <input
          id="story-atmosphere"
          maxLength={100}
          placeholder="Everyday, tender, mysterious, adventurous…"
          value={draft.atmosphere}
          disabled={busy}
          onChange={(e) => setDraft({ ...draft, atmosphere: e.target.value })}
        />
        <details>
          <summary>Anything to avoid? (optional)</summary>
          <label htmlFor="story-constraints" className="sr-only">
            Content to avoid
          </label>
          <textarea
            id="story-constraints"
            maxLength={500}
            rows={2}
            value={draft.constraints}
            disabled={busy}
            onChange={(e) =>
              setDraft({ ...draft, constraints: e.target.value })
            }
          />
        </details>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="actions">
          <button
            className="button primary"
            disabled={busy || !draft.description.trim()}
          >
            {busy ? "Sending invitation…" : "Send invitation"}
          </button>
          <button
            type="button"
            className="button"
            disabled={busy}
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
        <p className="form-note">
          This adds a scene card to this conversation. AI generation starts only
          when you open the card.
        </p>
      </form>
    </dialog>
  );
}
