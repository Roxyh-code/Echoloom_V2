"use client";
import { useEffect, useRef, useState } from "react";
import {
  api,
  Character,
  Health,
  Portrait,
  Profile,
  Proposal,
  Revision,
} from "./api";
import { creator } from "./creator-api";
import { localGet, localPut, operation } from "./rehearsal-api";
type Mode = "library" | "create" | "detail";
type Person = Character & { archived?: boolean };
type Creation = { request_id: string; description: string };
function Picture({
  character,
  large = false,
}: {
  character: Character;
  large?: boolean;
}) {
  const [bad, setBad] = useState(false);
  const image = character.current_image_id;
  useEffect(() => setBad(false), [image]);
  return (
    <div className={large ? "mc-portrait" : "rh-avatar"}>
      {image && !bad ? (
        <img
          src={`/api/characters/${character.id}/images/${image}/file`}
          alt={"Portrait of " + character.profile.name}
          onError={() => setBad(true)}
        />
      ) : (
        <span>{character.profile.name.slice(0, 1)}</span>
      )}
    </div>
  );
}
function Panel({
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
      if (trigger?.isConnected) trigger.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="rh-sheet mc-sheet"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <div className="rh-grab" />
      <header>
        <h2>{title}</h2>
        <button className="rh-icon" aria-label="Close panel" onClick={close}>
          ×
        </button>
      </header>
      <div className="rh-sheet-body">{children}</div>
    </dialog>
  );
}
export function MobileCharacterStudio({
  initialCreate = false,
  picking = false,
  onExit,
  onPick,
  onStart,
  onChanged,
  onMode,
}: {
  initialCreate?: boolean;
  picking?: boolean;
  onExit: () => void;
  onPick: (c: Character) => Promise<void>;
  onStart: (c: Character) => Promise<void>;
  onChanged: () => Promise<void>;
  onMode: (mode: Mode) => void;
}) {
  const [mode, setMode] = useState<Mode>(initialCreate ? "create" : "library");
  const [list, setList] = useState<Person[]>([]);
  const [person, setPerson] = useState<Person | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState<Creation | null>(null);
  const [imageError, setImageError] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [panel, setPanel] = useState<
    "profile" | "refine" | "portrait" | "history" | "more" | null
  >(null);
  const [portraits, setPortraits] = useState<Portrait[]>([]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const guard = useRef(false);
  const creationGuard = useRef(false);
  const alive = useRef(true);
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const personRef = useRef(person);
  personRef.current = person;
  const epoch = useRef(0);
  function url(next: Mode, cid?: string, replace = false) {
    const q = new URLSearchParams(location.search);
    q.set("view", "characters");
    q.delete("create");
    q.delete("character");
    if (next === "create") q.set("create", "1");
    if (next === "detail" && cid) q.set("character", cid);
    history[replace ? "replaceState" : "pushState"](
      null,
      "",
      "/rehearsal?" + q,
    );
    setMode(next);
    setPanel(null);
    setError("");
    onMode(next);
  }
  async function refresh(showArchived = archived) {
    const cs = await creator<Person[]>("/characters?archived=" + showArchived);
    if (alive.current) setList(cs);
    return cs;
  }
  async function open(cid: string, replace = false) {
    const n = ++epoch.current;
    setLoading(true);
    try {
      const c = await api<Person>("/characters/" + cid);
      if (alive.current && n === epoch.current) {
        setPerson(c);
        setImageError("");
        url("detail", c.id, replace);
      }
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    alive.current = true;
    const q = new URLSearchParams(location.search);
    setDescription(localGet("character-description", ""));
    const job = localGet<Creation | null>("character-creation", null);
    setPending(job);
    api<Health>("/health")
      .then(setHealth)
      .catch(() => {});
    void refresh()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    if (q.get("character")) void open(q.get("character")!, true);
    else if (initialCreate || q.has("create")) {
      setMode("create");
      onMode("create");
    } else onMode("library");
    const pop = () => {
      const q = new URLSearchParams(location.search);
      if (q.get("view") !== "characters") return;
      if (q.get("character")) void open(q.get("character")!, true);
      else {
        const next = q.has("create") ? "create" : "library";
        setMode(next);
        setPanel(null);
        onMode(next);
      }
    };
    window.addEventListener("popstate", pop);
    return () => {
      alive.current = false;
      epoch.current++;
      window.removeEventListener("popstate", pop);
    };
  }, []);
  async function run(fn: () => Promise<void>) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      guard.current = false;
      if (alive.current) setBusy(false);
    }
  }
  async function changed() {
    if (!alive.current) return;
    await refresh();
    await onChanged();
  }
  async function reloadPerson() {
    const c = await api<Person>("/characters/" + personRef.current!.id);
    if (alive.current) setPerson(c);
    return c;
  }
  function startCreate() {
    setPerson(null);
    setImageError("");
    url("create");
  }
  async function createCharacter(retry?: Creation) {
    if (creationGuard.current) return;
    creationGuard.current = true;
    setCreating(true);
    setError("");
    setImageError("");
    const job = retry || {
      request_id: operation(),
      description: description.trim(),
    };
    setPending(job);
    localPut("character-creation", job);
    try {
      const r = await creator<{
        character_id: string;
        phase: string;
        image_error?: string;
      }>("/characters", job);
      if (!alive.current) return;
      const c = await api<Person>("/characters/" + r.character_id);
      if (!alive.current) return;
      if (modeRef.current === "create" || personRef.current?.id === c.id) {
        setPerson(c);
        setImageError(r.image_error || "");
      }
      setPending(null);
      localPut("character-creation", null);
      localPut("character-description", "");
      setDescription("");
      await changed();
      if (modeRef.current === "create") url("detail", c.id);
      else setNotice(c.profile.name + " is ready in your characters.");
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      creationGuard.current = false;
      if (alive.current) setCreating(false);
    }
  }
  // Recover a profile/portrait even after refresh or a dropped POST response. Never regenerate the profile.
  useEffect(() => {
    if (!pending) return;
    let active = true;
    let polling = false;
    const tick = async () => {
      if (polling) return;
      polling = true;
      try {
        const j = await creator<{
          status: string;
          result?: {
            character_id?: string;
            image_error?: string;
            detail?: string;
          };
        }>("/jobs/" + pending.request_id);
        if (!active) return;
        if (j.result?.character_id) {
          const c = await api<Person>("/characters/" + j.result.character_id);
          if (!active) return;
          if (modeRef.current === "create" || personRef.current?.id === c.id)
            setPerson(c);
          if (j.status === "succeeded") {
            setImageError(j.result.image_error || "");
            setPending(null);
            setCreating(false);
            localPut("character-creation", null);
            localPut("character-description", "");
            setDescription("");
            await changed();
            if (alive.current && modeRef.current === "create")
              url("detail", c.id, true);
          }
        } else if (j.status === "failed") {
          setError(
            j.result?.detail ||
              "Character creation did not complete. Retry your saved description.",
          );
          setCreating(false);
        }
      } catch {
        /* The saved request ID remains available for explicit retry. */
      } finally {
        polling = false;
      }
    };
    void tick();
    const timer = setInterval(tick, 1500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [pending?.request_id]);
  async function loadPortraits() {
    const ps = await api<Portrait[]>(
      "/characters/" + personRef.current!.id + "/images",
    );
    if (alive.current) setPortraits(ps);
  }
  async function makePortrait(edit: boolean, instruction = "") {
    const c = personRef.current!;
    const payload = {
      editing: edit,
      instruction,
      expected_image_id: c.current_image_id,
    };
    const key = "portrait-operation:" + c.id;
    const prior = localGet<{
      payload: typeof payload;
      request_id: string;
    } | null>(key, null);
    const request_id =
      prior && JSON.stringify(prior.payload) === JSON.stringify(payload)
        ? prior.request_id
        : operation();
    localPut(key, { payload, request_id });
    try {
      await creator("/characters/" + c.id + "/portrait", {
        request_id,
        ...payload,
      });
      if (!alive.current || personRef.current?.id !== c.id) return;
      localPut(key, null);
      await loadPortraits();
      const fresh = await reloadPerson();
      if (!fresh.current_image_id && portraits.length === 0) {
        const ps = await api<Portrait[]>("/characters/" + c.id + "/images");
        if (ps.length === 1) {
          await api(`/characters/${c.id}/images/${ps[0].id}/select`, {});
          await reloadPerson();
        }
      }
      setImageError("");
      setNotice("Portrait ready. Choose the version you prefer.");
      await changed();
    } catch (e) {
      await loadPortraits().catch(() => {});
      throw e;
    }
  }
  useEffect(() => {
    if (panel === "portrait" && person)
      void loadPortraits().catch((e) => setError(e.message));
    if (panel === "history" && person)
      void api<Revision[]>("/characters/" + person.id + "/versions")
        .then(setRevisions)
        .catch((e) => setError(e.message));
  }, [panel, person?.id]);
  function back() {
    setError("");
    if (mode === "library") onExit();
    else {
      epoch.current++;
      url("library");
      void refresh().catch((e) => setError(e.message));
    }
  }
  const buttonDisabled = busy || creating;
  const field = (f: FormData, k: string) => String(f.get(k) || "").trim();
  return (
    <>
      <header className="rh-top mc-top">
        <button className="rh-icon" aria-label="Back" onClick={back}>
          ‹
        </button>
        <div>
          <span className="rh-top-title">
            {mode === "library"
              ? "Your characters"
              : mode === "create"
                ? "Create a character"
                : person?.profile.name || "Character"}
          </span>
          <small>
            {mode === "create"
              ? "A PERSONALITY. A PORTRAIT."
              : picking
                ? "CHOOSE YOUR CAST"
                : "THE REHEARSAL STUDIO"}
          </small>
        </div>
        <button
          className="rh-icon"
          aria-label={
            person && mode === "detail" ? "Character options" : "New character"
          }
          disabled={buttonDisabled}
          onClick={() =>
            person && mode === "detail" ? setPanel("more") : startCreate()
          }
        >
          {person && mode === "detail" ? "···" : "＋"}
        </button>
      </header>
      {!panel && (error || notice) && (
        <div
          className={"rh-alert " + (error ? "error" : "")}
          role={error ? "alert" : "status"}
        >
          <span>{error || notice}</span>
          <div>
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
        </div>
      )}
      {mode === "library" && (
        <div className="rh-scroll rh-pad mc-library">
          <span className="rh-eyebrow">YOUR CAST, YOUR STORIES</span>
          <h1>
            Every story
            <br />
            <em>starts with someone.</em>
          </h1>
          <button
            className="rh-primary"
            aria-label="Create character"
            onClick={startCreate}
            disabled={buttonDisabled}
          >
            ＋ Create character <span>→</span>
          </button>
          {pending && (
            <button
              className="mc-pending"
              onClick={() => {
                setDescription(pending.description);
                url("create");
              }}
            >
              <span>✧</span>
              <span>
                <strong>Resume character creation</strong>
                <small>Your description and request are saved.</small>
              </span>
              <span>→</span>
            </button>
          )}
          <label className="rh-search">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              <circle cx="10" cy="10" r="7" />
              <path d="M15 15l6 6" />
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Find a character…"
              aria-label="Search characters"
            />
          </label>
          <div className="rh-filters">
            <button
              className={!archived ? "active" : ""}
              onClick={() => {
                setArchived(false);
                void refresh(false).catch((e) => setError(e.message));
              }}
            >
              My characters
            </button>
            <button
              className={archived ? "active" : ""}
              onClick={() => {
                setArchived(true);
                void refresh(true).catch((e) => setError(e.message));
              }}
            >
              Archived
            </button>
          </div>
          {loading ? (
            <p className="rh-muted">Opening your cast…</p>
          ) : (
            <div className="mc-character-grid">
              {list
                .filter((c) =>
                  (c.profile.name + " " + c.original_description)
                    .toLowerCase()
                    .includes(search.toLowerCase()),
                )
                .map((c) => (
                  <button
                    className="mc-character-card"
                    key={c.id}
                    onClick={() => open(c.id)}
                  >
                    <Picture character={c} large />
                    <span className="mc-character-caption">
                      <strong>{c.profile.name}</strong>
                      <small>
                        {c.profile.short_description || c.original_description}
                      </small>
                      <span>
                        {picking
                          ? "Choose for this scene"
                          : "Meet this character"}{" "}
                        →
                      </span>
                    </span>
                  </button>
                ))}
            </div>
          )}
          {!loading && !list.length && (
            <div className="rh-empty">
              <span className="mc-empty-star">✧</span>
              <p>
                {archived
                  ? "Your archived characters will appear here."
                  : "Someone only you could imagine."}
              </p>
              <small>
                {archived
                  ? "Return to My characters to keep creating."
                  : "Describe them. We will bring their personality and portrait together."}
              </small>
            </div>
          )}
        </div>
      )}
      {mode === "create" && (
        <>
          <div className="rh-scroll rh-pad mc-create">
            <span className="rh-eyebrow">BRING SOMEONE TO LIFE</span>
            <h1>
              Who do you
              <br />
              <em>have in mind?</em>
            </h1>
            <p className="mc-intro">
              One description. Their character and portrait, together.
            </p>
            <form
              id="mc-create"
              onSubmit={(e) => {
                e.preventDefault();
                void createCharacter(pending || undefined);
              }}
            >
              <label>
                Describe your character
                <textarea
                  value={pending ? pending.description : description}
                  onChange={(e) => {
                    setDescription(e.target.value);
                    localPut("character-description", e.target.value);
                  }}
                  rows={8}
                  required
                  maxLength={health?.max_profile_input_chars || 5000}
                  disabled={!!pending || creating}
                  placeholder="A reserved astronomer with silver hair and a quiet, dry wit. She wants to save her observatory, but hides how much she fears failing…"
                />
              </label>
              {!pending && (
                <button
                  className="rh-text-button"
                  type="button"
                  onClick={() => {
                    const value =
                      "A reserved astronomer with silver hair and a quiet, dry wit. She wants to save her observatory, but hides how much she fears failing. Her voice is gentle and precise.";
                    setDescription(value);
                    localPut("character-description", value);
                  }}
                >
                  Try an example description →
                </button>
              )}
              {(creating || pending) && (
                <div className="mc-creation-progress" role="status">
                  <div className={person ? "done" : ""}>
                    <span>{person ? "✓" : "01"}</span>
                    <p>
                      <strong>
                        {person ? "Character saved" : "Creating the character"}
                      </strong>
                      <small>
                        {person?.profile.name ||
                          "Personality, appearance and voice"}
                      </small>
                    </p>
                  </div>
                  <div className={person?.current_image_id ? "done" : ""}>
                    <span>{person?.current_image_id ? "✓" : "02"}</span>
                    <p>
                      <strong>
                        {person?.current_image_id
                          ? "Portrait ready"
                          : person
                            ? "Creating the portrait"
                            : "Portrait follows automatically"}
                      </strong>
                      <small>
                        {person
                          ? "Your character is safe while the portrait is generated."
                          : "No second Generate button needed."}
                      </small>
                    </p>
                  </div>
                </div>
              )}
              {pending && !creating && (
                <p className="rh-muted">
                  {error
                    ? "Your description is saved. Retry the same creation."
                    : "Checking the saved request. Resume if the connection was interrupted."}
                </p>
              )}
            </form>
          </div>
          <footer className="rh-form-footer">
            <button
              className="rh-primary"
              form="mc-create"
              disabled={
                creating ||
                busy ||
                !(pending?.description || description).trim()
              }
            >
              {creating
                ? "Creating character & portrait…"
                : pending
                  ? "Resume creation"
                  : "Create character"}
              <span>✧</span>
            </button>
            {pending && !creating && (
              <button
                className="rh-text-button mc-center"
                onClick={() => {
                  setDescription(pending.description);
                  setPending(null);
                  localPut("character-creation", null);
                }}
              >
                Keep description & start a new request
              </button>
            )}
          </footer>
        </>
      )}
      {mode === "detail" && person && (
        <>
          <div className="rh-scroll mc-detail">
            <div className="mc-character-cover">
              <Picture character={person} large />
              <div className="mc-cover-shade" />
              <div className="mc-cover-title">
                <span className="rh-eyebrow">
                  YOUR CHARACTER · VERSION {person.profile_version}
                </span>
                <h1>{person.profile.name}</h1>
                <p>{person.profile.short_description}</p>
              </div>
              <button
                className="mc-cover-edit"
                onClick={() => setPanel("portrait")}
              >
                Edit portrait →
              </button>
            </div>
            {imageError && (
              <div className="rh-alert error" role="alert">
                <span>{imageError}</span>
                <p>Your character is saved. Retry only the portrait.</p>
                <button
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      setPanel("portrait");
                      await makePortrait(false);
                    })
                  }
                >
                  Retry portrait
                </button>
              </div>
            )}
            <div className="rh-pad mc-profile-body">
              <div className="mc-edit-actions">
                <button
                  className="rh-secondary"
                  onClick={() => setPanel("profile")}
                >
                  Edit character
                </button>
                <button
                  className="rh-secondary"
                  onClick={() => {
                    setProposal(null);
                    setPanel("refine");
                  }}
                >
                  Refine with AI
                </button>
              </div>
              <div className="mc-facts">
                {[
                  ["WANTS", person.profile.wants],
                  ["VOICE", person.profile.speech_style?.tone],
                  [
                    "CORE TRAITS",
                    person.profile.personality?.core_traits?.join(" · "),
                  ],
                ]
                  .filter(([, v]) => !!v)
                  .map(([k, v]) => (
                    <section key={k}>
                      <span className="rh-eyebrow">{k}</span>
                      <p>{v}</p>
                    </section>
                  ))}
              </div>
              <details className="rh-details">
                <summary>
                  Background & private details <span>＋</span>
                </summary>
                {[
                  ["Background", person.profile.backstory],
                  ["Why it matters", person.profile.why_it_matters],
                  ["Fear or boundary", person.profile.fear],
                  ["Private information", person.profile.private_information],
                  ["Original description", person.original_description],
                ]
                  .filter(([, v]) => !!v)
                  .map(([k, v]) => (
                    <section className="mc-fact" key={k}>
                      <h3>{k}</h3>
                      <p>{v}</p>
                    </section>
                  ))}
              </details>
              <button
                className="rh-text-button"
                onClick={() => setPanel("history")}
              >
                Character version history →
              </button>
            </div>
          </div>
          <footer className="rh-form-footer">
            <button
              className="rh-primary"
              disabled={buttonDisabled}
              onClick={() =>
                run(async () => {
                  let c = person;
                  if (person.archived) {
                    await creator(
                      "/characters/" + person.id + "/archive",
                      { archived: false },
                      "PATCH",
                    );
                    c = await reloadPerson();
                    await changed();
                  }
                  if (picking) await onPick(c);
                  else await onStart(c);
                })
              }
            >
              {person.archived
                ? "Unarchive & rehearse"
                : picking
                  ? "Use in this scene"
                  : "Rehearse with " + person.profile.name}
              <span>→</span>
            </button>
          </footer>
        </>
      )}
      {panel && person && (
        <Panel
          title={
            {
              profile: "Shape your character",
              refine: "A little more like you imagined",
              portrait: "Their portrait",
              history: "Character versions",
              more: "Character options",
            }[panel]
          }
          close={() => {
            setPanel(null);
            setError("");
          }}
        >
          {error && (
            <div className="rh-alert error" role="alert">
              {error}
            </div>
          )}
          {panel === "profile" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                void run(async () => {
                  const p: Profile = {
                    ...person.profile,
                    name: field(f, "name"),
                    short_description: field(f, "short"),
                    wants: field(f, "wants"),
                    why_it_matters: field(f, "why"),
                    fear: field(f, "fear"),
                    private_information: field(f, "secret"),
                    backstory: field(f, "background"),
                    visual_style: field(f, "style"),
                    personality: {
                      ...person.profile.personality,
                      core_traits: field(f, "traits")
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean),
                    },
                    speech_style: {
                      ...person.profile.speech_style,
                      tone: field(f, "voice"),
                    },
                    appearance: {
                      ...person.profile.appearance,
                      ...Object.fromEntries(
                        [
                          "age_description",
                          "hair",
                          "eyes",
                          "clothing",
                          "other_details",
                        ].map((k) => [k, field(f, "appearance_" + k)]),
                      ),
                    },
                  };
                  const c = await api<Person>(
                    "/characters/" + person.id,
                    { profile: p, expected_version: person.profile_version },
                    "PATCH",
                  );
                  setPerson(c);
                  await changed();
                  setPanel(null);
                  setNotice(
                    "Character saved. Existing scenes keep their snapshots.",
                  );
                });
              }}
            >
              {[
                ["name", "Name", person.profile.name, 60],
                [
                  "short",
                  "One-line description",
                  person.profile.short_description,
                  500,
                ],
                ["wants", "What do they want?", person.profile.wants, 300],
                [
                  "traits",
                  "Core traits",
                  person.profile.personality?.core_traits?.join(", "),
                  1500,
                ],
                [
                  "voice",
                  "Speaking style",
                  person.profile.speech_style?.tone,
                  500,
                ],
                ["why", "Why it matters", person.profile.why_it_matters, 500],
                ["fear", "Fear or boundary", person.profile.fear, 300],
                [
                  "secret",
                  "Private information",
                  person.profile.private_information,
                  500,
                ],
                ["background", "Background", person.profile.backstory, 4000],
              ].map(([key, label, value, max]) => (
                <label key={String(key)}>
                  {label}
                  {key === "name" || key === "short" ? (
                    <input
                      name={String(key)}
                      defaultValue={String(value || "")}
                      maxLength={Number(max)}
                      required={key === "name"}
                    />
                  ) : (
                    <textarea
                      name={String(key)}
                      defaultValue={String(value || "")}
                      maxLength={Number(max)}
                      rows={key === "background" ? 4 : 2}
                    />
                  )}
                </label>
              ))}
              <details className="rh-details">
                <summary>
                  Appearance & portrait style <span>＋</span>
                </summary>
                {[
                  "age_description",
                  "hair",
                  "eyes",
                  "clothing",
                  "other_details",
                ].map((k) => (
                  <label key={k}>
                    {k.replaceAll("_", " ")}
                    <input
                      name={"appearance_" + k}
                      defaultValue={person.profile.appearance?.[k] || ""}
                      maxLength={500}
                    />
                  </label>
                ))}
                <label>
                  Portrait style
                  <input
                    name="style"
                    defaultValue={person.profile.visual_style}
                    maxLength={500}
                  />
                </label>
              </details>
              <button className="rh-primary" disabled={busy}>
                Save character
              </button>
            </form>
          )}
          {panel === "refine" && (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const text = field(
                    new FormData(e.currentTarget),
                    "instruction",
                  );
                  void run(async () =>
                    setProposal(
                      await api<Proposal>(
                        "/characters/" + person.id + "/refine",
                        {
                          instruction: text,
                          expected_version: person.profile_version,
                        },
                      ),
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
                <button className="rh-secondary" disabled={busy}>
                  Preview changes
                </button>
              </form>
              {proposal && (
                <div className="mc-proposal">
                  <p>{proposal.explanation}</p>
                  {proposal.changes.map((c, i) => (
                    <section key={i}>
                      <small>{c.path}</small>
                      <p>
                        <del>
                          {Array.isArray(c.before)
                            ? c.before.join(", ")
                            : c.before}
                        </del>
                        <span> → </span>
                        <strong>
                          {Array.isArray(c.after)
                            ? c.after.join(", ")
                            : c.after}
                        </strong>
                      </p>
                    </section>
                  ))}
                  <button
                    className="rh-primary"
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        const c = await api<Person>(
                          "/characters/" + person.id + "/refine/confirm",
                          { proposal_id: proposal.proposal_id },
                        );
                        setPerson(c);
                        setProposal(null);
                        await changed();
                        setPanel(null);
                      })
                    }
                  >
                    Apply these changes
                  </button>
                </div>
              )}
            </>
          )}
          {panel === "portrait" && (
            <>
              <Picture character={person} large />
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const instruction = field(
                    new FormData(e.currentTarget),
                    "instruction",
                  );
                  void run(async () => {
                    await makePortrait(!!person.current_image_id, instruction);
                  });
                }}
              >
                <label>
                  What should change in the portrait?
                  <textarea
                    name="instruction"
                    rows={3}
                    maxLength={2000}
                    required={!!person.current_image_id}
                    placeholder="Change her hair to auburn. Keep her face and clothing."
                  />
                </label>
                <button className="rh-primary" disabled={busy}>
                  {busy
                    ? "Creating a portrait…"
                    : person.current_image_id
                      ? "Edit portrait"
                      : "Generate portrait"}
                </button>
                <button
                  type="button"
                  className="rh-secondary mc-another"
                  disabled={busy}
                  onClick={() => run(() => makePortrait(false))}
                >
                  Try another portrait
                </button>
              </form>
              <h3 className="mc-versions-heading">Portrait versions</h3>
              <div className="mc-portrait-grid">
                {portraits.map((p) => (
                  <section key={p.id}>
                    <img src={p.url} alt={"Portrait version " + p.version} />
                    <small>Version {p.version}</small>
                    <button
                      className="rh-secondary"
                      disabled={busy || person.current_image_id === p.id}
                      onClick={() =>
                        run(async () => {
                          await api(
                            `/characters/${person.id}/images/${p.id}/select`,
                            {},
                          );
                          await reloadPerson();
                          await changed();
                          setImageError("");
                        })
                      }
                    >
                      {person.current_image_id === p.id
                        ? "Selected"
                        : "Use this portrait"}
                    </button>
                  </section>
                ))}
              </div>
              <p className="rh-muted">
                Portrait changes do not rewrite the character profile.
              </p>
            </>
          )}
          {panel === "history" && (
            <div className="rh-version-list">
              {revisions.map((r) => (
                <article key={r.version}>
                  <h3>
                    Version {r.version} · {r.profile.name}
                  </h3>
                  <p>{r.change_summary}</p>
                  <p>{r.profile.short_description}</p>
                  <button
                    className="rh-secondary"
                    disabled={busy || r.version === person.profile_version}
                    onClick={() =>
                      run(async () => {
                        const c = await api<Person>(
                          "/characters/" + person.id + "/restore",
                          {
                            version: r.version,
                            expected_version: person.profile_version,
                          },
                        );
                        setPerson(c);
                        await changed();
                        setPanel(null);
                      })
                    }
                  >
                    {r.version === person.profile_version
                      ? "Current version"
                      : "Restore as a new version"}
                  </button>
                </article>
              ))}
            </div>
          )}
          {panel === "more" && (
            <div className="rh-more-menu">
              <button
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const c = await creator<Person>(
                      "/characters/" + person.id + "/duplicate",
                      { request_id: operation() },
                    );
                    setPerson(c);
                    await changed();
                    url("detail", c.id);
                  })
                }
              >
                Duplicate character <span>→</span>
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await creator(
                      "/characters/" + person.id + "/archive",
                      { archived: !person.archived },
                      "PATCH",
                    );
                    await changed();
                    setPanel(null);
                    url("library");
                  })
                }
              >
                {person.archived ? "Unarchive character" : "Archive character"}
              </button>
              <button
                className="rh-danger"
                disabled={busy}
                onClick={() => {
                  if (
                    confirm(
                      "Delete this character and their companion history? Saved rehearsal snapshots remain.",
                    )
                  )
                    void run(async () => {
                      await api(
                        "/characters/" + person.id,
                        undefined,
                        "DELETE",
                      );
                      await changed();
                      url("library");
                    });
                }}
              >
                Delete character
              </button>
            </div>
          )}
        </Panel>
      )}
    </>
  );
}
