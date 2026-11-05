"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { ActionResult, Story, StoryAction } from "./story-api";
import { statusLabel } from "./story-api";

function savedCount(story: Story) {
  let count = 0;
  for (const segment of story.segments) {
    if (segment.id === story.progress.segment_id) {
      const index = segment.blocks.findIndex(
        (b) => b.id === story.progress.last_revealed_block_id,
      );
      return count + index + 1;
    }
    count += segment.blocks.length;
  }
  return 0;
}
export function StoryReader({
  characterId,
  storyId,
}: {
  characterId: string;
  storyId: string;
}) {
  const router = useRouter();
  const [story, setStory] = useState<Story | null>(null);
  const [visible, setVisible] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [failed, setFailed] = useState<StoryAction | null>(null);
  const [input, setInput] = useState("");
  const [inputType, setInputType] = useState<
    "dialogue" | "action" | "direction"
  >("direction");
  const [rewrite, setRewrite] = useState(false);
  const [rewriteText, setRewriteText] = useState("");
  const guard = useRef(false);
  const auto = useRef(false);
  const endRef = useRef<HTMLDivElement>(null);
  const current = useRef<{ story: Story | null; visible: number }>({
    story: null,
    visible: 0,
  });
  current.current = { story, visible };
  const actionKey = `echoloom-story-action-${storyId}`;
  const draftKey = `echoloom-story-draft-${storyId}`;
  function accept(value: Story) {
    if (value.character_id !== characterId)
      throw new Error("This story does not belong to this character.");
    setStory(value);
    setVisible(savedCount(value));
  }
  async function execute(
    value: Story,
    operation: StoryAction["operation"],
    fields: Partial<StoryAction> = {},
    retry?: StoryAction,
  ) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setPlaying(false);
    setError("");
    setNotice("");
    const body = retry || {
      request_id: crypto.randomUUID(),
      expected_revision: value.revision,
      operation,
      ...fields,
    };
    sessionStorage.setItem(actionKey, JSON.stringify(body));
    setFailed(null);
    try {
      const result = await api<ActionResult>(
        `/stories/${storyId}/actions`,
        body,
      );
      accept(result.story);
      sessionStorage.removeItem(actionKey);
      setFailed(null);
      if (operation === "decide" || operation === "interject") {
        setInput("");
        sessionStorage.removeItem(draftKey);
      }
      if (operation === "rewrite") {
        setRewrite(false);
        setRewriteText("");
      }
      if (operation !== "undo") setPlaying(auto.current);
    } catch (e) {
      setError((e as Error).message);
      setFailed(body);
      try {
        accept(await api<Story>(`/stories/${storyId}`));
      } catch {
        /* Keep the last readable scene when the connection fails. */
      }
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  useEffect(() => {
    let active = true;
    auto.current = !window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches;
    try {
      setInput(sessionStorage.getItem(draftKey) || "");
    } catch {
      /* A local draft is optional. */
    }
    api<Story>(`/stories/${storyId}`)
      .then((value) => {
        if (!active) return;
        accept(value);
        let pending: StoryAction | null = null;
        try {
          pending = JSON.parse(sessionStorage.getItem(actionKey) || "null");
        } catch {
          /* Use a fresh start ID if no valid pending request exists. */
        }
        if (
          value.status === "ready" &&
          !value.segments.length &&
          !value.last_error
        ) {
          void execute(
            value,
            "start",
            {},
            pending?.operation === "start" ? pending : undefined,
          );
        } else {
          setPlaying(auto.current);
          if (value.last_error) {
            setError(value.last_error);
            setFailed(
              pending ||
                value.retry_action || {
                  request_id: crypto.randomUUID(),
                  expected_revision: value.revision,
                  operation: "start",
                },
            );
          }
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
    // The story URL defines the lifetime of a reader; requests are idempotent across remounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyId, characterId]);
  useEffect(() => {
    if (story?.status !== "generating") return;
    const timer = setInterval(() => {
      api<Story>(`/stories/${storyId}`)
        .then(accept)
        .catch(() => {});
    }, 1500);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [story?.status, storyId]);
  async function savePosition(value: Story, count: number) {
    const blocks = value.segments.flatMap((s) =>
      s.blocks.map((b) => ({ segment: s.id, block: b.id })),
    );
    const position = blocks[count - 1];
    const segmentId = position?.segment || value.segments[0]?.id;
    if (!segmentId) return;
    try {
      await api(
        `/stories/${storyId}/progress`,
        {
          expected_revision: value.revision,
          segment_id: segmentId,
          last_revealed_block_id: position?.block || null,
        },
        "PATCH",
      );
    } catch {
      setNotice(
        "Reading position could not be saved. A few blocks may replay when you return.",
      );
    }
  }
  function reveal(count: number) {
    if (!story) return;
    setVisible(count);
    void savePosition(story, count);
  }
  const blocks = story?.segments.flatMap((s) => s.blocks) || [];
  useEffect(() => {
    if (!playing || busy || !story || visible >= blocks.length) return;
    const delay = Math.max(
      1500,
      Math.min(4000, (blocks[visible]?.text.length || 0) * 22),
    );
    const timer = setTimeout(() => reveal(visible + 1), delay);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, visible, busy, story?.active_segment_id, blocks.length]);
  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: auto.current ? "smooth" : "instant",
      block: "nearest",
    });
  }, [visible]);
  useEffect(() => {
    function key(e: KeyboardEvent) {
      if ((e.target as HTMLElement).closest("input,textarea,select,button,a"))
        return;
      if (e.code === "Space") {
        e.preventDefault();
        setPlaying((v) => !v);
      }
      if (e.code === "ArrowRight") {
        const value = current.current;
        const length =
          value.story?.segments.flatMap((s) => s.blocks).length || 0;
        if (value.story && value.visible < length) {
          e.preventDefault();
          setPlaying(false);
          setVisible(value.visible + 1);
          void savePosition(value.story, value.visible + 1);
        }
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyId]);
  async function reload() {
    setError("");
    setFailed(null);
    sessionStorage.removeItem(actionKey);
    try {
      accept(await api(`/stories/${storyId}`));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!story)
    return (
      <main className="container">
        {error ? (
          <div className="error" role="alert">
            {error}
            <button onClick={reload}>Reload</button>
          </div>
        ) : (
          <p role="status">Opening your activity…</p>
        )}
      </main>
    );
  const back = `/characters/${story.character_id}/chat?conversation=${story.origin_conversation_id}&event=${story.event_id}`;
  const head = story.segments.at(-1);
  const allShown = visible >= blocks.length;
  const complete = story.status === "completed";
  const waiting = story.status === "generating";
  const disabled = busy || waiting;
  const decision = head?.ending.type === "decision" && allShown && !complete;
  const portrait = story.portrait_id
    ? `/api/characters/${story.character_id}/images/${story.portrait_id}/file`
    : null;
  let offset = 0;
  async function interject(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !head) return;
    setPlaying(false);
    if (decision)
      void execute(story!, "decide", {
        decision_id: head.ending.id,
        content: input,
        input_type: inputType,
      });
    else {
      const headStart = blocks.length - head.blocks.length;
      const count = Math.max(0, visible - headStart);
      void execute(story!, "interject", {
        content: input,
        input_type: inputType,
        revealed_block_id: head.blocks[count - 1]?.id || null,
      });
    }
  }
  return (
    <main className="container story-reader">
      <div className="chat-top">
        <Link
          className="back-link"
          href={back}
          onClick={() => {
            setPlaying(false);
            void savePosition(story, visible);
          }}
        >
          ← Back to chat
        </Link>
        <span className="story-status">
          {statusLabel[story.status]} · Revision {story.revision}
        </span>
      </div>
      <header className="story-heading">
        <div className="avatar">
          {portrait ? (
            <img
              src={portrait}
              alt={`Saved portrait of ${story.character_snapshot.name}`}
            />
          ) : (
            <span>{story.character_snapshot.name.slice(0, 1)}</span>
          )}
        </div>
        <div>
          <p className="eyebrow">AN ACTIVITY TOGETHER</p>
          <h1>{story.title}</h1>
          <p className="muted small">
            {story.player_name} &amp; {story.character_snapshot.name} · Frozen
            profile v{story.profile_version} · Fictional AI scene
          </p>
        </div>
      </header>
      <details className="panel story-setup">
        <summary>Scene and boundaries</summary>
        <p>{story.setup.description}</p>
        {story.setup.relationship && (
          <p>
            <strong>Relationship: </strong>
            {story.setup.relationship}
          </p>
        )}
        {story.setup.atmosphere && (
          <p>
            <strong>Atmosphere: </strong>
            {story.setup.atmosphere}
          </p>
        )}
        {story.setup.constraints && (
          <p>
            <strong>Avoid: </strong>
            {story.setup.constraints}
          </p>
        )}
      </details>
      {error && (
        <div className="error" role="alert">
          {error}
          <div className="actions">
            {failed && (
              <button
                disabled={disabled}
                onClick={() => execute(story, failed.operation, {}, failed)}
              >
                Retry
              </button>
            )}
            <button disabled={disabled} onClick={reload}>
              Reload latest
            </button>
          </div>
        </div>
      )}
      {(busy || waiting) && (
        <p className="notice" role="status">
          Preparing the next scene… Your saved story is kept safe.
        </p>
      )}
      {notice && <p className="notice">{notice}</p>}
      {head && (
        <div className="playback-toolbar" aria-label="Reading controls">
          <button
            className="button"
            disabled={disabled || allShown}
            onClick={() => {
              auto.current = !playing;
              setPlaying(!playing);
            }}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button
            className="button"
            disabled={disabled || allShown}
            onClick={() => {
              setPlaying(false);
              reveal(visible + 1);
            }}
          >
            Next
          </button>
          <button
            className="button"
            disabled={disabled || allShown}
            onClick={() => {
              setPlaying(false);
              reveal(blocks.length);
            }}
          >
            Show all
          </button>
          <span className="muted small">
            {Math.min(visible, blocks.length)} / {blocks.length} blocks
          </span>
        </div>
      )}
      <section
        className="story-transcript"
        aria-live="polite"
        aria-label="Story scene"
      >
        {story.segments.map((segment) => {
          const start = offset;
          offset += segment.blocks.length;
          const shown = segment.blocks.slice(0, Math.max(0, visible - start));
          return (
            <section className="story-segment" key={segment.id}>
              {shown.map((block) => (
                <div
                  key={block.id}
                  className={`story-block ${block.type} ${block.speaker || ""}`}
                >
                  {block.speaker && (
                    <small>
                      {block.speaker === "character"
                        ? story.character_snapshot.name
                        : story.player_name}{" "}
                      <span className="source-label">
                        {block.source === "user"
                          ? "Your input"
                          : block.speaker === "player"
                            ? "AI-assisted"
                            : "AI"}
                      </span>
                    </small>
                  )}
                  <p>{block.text}</p>
                </div>
              ))}
              {shown.length === segment.blocks.length &&
                segment.ending.selected_option_id && (
                  <p className="decision-history">
                    Your choice:{" "}
                    {
                      segment.ending.options?.find(
                        (o) => o.id === segment.ending.selected_option_id,
                      )?.intent
                    }
                  </p>
                )}
            </section>
          );
        })}
        <div ref={endRef} />
      </section>
      {decision && (
        <section className="panel decision-card">
          <p className="eyebrow">YOUR DECISION</p>
          <h2>{head.ending.question}</h2>
          <div className="decision-options">
            {head.ending.options?.map((option) => (
              <button
                className="button"
                key={option.id}
                disabled={disabled}
                onClick={() =>
                  execute(story, "decide", {
                    decision_id: head.ending.id,
                    option_id: option.id,
                  })
                }
              >
                {option.intent}
              </button>
            ))}
          </div>
          <p className="muted small">
            Or write your own response below. Nothing is chosen automatically.
          </p>
        </section>
      )}
      {head && allShown && head.ending.type === "continue" && !complete && (
        <button
          className="button primary"
          disabled={disabled}
          onClick={() => execute(story, "continue")}
        >
          Continue story →
        </button>
      )}
      {!complete && head && (
        <form className="panel story-interject" onSubmit={interject}>
          <h2>
            {decision
              ? "Respond in your own way"
              : "Speak up or redirect the scene"}
          </h2>
          <p className="muted small">
            Typing pauses playback. If you interrupt mid-scene, unread content
            is replaced only after the new scene saves successfully.
          </p>
          <label htmlFor="story-input-type">Contribution type</label>
          <select
            id="story-input-type"
            value={inputType}
            disabled={disabled}
            onChange={(e) => setInputType(e.target.value as typeof inputType)}
          >
            <option value="direction">Direction</option>
            <option value="dialogue">My dialogue</option>
            <option value="action">My action</option>
          </select>
          <label htmlFor="story-input">Your contribution</label>
          <textarea
            id="story-input"
            rows={3}
            maxLength={2000}
            value={input}
            disabled={disabled}
            onFocus={() => setPlaying(false)}
            onChange={(e) => {
              setInput(e.target.value);
              sessionStorage.setItem(draftKey, e.target.value);
            }}
            placeholder="Say something, take an action, or ask for a slower pace…"
          />
          <button
            className="button primary"
            disabled={disabled || !input.trim()}
          >
            {decision ? "Respond" : "Contribute"}
          </button>
        </form>
      )}
      {!complete && head && (
        <div className="story-management">
          <button
            className="button"
            disabled={disabled}
            onClick={() => {
              setPlaying(false);
              setRewrite(!rewrite);
            }}
          >
            Rewrite latest segment
          </button>
          <button
            className="button"
            disabled={disabled || !story.can_undo}
            onClick={() => {
              if (
                confirm(
                  "Undo the latest decision and remove its consequences from the active story?",
                )
              )
                void execute(story, "undo");
            }}
          >
            Undo last decision
          </button>
          <button
            className="button"
            disabled={disabled}
            onClick={() => {
              if (confirm("Write a short closing scene and end this story?"))
                void execute(story, "end");
            }}
          >
            End story
          </button>
          <button
            className="text-button"
            disabled={disabled}
            onClick={() => {
              if (
                confirm(
                  "End now without generating a closing scene? Saved content will remain available.",
                )
              )
                void execute(story, "end", { skip_generation: true });
            }}
          >
            End without epilogue
          </button>
        </div>
      )}
      {rewrite && !complete && (
        <form
          className="panel"
          onSubmit={(e) => {
            e.preventDefault();
            void execute(story, "rewrite", { content: rewriteText });
          }}
        >
          <label htmlFor="rewrite-instruction">
            How should this segment change?
          </label>
          <textarea
            id="rewrite-instruction"
            rows={3}
            maxLength={2000}
            value={rewriteText}
            onChange={(e) => setRewriteText(e.target.value)}
            disabled={disabled}
          />
          <p className="muted small">
            Only the latest segment is replaced. If generation fails, the
            original stays active.
          </p>
          <button
            className="button primary"
            disabled={disabled || !rewriteText.trim()}
          >
            Rewrite segment
          </button>
        </form>
      )}
      {!complete && !head && !disabled && (
        <button
          className="button"
          onClick={() => {
            if (confirm("End this activity without generating a scene?"))
              void execute(story, "end", { skip_generation: true });
          }}
        >
          End without a scene
        </button>
      )}
      {complete && (
        <section className="panel">
          <h2>This story is complete.</h2>
          <p className="muted">
            You can revisit the saved scene or start a new invitation from chat.
          </p>
          <Link className="button primary" href={`${back}&invite=1`}>
            Start another activity
          </Link>
        </section>
      )}
      <div className="story-delete">
        <button
          className="text-button danger"
          disabled={disabled}
          onClick={async () => {
            if (
              !confirm(
                "Delete this story and its revisions? Its chat card will remain as a deleted placeholder.",
              )
            )
              return;
            setPlaying(false);
            try {
              await api(`/stories/${storyId}`, undefined, "DELETE");
              router.push(back);
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Delete story
        </button>
      </div>
    </main>
  );
}
