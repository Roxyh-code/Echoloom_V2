"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, Health, Profile, Portrait, Proposal } from "./api";
import {
  Block,
  chain,
  Checkpoint,
  creator,
  CreatorCharacter,
  Document as StoryDocument,
  download,
  Line,
  Member,
  Moment,
  Fact,
  Work,
} from "./creator-api";

type Screen =
  | "home"
  | "characters"
  | "stories"
  | "character"
  | "overview"
  | "reader"
  | "lines"
  | "scenes"
  | "compare"
  | "saved"
  | "notes";
type Sheet =
  | "create"
  | "profile"
  | "refine"
  | "portrait"
  | "setup"
  | "save"
  | "fork"
  | "scene"
  | "edit"
  | "rewrite"
  | "fact"
  | "export"
  | "settings"
  | "rename"
  | "rules"
  | "source"
  | null;
const premise =
  "A rainy station, 23:02. Leo has discovered Mira’s one-way ticket. The last train leaves at 23:10. He does not know about her residency offer.";
const id = () => crypto.randomUUID();
function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: "M3 10l9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z",
    people:
      "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m13 10v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
    book: "M4 3h6a3 3 0 0 1 3 3v15a4 4 0 0 0-4-2H4zM13 6a3 3 0 0 1 3-3h5v16h-4a4 4 0 0 0-4 2",
    spark: "M12 3l2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3z",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.spark} />
    </svg>
  );
}
function SheetPanel({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => {
      if (trigger?.isConnected) requestAnimationFrame(() => trigger.focus());
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="cr-sheet"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <div className="cr-sheet-handle" />
      <header>
        <h2>{title}</h2>
        <button className="cr-icon" aria-label="Close panel" onClick={close}>
          ×
        </button>
      </header>
      {children}
    </dialog>
  );
}
function Face({
  member,
  character,
  large = false,
}: {
  member?: Member;
  character?: CreatorCharacter;
  large?: boolean;
}) {
  const url =
    member?.portrait_url ||
    (character?.current_image_id
      ? `/api/characters/${character.id}/images/${character.current_image_id}/file`
      : null);
  const name = member?.profile.name || character?.profile.name || "You";
  return (
    <div className={"cr-face" + (large ? " large" : "")}>
      {url ? (
        <img
          src={url}
          alt={`Portrait of ${name}`}
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      ) : (
        <span>{name.slice(0, 1)}</span>
      )}
    </div>
  );
}

export function CreatorApp() {
  const [screen, setScreen] = useState<Screen>("home");
  const [sheet, setSheet] = useState<Sheet>(null);
  const [characters, setCharacters] = useState<CreatorCharacter[]>([]);
  const [works, setWorks] = useState<Work[]>([]);
  const [character, setCharacter] = useState<CreatorCharacter | null>(null);
  const [work, setWork] = useState<Work | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [direction, setDirection] = useState("");
  const [inputType, setInputType] = useState("direction");
  const creationGuard = useRef(false);
  const screenRef = useRef(screen);
  screenRef.current = screen;
  const characterRef = useRef(character);
  characterRef.current = character;
  const [moment, setMoment] = useState<Moment | null>(null);
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null);
  const [compare, setCompare] = useState("");
  const [portraits, setPortraits] = useState<Portrait[]>([]);
  const [editingFact, setEditingFact] = useState<Fact | null>(null);
  const [setupDraft, setSetupDraft] = useState<Record<string, string>>({});
  const returnToSetup = useRef(false);
  const [exportScope, setExportScope] = useState("storyline");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [exportText, setExportText] = useState("");
  const [exportFormat, setExportFormat] = useState("script");
  const [job, setJob] = useState<{
    request_id: string;
    description: string;
  } | null>(null);
  const [imageError, setImageError] = useState("");
  const [setupMode, setSetupMode] = useState("play");
  const [showArchived, setShowArchived] = useState(false);
  const current = useRef<Work | null>(null);
  current.current = work;
  const guard = useRef(false);
  const scroll = useRef<HTMLDivElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const follow = useRef(true);
  const controller = useRef<AbortController | null>(null);
  const retry = useRef<{ wid: string; body: Record<string, unknown> } | null>(
    null,
  );
  const draftKey = work
    ? `echoloom-creator-draft:${work.id}:${work.document.active_line}`
    : "";
  const d = work?.document;
  const line = d?.lines[d.active_line];
  const moments = d && line ? chain(d, line.head) : [];
  const total = moments.reduce((n, m) => n + m.blocks.length, 0);
  const revealed = line?.revealed || 0;
  const members = d && line ? d.casts[line.cast_id] : [];
  function go(next: Screen, wid?: string, cid?: string) {
    setScreen(next);
    setError("");
    setCheckpoint(null);
    const q = new URLSearchParams({ screen: next });
    if (
      wid ||
      (current.current?.id &&
        [
          "overview",
          "reader",
          "lines",
          "scenes",
          "compare",
          "saved",
          "notes",
        ].includes(next))
    )
      q.set("story", wid || current.current!.id);
    if (cid) q.set("character", cid);
    history.pushState(null, "", `/creator?${q}`);
    scroll.current?.scrollTo(0, 0);
  }
  async function refresh() {
    const [cs, ws] = await Promise.all([
      creator<CreatorCharacter[]>(`/characters?archived=${showArchived}`),
      creator<Work[]>("/works"),
    ]);
    setCharacters(cs);
    setWorks(ws);
    return cs;
  }
  function accept(w: Work) {
    current.current = w;
    setWork(w);
    setWorks((old) => [w, ...old.filter((x) => x.id !== w.id)]);
  }
  useEffect(() => {
    const viewport = window.visualViewport;
    const resize = () =>
      document.documentElement.style.setProperty(
        "--creator-vh",
        `${viewport?.height || window.innerHeight}px`,
      );
    resize();
    viewport?.addEventListener("resize", resize);
    window.addEventListener("resize", resize);
    return () => {
      viewport?.removeEventListener("resize", resize);
      window.removeEventListener("resize", resize);
      document.documentElement.style.removeProperty("--creator-vh");
    };
  }, []);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const h = await api<Health>("/health");
        if (h.creator_database_ready === false)
          throw new Error(
            "Creator database needs an upgrade. Run alembic upgrade head, then reload.",
          );
        await refresh();
        if (active) setHealth(h);
        const q = new URLSearchParams(location.search);
        const wid = q.get("story"),
          cid = q.get("character");
        if (wid) {
          const w = await creator<Work>(`/works/${wid}`);
          if (active) {
            accept(w);
            try {
              const pending = localStorage.getItem(`creator-pending:${wid}`);
              if (pending) {
                const op = JSON.parse(pending);
                retry.current = { wid, body: op };
                const r = await creator<{
                  status: string;
                  result?: { detail?: string };
                }>(`/jobs/${op.request_id}`);
                if (r.status === "succeeded") {
                  localStorage.removeItem(`creator-pending:${wid}`);
                  retry.current = null;
                  accept(await creator<Work>(`/works/${wid}`));
                } else if (active)
                  setNotice(
                    r.status === "failed"
                      ? "The last action did not finish. Your previous draft is safe."
                      : "A previous request may still be running. Retry to check its saved result.",
                  );
              }
            } catch {
              /* The previous action can still be reviewed before retrying. */
            }
            const saved = q.get("checkpoint");
            if (saved)
              setCheckpoint(
                w.document.checkpoints.find((c) => c.id === saved) || null,
              );
          }
        }
        if (cid) {
          const c = await api<CreatorCharacter>(`/characters/${cid}`);
          if (active) setCharacter(c);
        }
        if (active) setScreen((q.get("screen") as Screen) || "home");
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    }
    try {
      const saved = localStorage.getItem("echoloom-creator-creation");
      if (saved) setJob(JSON.parse(saved));
    } catch {
      /* No recoverable creation. */
    }
    void load();
    const pop = () => void load();
    window.addEventListener("popstate", pop);
    return () => {
      active = false;
      window.removeEventListener("popstate", pop);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    try {
      setDirection(draftKey ? localStorage.getItem(draftKey) || "" : "");
    } catch {
      setNotice(
        "Device drafts are unavailable. Save or export before leaving.",
      );
    }
  }, [draftKey]);
  useEffect(() => {
    if (screen === "reader" && follow.current)
      end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [revealed, screen]);
  useEffect(() => {
    if (sheet === "portrait" && character)
      void api<Portrait[]>(`/characters/${character.id}/images`)
        .then(setPortraits)
        .catch((e) => setError(e.message));
  }, [sheet, character]);
  useEffect(() => {
    if (!job) return;
    let active = true;
    const timer = setInterval(async () => {
      try {
        const r = await creator<{
          status: string;
          result?: {
            character_id?: string;
            phase?: string;
            detail?: string;
            image_error?: string;
          };
        }>(`/jobs/${job.request_id}`);
        if (active && r.result?.character_id) {
          const c = await api<CreatorCharacter>(
            `/characters/${r.result.character_id}`,
          );
          if (
            active &&
            screenRef.current === "character" &&
            (!characterRef.current || characterRef.current.id === c.id)
          )
            setCharacter(c);
          if (active)
            setCharacters((old) => [c, ...old.filter((x) => x.id !== c.id)]);
          if (active && r.status === "succeeded") {
            setImageError(r.result?.image_error || "");
            setJob(null);
            try {
              localStorage.removeItem("echoloom-creator-creation");
            } catch {}
          }
        }
      } catch {
        /* The original request remains retryable. */
      }
    }, 1500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [job]);
  function draft(text: string) {
    setDirection(text);
    try {
      localStorage.setItem(draftKey, text);
    } catch {
      setNotice("Device draft could not be saved.");
    }
  }
  async function task(fn: () => Promise<void>) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  async function act(
    operation: string,
    fields: Record<string, unknown> = {},
    target?: Work,
  ): Promise<Work | null> {
    if (guard.current) return null;
    const w = target || current.current;
    if (!w) return null;
    guard.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    const body = {
      request_id: id(),
      expected_revision: w.revision,
      operation,
      ...fields,
    };
    retry.current = { wid: w.id, body };
    try {
      localStorage.setItem(`creator-pending:${w.id}`, JSON.stringify(body));
    } catch {
      /* The server still stores the request ID. */
    }
    controller.current = new AbortController();
    try {
      const response = await fetch(`/api/creator/works/${w.id}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.current.signal,
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Check your input and try again.",
        );
      if (current.current?.id === w.id) {
        accept(result);
        if (
          ["fact", "rename", "restore", "setup", "finish"].includes(operation)
        )
          setNotice("Saved");
      }
      retry.current = null;
      try {
        localStorage.removeItem(`creator-pending:${w.id}`);
      } catch {}
      return result;
    } catch (e) {
      if ((e as Error).name === "AbortError")
        setNotice("Stopped waiting. The original story may finish saving.");
      else {
        setError((e as Error).message);
        if ((e as Error).message.includes("another window")) {
          try {
            retry.current = null;
            localStorage.removeItem(`creator-pending:${w.id}`);
            accept(await creator<Work>(`/works/${w.id}`));
          } catch {
            /* Keep the current draft. */
          }
        }
      }
      return null;
    } finally {
      guard.current = false;
      setBusy(false);
      controller.current = null;
    }
  }
  async function retryAction() {
    const r = retry.current;
    if (!r) return;
    await task(async () => {
      const result = await creator<Work>(`/works/${r.wid}/actions`, r.body);
      if (current.current?.id === r.wid) accept(result);
      retry.current = null;
      try {
        localStorage.removeItem(`creator-pending:${r.wid}`);
      } catch {}
      setNotice("Saved");
    });
  }
  async function openWork(w: Work, next: Screen = "overview") {
    accept(w);
    go(next, w.id);
  }
  async function demo() {
    await task(async () => {
      const w = await creator<Work>("/works", {
        request_id: id(),
        demo: true,
        mode: "direct",
        premise,
        title: "The Last Train",
      });
      accept(w);
      go("overview", w.id);
    });
  }
  async function createCharacter(
    description: string,
    previous?: { request_id: string; description: string },
  ) {
    if (creationGuard.current) return;
    creationGuard.current = true;
    const pending = previous || { request_id: id(), description };
    setJob(pending);
    setImageError("");
    setSheet(null);
    setCharacter(null);
    go("character");
    setError("");
    try {
      try {
        localStorage.setItem(
          "echoloom-creator-creation",
          JSON.stringify(pending),
        );
      } catch {
        setNotice(
          "Device draft storage is unavailable; the server request is still saved.",
        );
      }
      const r = await creator<{
        character_id: string;
        phase: string;
        image_error?: string;
      }>("/characters", pending);
      const c = await api<CreatorCharacter>(`/characters/${r.character_id}`);
      if (
        screenRef.current === "character" &&
        (!characterRef.current || characterRef.current.id === c.id)
      ) {
        setCharacter(c);
        setImageError(r.image_error || "");
        history.replaceState(
          null,
          "",
          `/creator?screen=character&character=${c.id}`,
        );
      }
      await refresh();
      try {
        localStorage.removeItem("echoloom-creator-creation");
      } catch {}
      setJob(null);
      if (returnToSetup.current) {
        returnToSetup.current = false;
        setSetupDraft((old) => ({ ...old, second: c.id }));
        setSetupMode("direct");
        setSheet("setup");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      creationGuard.current = false;
    }
  }
  function openSetup() {
    let saved: Record<string, string> = {
      first: character?.id || "",
      mode: "play",
    };
    try {
      const raw = sessionStorage.getItem(`creator-setup:${character?.id}`);
      if (raw) saved = JSON.parse(raw);
    } catch {}
    setSetupDraft(saved);
    setSetupMode(saved.mode || "play");
    setSheet("setup");
  }
  function rememberSetup(form: HTMLFormElement) {
    const data = Object.fromEntries(new FormData(form).entries()) as Record<
      string,
      string
    >;
    data.mode = setupMode;
    setSetupDraft(data);
    try {
      sessionStorage.setItem(
        `creator-setup:${data.first}`,
        JSON.stringify(data),
      );
    } catch {}
  }
  async function startStory(form: FormData) {
    let created: Work | undefined;
    await task(async () => {
      const ids = [
        String(form.get("first") || character?.id || ""),
        ...(setupMode === "direct" ? [String(form.get("second") || "")] : []),
      ];
      const w = await creator<Work>("/works", {
        request_id: id(),
        title: String(form.get("title") || ""),
        premise: String(form.get("premise") || ""),
        character_ids: ids,
        mode: setupMode,
        player_name: String(form.get("player") || "You"),
        player_description: field(form, "player_description"),
        location: field(form, "location"),
        time: field(form, "time"),
        atmosphere: field(form, "atmosphere"),
        boundaries: field(form, "boundaries"),
        world_rules: field(form, "world_rules"),
      });
      created = w;
      accept(w);
      setSheet(null);
      go("reader", w.id);
      try {
        sessionStorage.removeItem(`creator-setup:${form.get("first")}`);
      } catch {}
    });
    if (created) await act("continue", {}, created);
  }
  function field(form: FormData, key: string) {
    return String(form.get(key) || "").trim();
  }
  const storyScreens = [
    "overview",
    "reader",
    "lines",
    "scenes",
    "compare",
    "saved",
    "notes",
  ];
  const title =
    screen === "home"
      ? "EchoLoom"
      : screen === "characters"
        ? "Your characters"
        : screen === "stories"
          ? "Your stories"
          : screen === "character"
            ? character?.profile.name || "Creating character"
            : d?.title || "EchoLoom";
  const busyText = job
    ? character
      ? "Creating portrait…"
      : "Creating character…"
    : "Exploring…";
  return (
    <main className="creator-app">
      <header className="cr-top">
        <button
          className="cr-icon"
          aria-label={screen === "home" ? "Creator settings" : "Back"}
          onClick={() =>
            screen === "home"
              ? setSheet("settings")
              : go(
                  storyScreens.includes(screen) && screen !== "overview"
                    ? "overview"
                    : "home",
                )
          }
        >
          {screen === "home" ? <Icon name="spark" /> : "‹"}
        </button>
        <div>
          {screen === "home" ? (
            <>
              <span className="cr-brand">EchoLoom</span>
              <small>CHARACTER-DRIVEN STORIES</small>
            </>
          ) : (
            <>
              <span className="cr-top-title">{title}</span>
              <small>
                {d && storyScreens.includes(screen)
                  ? `${d.demo ? "DEMO MODE" : "LIVE AI"} · ${line?.name}`
                  : "YOUR CREATIVE SPACE"}
              </small>
            </>
          )}
        </div>
        <button
          className="cr-icon"
          aria-label="More options"
          onClick={() => setSheet("settings")}
        >
          ⋯
        </button>
      </header>
      {(error || notice) && (
        <div
          className={error ? "cr-alert" : "cr-notice"}
          role={error ? "alert" : "status"}
        >
          {error || notice}
          {error && retry.current && (
            <button onClick={retryAction} disabled={busy}>
              Retry
            </button>
          )}
          <button
            aria-label="Dismiss message"
            onClick={() => {
              setError("");
              setNotice("");
            }}
          >
            ×
          </button>
        </div>
      )}
      <div
        ref={scroll}
        className="cr-scroll"
        onScroll={(e) => {
          const x = e.currentTarget;
          follow.current = x.scrollHeight - x.scrollTop - x.clientHeight < 160;
        }}
      >
        {loading ? (
          <div className="cr-empty">
            <Icon name="spark" />
            <h2>Opening your studio…</h2>
          </div>
        ) : (
          <>
            {screen === "home" && (
              <>
                <section className="cr-hero">
                  <span className="cr-eyebrow">
                    EVERY STORY STARTS WITH SOMEONE
                  </span>
                  <h1>
                    Create characters.
                    <br />
                    <em>Discover their stories.</em>
                  </h1>
                  <p>
                    A personality. A first encounter.
                    <br />A story only you could shape.
                  </p>
                  <button
                    className="cr-btn gold"
                    onClick={() => {
                      setCharacter(null);
                      setSheet("create");
                    }}
                  >
                    <Icon name="spark" />
                    Create character <span>→</span>
                  </button>
                  <div className="cr-hero-art" aria-hidden="true">
                    <span className="cr-moon" />
                    <span className="cr-orbit" />
                    <img src="/creator/station.svg" alt="" />
                  </div>
                </section>
                <div className="cr-section-head">
                  <h2>Pick up the thread</h2>
                  <button onClick={() => go("stories")}>All stories →</button>
                </div>
                {works
                  .filter((w) => !w.document.archived)
                  .slice(0, 2)
                  .map((w) => (
                    <StoryCard key={w.id} w={w} onClick={() => openWork(w)} />
                  ))}
                {!works.length && (
                  <div className="cr-soft-card">
                    <p>Your next story starts with a character.</p>
                    <span className="cr-muted">
                      Create someone original, or explore the example below.
                    </span>
                  </div>
                )}
                <button className="cr-example" disabled={busy} onClick={demo}>
                  <img
                    src="/creator/station.svg"
                    alt="Rain at a railway station"
                  />
                  <div>
                    <span className="cr-eyebrow">TRY AN EXAMPLE · DEMO</span>
                    <h2>The Last Train</h2>
                    <p>
                      Two siblings. One ticket.
                      <br />
                      Eight minutes to tell the truth.
                    </p>
                    <span className="cr-text-link">Explore their story →</span>
                  </div>
                </button>
                <div className="cr-section-head">
                  <h2>Your cast</h2>
                  <button onClick={() => go("characters")}>View all →</button>
                </div>
                <div className="cr-cast-strip">
                  {characters.slice(0, 4).map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setCharacter(c);
                        go("character", undefined, c.id);
                      }}
                    >
                      <Face character={c} />
                      <strong>{c.profile.name}</strong>
                    </button>
                  ))}
                  <button
                    className="cr-add-character"
                    onClick={() => {
                      setCharacter(null);
                      setSheet("create");
                    }}
                  >
                    <span>＋</span>
                    <strong>Someone new</strong>
                  </button>
                </div>
              </>
            )}
            {screen === "characters" && (
              <>
                <div className="cr-page-heading">
                  <span className="cr-eyebrow">
                    THE PEOPLE WHO MOVE THE PLOT
                  </span>
                  <h1>
                    Your cast,
                    <br />
                    <em>full of possibility.</em>
                  </h1>
                  <button
                    className="cr-btn gold"
                    onClick={() => {
                      setCharacter(null);
                      setSheet("create");
                    }}
                  >
                    ＋ Create character
                  </button>
                </div>
                <div className="cr-filter">
                  <button
                    onClick={async () => {
                      const next = !showArchived;
                      setShowArchived(next);
                      setCharacters(
                        await creator(`/characters?archived=${next}`),
                      );
                    }}
                  >
                    {showArchived ? "Show active characters" : "Show archived"}
                  </button>
                </div>
                <div className="cr-character-grid">
                  {characters.map((c) => (
                    <button
                      className="cr-character-card"
                      key={c.id}
                      onClick={() => {
                        setCharacter(c);
                        go("character", undefined, c.id);
                      }}
                    >
                      <Face character={c} large />
                      <div>
                        <h2>{c.profile.name}</h2>
                        <p>{c.profile.short_description}</p>
                      </div>
                    </button>
                  ))}
                </div>
                {!characters.length && (
                  <div className="cr-empty">
                    <h2>Someone worth writing.</h2>
                    <p>Describe a character. Their portrait comes with them.</p>
                  </div>
                )}
              </>
            )}
            {screen === "stories" && (
              <>
                <div className="cr-page-heading">
                  <span className="cr-eyebrow">
                    EVERY POSSIBILITY HAS A PLACE
                  </span>
                  <h1>
                    Stories to
                    <br />
                    <em>come back to.</em>
                  </h1>
                </div>
                <div className="cr-filter">
                  <button onClick={() => setShowArchived(!showArchived)}>
                    {showArchived ? "Show in progress" : "Show archived"}
                  </button>
                  <button onClick={() => go("characters")}>
                    ＋ Start a story
                  </button>
                </div>
                {works
                  .filter((w) => w.document.archived === showArchived)
                  .map((w) => (
                    <StoryCard key={w.id} w={w} onClick={() => openWork(w)} />
                  ))}
                {!works.length && (
                  <div className="cr-empty">
                    <h2>A first scene is waiting.</h2>
                    <button className="cr-btn" onClick={demo}>
                      Try The Last Train
                    </button>
                  </div>
                )}
              </>
            )}
            {screen === "character" && (
              <>
                {character ? (
                  <>
                    <section className="cr-character-hero">
                      <Face character={character} large />
                      <div>
                        <span className="cr-eyebrow">
                          CHARACTER · VERSION {character.profile_version}
                        </span>
                        <h1>{character.profile.name}</h1>
                        <p>{character.profile.short_description}</p>
                      </div>
                      <button
                        className="cr-icon cr-portrait-edit"
                        aria-label="Edit portrait"
                        onClick={() => setSheet("portrait")}
                      >
                        ✎
                      </button>
                    </section>
                    {job && (
                      <p className="cr-status" role="status">
                        Creating portrait… Your character is saved.
                      </p>
                    )}
                    {imageError && (
                      <div className="cr-alert">
                        Portrait unavailable. Your character is ready.
                        <button onClick={() => setSheet("portrait")}>
                          Retry portrait
                        </button>
                      </div>
                    )}
                    <div className="cr-pad">
                      <button
                        className="cr-btn gold full"
                        disabled={busy && !job}
                        onClick={() => {
                          openSetup();
                        }}
                      >
                        Start a story <span>→</span>
                      </button>
                      <button
                        className="cr-btn secondary full"
                        disabled={busy}
                        onClick={() => setSheet("profile")}
                      >
                        Edit character
                      </button>
                      <div className="cr-tags">
                        {character.profile.personality.core_traits.map((t) => (
                          <span key={t}>{t}</span>
                        ))}
                      </div>
                      <CharacterDetail character={character} />
                      <button
                        className="cr-text-link"
                        onClick={() => {
                          setProposal(null);
                          setSheet("refine");
                        }}
                      >
                        Adjust with a few words →
                      </button>
                      <details className="cr-details">
                        <summary>Character options</summary>
                        <button
                          className="cr-btn secondary full"
                          disabled={busy}
                          onClick={() =>
                            task(async () => {
                              const c = await creator<CreatorCharacter>(
                                `/characters/${character.id}/duplicate`,
                                { request_id: id() },
                              );
                              setCharacter(c);
                              await refresh();
                              go("character", undefined, c.id);
                            })
                          }
                        >
                          Duplicate character
                        </button>
                        <p>
                          Stories keep their own snapshots when this character
                          changes.
                        </p>
                        <button
                          className="cr-btn secondary full"
                          onClick={() =>
                            task(async () => {
                              await creator(
                                `/characters/${character.id}/archive`,
                                {},
                                "PATCH",
                              );
                              await refresh();
                              go("characters");
                            })
                          }
                        >
                          {character.archived
                            ? "Unarchive character"
                            : "Archive character"}
                        </button>
                        <Link
                          className="cr-text-link"
                          href={`/characters/${character.id}/edit`}
                        >
                          Open full profile & history →
                        </Link>
                      </details>
                    </div>
                  </>
                ) : (
                  <div className="cr-empty">
                    <Icon name="spark" />
                    <h2>
                      {job ? "Creating someone new…" : "Create your character"}
                    </h2>
                    <p>
                      {job
                        ? "Your description is safe. The portrait follows automatically."
                        : "One description, a character and a portrait."}
                    </p>
                    {!busy && job && error && (
                      <button
                        className="cr-btn"
                        onClick={() => createCharacter(job.description, job)}
                      >
                        Retry creation
                      </button>
                    )}
                    {!job && (
                      <button
                        className="cr-btn gold"
                        onClick={() => setSheet("create")}
                      >
                        Create character
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
            {d && line && screen === "overview" && (
              <>
                <section className="cr-story-cover">
                  <img
                    src="/creator/station.svg"
                    alt="An illustrated rainy railway station"
                  />
                  <span className="cr-pill">
                    {d.demo ? "Demo mode" : "Your story"}
                  </span>
                  <div>
                    <h1>{d.title}</h1>
                    <p>{d.premise}</p>
                    {line.world_rules && <p>{line.world_rules}</p>}
                    <button
                      className="cr-text-link"
                      onClick={() => setSheet("rules")}
                    >
                      Edit world rules in a new storyline →
                    </button>
                  </div>
                </section>
                <div className="cr-pad">
                  <div className="cr-participants">
                    {members.map((m) => (
                      <div key={m.id}>
                        <Face member={m} />
                        <strong>{m.profile.name}</strong>
                      </div>
                    ))}
                  </div>
                  <button
                    className="cr-btn gold full"
                    disabled={busy}
                    onClick={async () => {
                      setCheckpoint(null);
                      go("reader", work!.id);
                      if (!line.head) await act("continue");
                    }}
                  >
                    {line.head ? "Continue story" : "Begin story"} →
                  </button>
                  <div className="cr-overview-line">
                    <span>Current storyline</span>
                    <strong>{line.name}</strong>
                    <small>
                      {d.finished
                        ? "Finished"
                        : d.archived
                          ? "Archived"
                          : "In progress"}{" "}
                      · {moments.length} moments
                    </small>
                  </div>
                  <div className="cr-menu-grid">
                    {[
                      [
                        "Scenes",
                        "scenes",
                        `${new Set(moments.map((n) => n.scene_id)).size} on this path`,
                      ],
                      [
                        "Storylines",
                        "lines",
                        `${Object.keys(d.lines).length} possibilities`,
                      ],
                      [
                        "Saved versions",
                        "saved",
                        `${d.checkpoints.length} places to return`,
                      ],
                      [
                        "Story notes",
                        "notes",
                        `${d.facts.filter((f) => f.line_id === line.id).length} details`,
                      ],
                    ].map(([label, next, sub]) => (
                      <button
                        key={next}
                        onClick={() => go(next as Screen, work!.id)}
                      >
                        <Icon name={next === "notes" ? "spark" : "book"} />
                        <strong>{label}</strong>
                        <small>{sub}</small>
                        <span>→</span>
                      </button>
                    ))}
                  </div>
                  <div className="cr-inline-actions">
                    <button onClick={() => setSheet("export")}>
                      Export story →
                    </button>
                    <button onClick={() => setSheet("rename")}>Rename</button>
                    <button disabled={busy} onClick={() => act("archive")}>
                      {d.archived ? "Unarchive" : "Archive"}
                    </button>
                  </div>
                </div>
              </>
            )}
            {d && line && screen === "reader" && (
              <>
                <div className="cr-reader-heading">
                  <span className="cr-eyebrow">
                    {checkpoint
                      ? "SAVED VERSION · READ ONLY"
                      : d.demo
                        ? "DEMO MODE · PREPARED FICTION"
                        : "YOUR STORY IN MOTION"}
                  </span>
                  <h1>{d.title}</h1>
                  <button
                    className="cr-line-chip"
                    onClick={() => go("lines", work!.id)}
                  >
                    {checkpoint?.name || line.name}⌄
                  </button>
                </div>
                <div className="cr-reader-scene-art">
                  <img
                    src="/creator/station.svg"
                    alt="A quiet station in the rain"
                  />
                </div>
                {checkpoint ? (
                  <MomentList
                    doc={d}
                    nodes={chain(d, checkpoint.line.head)}
                    readOnly
                    visible={8000}
                    onEdit={() => {}}
                  />
                ) : (
                  <MomentList
                    doc={d}
                    nodes={moments}
                    visible={revealed}
                    onEdit={(n) => {
                      setMoment(n);
                      setSheet("edit");
                    }}
                  />
                )}
                <div ref={end} />
                {!total && !checkpoint && (
                  <div className="cr-empty">
                    <h2>The scene is yours.</h2>
                    <p>
                      Reveal an opening, or write the first moment yourself.
                    </p>
                    <button
                      className="cr-btn gold"
                      disabled={busy}
                      onClick={() => act("continue")}
                    >
                      Generate opening
                    </button>
                    <button
                      className="cr-btn secondary"
                      disabled={busy}
                      onClick={() => {
                        setMoment(null);
                        setSheet("edit");
                      }}
                    >
                      Write first moment
                    </button>
                  </div>
                )}
                {busy && (
                  <div className="cr-writing" role="status">
                    <span /> {busyText}
                  </div>
                )}
                {!checkpoint && total > 0 && (
                  <div className="cr-reading-controls">
                    <button
                      disabled={busy || revealed >= total}
                      onClick={() =>
                        act("progress", { revealed: revealed + 1 })
                      }
                    >
                      Next
                    </button>
                    <button
                      disabled={busy || revealed >= total}
                      onClick={() => act("progress", { revealed: total })}
                    >
                      Show all
                    </button>
                    <small>
                      {revealed} / {total}
                    </small>
                  </div>
                )}
                {!checkpoint && revealed >= total && total > 0 && (
                  <div className="cr-suggestions">
                    {moments.at(-1)?.suggestions.map((s) => (
                      <button
                        key={s}
                        disabled={busy}
                        onClick={() => act("direct", { content: s })}
                      >
                        {s}
                        <span>→</span>
                      </button>
                    ))}
                  </div>
                )}
                {!checkpoint && total > 0 && (
                  <div className="cr-inline-actions cr-reader-tools">
                    <button
                      disabled={busy}
                      onClick={() => {
                        setMoment(moments.at(-1)!);
                        setSheet("fork");
                      }}
                    >
                      Try another version →
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => {
                        setMoment(moments.at(-1)!);
                        setSheet("rewrite");
                      }}
                    >
                      Rewrite moment
                    </button>
                    <button disabled={busy} onClick={() => setSheet("scene")}>
                      New scene
                    </button>
                    <button onClick={() => go("notes", work!.id)}>
                      Story notes
                    </button>
                    <button onClick={() => setSheet("export")}>Export</button>
                  </div>
                )}
              </>
            )}
            {d && line && screen === "scenes" && (
              <div className="cr-pad">
                <span className="cr-eyebrow">THE SHAPE OF THIS STORY</span>
                <h1>Scene by scene.</h1>
                {Array.from(new Set(moments.map((n) => n.scene_id))).map(
                  (sid, i) => {
                    const nodes = moments.filter((n) => n.scene_id === sid);
                    const first = moments.findIndex((n) => n.scene_id === sid);
                    const count = moments
                      .slice(0, first)
                      .reduce((a, n) => a + n.blocks.length, 0);
                    return (
                      <div className="cr-line-card" key={sid}>
                        <small>
                          SCENE {i + 1} · {nodes.length} moments
                        </small>
                        <h2>{d.scenes[sid].title}</h2>
                        <p>{d.scenes[sid].premise}</p>
                        <div className="cr-inline-actions">
                          <button
                            disabled={busy}
                            onClick={async () => {
                              const w = await act("progress", {
                                revealed: count + 1,
                              });
                              if (w) go("reader", w.id);
                            }}
                          >
                            Read this scene →
                          </button>
                          <button
                            disabled={busy}
                            onClick={() => {
                              setMoment(nodes.at(-1)!);
                              setSheet("fork");
                            }}
                          >
                            Explore another direction
                          </button>
                        </div>
                      </div>
                    );
                  },
                )}
                <button
                  className="cr-btn gold full"
                  disabled={busy}
                  onClick={() => setSheet("scene")}
                >
                  ＋ New scene
                </button>
              </div>
            )}
            {d && line && (screen === "lines" || screen === "compare") && (
              <div className="cr-pad">
                <span className="cr-eyebrow">
                  ONE STORY, MANY POSSIBILITIES
                </span>
                <h1>
                  {screen === "compare"
                    ? "Another way forward."
                    : "Choose your thread."}
                </h1>
                {Object.values(d.lines).map((l) => (
                  <div
                    className={
                      "cr-line-card" +
                      (l.id === d.active_line ? " selected" : "")
                    }
                    key={l.id}
                  >
                    <span className="cr-eyebrow">
                      {l.id === d.active_line ? "CURRENT STORYLINE" : l.origin}
                    </span>
                    <h2>{l.name}</h2>
                    <p>
                      {chain(d, l.head)
                        .at(-1)
                        ?.blocks.find((b) => b.type === "dialogue")?.text ||
                        "The beginning of a possibility."}
                    </p>
                    <div className="cr-inline-actions">
                      <button
                        disabled={busy}
                        onClick={async () => {
                          const w = await act("switch", { target_id: l.id });
                          if (w) go("reader", w.id);
                        }}
                      >
                        Use this storyline →
                      </button>
                      <button
                        onClick={() => {
                          setCompare(l.id);
                          go("compare", work!.id);
                        }}
                      >
                        Read version
                      </button>
                      <button
                        disabled={busy}
                        onClick={() => {
                          if (
                            confirm(
                              "Delete this storyline? Other storylines and saved versions stay.",
                            )
                          )
                            void act("delete_line", { target_id: l.id });
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
                {screen === "compare" && compare && d.lines[compare] && (
                  <>
                    <h2>{d.lines[compare].name}</h2>
                    <MomentList
                      doc={d}
                      nodes={chain(d, d.lines[compare].head)}
                      readOnly
                      visible={8000}
                      onEdit={() => {}}
                    />
                  </>
                )}
              </div>
            )}
            {d && screen === "saved" && (
              <div className="cr-pad">
                <span className="cr-eyebrow">PLACES TO RETURN TO</span>
                <h1>
                  Keep a moment.
                  <br />
                  <em>Keep a possibility.</em>
                </h1>
                <p className="cr-muted">
                  Named versions stay exactly as you saved them.
                </p>
                {d.checkpoints.map((c) => (
                  <div className="cr-line-card" key={c.id}>
                    <small>
                      {c.line.name} ·{" "}
                      {new Date(c.created_at).toLocaleDateString("en-US")}
                    </small>
                    <h2>{c.name}</h2>
                    <div className="cr-inline-actions">
                      <button
                        onClick={() => {
                          go("reader", work!.id);
                          setCheckpoint(c);
                          const q = new URLSearchParams(location.search);
                          q.set("checkpoint", c.id);
                          history.replaceState(null, "", `/creator?${q}`);
                        }}
                      >
                        Preview
                      </button>
                      <button
                        disabled={busy}
                        onClick={async () => {
                          const w = await act("restore", { target_id: c.id });
                          if (w) go("reader", w.id);
                        }}
                      >
                        Continue from here →
                      </button>
                      <button
                        disabled={busy}
                        onClick={() => {
                          if (
                            confirm(
                              "Delete this named version? Your storylines stay.",
                            )
                          )
                            void act("delete_checkpoint", { target_id: c.id });
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
                {!d.checkpoints.length && (
                  <div className="cr-empty">
                    <p>Save a named version while writing.</p>
                    <button
                      className="cr-btn"
                      onClick={() => go("reader", work!.id)}
                    >
                      Back to the story
                    </button>
                  </div>
                )}
              </div>
            )}
            {d && line && screen === "notes" && (
              <div className="cr-pad">
                <span className="cr-eyebrow">WHAT THIS STORY KNOWS</span>
                <h1>
                  Details that
                  <br />
                  <em>stay with the story.</em>
                </h1>
                <p className="cr-muted">
                  Facts on {line.name} stay on this storyline.
                </p>
                <div className="cr-note-card">
                  <small>AUTHOR SETUP</small>
                  <p>{d.premise}</p>
                </div>
                {members.map((m) => (
                  <details className="cr-details" key={m.id}>
                    <summary>{m.profile.name} · character setup</summary>
                    <p>
                      <strong>Wants:</strong>{" "}
                      {m.profile.wants || "Not specified"}
                    </p>
                    <p>
                      <strong>Private information:</strong>{" "}
                      {m.profile.private_information || "Not specified"}
                    </p>
                    <small>
                      Private setup does not mean the other character knows.
                    </small>
                  </details>
                ))}
                {d.facts
                  .filter((f) => f.line_id === line.id)
                  .map((f) => (
                    <div className="cr-note-card" key={f.id}>
                      <span className={"cr-pill " + f.status}>
                        {f.status.replace("_", " ")}
                      </span>
                      <p>{f.text}</p>
                      <small>
                        Known by:{" "}
                        {f.known_by
                          .map(
                            (w) =>
                              members.find((m) => m.id === w)?.profile.name,
                          )
                          .join(", ") || "Unspecified"}
                      </small>
                      <div className="cr-inline-actions">
                        {f.source && (
                          <button
                            onClick={() => {
                              setMoment(d.nodes[f.source!]);
                              setSheet("source");
                            }}
                          >
                            View source
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setEditingFact(f);
                            setMoment(
                              moments.find((n) => n.id === f.source) ||
                                moments.at(-1) ||
                                null,
                            );
                            setSheet("fact");
                          }}
                        >
                          Edit fact
                        </button>
                        <button
                          disabled={busy}
                          onClick={() =>
                            act("fact", {
                              target_id: f.id,
                              node_id: f.source,
                              content: f.text,
                              known_by: f.known_by,
                              confirmed: f.status !== "confirmed",
                            })
                          }
                        >
                          {f.status === "confirmed" ? "Unconfirm" : "Confirm"}
                        </button>
                        <button
                          disabled={busy}
                          onClick={() =>
                            act("delete_fact", { target_id: f.id })
                          }
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                <button
                  className="cr-btn gold full"
                  onClick={() => {
                    setEditingFact(null);
                    setMoment(moments.at(-1) || null);
                    setSheet("fact");
                  }}
                >
                  ＋ Add story fact
                </button>
                <button
                  className="cr-btn secondary full"
                  disabled={busy}
                  onClick={() =>
                    act("update_cast", { name: "Updated characters" })
                  }
                >
                  Use updated characters in a new storyline
                </button>
              </div>
            )}
          </>
        )}
      </div>
      {screen === "reader" && d && line ? (
        <footer className="cr-composer">
          {checkpoint ? (
            <button
              className="cr-btn gold full"
              disabled={busy}
              onClick={async () => {
                const w = await act("restore", { target_id: checkpoint.id });
                if (w) {
                  setCheckpoint(null);
                  setNotice("Continued in a new storyline.");
                }
              }}
            >
              Continue from this saved version →
            </button>
          ) : (
            <>
              <div className="cr-composer-actions">
                <button
                  className="cr-btn secondary"
                  disabled={busy || d.finished || revealed < total}
                  onClick={() => act("continue")}
                >
                  Continue <span>→</span>
                </button>
                <button
                  className="cr-btn gold"
                  disabled={busy || !total}
                  onClick={() => setSheet("save")}
                >
                  Save storyline <span>✧</span>
                </button>
              </div>
              {d.mode === "play" && (
                <label className="cr-input-type">
                  Your contribution
                  <select
                    aria-label="Contribution type"
                    value={inputType}
                    onChange={(e) => setInputType(e.target.value)}
                  >
                    <option value="direction">Direction</option>
                    <option value="dialogue">My dialogue</option>
                    <option value="action">My action</option>
                  </select>
                </label>
              )}
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!direction.trim()) return;
                  const w = await act("direct", {
                    content: direction,
                    input_type: inputType,
                  });
                  if (w) draft("");
                }}
              >
                <textarea
                  maxLength={inputType === "direction" ? 2000 : 1200}
                  aria-label="Direct the scene or write a line"
                  placeholder={
                    d.mode === "play"
                      ? "Write your line, action, or direction…"
                      : "Direct the scene or write a line…"
                  }
                  rows={2}
                  value={direction}
                  onChange={(e) => draft(e.target.value)}
                  disabled={busy}
                />
                <button
                  aria-label="Send direction"
                  disabled={busy || !direction.trim() || d.finished}
                >
                  ↑
                </button>
              </form>
              <small>
                {busy ? (
                  <button
                    type="button"
                    onClick={() => controller.current?.abort()}
                  >
                    Stop waiting
                  </button>
                ) : (
                  <>
                    <span className="cr-save-dot" />{" "}
                    {error
                      ? "Save not confirmed · Your last saved draft is safe"
                      : "Changes saved to this story"}
                    {direction ? " · Input draft on this device" : ""}
                  </>
                )}
              </small>
            </>
          )}
        </footer>
      ) : (
        <nav className="cr-nav" aria-label="Creator navigation">
          {[
            ["home", "home", "Home"],
            ["characters", "people", "Characters"],
            ["stories", "book", "Stories"],
          ].map(([next, icon, label]) => (
            <button
              className={
                screen === next ||
                (next === "stories" && storyScreens.includes(screen))
                  ? "active"
                  : ""
              }
              key={next}
              onClick={() => go(next as Screen)}
            >
              <Icon name={icon} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      )}
      {sheet && (
        <SheetPanel
          title={
            {
              create: "Someone worth writing",
              profile: "Shape your character",
              refine: "A little more like them",
              portrait: "Their look, your choice",
              setup: "Where does it begin?",
              save: "Save this storyline",
              fork: "Another possibility",
              scene: "A new scene",
              edit: "Edit this moment",
              rewrite: "Rewrite this moment",
              fact: "A detail to remember",
              export: "Take your story with you",
              settings: "Your studio",
              rename: "Give it a name",
              rules: "Story setup",
              source: "Where this detail came from",
            }[sheet]
          }
          close={() => setSheet(null)}
        >
          {sheet === "create" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void createCharacter(
                  field(new FormData(e.currentTarget), "description"),
                );
              }}
            >
              <p className="cr-muted">
                One description. A character and a portrait.
              </p>
              <label>
                Who would you like to create?
                <textarea
                  name="description"
                  required
                  maxLength={5000}
                  rows={6}
                  defaultValue={job?.description || ""}
                  placeholder="A reserved young restorer with short dark hair, a precise way of speaking, and a one-way ticket home…"
                />
              </label>
              <button className="cr-btn gold full" disabled={busy}>
                Create character <span>✧</span>
              </button>
              {!health?.text_configured && (
                <p className="cr-small">
                  Live creation needs a configured text and image model.{" "}
                  <button
                    type="button"
                    className="cr-text-link"
                    onClick={() => {
                      setSheet(null);
                      void demo();
                    }}
                  >
                    Try an example instead →
                  </button>
                </p>
              )}
            </form>
          )}
          {sheet === "profile" && character && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                void task(async () => {
                  const p = {
                    ...character.profile,
                    name: field(f, "name"),
                    short_description: field(f, "short"),
                    backstory: field(f, "background"),
                    wants: field(f, "wants"),
                    why_it_matters: field(f, "why"),
                    fear: field(f, "fear"),
                    private_information: field(f, "secret"),
                    speech_style: {
                      ...character.profile.speech_style,
                      tone: field(f, "voice"),
                    },
                    personality: {
                      ...character.profile.personality,
                      core_traits: field(f, "traits")
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean),
                    },
                    appearance: {
                      ...character.profile.appearance,
                      hair: field(f, "hair"),
                      eyes: field(f, "eyes"),
                      clothing: field(f, "clothing"),
                    },
                  };
                  await api(
                    `/characters/${character.id}`,
                    { profile: p, expected_version: character.profile_version },
                    "PATCH",
                  );
                  setCharacter(await api(`/characters/${character.id}`));
                  await refresh();
                  setSheet(null);
                  setNotice(
                    "Character saved. Existing stories keep their snapshots.",
                  );
                });
              }}
            >
              <label>
                Name
                <input
                  name="name"
                  defaultValue={character.profile.name}
                  required
                  maxLength={60}
                />
              </label>
              <label>
                One-line description
                <input
                  name="short"
                  defaultValue={character.profile.short_description}
                  maxLength={160}
                />
              </label>
              <label>
                What do they want?
                <textarea
                  name="wants"
                  defaultValue={character.profile.wants || ""}
                  maxLength={300}
                  rows={2}
                />
              </label>
              <label>
                Core traits
                <input
                  name="traits"
                  defaultValue={character.profile.personality.core_traits.join(
                    ", ",
                  )}
                  maxLength={1500}
                  placeholder="Reserved, determined, quietly caring"
                />
              </label>
              <details className="cr-details" open>
                <summary>More about this character</summary>
                {[
                  [
                    "why",
                    "Why it matters",
                    character.profile.why_it_matters,
                    500,
                  ],
                  ["fear", "Fear or boundary", character.profile.fear, 300],
                  [
                    "voice",
                    "Speaking style",
                    character.profile.speech_style.tone,
                    300,
                  ],
                  [
                    "secret",
                    "Private information",
                    character.profile.private_information,
                    500,
                  ],
                  [
                    "background",
                    "Background",
                    character.profile.backstory,
                    1500,
                  ],
                  ["hair", "Hair", character.profile.appearance.hair, 500],
                  ["eyes", "Eyes", character.profile.appearance.eyes, 500],
                  [
                    "clothing",
                    "Clothing",
                    character.profile.appearance.clothing,
                    500,
                  ],
                ].map(([key, label, value, max]) => (
                  <label key={String(key)}>
                    {label}
                    <textarea
                      name={String(key)}
                      defaultValue={String(value || "")}
                      maxLength={Number(max)}
                      rows={2}
                    />
                  </label>
                ))}
              </details>
              <button className="cr-btn gold full" disabled={busy}>
                Save character
              </button>
            </form>
          )}
          {sheet === "refine" && character && (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  void task(async () =>
                    setProposal(
                      await api(`/characters/${character.id}/refine`, {
                        instruction: field(f, "instruction"),
                        expected_version: character.profile_version,
                      }),
                    ),
                  );
                }}
              >
                <label>
                  What should change?
                  <textarea
                    name="instruction"
                    required
                    maxLength={2000}
                    rows={4}
                    placeholder="Make her more reserved, but keep her appearance and background."
                  />
                </label>
                <button className="cr-btn secondary full" disabled={busy}>
                  Preview changes
                </button>
              </form>
              {proposal && (
                <div className="cr-change-preview">
                  {proposal.changes.map((c) => (
                    <div key={c.path}>
                      <strong>{c.path.replaceAll(".", " · ")}</strong>
                      <p>{String(c.before)}</p>
                      <p>→ {String(c.after)}</p>
                    </div>
                  ))}
                  <button
                    className="cr-btn gold full"
                    disabled={busy}
                    onClick={() =>
                      task(async () => {
                        await api(
                          `/characters/${character.id}/refine/confirm`,
                          { proposal_id: proposal.proposal_id },
                        );
                        setCharacter(await api(`/characters/${character.id}`));
                        await refresh();
                        setSheet(null);
                        setNotice("Changes applied.");
                      })
                    }
                  >
                    Apply changes
                  </button>
                </div>
              )}
            </>
          )}
          {sheet === "portrait" && character && (
            <>
              <div className="cr-portrait-preview">
                <Face character={character} large />
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  void task(async () => {
                    await creator(`/characters/${character.id}/portrait`, {
                      request_id: id(),
                      instruction: field(f, "instruction"),
                      editing: !!character.current_image_id,
                      expected_image_id: character.current_image_id,
                    });
                    setPortraits(
                      await api(`/characters/${character.id}/images`),
                    );
                    setNotice(
                      "Candidate ready. Choose the portrait you prefer.",
                    );
                  });
                }}
              >
                <label>
                  Edit portrait
                  <textarea
                    name="instruction"
                    maxLength={2000}
                    required={!!character.current_image_id}
                    rows={3}
                    placeholder="Change her hair to auburn. Keep her face and clothing."
                  />
                </label>
                <button className="cr-btn gold full" disabled={busy}>
                  {character.current_image_id
                    ? "Edit portrait"
                    : "Retry portrait"}
                </button>
                <button
                  type="button"
                  className="cr-btn secondary full"
                  disabled={busy}
                  onClick={() =>
                    task(async () => {
                      await creator(`/characters/${character.id}/portrait`, {
                        request_id: id(),
                        editing: false,
                        expected_image_id: character.current_image_id,
                      });
                      setPortraits(
                        await api(`/characters/${character.id}/images`),
                      );
                    })
                  }
                >
                  Try another portrait
                </button>
              </form>
              <button
                className="cr-text-link"
                onClick={() => setSheet("profile")}
              >
                Update appearance to match →
              </button>
              <div className="cr-portrait-history">
                {portraits.map((p) => (
                  <div key={p.id}>
                    <img src={p.url} alt={`Portrait version ${p.version}`} />
                    <small>Version {p.version}</small>
                    <button
                      className="cr-btn secondary"
                      disabled={busy || character.current_image_id === p.id}
                      onClick={() =>
                        task(async () => {
                          await api(
                            `/characters/${character.id}/images/${p.id}/select`,
                            {},
                          );
                          setCharacter(
                            await api(`/characters/${character.id}`),
                          );
                          await refresh();
                          setImageError("");
                        })
                      }
                    >
                      {character.current_image_id === p.id
                        ? "Selected"
                        : "Use this portrait"}
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
          {sheet === "setup" && (
            <form
              onChange={(e) => rememberSetup(e.currentTarget)}
              onSubmit={(e) => {
                e.preventDefault();
                void startStory(new FormData(e.currentTarget));
              }}
            >
              <label>
                First character
                <select
                  name="first"
                  defaultValue={setupDraft.first || character?.id}
                  required
                >
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.profile.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                How would you like to write?
                <select
                  value={setupMode}
                  onChange={(e) => setSetupMode(e.target.value)}
                >
                  <option value="play">Play a role</option>
                  <option value="direct">Direct the cast</option>
                </select>
              </label>
              {setupMode === "direct" ? (
                <label>
                  Second character
                  <select
                    name="second"
                    required
                    defaultValue={setupDraft.second || ""}
                  >
                    <option value="" disabled>
                      Choose another character
                    </option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.profile.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label>
                  Your name in the story
                  <input
                    name="player"
                    defaultValue={setupDraft.player || "You"}
                    maxLength={60}
                    required
                  />
                </label>
              )}
              <label>
                What happens first?
                <textarea
                  name="premise"
                  defaultValue={setupDraft.premise || ""}
                  required
                  maxLength={1000}
                  rows={5}
                  placeholder="A rainy station. A one-way ticket. Something neither of them has said."
                />
              </label>
              {setupMode === "direct" && (
                <button
                  className="cr-text-link"
                  type="button"
                  onClick={() => {
                    returnToSetup.current = true;
                    setSheet("create");
                  }}
                >
                  ＋ Create a second character
                </button>
              )}
              <details className="cr-details">
                <summary>Story details</summary>
                {[
                  ["player_description", "Your role (optional)", 300],
                  ["location", "Location", 300],
                  ["time", "Time", 100],
                  ["atmosphere", "Atmosphere", 300],
                  ["boundaries", "Boundaries", 500],
                  ["world_rules", "World rules", 2000],
                ]
                  .filter(
                    ([key]) =>
                      key !== "player_description" || setupMode === "play",
                  )
                  .map(([key, label, max]) => (
                    <label key={String(key)}>
                      {label}
                      <textarea
                        name={String(key)}
                        rows={2}
                        maxLength={Number(max)}
                        defaultValue={setupDraft[String(key)] || ""}
                      />
                    </label>
                  ))}
                <label>
                  Story title
                  <input
                    name="title"
                    defaultValue={setupDraft.title || ""}
                    maxLength={100}
                    placeholder="A working title, if you have one"
                  />
                </label>
              </details>
              <button className="cr-btn gold full" disabled={busy}>
                Begin story →
              </button>
            </form>
          )}
          {(sheet === "save" ||
            sheet === "fork" ||
            sheet === "scene" ||
            sheet === "rewrite" ||
            sheet === "fact" ||
            sheet === "rename") &&
            work && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const operation =
                    sheet === "save"
                      ? "checkpoint"
                      : sheet === "fact"
                        ? "fact"
                        : sheet === "rename"
                          ? "rename"
                          : sheet;
                  const fields: Record<string, unknown> = {
                    name: field(f, "name"),
                    content: field(f, "content"),
                  };
                  if (
                    sheet === "fork" ||
                    sheet === "rewrite" ||
                    sheet === "fact"
                  )
                    fields.node_id = moment?.id || "";
                  if (sheet === "fact") {
                    fields.known_by = f.getAll("known");
                    if (editingFact) fields.target_id = editingFact.id;
                  }
                  if (sheet === "rename") fields.target_id = field(f, "target");
                  const w = await act(operation, fields);
                  if (w) {
                    setSheet(null);
                    if (["fork", "scene", "rewrite"].includes(sheet!))
                      go("reader", w.id);
                    else if (sheet === "save")
                      setNotice(
                        "Version saved. Keep writing without changing this snapshot.",
                      );
                  }
                }}
              >
                {["save", "fork", "scene", "rename"].includes(sheet) && (
                  <label>
                    {sheet === "save"
                      ? "Version name"
                      : sheet === "scene"
                        ? "Scene title"
                        : "Name"}
                    <input
                      name="name"
                      maxLength={100}
                      required
                      defaultValue={
                        sheet === "save"
                          ? "Before everything changes"
                          : sheet === "rename"
                            ? d?.title
                            : ""
                      }
                      placeholder={
                        sheet === "fork"
                          ? "Another possibility"
                          : "A name to find it again"
                      }
                    />
                  </label>
                )}
                {["fork", "scene", "rewrite", "fact"].includes(sheet) && (
                  <label>
                    {sheet === "fork"
                      ? "What happens differently?"
                      : sheet === "rewrite"
                        ? "How should this moment change?"
                        : sheet === "fact"
                          ? "Story fact"
                          : "What happens in this scene?"}
                    <textarea
                      name="content"
                      defaultValue={
                        sheet === "fact" ? editingFact?.text || "" : ""
                      }
                      required
                      maxLength={2000}
                      rows={4}
                      placeholder={
                        sheet === "fork"
                          ? "Let Mira admit the residency offer."
                          : ""
                      }
                    />
                  </label>
                )}
                {sheet === "fact" && (
                  <fieldset>
                    <legend>Who knows this?</legend>
                    {members.map((m) => (
                      <label className="cr-checkbox" key={m.id}>
                        <input
                          type="checkbox"
                          name="known"
                          value={m.id}
                          defaultChecked={
                            editingFact?.known_by.includes(m.id) || false
                          }
                        />
                        {m.profile.name}
                      </label>
                    ))}
                  </fieldset>
                )}
                {sheet === "rename" && (
                  <label>
                    Rename
                    <select name="target">
                      <option value="story">Story</option>
                      <option value="line">Current storyline</option>
                    </select>
                  </label>
                )}
                {sheet === "save" && (
                  <p className="cr-muted">
                    This named version stays as it is. Your storyline can keep
                    growing.
                  </p>
                )}
                <button className="cr-btn gold full" disabled={busy}>
                  {busy
                    ? "Saving…"
                    : sheet === "save"
                      ? "Save version"
                      : sheet === "fork"
                        ? "Explore another version"
                        : sheet === "scene"
                          ? "Begin scene"
                          : sheet === "rewrite"
                            ? "Rewrite moment"
                            : sheet === "fact"
                              ? "Confirm fact"
                              : "Save name"}
                </button>
              </form>
            )}
          {sheet === "edit" && work && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const blocks: Block[] = [];
                const count = moment?.blocks.length || 1;
                for (let i = 0; i < count; i++) {
                  const type = field(f, `type${i}`) as Block["type"];
                  blocks.push({
                    type,
                    speaker:
                      type === "narration" ? null : field(f, `speaker${i}`),
                    text: field(f, `text${i}`),
                  });
                }
                const fields = {
                  node_id: moment?.id || "",
                  blocks,
                  content: "",
                  name: "Edited version",
                };
                const w = await act("edit", fields);
                if (w) {
                  setSheet(null);
                  go("reader", w.id);
                }
              }}
            >
              <p className="cr-small">
                {moment
                  ? "Editing an earlier moment creates a new storyline. Saved versions stay intact."
                  : "Write the first moment in your own words."}
              </p>
              {(
                moment?.blocks || [
                  { type: "dialogue", speaker: members[0]?.id, text: "" },
                ]
              ).map((b, i) => (
                <div className="cr-edit-block" key={i}>
                  <label>
                    Block {i + 1} type
                    <select name={`type${i}`} defaultValue={b.type}>
                      <option value="narration">Narration</option>
                      <option value="dialogue">Dialogue</option>
                      <option value="action">Action</option>
                    </select>
                  </label>
                  <label>
                    Speaker
                    <select
                      name={`speaker${i}`}
                      defaultValue={b.speaker || members[0]?.id}
                    >
                      {members.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.profile.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Text
                    <textarea
                      name={`text${i}`}
                      required
                      maxLength={1200}
                      defaultValue={b.text}
                      rows={3}
                    />
                  </label>
                </div>
              ))}
              <button className="cr-btn gold full" disabled={busy}>
                Save edit
              </button>
            </form>
          )}
          {sheet === "source" && d && moment && (
            <MomentList
              doc={d}
              nodes={[moment]}
              visible={8000}
              readOnly
              onEdit={() => {}}
            />
          )}
          {sheet === "rules" && work && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const w = await act("setup", {
                  content: field(f, "rules"),
                  name: "Updated world rules",
                });
                if (w) setSheet(null);
              }}
            >
              <label>
                World rules
                <textarea
                  name="rules"
                  maxLength={2000}
                  rows={5}
                  defaultValue={line?.world_rules || ""}
                />
              </label>
              <p className="cr-small">
                This creates a new storyline. Existing storylines and saved
                versions keep their setup.
              </p>
              <button className="cr-btn gold full" disabled={busy}>
                Use updated setup
              </button>
            </form>
          )}
          {sheet === "export" && work && (
            <>
              <label>
                Format
                <select
                  value={exportFormat}
                  onChange={(e) => {
                    setExportFormat(e.target.value);
                    setExportText("");
                  }}
                >
                  <option value="script">Script draft</option>
                  <option value="prose">Prose draft</option>
                  <option value="json">Story backup (.json)</option>
                </select>
              </label>
              {exportFormat !== "json" && (
                <label>
                  Scope
                  <select
                    value={exportScope}
                    onChange={(e) => {
                      setExportScope(e.target.value);
                      setExportText("");
                    }}
                  >
                    <option value="storyline">Entire selected storyline</option>
                    <option value="scene">Latest scene</option>
                  </select>
                </label>
              )}
              <p className="cr-small">
                Only the selected storyline is in a text export. JSON includes
                all versions and portrait references, not image files.
              </p>
              <button
                className="cr-btn secondary full"
                onClick={() =>
                  task(async () => {
                    const r = await fetch(
                      `/api/creator/works/${work.id}/export?format=${exportFormat}${exportScope === "scene" && moments.length ? `&scene_id=${moments.at(-1)!.scene_id}` : ""}${checkpoint ? `&checkpoint_id=${checkpoint.id}` : ""}`,
                    );
                    if (!r.ok) throw new Error("Export could not be prepared.");
                    setExportText(await r.text());
                  })
                }
              >
                Prepare preview
              </button>
              {exportText && (
                <>
                  <label>
                    Export preview
                    <textarea rows={8} value={exportText} readOnly />
                  </label>
                  <div className="cr-two">
                    <button
                      className="cr-btn gold"
                      onClick={() => {
                        download(
                          exportText,
                          `echoloom-story.${exportFormat === "json" ? "json" : "md"}`,
                          exportFormat === "json"
                            ? "application/json"
                            : "text/markdown",
                        );
                        setNotice(
                          "Download prepared. If your browser blocks it, copy the preview.",
                        );
                      }}
                    >
                      Download
                    </button>
                    <button
                      className="cr-btn secondary"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(exportText);
                          setNotice("Copied.");
                        } catch {
                          setNotice("Select and copy the preview manually.");
                        }
                      }}
                    >
                      Copy
                    </button>
                  </div>
                </>
              )}
            </>
          )}
          {sheet === "settings" && (
            <>
              <p className="cr-muted">
                Your characters, stories, and saved versions live on this
                installation.
              </p>
              <label className="cr-import">
                Import a story backup
                <input
                  type="file"
                  accept="application/json,.json"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    if (file.size > 5 * 1024 * 1024) {
                      setError("Backups must be smaller than 5 MiB.");
                      return;
                    }
                    if (
                      !confirm(
                        "Import as a new story? Existing stories will stay unchanged.",
                      )
                    )
                      return;
                    await task(async () => {
                      const document = JSON.parse(await file.text());
                      const w = await creator<Work>("/import", {
                        request_id: id(),
                        document,
                      });
                      accept(w);
                      await refresh();
                      setSheet(null);
                      go("overview", w.id);
                    });
                  }}
                />
              </label>
              {work && storyScreens.includes(screen) && (
                <>
                  <button
                    className="cr-btn secondary full"
                    onClick={() => setSheet("export")}
                  >
                    Export / backup this story
                  </button>
                  <button
                    className="cr-btn secondary full"
                    onClick={() => {
                      setSheet(null);
                      go("saved", work.id);
                    }}
                  >
                    Saved versions
                  </button>
                  <button
                    className="cr-btn secondary full"
                    disabled={busy}
                    onClick={async () => {
                      const w = await act("finish");
                      if (w) setSheet(null);
                    }}
                  >
                    Finish story
                  </button>
                  <button
                    className="cr-btn danger full"
                    onClick={() => {
                      if (
                        confirm(
                          "Delete this story, all its storylines and named versions? Characters stay.",
                        )
                      )
                        void task(async () => {
                          await creator(
                            `/works/${work.id}`,
                            undefined,
                            "DELETE",
                          );
                          setWork(null);
                          await refresh();
                          setSheet(null);
                          go("stories");
                        });
                    }}
                  >
                    Delete story
                  </button>
                </>
              )}
              <Link className="cr-btn secondary full" href="/characters">
                Open original companion studio →
              </Link>
              <button
                className="cr-btn secondary full"
                onClick={() => {
                  setSheet(null);
                  void demo();
                }}
              >
                Try the prepared demo
              </button>
              <p className="cr-small">
                Live AI uses your server-side text and image settings. Demo mode
                uses prepared fiction and illustrations. Existing companion data
                is preserved.
              </p>
            </>
          )}
          {busy && (
            <p className="cr-status" role="status">
              {busyText}
            </p>
          )}
          {error && (
            <p className="cr-alert" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="cr-notice" role="status">
              {notice}
            </p>
          )}
        </SheetPanel>
      )}
    </main>
  );
}
function StoryCard({ w, onClick }: { w: Work; onClick: () => void }) {
  const d = w.document;
  return (
    <button className="cr-story-card" onClick={onClick}>
      <img src="/creator/station.svg" alt="" />
      <div>
        <small>
          {d.demo ? "DEMO STORY" : d.finished ? "FINISHED" : "IN PROGRESS"}
        </small>
        <h2>{d.title}</h2>
        <p>
          {d.lines[d.active_line].name} · {Object.keys(d.nodes).length} moments
        </p>
      </div>
      <span>→</span>
    </button>
  );
}
function CharacterDetail({ character: c }: { character: CreatorCharacter }) {
  return (
    <div className="cr-character-details">
      {[
        ["WANTS", c.profile.wants],
        ["VOICE", c.profile.speech_style.tone],
        ["BACKGROUND", c.profile.backstory],
      ].map(
        ([label, text]) =>
          text && (
            <div key={label}>
              <span className="cr-eyebrow">{label}</span>
              <p>{text}</p>
            </div>
          ),
      )}
    </div>
  );
}
function MomentList({
  doc,
  nodes,
  visible,
  onEdit,
  readOnly = false,
}: {
  readOnly?: boolean;
  doc: StoryDocument;
  nodes: Moment[];
  visible: number;
  onEdit: (m: Moment) => void;
}) {
  let index = 0;
  let previous = "";
  return (
    <div className="cr-moments">
      {nodes.map((n, i) => {
        const start = index;
        index += n.blocks.length;
        if (start >= visible) return null;
        const newScene = n.scene_id !== previous;
        previous = n.scene_id;
        const names = Object.fromEntries(
          doc.casts[n.cast_id].map((m) => [m.id, m.profile.name]),
        );
        return (
          <section className="cr-moment" key={n.id}>
            {newScene && (
              <div className="cr-scene-divider">
                <span>
                  SCENE{" "}
                  {new Set(nodes.slice(0, i + 1).map((x) => x.scene_id)).size}
                </span>
                <h2>{doc.scenes[n.scene_id].title}</h2>
              </div>
            )}
            {n.instruction && (
              <div className="cr-direction-note">→ {n.instruction}</div>
            )}
            {n.blocks.slice(0, Math.max(0, visible - start)).map((b, j) => (
              <div className={`cr-block ${b.type}`} key={j}>
                {b.type === "dialogue" && (
                  <span className="cr-speaker">
                    {names[b.speaker!]}
                    {b.source === "author" ? " · Your line" : ""}
                  </span>
                )}
                <p>{b.text}</p>
              </div>
            ))}
            <div className="cr-moment-meta">
              <small>
                {n.source === "author"
                  ? "Your edit"
                  : n.source === "demo"
                    ? "Demo draft"
                    : "AI draft"}{" "}
                · Moment {i + 1}
              </small>
              {!readOnly && (
                <button
                  aria-label={`Edit moment ${i + 1}`}
                  onClick={() => onEdit(n)}
                >
                  Edit →
                </button>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
