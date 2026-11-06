"use client";
import { MobileCharacterStudio } from "./mobile-character-studio";
import { countLines, visibleLines, readState } from "./rehearsal-reading";
import { useEffect, useRef, useState } from "react";
import {
  Actor,
  Block,
  Character,
  Choice,
  Command,
  Job,
  Node,
  Review,
  Scene,
  Setup,
  blankSetup,
  chain,
  localGet,
  scopeCache,
  clearSceneCache,
  localPut,
  operation,
  rehearsal,
  RehearsalError,
} from "./rehearsal-api";

type Page = "list" | "cast" | "setup" | "stage" | "review" | "characters";
type Panel =
  | "actor"
  | "intervene"
  | "direction"
  | "event"
  | "takeover"
  | "settings"
  | "versions"
  | "directions"
  | "paragraph"
  | "edit"
  | "replay"
  | "feedback"
  | "export"
  | "more"
  | "organize"
  | "rename"
  | null;
const example =
  "Years after a betrayal, Lin and Xu meet at a railway station. Lin knows what Xu did, but Xu believes the secret is still safe.";
function Glyph({ name }: { name: string }) {
  const paths: Record<string, string> = {
    star: "M12 2l2.7 7.3L22 12l-7.3 2.7L12 22l-2.7-7.3L2 12l7.3-2.7z",
    people:
      "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m13 10v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
    book: "M4 3h6a3 3 0 0 1 3 3v15a4 4 0 0 0-4-2H4zM13 6a3 3 0 0 1 3-3h5v16h-4a4 4 0 0 0-4 2",
    branch: "M7 3v12a5 5 0 0 0 10 0V9M4 6l3-3 3 3M14 12l3-3 3 3",
    pen: "M15 4l5 5M3 21l5-1L21 7l-5-5L3 15z",
    search: "M21 21l-5-5M18 10a8 8 0 1 0-16 0 8 8 0 0 0 16 0",
    event: "M12 3v18M3 12h18M5 5l14 14M5 19L19 5",
    chevron: "M9 5l7 7-7 7",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.star} />
    </svg>
  );
}
function Avatar({
  actor,
  size = "normal",
}: {
  actor: { name: string; avatar?: string | null };
  size?: string;
}) {
  const [bad, setBad] = useState(false);
  return (
    <span className={"rh-avatar " + size}>
      {actor.avatar && !bad ? (
        <img src={actor.avatar} alt={actor.name} onError={() => setBad(true)} />
      ) : (
        <span>{actor.name.slice(0, 1)}</span>
      )}
    </span>
  );
}
function Sheet({
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
      className="rh-sheet"
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
function SetupFields({
  value,
  onChange,
  actors,
  compact = false,
  tr,
}: {
  value: Setup;
  onChange: (s: Setup) => void;
  actors: Actor[];
  compact?: boolean;
  tr: (a: string, b: string) => string;
}) {
  const set = (k: keyof Setup, v: string | string[]) =>
    onChange({ ...value, [k]: v });
  return (
    <>
      <label>
        {tr("What situation are they in?", "把他们放进什么局面？")}
        <textarea
          name="premise"
          value={value.premise}
          onChange={(e) => set("premise", e.target.value)}
          minLength={10}
          maxLength={2000}
          rows={compact ? 4 : 6}
          required
          placeholder={example}
        />
        <small>
          {value.premise.length}/2000 ·{" "}
          {tr(
            "A place, a tension, something left unsaid.",
            "一个地点，一点张力，一句没说出口的话。",
          )}
        </small>
      </label>
      <label>
        {tr("What would you like to explore?", "你想看什么发生？")}{" "}
        <span className="rh-optional">{tr("optional", "可选")}</span>
        <textarea
          value={value.goal}
          onChange={(e) => set("goal", e.target.value)}
          maxLength={500}
          rows={2}
          placeholder={tr(
            "A gentle conversation that ends with a crack in their trust.",
            "表面温柔，最后关系出现裂痕。",
          )}
        />
      </label>
      <fieldset className="rh-format">
        <legend>{tr("Written as", "表现形式")}</legend>
        {(["prose", "script"] as const).map((f) => (
          <label key={f} className={value.format === f ? "selected" : ""}>
            <input
              type="radio"
              name="format"
              value={f}
              checked={value.format === f}
              onChange={() => set("format", f)}
            />
            {f === "prose"
              ? tr("Novel scene", "小说场景")
              : tr("Script dialogue", "剧本对白")}
          </label>
        ))}
      </fieldset>
      <details className="rh-details">
        <summary>
          {tr("Add scene details", "补充本场设定")}{" "}
          <span>{tr("optional", "可选")} ＋</span>
        </summary>
        <div>
          {(
            [
              ["relation", tr("Their relationship", "两人关系")],
              ["location", tr("Place", "地点")],
              ["time", tr("Time", "时间")],
              [
                "knowledge_a",
                `${actors[0]?.name || "A"} · ${tr("knows / believes", "知道什么／相信什么")}`,
              ],
              [
                "knowledge_b",
                `${actors[1]?.name || "B"} · ${tr("knows / believes", "知道什么／相信什么")}`,
              ],
            ] as [keyof Setup, string][]
          ).map(([k, label]) => (
            <label key={k}>
              {label}
              <textarea
                value={String(value[k])}
                onChange={(e) => set(k, e.target.value)}
                maxLength={1000}
                rows={2}
              />
            </label>
          ))}
          <label>
            {tr("Locked rules", "必须遵守的规则")}
            <textarea
              value={value.rules.join("\n")}
              onChange={(e) => {
                const rules = e.target.value.split("\n");
                e.target.setCustomValidity(
                  rules.filter((x) => x.trim()).length > 10 ||
                    rules.some((x) => x.length > 200)
                    ? tr(
                        "Use up to 10 rules, each no longer than 200 characters.",
                        "最多 10 条规则，每条不超过 200 字。",
                      )
                    : "",
                );
                set("rules", rules);
              }}
              rows={3}
              placeholder={tr(
                "One rule per line. Up to 10, 200 characters each.",
                "每行一条，最多 10 条，每条 200 字。",
              )}
            />
          </label>
        </div>
      </details>
    </>
  );
}
export function RehearsalApp() {
  const [lang, setLang] = useState<"en" | "zh">("en");
  const tr = (a: string, b: string) => (lang === "en" ? a : b);
  const [page, setPage] = useState<Page>("list");
  const [panel, setPanel] = useState<Panel>(null);
  const [scene, setScene] = useState<Scene | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [online, setOnline] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deps, setDeps] = useState<{ id: string; title: string }[]>([]);
  const [form, setForm] = useState<Setup>(blankSetup);
  const [cast, setCast] = useState<string[]>([]);
  const [slot, setSlot] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [actor, setActor] = useState<Actor | null>(null);
  const [selected, setSelected] = useState<{ node: Node; block: Block } | null>(
    null,
  );
  const [choices, setChoices] = useState<Choice[]>([]);
  const [review, setReview] = useState<Review | null>(null);
  const [reviewError, setReviewError] = useState("");
  const [job, setJob] = useState<string | null>(null);
  const [jobFailed, setJobFailed] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [roleText, setRoleText] = useState("");
  const [inputType, setInputType] = useState<"dialogue" | "action">("dialogue");
  const [font, setFont] = useState(17);
  const [unread, setUnread] = useState(false);
  const [characterPicking, setCharacterPicking] = useState(false);
  const [characterCreate, setCharacterCreate] = useState(false);
  const [characterMode, setCharacterMode] = useState("library");
  const [exportFormat, setExportFormat] = useState("txt");
  const [exportNames, setExportNames] = useState(true);
  const [exportTitle, setExportTitle] = useState(true);
  const [exportText, setExportText] = useState("");
  const [editText, setEditText] = useState("");
  const [editType, setEditType] = useState("plot");
  const [conflict, setConflict] = useState(false);
  const current = useRef<Scene | null>(null);
  current.current = scene;
  const commandGuard = useRef(false);
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());
  const commandQueue = useRef<Promise<unknown>>(Promise.resolve());
  const reader = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const progressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const visiblePage = useRef(page);
  visiblePage.current = page;
  const pollSequence = useRef(0);
  const pendingDraft = useRef<Setup | null>(null);
  const doc = scene?.document;
  const version = doc?.versions[doc.active_version];
  const nodes = scene && version ? chain(scene, version.head) : [];
  const totalLines = countLines(nodes);
  const revealed = Math.min(version?.revealed ?? totalLines, totalLines);
  const visibleNodes = visibleLines(nodes, revealed);
  const waitingLines = totalLines - revealed;
  const visibleText = visibleNodes
    .map((n) => n.blocks.map((b) => b.text).join(""))
    .join("");
  const lastReadingView = useRef("");
  useEffect(() => {
    if (page !== "stage") {
      lastReadingView.current = "";
      return;
    }
    const key = scene?.id + ":" + version?.id;
    if (lastReadingView.current !== key) {
      lastReadingView.current = key;
      return;
    }
    if (following.current)
      requestAnimationFrame(() =>
        reader.current?.scrollTo({
          top: reader.current.scrollHeight,
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
        }),
      );
    else setUnread(true);
  }, [page, scene?.id, version?.id, visibleText]);
  const actors = doc?.cast || [];
  const taken = actors.find((a) => a.id === version?.takeover);
  const state =
    readState(nodes, revealed, new Set(Object.keys(doc?.nodes || {}))) ||
    doc?.initial_state;
  function accept(s: Scene) {
    if (current.current?.id === s.id && current.current.revision > s.revision)
      return;
    current.current = s;
    setScene(s);
    setScenes((old) => [s, ...old.filter((x) => x.id !== s.id)]);
    localPut("scene:" + s.id, s);
  }
  function openCharacters(create = false, pick = false) {
    setCharacterPicking(pick);
    setCharacterCreate(create);
    setCharacterMode(create ? "create" : "library");
    setPanel(null);
    setError("");
    setNotice("");
    setPage("characters");
    const q = new URLSearchParams({ view: "characters" });
    if (create) q.set("create", "1");
    if (pick && current.current) {
      q.set("scene", current.current.id);
      q.set("pick", "1");
    }
    history.pushState(null, "", "/rehearsal?" + q);
  }
  async function rehearseWith(c: Character) {
    const s = await rehearsal<Scene>("/scenes", {
      operation_id: operation(),
      character_ids: [c.id],
      setup: { ...blankSetup, language: lang },
    });
    accept(s);
    setCast([c.id, ""]);
    setForm(s.document.setup);
    setSearch("");
    navigate("cast", s.id);
  }
  function navigate(p: Page, sid?: string) {
    setPage(p);
    setPanel(null);
    setError("");
    setNotice("");
    setSelected(null);
    const q = new URLSearchParams({ view: p });
    if (sid || (current.current?.id && p !== "list"))
      q.set("scene", sid || current.current!.id);
    history.pushState(null, "", "/rehearsal?" + q);
    reader.current?.scrollTo(0, 0);
  }
  async function loadScene(sid: string, p: Page) {
    try {
      const s = await rehearsal<Scene>("/scenes/" + sid);
      accept(s);
      setCast(
        [0, 1].map((i) => {
          const a = s.document.cast.find((a, j) => (a.slot ?? j) === i);
          return a?.source_character_id || a?.id || "";
        }),
      );
      const v = s.document.versions[s.document.active_version];
      const pending = localGet<Setup | null>("draft:" + sid, null);
      setForm(pending || v.setup);
      setJob(s.active_job || null);
      setJobFailed(null);
      if (s.active_job) {
        pollSequence.current = 0;
        setJob(s.active_job);
      }
      const divergent =
        !!pending &&
        JSON.stringify(pending) !== JSON.stringify(v.setup) &&
        localGet("draft-base:" + sid, s.revision) !== s.revision;
      setPage(p);
      setConflict(divergent);
      pendingDraft.current = pending;
      if (divergent)
        setError(
          "A newer revision exists. Keep your device draft as a new scene, or load the server version.",
        );
      const last = localGet<string | null>("last-job:" + sid, null);
      if (!s.active_job && last) {
        try {
          const j = await rehearsal<Job>("/jobs/" + last);
          if (j.status === "failed") {
            setJobFailed(last);
            setError(
              j.events.findLast((e) => !!e.error)?.error ||
                "This segment did not finish. Retry the response.",
            );
          }
        } catch {}
      }
    } catch (e) {
      if (e instanceof RehearsalError && [401, 403, 404].includes(e.status)) {
        current.current = null;
        setScene(null);
        setPage("list");
        setScenes([]);
        setCharacters([]);
        throw e;
      }
      const cached = localGet<Scene | null>("scene:" + sid, null);
      if (cached) {
        accept(cached);
        setPage(p);
        setForm(localGet("draft:" + sid, cached.document.setup));
        setNotice(
          tr(
            "Showing a device copy. Reconnect to sync.",
            "正在显示本机副本，联网后同步。",
          ),
        );
      } else throw e;
    }
  }
  async function refresh() {
    const account = await fetch("/api/account/session", {
      cache: "no-store",
    }).then((r) => r.json());
    if (!account.authenticated && !account.setup_required)
      throw new RehearsalError("Sign in to open your studio.", 401);
    scopeCache(account.username || "local");
    const health = await fetch("/api/health").then((r) => r.json());
    if (health.rehearsal_database_ready === false)
      throw new Error(
        "Rehearsal needs a database update. Run alembic upgrade head in the project root, then restart the backend.",
      );
    const [ss, cc] = await Promise.all([
      rehearsal<Scene[]>("/scenes"),
      rehearsal<Character[]>("/characters"),
    ]);
    setScenes(ss);
    setCharacters(cc);
    localPut("scenes", ss);
    localPut("characters", cc);
  }
  function report(e: unknown) {
    if (e instanceof RehearsalError) {
      setError(e.message);
      setDeps(e.dependencies || []);
      if (e.status === 409 && e.message.includes("revision")) setConflict(true);
    } else setError((e as Error).message || "Please try again.");
  }
  async function task(fn: () => Promise<void>) {
    if (commandGuard.current) return;
    commandGuard.current = true;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      report(e);
    } finally {
      commandGuard.current = false;
      setBusy(false);
    }
  }
  useEffect(() => {
    setLang(localGet("language", "en"));
    setFont(localGet("font", 17));
    setOnline(navigator.onLine);
    const connection = () => setOnline(navigator.onLine);
    window.addEventListener("online", connection);
    window.addEventListener("offline", connection);
    let active = true;
    async function load() {
      try {
        await refresh();
        setLang(localGet("language", "en"));
        setFont(localGet("font", 17));
        const q = new URLSearchParams(location.search);
        setCharacterPicking(q.get("pick") === "1");
        setCharacterCreate(q.get("create") === "1");
        const sid = q.get("scene");
        if (sid) await loadScene(sid, (q.get("view") as Page) || "stage");
        else if (active)
          setPage(q.get("view") === "characters" ? "characters" : "list");
      } catch (e) {
        const denied =
          e instanceof RehearsalError && [401, 403, 404].includes(e.status);
        setScenes(denied ? [] : localGet("scenes", []));
        setCharacters(denied ? [] : localGet("characters", []));
        report(e);
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    const back = () => {
      const q = new URLSearchParams(location.search);
      setCharacterPicking(q.get("pick") === "1");
      setCharacterCreate(q.get("create") === "1");
      if (q.get("scene"))
        void loadScene(
          q.get("scene")!,
          (q.get("view") as Page) || "stage",
        ).catch(report);
      else setPage(q.get("view") === "characters" ? "characters" : "list");
    };
    window.addEventListener("popstate", back);
    return () => {
      active = false;
      window.removeEventListener("popstate", back);
      window.removeEventListener("online", connection);
      window.removeEventListener("offline", connection);
    };
  }, []);
  useEffect(() => {
    const viewport = window.visualViewport;
    const resize = () =>
      document.documentElement.style.setProperty(
        "--rh-vh",
        `${viewport?.height || innerHeight}px`,
      );
    resize();
    viewport?.addEventListener("resize", resize);
    return () => {
      viewport?.removeEventListener("resize", resize);
      document.documentElement.style.removeProperty("--rh-vh");
    };
  }, []);
  function send(
    cmd: Command,
    oid = operation(),
  ): Promise<Scene & { job_id?: string | null }> {
    const target = current.current?.id;
    const originVersion = current.current?.document.active_version;
    const next = commandQueue.current
      .catch(() => {})
      .then(() => {
        if (current.current?.id !== target)
          throw new Error(
            "The scene changed. Your previous input is still saved.",
          );
        return executeSend(
          { ...cmd, version_id: cmd.version_id || originVersion },
          oid,
        );
      });
    commandQueue.current = next;
    return next;
  }
  async function executeSend(
    cmd: Command,
    oid = operation(),
  ): Promise<Scene & { job_id?: string | null }> {
    const s = current.current;
    if (!s) throw new Error("Open a scene first.");
    if (!navigator.onLine)
      throw new Error(
        tr(
          "Reconnect before rehearsing. Your device draft is safe.",
          "请联网后排练，本机草稿已保留。",
        ),
      );
    const payload = {
      ...cmd,
      operation_id: oid,
      expected_revision: s.revision,
    };
    localPut("pending:" + s.id, payload);
    const next = await rehearsal<Scene & { job_id?: string }>(
      "/scenes/" + s.id + "/commands",
      payload,
    );
    if (current.current?.id === s.id) {
      accept(next);
      if (next.job_id) {
        pollSequence.current = 0;
        setJob(next.job_id);
        localPut("last-job:" + s.id, next.job_id);
        localPut("job-version:" + next.job_id, next.document.active_version);
        setJobFailed(null);
        setElapsed(0);
      }
    }
    localPut("pending:" + s.id, null);
    return next;
  }
  async function syncSetup(value: Setup) {
    setSaving(true);
    try {
      await send({
        kind: "setup",
        setup: { ...value, rules: value.rules.filter((x) => x.trim()) },
      });
      localPut("draft:" + current.current!.id, null);
      pendingDraft.current = null;
    } finally {
      setSaving(false);
    }
  }
  useEffect(() => {
    if (page !== "setup" || !scene || !online || job || busy || conflict)
      return;
    if (
      form.rules.filter((r) => r.trim()).length > 10 ||
      form.rules.some((r) => r.length > 200)
    )
      return;
    const saved = scene.document.versions[scene.document.active_version].setup;
    if (JSON.stringify(form) === JSON.stringify(saved)) return;
    const timer = setTimeout(() => {
      saveQueue.current = saveQueue.current
        .catch(() => {})
        .then(() => syncSetup(form))
        .catch(report);
    }, 800);
    return () => clearTimeout(timer);
  }, [form, page, online, busy, conflict, scene?.id]);
  function updateForm(s: Setup) {
    setForm(s);
    if (!pendingDraft.current && scene)
      localPut("draft-base:" + scene.id, scene.revision);
    pendingDraft.current = s;
    if (scene && !localPut("draft:" + scene.id, s))
      setNotice(
        tr(
          "Device storage unavailable. Keep this page open until synced.",
          "本机存储不可用，请等同步后离开。",
        ),
      );
  }
  useEffect(() => {
    const key = scene && taken ? `role:${scene.id}:${taken.id}` : "";
    setRoleText(key ? localGet(key, "") : "");
  }, [scene?.id, taken?.id]);
  useEffect(() => {
    if (!job) return;
    let active = true;
    const started = Date.now();
    let timer: ReturnType<typeof setTimeout>;
    const elapsedTimer = setInterval(
      () => setElapsed(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    async function poll() {
      try {
        const j = await rehearsal<Job>(
          "/jobs/" + job + "?after=" + pollSequence.current,
        );
        if (!active) return;
        const events = j.events.filter(
          (e) => e.sequence > pollSequence.current,
        );
        for (const e of events) {
          pollSequence.current = Math.max(pollSequence.current, e.sequence);
          if (e.error) {
            setError(e.error);
            setJobFailed(job);
          }
          if (e.ending)
            setNotice(
              tr(
                "This could be a natural place to end the scene.",
                "这一场可以在这里结束。",
              ),
            );
        }
        if (current.current?.id === j.scene.id) {
          accept(j.scene);
        }
        if (["completed", "cancelled", "failed"].includes(j.status)) {
          setJob(null);
          if (j.status === "cancelled")
            setNotice(
              tr(
                "Stopped at the last complete paragraph.",
                "已停在上一段完整内容。",
              ),
            );
          if (j.status === "failed") setJobFailed(job);
          if (j.status === "completed" && !localGet("tip-seen", false)) {
            setNotice(
              tr(
                "Take your time. Next line reveals one sentence; step in whenever you like.",
                "随时暂停，改变一句话或亲自演一个角色。",
              ),
            );
            localPut("tip-seen", true);
          }
          return;
        }
      } catch (e) {
        if (active)
          setNotice(
            tr(
              "Connection interrupted. Checking the saved performance…",
              "连接中断，正在确认已保存的排练…",
            ),
          );
      }
      if (active) timer = setTimeout(poll, 500);
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
      clearInterval(elapsedTimer);
    };
  }, [job]);
  useEffect(() => {
    if (page !== "stage" || !reader.current || !version) return;
    const r = reader.current;
    r.scrollTop = version.position;
    following.current = r.scrollHeight - r.scrollTop - r.clientHeight < 100;
  }, [page, version?.id]);
  async function newScene(demo = false, source?: Scene) {
    await task(async () => {
      const old = localGet<{
        operation_id: string;
        demo: boolean;
        source_scene_id?: string;
      } | null>("create-pending", null);
      const body =
        old && old.demo === demo && old.source_scene_id === source?.id
          ? old
          : {
              operation_id: operation(),
              demo,
              ...(source ? { source_scene_id: source.id } : {}),
            };
      localPut("create-pending", body);
      const setup: Setup = {
        ...blankSetup,
        language: lang,
        ...(demo
          ? {
              premise: example,
              goal: "A gentle conversation with a fracture beneath it.",
              knowledge_a: "Lin knows Xu betrayed her.",
              knowledge_b: "Xu believes Lin does not know.",
            }
          : {}),
      };
      const s = await rehearsal<Scene>("/scenes", { ...body, setup });
      accept(s);
      setJob(null);
      setJobFailed(null);
      setForm(setup);
      setCast([0, 1].map((i) => s.document.cast[i]?.id || ""));
      setSearch("");
      localPut("create-pending", null);
      navigate(demo || source ? "setup" : "cast", s.id);
    });
  }
  async function choose(c: Character) {
    const old = cast.slice();
    let index = slot;
    if (index === null) {
      index = [0, 1].find((i) => !old[i]) ?? null;
    }
    if (index === null) {
      setActor({
        id: c.id,
        source_character_id: c.id,
        name: c.profile.name,
        avatar: c.current_image_id
          ? `/api/characters/${c.id}/images/${c.current_image_id}/file`
          : null,
        description: c.original_description,
        profile: c.profile,
        snapshot_revision: c.profile_version,
      });
      setNotice(tr("Choose A or B to replace.", "请选择替换 A 或 B。"));
      setPanel("actor");
      return;
    }
    if (old.includes(c.id) && old[index] !== c.id) {
      setNotice(tr("Choose two different characters.", "请选择两位不同角色。"));
      return;
    }
    old[index] = c.id;
    const clean = [old[0] || "", old[1] || ""];
    setCast(clean);
    setSlot(null);
    localPut("cast:" + scene!.id, clean);
    await task(async () => {
      await send({ kind: "cast", character_ids: clean.map((x) => x || null) });
    });
  }
  async function begin() {
    await task(async () => {
      if (conflict)
        throw new Error("Resolve the newer revision before starting.");
      await saveQueue.current;
      await syncSetup(form);
      const next = await send({ kind: "continue" });
      navigate("stage", next.id);
      following.current = true;
    });
  }
  async function enterReview() {
    setError("");
    try {
      const s = current.current!;
      const v = s.document.versions[s.document.active_version];
      if (
        (v.revealed ?? countLines(chain(s, v.head))) <
        countLines(chain(s, v.head))
      )
        await send({ kind: "settle" });
    } catch (e) {
      report(e);
      return;
    }
    navigate("review");
    setReview(null);
    setReviewError("");
    const s = current.current!;
    const v = s.document.versions[s.document.active_version];
    const key = `review:${s.id}:${v.id}:${v.head}`;
    const saved = localGet<Review | null>(key, null);
    if (saved) {
      setReview(saved);
      return;
    }
    try {
      const oid = localGet(key + ":operation", "") || operation();
      localPut(key + ":operation", oid);
      const r = await rehearsal<Review>("/scenes/" + s.id + "/review", {
        operation_id: oid,
        version_id: v.id,
      });
      if (current.current?.id === s.id) {
        setReview(r);
        localPut(key, r);
      }
    } catch {
      setReviewError(
        tr(
          "Summary unavailable. You can still save and export the full scene.",
          "摘要暂不可用，你仍可保存和导出正文。",
        ),
      );
    }
  }
  async function showDirections() {
    setPanel("directions");
    setChoices([]);
    await task(async () => {
      const s = current.current!;
      const v = s.document.versions[s.document.active_version];
      const head = selected?.node.id || v.head;
      const key = `choices:${s.id}:${v.id}:${head}:read-${v.revealed ?? countLines(chain(s, v.head))}`;
      let result = localGet<{ options: Choice[] } | null>(key, null);
      if (!result) {
        const oid = localGet(key + ":operation", "") || operation();
        localPut(key + ":operation", oid);
        result = await rehearsal("/scenes/" + s.id + "/directions", {
          operation_id: oid,
          version_id: v.id,
          node_id: head || "",
        });
        localPut(key, result);
      }
      setChoices(result!.options);
    });
  }
  async function prepareExport() {
    const s = current.current!;
    const q = new URLSearchParams({
      version_id: s.document.active_version,
      format: exportFormat,
      include_names: String(exportNames),
      include_title: String(exportTitle),
      visible_only: "true",
    });
    const r = await fetch(`/api/rehearsal/scenes/${s.id}/export?${q}`);
    if (!r.ok) throw new Error("Could not prepare export.");
    const text = await r.text();
    setExportText(text);
    return text;
  }
  function back() {
    if (page === "cast") {
      navigate("list");
      void refresh().catch(report);
    } else if (page === "setup")
      navigate(doc?.source || doc?.demo ? "list" : "cast");
    else if (page === "review") navigate("stage");
    else {
      navigate("list");
      void refresh().catch(report);
    }
  }
  function scrolling() {
    const r = reader.current;
    if (!r || !version || page !== "stage") return;
    following.current = r.scrollHeight - r.scrollTop - r.clientHeight < 100;
    if (following.current) setUnread(false);
    if (progressTimer.current) clearTimeout(progressTimer.current);
    const pos = Math.round(r.scrollTop);
    progressTimer.current = setTimeout(() => {
      if (current.current?.id === scene?.id && !job && !commandGuard.current)
        void send({ kind: "progress", position: pos }).catch(() => {});
    }, 1000);
  }
  const titles: Record<NonNullable<Panel>, string> = {
    actor: actor?.name || tr("Character", "角色"),
    intervene: tr("How would you like to step in?", "你想怎样改变这一场？"),
    direction: tr("Give a direction", "给一句导演指令"),
    event: tr("Introduce an event", "加入一个事件"),
    takeover: tr("Step into a character", "我来演一个角色"),
    settings: tr("Cast & scene", "人物与本场设定"),
    versions: tr("Versions of this scene", "本场版本"),
    directions: tr("What if…", "其他走向"),
    paragraph: tr("This paragraph", "这段内容"),
    edit: tr("Edit this paragraph", "编辑这段"),
    replay: tr("Try a different reaction", "换一种反应"),
    feedback: tr("Help this character feel right", "人物反应不对"),
    export: tr("Take the scene with you", "导出本场"),
    more: tr("Your creative space", "创作空间"),
    organize: tr("Review your setup", "整理设定"),
    rename: tr("Give this scene a name", "重命名本场"),
  };
  const syncLabel = !online
    ? tr("Offline · device draft", "离线 · 本机草稿")
    : saving
      ? tr("Syncing…", "同步中…")
      : conflict
        ? tr("Not synced", "尚未同步")
        : pendingDraft.current
          ? tr("Device draft · waiting to sync", "本机草稿 · 等待同步")
          : tr("Saved automatically", "已自动保存");
  function bodyBlocks(list: Node[], readOnly = false) {
    return list.map((n, i) => (
      <section className="rh-segment" key={n.id}>
        <header>
          <span>
            {tr("SEGMENT", "片段")} {String(i + 1).padStart(2, "0")}
          </span>
          {n.source === "author" && (
            <small>{tr("Author edit", "作者编辑")}</small>
          )}
        </header>
        {n.blocks.map((b) => {
          const who = actors.find((a) => a.id === b.character_id);
          return (
            <div className={"rh-block " + b.type} key={b.id}>
              {who && b.type !== "narration" && (
                <div className="rh-speaker">
                  <Avatar actor={who} size="tiny" />
                  <strong>{who.name}</strong>
                  {b.locked && (
                    <small>
                      {tr("Your words · locked", "你的文字 · 已锁定")}
                    </small>
                  )}
                </div>
              )}
              <p>{b.text}</p>
              {!readOnly && (
                <button
                  className="rh-block-menu"
                  aria-label={tr("Paragraph options", "段落操作") + " " + b.id}
                  disabled={!!job}
                  onClick={() => {
                    setSelected({ node: n, block: b });
                    setEditText(b.text);
                    setPanel("paragraph");
                  }}
                >
                  ···
                </button>
              )}
            </div>
          );
        })}
        {n.state_review && (
          <small className="rh-warning">
            {tr(
              "Wording changed · review the scene state.",
              "文字已修改，请复核场景状态。",
            )}
          </small>
        )}
      </section>
    ));
  }
  return (
    <main
      className={"rehearsal-app rh-" + page}
      data-working={busy ? "true" : "false"}
      data-generating={job ? "true" : "false"}
      style={{ "--rh-reading": font + "px" } as React.CSSProperties}
    >
      {page !== "characters" && (
        <>
          <header className="rh-top">
            <button
              className="rh-icon"
              aria-label={page === "list" ? "Studio settings" : "Back"}
              onClick={() => (page === "list" ? setPanel("more") : back())}
            >
              {page === "list" ? <Glyph name="star" /> : "‹"}
            </button>
            <div>
              {page === "list" ? (
                <>
                  <span className="rh-brand">EchoLoom</span>
                  <small>THE REHEARSAL STUDIO</small>
                </>
              ) : (
                <>
                  <span className="rh-top-title">
                    {page === "cast"
                      ? tr("Choose your cast", "选择角色")
                      : page === "setup"
                        ? tr("Set the scene", "设置开场")
                        : doc?.title}
                  </span>
                  <small>
                    {page === "cast" ? (
                      "01 / 02"
                    ) : page === "setup" ? (
                      "02 / 02"
                    ) : (
                      <button
                        className="rh-version-link"
                        onClick={() => setPanel("versions")}
                      >
                        {tr("Version", "版本")} {version?.label} <span>⌄</span>
                      </button>
                    )}
                  </small>
                </>
              )}
            </div>
            <button
              className="rh-icon"
              aria-label="More options"
              onClick={() => setPanel("more")}
            >
              ···
            </button>
          </header>
        </>
      )}
      {(error || notice || !online) && (
        <div
          className={"rh-alert " + (error ? "error" : "")}
          role={error ? "alert" : "status"}
        >
          <span>
            {error ||
              (!online
                ? tr(
                    "Offline. Your saved scenes and device drafts are available.",
                    "已离线，已保存内容和本机草稿仍可阅读。",
                  )
                : notice)}
          </span>
          <div>
            {jobFailed && (
              <button
                onClick={() =>
                  task(async () => {
                    const r = await rehearsal<{ job_id: string }>(
                      "/jobs/" + jobFailed + "/retry",
                      {},
                    );
                    pollSequence.current = 0;
                    setJob(r.job_id);
                    if (scene) localPut("last-job:" + scene.id, r.job_id);
                    setJobFailed(null);
                  })
                }
              >
                {tr("Retry response", "重试回复")}
              </button>
            )}
            {error && !jobFailed && (
              <button
                onClick={() => {
                  setError("");
                  void refresh().catch(report);
                }}
              >
                {tr("Retry", "重试")}
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
          {deps.map((d) => (
            <button
              key={d.id}
              onClick={() => {
                void loadScene(d.id, "stage");
                navigate("stage", d.id);
              }}
            >
              {d.title} →
            </button>
          ))}
          {conflict && (
            <>
              <button
                onClick={() => {
                  localPut("draft:" + scene!.id, null);
                  pendingDraft.current = null;
                  void loadScene(scene!.id, page).catch(report);
                }}
              >
                {tr("Load server version", "加载服务器版本")}
              </button>
              <button
                onClick={() =>
                  task(async () => {
                    const s = await rehearsal<Scene>("/scenes", {
                      operation_id: operation(),
                      character_ids: cast,
                      setup: form,
                    });
                    accept(s);
                    setConflict(false);
                    navigate("setup", s.id);
                  })
                }
              >
                {tr("Save my setup as a new scene", "将本机设定另存一场")}
              </button>
            </>
          )}
        </div>
      )}
      {loading ? (
        <div className="rh-empty">
          <Glyph name="star" />
          <p>{tr("Opening your studio…", "正在打开创作空间…")}</p>
        </div>
      ) : (
        <>
          {page === "characters" && (
            <MobileCharacterStudio
              initialCreate={characterCreate}
              picking={characterPicking}
              onMode={setCharacterMode}
              onExit={() => {
                navigate(characterPicking ? "cast" : "list");
                void refresh().catch(report);
              }}
              onChanged={refresh}
              onPick={async (c) => {
                if (cast.includes(c.id))
                  throw new Error(
                    "This character is already in this scene. Choose someone else.",
                  );
                const i = slot ?? [0, 1].find((i) => !cast[i]);
                if (i === undefined) {
                  navigate("cast");
                  setActor({
                    id: c.id,
                    source_character_id: c.id,
                    name: c.profile.name,
                    avatar: c.current_image_id
                      ? `/api/characters/${c.id}/images/${c.current_image_id}/file`
                      : null,
                    description: c.original_description,
                    profile: c.profile,
                    snapshot_revision: c.profile_version,
                  });
                  setPanel("actor");
                  return;
                }
                const next = cast.slice();
                next[i] = c.id;
                await send({
                  kind: "cast",
                  character_ids: next.map((x) => x || null),
                });
                setCast(next);
                navigate("cast");
              }}
              onStart={rehearseWith}
            />
          )}
          {page === "list" && (
            <div className="rh-scroll">
              <section className="rh-hero">
                <div className="rh-constellation" aria-hidden="true">
                  ✧<span>·</span>✦<i>✧</i>
                </div>
                <span className="rh-eyebrow">
                  {tr(
                    "A LITTLE STAGE. ENDLESS POSSIBILITIES.",
                    "让灵感，在这里登场。",
                  )}
                </span>
                <h1>
                  {tr("Let your characters,", "让角色，")}
                  <br />
                  <em>{tr("play it out.", "把故事演出来。")}</em>
                </h1>
                <p>
                  {tr("Two characters. One situation.", "两个人物，一个局面。")}
                  <br />
                  {tr(
                    "See what happens when they meet.",
                    "看看相遇之后，故事会往哪里走。",
                  )}
                </p>
                <button
                  className="rh-primary"
                  disabled={busy || !online}
                  onClick={() => newScene()}
                >
                  <span>＋</span>
                  {tr("Rehearse a scene", "排一场戏")}
                  <span>→</span>
                </button>
                <div className="rh-stage-art" aria-hidden="true">
                  <div className="rh-orbit" />
                  <div className="rh-art-person a">
                    <img src="/creator/mira.svg" alt="" />
                    <span>LIN</span>
                  </div>
                  <div className="rh-art-person b">
                    <img src="/creator/leo.svg" alt="" />
                    <span>XU</span>
                  </div>
                  <div className="rh-art-caption">
                    <span>✧</span>
                    {tr(
                      "Every scene starts with someone.",
                      "故事，从人物开始。",
                    )}
                  </div>
                </div>
              </section>
              <section className="rh-library">
                <div className="rh-section-title">
                  <h2>{tr("Your rehearsals", "我的排戏")}</h2>
                  <button
                    className="rh-icon"
                    aria-label="Search rehearsals"
                    onClick={() =>
                      document.getElementById("scene-search")?.focus()
                    }
                  >
                    <Glyph name="search" />
                  </button>
                </div>
                <label className="rh-search">
                  <Glyph name="search" />
                  <input
                    id="scene-search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder={tr("Find a scene…", "搜索场景…")}
                    aria-label="Search scenes"
                  />
                </label>
                <div className="rh-filters">
                  {[
                    ["all", tr("All", "全部")],
                    ["rehearsing", tr("In rehearsal", "排练中")],
                    ["saved", tr("Saved", "已保存")],
                  ].map(([id, label]) => (
                    <button
                      key={id}
                      className={filter === id ? "active" : ""}
                      onClick={() => setFilter(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {scenes
                  .filter(
                    (s) =>
                      (filter === "all" || s.document.status === filter) &&
                      s.document.title
                        .toLowerCase()
                        .includes(search.toLowerCase()),
                  )
                  .map((s) => (
                    <article className="rh-scene-card" key={s.id}>
                      <button
                        className="rh-card-open"
                        onClick={() => {
                          const p =
                            s.document.status === "draft"
                              ? s.document.cast.length === 2
                                ? "setup"
                                : "cast"
                              : s.document.status === "saved"
                                ? "review"
                                : "stage";
                          void loadScene(s.id, p)
                            .then(() => {
                              navigate(p, s.id);
                              if (p === "review") void enterReview();
                            })
                            .catch(report);
                        }}
                      >
                        <div className="rh-double-avatar">
                          {s.document.cast.slice(0, 2).map((a) => (
                            <Avatar actor={a} key={a.id} />
                          ))}
                          {!s.document.cast.length && (
                            <span className="rh-empty-cast">
                              <Glyph name="people" />
                            </span>
                          )}
                        </div>
                        <div>
                          <span className={"rh-badge " + s.document.status}>
                            {s.document.demo ? "DEMO · " : ""}
                            {s.document.status === "draft"
                              ? tr("DRAFT", "草稿")
                              : s.document.status === "saved"
                                ? tr("SAVED RESULT", "已保存结果")
                                : tr("IN REHEARSAL", "排练中")}
                          </span>
                          <h3>
                            {s.document.title === "未命名场景"
                              ? tr("Untitled scene", "未命名场景")
                              : s.document.title}
                          </h3>
                          <p>
                            {s.document.setup.premise ||
                              tr(
                                "Your scene is waiting for its cast.",
                                "这场戏，正在等待人物登场。",
                              )}
                          </p>
                          <small>
                            {s.document.cast.map((a) => a.name).join(" & ")}
                            {s.document.cast.length ? " · " : ""}
                            {new Date(s.updated_at).toLocaleDateString(
                              lang === "en" ? "en-US" : "zh-CN",
                              { month: "short", day: "numeric" },
                            )}
                          </small>
                        </div>
                        <span>›</span>
                      </button>
                      <button
                        className="rh-card-more rh-icon"
                        aria-label={"Scene options " + s.document.title}
                        onClick={() => {
                          accept(s);
                          setPanel("rename");
                        }}
                      >
                        ···
                      </button>
                    </article>
                  ))}
                {!scenes.length && (
                  <div className="rh-empty-list">
                    <Glyph name="pen" />
                    <p>
                      {tr("Let two characters meet.", "让两个角色相遇。")}
                      <small>
                        {tr(
                          "A moment you have in mind can become a scene.",
                          "一个心里的片段，也可以成为一场戏。",
                        )}
                      </small>
                    </p>
                  </div>
                )}
                <button
                  className="rh-example"
                  onClick={() => newScene(true)}
                  disabled={busy || !online}
                >
                  <span className="rh-example-star">✧</span>
                  <span>
                    <small>
                      {tr("TRY A PREPARED EXAMPLE", "体验预置示例")} · DEMO
                    </small>
                    <strong>{tr("The station reunion", "车站重逢")}</strong>
                    <span>
                      {tr(
                        "Two old friends. One unspoken secret.",
                        "两位故人，一个未说破的秘密。",
                      )}
                    </span>
                  </span>
                  <span>→</span>
                </button>
              </section>
            </div>
          )}
          {page === "cast" && (
            <>
              <div className="rh-scroll rh-pad">
                <span className="rh-eyebrow">
                  {tr("01 / 02 · THE CAST", "01 / 02 · 选择角色")}
                </span>
                <h1>
                  {tr("Who is in", "这场戏，")}
                  <br />
                  <em>{tr("this scene?", "谁来演？")}</em>
                </h1>
                <div className="rh-cast-slots">
                  {[0, 1].map((i) => {
                    const c = characters.find((c) => c.id === cast[i]);
                    const a = c
                      ? {
                          name: c.profile.name,
                          avatar: c.current_image_id
                            ? `/api/characters/${c.id}/images/${c.current_image_id}/file`
                            : null,
                        }
                      : null;
                    return (
                      <div
                        className={
                          "rh-cast-slot " + (slot === i ? "selected" : "")
                        }
                        key={i}
                      >
                        <button onClick={() => setSlot(i)}>
                          <span className="rh-slot-letter">
                            {i ? "B" : "A"}
                          </span>
                          {a ? (
                            <Avatar actor={a} size="large" />
                          ) : (
                            <span className="rh-add-circle">＋</span>
                          )}
                          <strong>
                            {a?.name || tr("Choose a character", "选择角色")}
                          </strong>
                        </button>
                        {a && (
                          <button
                            className="rh-remove"
                            aria-label={"Remove " + a.name}
                            onClick={() => {
                              const next = cast.slice();
                              next[i] = "";
                              setCast(next);
                              void task(async () => {
                                await send({
                                  kind: "cast",
                                  character_ids: next.map((x) => x || null),
                                });
                              });
                            }}
                          >
                            ×
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="rh-section-title">
                  <h2>{tr("Your characters", "我的角色")}</h2>
                  <button
                    className="rh-text-button"
                    onClick={() => openCharacters(true, true)}
                  >
                    ＋ {tr("Create", "创建")}
                  </button>
                </div>
                <label className="rh-search">
                  <Glyph name="search" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder={tr("Search your cast", "搜索人物")}
                    aria-label="Search characters"
                  />
                </label>
                <div className="rh-character-list">
                  {characters
                    .filter((c) =>
                      (c.profile.name + " " + c.original_description)
                        .toLowerCase()
                        .includes(search.toLowerCase()),
                    )
                    .map((c) => (
                      <article
                        className={cast.includes(c.id) ? "selected" : ""}
                        key={c.id}
                      >
                        <button
                          className="rh-character-pick"
                          disabled={busy}
                          onClick={() => choose(c)}
                        >
                          <Avatar
                            actor={{
                              name: c.profile.name,
                              avatar: c.current_image_id
                                ? `/api/characters/${c.id}/images/${c.current_image_id}/file`
                                : null,
                            }}
                          />
                          <span>
                            <strong>{c.profile.name}</strong>
                            <small>
                              {c.profile.short_description ||
                                c.original_description}
                            </small>
                          </span>
                          <span className="rh-picked">
                            {cast.includes(c.id)
                              ? ["A", "B"][cast.indexOf(c.id)]
                              : "＋"}
                          </span>
                        </button>
                        <button
                          className="rh-icon"
                          aria-label={"Details for " + c.profile.name}
                          onClick={() => {
                            setActor({
                              id: c.id,
                              source_character_id: c.id,
                              name: c.profile.name,
                              avatar: c.current_image_id
                                ? `/api/characters/${c.id}/images/${c.current_image_id}/file`
                                : null,
                              description: c.original_description,
                              profile: c.profile,
                              snapshot_revision: c.profile_version,
                            });
                            setPanel("actor");
                          }}
                        >
                          ⓘ
                        </button>
                      </article>
                    ))}
                </div>
                {!characters.length && (
                  <div className="rh-empty">
                    <p>
                      {tr(
                        "Create two characters to take the stage.",
                        "创建两个人物，让他们登场。",
                      )}
                    </p>
                    <button
                      className="rh-secondary"
                      onClick={() => openCharacters(true, true)}
                    >
                      ＋ {tr("Create character", "创建角色")}
                    </button>
                  </div>
                )}
              </div>
              <footer className="rh-form-footer">
                <small className="rh-sync">{syncLabel}</small>
                <button
                  className="rh-primary"
                  disabled={
                    cast.filter(Boolean).length !== 2 ||
                    new Set(cast).size !== 2 ||
                    busy ||
                    !online
                  }
                  onClick={() => {
                    setSearch("");
                    navigate("setup");
                  }}
                >
                  {tr("Next: set the scene", "下一步：设置开场")} →
                </button>
              </footer>
            </>
          )}
          {page === "setup" && (
            <>
              <div className="rh-scroll rh-pad">
                <span className="rh-eyebrow">
                  {tr("02 / 02 · THE OPENING", "02 / 02 · 设置开场")}
                </span>
                <h1>
                  {tr("Give them", "把他们放进")}
                  <br />
                  <em>{tr("a moment.", "一个局面。")}</em>
                </h1>
                <div className="rh-cast-strip">
                  {actors.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => {
                        setActor(a);
                        setPanel("actor");
                      }}
                    >
                      <Avatar actor={a} />
                      <span>{a.name}</span>
                    </button>
                  ))}
                </div>
                {doc?.source && (
                  <p className="rh-source">
                    {tr("Continuing from", "接续")}{" "}
                    <strong>{doc.source.title}</strong> ·{" "}
                    {tr("saved result", "已认可结果")}
                  </p>
                )}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void begin();
                  }}
                  id="rh-setup-form"
                >
                  <SetupFields
                    value={form}
                    onChange={updateForm}
                    actors={actors}
                    tr={tr}
                  />
                  <button
                    className="rh-text-button rh-organize"
                    type="button"
                    onClick={() => setPanel("organize")}
                  >
                    <Glyph name="star" />
                    {tr("Review setup", "整理设定")}
                  </button>
                </form>
              </div>
              <footer className="rh-form-footer">
                <small className="rh-sync">{syncLabel}</small>
                <button
                  form="rh-setup-form"
                  className="rh-primary"
                  disabled={
                    busy ||
                    !!job ||
                    !online ||
                    form.premise.trim().length < 10 ||
                    actors.length !== 2
                  }
                >
                  {busy
                    ? tr("Setting the stage…", "准备舞台…")
                    : tr("Start rehearsal", "开始排戏")}
                  <span>→</span>
                </button>
              </footer>
            </>
          )}
          {page === "stage" && scene && version && (
            <>
              <div className="rh-stage-context">
                <button
                  onClick={() => {
                    setForm(version.setup);
                    setPanel("settings");
                  }}
                >
                  <span className="rh-small-pair">
                    {actors.map((a) => (
                      <Avatar actor={a} size="tiny" key={a.id} />
                    ))}
                  </span>
                  {tr("Cast & scene", "人物与设定")} <span>⌄</span>
                </button>
                <span className="rh-sync">
                  {job ? tr("Rehearsing…", "正在排演…") : syncLabel}
                </span>
                {doc?.demo && <span className="rh-demo">DEMO</span>}
              </div>
              <div className="rh-reading" ref={reader} onScroll={scrolling}>
                {doc?.source && (
                  <p className="rh-source">
                    {tr("Continuing", "接续")} · {doc.source.title}
                    {scene.source_updated && (
                      <span>
                        {tr(
                          "Previous result changed. This scene keeps its original source.",
                          "上一场结果已更新，本场仍基于原结果。",
                        )}
                      </span>
                    )}
                  </p>
                )}
                <div className="rh-scene-opening">
                  <span className="rh-eyebrow">
                    {tr("THE SCENE", "这一场")}
                  </span>
                  <p>{version.setup.premise}</p>
                  <span className="rh-reading-divider">✧</span>
                </div>
                {bodyBlocks(visibleNodes)}
                {!nodes.length && !job && (
                  <div className="rh-empty">
                    <p>{tr("The stage is ready.", "舞台已准备好。")}</p>
                    <button
                      className="rh-secondary"
                      onClick={() =>
                        task(async () => {
                          await send({ kind: "continue" });
                        })
                      }
                    >
                      {tr("Rehearse the opening", "排演开场")}
                    </button>
                  </div>
                )}
                {job && (
                  <div className="rh-performing" role="status">
                    <span>✧</span>
                    {tr("Rehearsing…", "正在排演…")}
                    <small>
                      {elapsed >= 15
                        ? tr(
                            "Still working. You can pause; completed paragraphs stay saved.",
                            "仍在排演中。你可以暂停，完整内容会保留。",
                          )
                        : tr(
                            "A little room for the unexpected.",
                            "为意料之外，留一点空间。",
                          )}
                    </small>
                  </div>
                )}
                <div className="rh-reader-end" />
              </div>
              {unread && (
                <button
                  className="rh-new-content"
                  onClick={() => {
                    following.current = true;
                    setUnread(false);
                    reader.current?.scrollTo({
                      top: reader.current.scrollHeight,
                      behavior: "smooth",
                    });
                  }}
                >
                  {tr("See new content", "查看新内容")} ↓
                </button>
              )}
              <footer className="rh-stage-footer">
                {totalLines > 0 && (
                  <div className="rh-line-progress" role="status">
                    {revealed} / {totalLines} {tr("lines", "句")}
                    <span>{tr("At your pace", "按你的节奏")}</span>
                  </div>
                )}
                {taken && waitingLines > 0 && !job && (
                  <button
                    className="rh-secondary rh-takeover-next"
                    aria-label="Next line"
                    disabled={busy || !online}
                    onClick={() =>
                      task(async () => {
                        await send({ kind: "read", revealed: revealed + 1 });
                      })
                    }
                  >
                    {tr("Next line", "下一句")} ↓
                  </button>
                )}
                {taken ? (
                  <>
                    <div className="rh-takeover-status">
                      <span>
                        {tr("You are playing", "你正在扮演")}{" "}
                        <strong>{taken.name}</strong>
                      </span>
                      <button
                        disabled={!!job || busy}
                        onClick={() =>
                          task(async () => {
                            await send({ kind: "release" });
                          })
                        }
                      >
                        {tr("Hand back role", "交还角色")}
                      </button>
                    </div>
                    <form
                      className="rh-role-input"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const text = roleText;
                        void task(async () => {
                          await send({
                            kind: "speak",
                            text,
                            input_type: inputType,
                          });
                          setRoleText("");
                          localPut(`role:${scene.id}:${taken.id}`, "");
                        });
                      }}
                    >
                      <select
                        value={inputType}
                        onChange={(e) =>
                          setInputType(e.target.value as "dialogue" | "action")
                        }
                        aria-label="Contribution type"
                      >
                        <option value="dialogue">{tr("Line", "台词")}</option>
                        <option value="action">{tr("Action", "动作")}</option>
                      </select>
                      <textarea
                        value={roleText}
                        onChange={(e) => {
                          setRoleText(e.target.value);
                          localPut(
                            `role:${scene.id}:${taken.id}`,
                            e.target.value,
                          );
                        }}
                        placeholder={tr(
                          "Your words. Their response.",
                          "写下你的话，等待对方回应。",
                        )}
                        rows={2}
                        maxLength={2000}
                        aria-label="Your performance"
                      />
                      <button
                        className="rh-send"
                        disabled={busy || !!job || !online || !roleText.trim()}
                        aria-label="Send performance"
                      >
                        ↑
                      </button>
                    </form>
                    {job && (
                      <button
                        className="rh-pause-role"
                        onClick={() =>
                          task(async () => {
                            await rehearsal("/jobs/" + job + "/pause", {});
                          })
                        }
                      >
                        {tr("Pause", "暂停")}
                      </button>
                    )}
                  </>
                ) : (
                  <div className="rh-stage-actions">
                    <button
                      disabled={busy || !!job || !online}
                      onClick={() => setPanel("intervene")}
                    >
                      <Glyph name="pen" />
                      {tr("Intervene", "我来介入")}
                    </button>
                    <button
                      aria-label={
                        job ? "Pause" : waitingLines ? "Next line" : "Continue"
                      }
                      className="rh-primary"
                      disabled={busy || !online}
                      onClick={() =>
                        task(async () => {
                          if (job)
                            await rehearsal("/jobs/" + job + "/pause", {});
                          else if (waitingLines)
                            await send({
                              kind: "read",
                              revealed: revealed + 1,
                            });
                          else await send({ kind: "continue" });
                        })
                      }
                    >
                      {job ? (
                        <>
                          <span>Ⅱ</span>
                          {tr("Pause", "暂停")}
                        </>
                      ) : (
                        <>
                          {waitingLines
                            ? tr("Next line", "下一句")
                            : tr("Continue", "继续演")}
                          <span>→</span>
                        </>
                      )}
                    </button>
                    <button
                      disabled={busy || !!job || !online || !nodes.length}
                      onClick={() => {
                        setSelected(null);
                        void showDirections();
                      }}
                    >
                      <Glyph name="branch" />
                      {tr("Other directions", "其他走向")}
                    </button>
                  </div>
                )}
              </footer>
            </>
          )}
          {page === "review" && scene && version && (
            <>
              <div className="rh-scroll rh-pad">
                <span className="rh-eyebrow">
                  {tr("SCENE REVIEW", "场景回顾")}
                </span>
                <h1>
                  {tr("A scene worth", "把这一场，")}
                  <br />
                  <em>{tr("keeping.", "留在故事里。")}</em>
                </h1>
                <div className="rh-review-version">
                  <span>{tr("Reviewing", "正在回顾")}</span>
                  <button onClick={() => setPanel("versions")}>
                    {tr("Version", "版本")} {version.label} ⌄
                  </button>
                </div>
                <div className="rh-review-summary">
                  <span className="rh-eyebrow">
                    {tr("WHAT HAPPENED", "这一场发生了什么")}
                  </span>
                  {review ? (
                    <p>{review.summary}</p>
                  ) : (
                    <p>
                      {reviewError ||
                        tr(
                          "Preparing a recap from the completed text…",
                          "正在根据已完成正文整理回顾…",
                        )}
                    </p>
                  )}
                  {reviewError && (
                    <button
                      className="rh-text-button"
                      onClick={() => enterReview()}
                    >
                      {tr("Retry recap", "重试摘要")}
                    </button>
                  )}
                </div>
                {review &&
                  [
                    ["Character changes", review.changes],
                    ["Open threads", review.threads],
                  ].map(([label, items]) => (
                    <section className="rh-review-detail" key={String(label)}>
                      <h3>
                        {label === "Character changes"
                          ? tr("Character changes", "人物变化")
                          : tr("Open threads", "未解决线索")}
                      </h3>
                      {(items as string[]).length ? (
                        (items as string[]).map((x, i) => <p key={i}>{x}</p>)
                      ) : (
                        <p className="rh-muted">
                          {tr(
                            "No explicit changes recorded.",
                            "没有明确记录的变化。",
                          )}
                        </p>
                      )}
                    </section>
                  ))}
                <details className="rh-full-scene">
                  <summary>
                    {tr("Read the full scene", "阅读全文")}{" "}
                    <span>
                      {nodes.length} {tr("segments", "片段")} ⌄
                    </span>
                  </summary>
                  {bodyBlocks(nodes, true)}
                </details>
                <p className="rh-review-note">
                  {tr(
                    "Autosave keeps your drafts. Saving a scene chooses the version you want to carry forward.",
                    "自动保存留住草稿；保存本场，是选择你认可的结果。",
                  )}
                </p>
                {doc?.result?.version_id === version.id &&
                  doc.result.head === version.head && (
                    <div className="rh-result-saved">
                      ✓ {tr("Saved as this scene’s result", "已保存为本场结果")}
                    </div>
                  )}
                <div className="rh-review-links">
                  <button onClick={() => navigate("stage")}>
                    {tr("Keep editing", "继续修改")}
                  </button>
                  <button
                    onClick={() => {
                      setExportText("");
                      setPanel("export");
                    }}
                  >
                    {tr("Export scene", "导出")}
                  </button>
                </div>
              </div>
              <footer className="rh-form-footer">
                <button
                  className="rh-primary"
                  disabled={busy || !online || !nodes.length}
                  onClick={() =>
                    doc?.result?.version_id === version.id &&
                    doc.result.head === version.head
                      ? newScene(false, scene)
                      : task(async () => {
                          await send({ kind: "result" });
                          setNotice(
                            tr(
                              "Saved as this scene’s result.",
                              "已保存为本场结果。",
                            ),
                          );
                        })
                  }
                >
                  {doc?.result?.version_id === version.id &&
                  doc.result.head === version.head
                    ? tr("Rehearse the next scene", "接着排下一场")
                    : tr("Save this scene", "保存本场")}
                  <span>→</span>
                </button>
              </footer>
            </>
          )}
        </>
      )}
      {(page === "list" ||
        (page === "characters" &&
          characterMode === "library" &&
          !characterPicking)) && (
        <nav className="rh-nav" aria-label="Studio navigation">
          <button
            className={page === "list" ? "active" : ""}
            onClick={() => navigate("list")}
          >
            <Glyph name="star" />
            {tr("Create", "创作")}
          </button>
          <button
            className={page === "characters" ? "active" : ""}
            onClick={() => openCharacters()}
          >
            <Glyph name="people" /> Characters
          </button>
        </nav>
      )}
      {panel && (
        <Sheet key={panel} title={titles[panel]} close={() => setPanel(null)}>
          {panel === "actor" && actor && (
            <>
              <div className="rh-actor-detail">
                <Avatar actor={actor} size="hero" />
                <span className="rh-eyebrow">{tr("CHARACTER", "人物")}</span>
                <h2>{actor.name}</h2>
                <p>{actor.description}</p>
                <small>
                  {tr(
                    "This scene uses an independent snapshot. Private chats stay private.",
                    "本场使用独立设定快照，不读取私人聊天。",
                  )}
                </small>
              </div>
              {page === "cast" && (
                <div className="rh-replace-buttons">
                  {[0, 1].map((i) => (
                    <button
                      className="rh-secondary"
                      key={i}
                      onClick={() =>
                        task(async () => {
                          if (cast.includes(actor.id) && cast[i] !== actor.id)
                            throw new Error("Choose two different characters.");
                          const next = cast.slice();
                          next[i] = actor.id;
                          const clean = [next[0] || "", next[1] || ""];
                          setCast(clean);
                          await send({
                            kind: "cast",
                            character_ids: clean.map((x) => x || null),
                          });
                          setPanel(null);
                        })
                      }
                    >
                      {tr("Use as", "加入位置")} {i ? "B" : "A"}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
          {panel === "intervene" && (
            <div className="rh-interventions">
              {(
                [
                  [
                    "direction",
                    "pen",
                    tr("Give a direction", "给一句导演指令"),
                    tr("Shape the next reaction.", "改变下一段的反应。"),
                  ],
                  [
                    "takeover",
                    "people",
                    tr("Play a character", "我来演一个角色"),
                    tr("Your lines. Their response.", "你的台词，对方的回应。"),
                  ],
                  [
                    "event",
                    "event",
                    tr("Introduce an event", "加入一个事件"),
                    tr(
                      "Change what happens around them.",
                      "让周围发生一点变化。",
                    ),
                  ],
                  [
                    "settings",
                    "book",
                    tr("Adjust this scene", "调整本场设定"),
                    tr(
                      "Goals, knowledge and locked rules.",
                      "目标、知识与必须遵守的规则。",
                    ),
                  ],
                ] as [Panel, string, string, string][]
              ).map(([id, icon, title, sub]) => (
                <button
                  key={id}
                  onClick={() => {
                    if (id === "settings") setForm(version!.setup);
                    setPanel(id);
                  }}
                >
                  <Glyph name={icon} />
                  <span>
                    <strong>{title}</strong>
                    <small>{sub}</small>
                  </span>
                  <span>›</span>
                </button>
              ))}
            </div>
          )}
          {(panel === "direction" ||
            panel === "event" ||
            panel === "replay" ||
            panel === "feedback") && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const kind =
                  panel === "feedback"
                    ? "feedback"
                    : panel === "replay"
                      ? "replay"
                      : panel;
                void task(async () => {
                  await send({
                    kind,
                    text: String(f.get("text")),
                    persistent: f.get("persistent") === "on",
                    node_id: selected?.node.id,
                    block_id: selected?.block.id,
                  });
                  setPanel(null);
                });
              }}
            >
              <p className="rh-muted">
                {panel === "event"
                  ? tr(
                      "This will actually happen in the scene, once.",
                      "这个事件会在场景中实际发生一次。",
                    )
                  : panel === "replay"
                    ? tr(
                        "A new version starts here. The original stays intact.",
                        "将从这段开始建立新版本，原版本保留。",
                      )
                    : panel === "feedback"
                      ? tr(
                          "What felt wrong, and what should be different?",
                          "哪里不像这个人物？你希望如何纠正？",
                        )
                      : tr(
                          "A small nudge can change the whole scene.",
                          "一点方向，也可以改变整场戏。",
                        )}
              </p>
              <label>
                {panel === "event"
                  ? tr("What happens?", "发生什么事件？")
                  : panel === "feedback"
                    ? tr("Your correction", "你的纠正")
                    : tr("Your direction", "你的导演指令")}
                <textarea
                  name="text"
                  rows={5}
                  maxLength={1000}
                  required
                  defaultValue={
                    panel === "replay"
                      ? tr("Try a different reaction.", "换一种反应。")
                      : ""
                  }
                  placeholder={
                    panel === "event"
                      ? tr(
                          "The departure announcement interrupts them.",
                          "列车广播响起。",
                        )
                      : tr(
                          "Let him ask her to stay, without saying he will miss her.",
                          "让他挽留，但不要直接说舍不得。",
                        )
                  }
                />
              </label>
              {panel === "direction" && (
                <label className="rh-check">
                  <input type="checkbox" name="persistent" />
                  {tr(
                    "Keep this direction until the scene ends",
                    "持续到本场结束",
                  )}
                </label>
              )}
              <button className="rh-primary" disabled={busy || !online}>
                {panel === "event"
                  ? tr("Add event & continue", "加入并继续")
                  : panel === "feedback"
                    ? tr("Save correction", "保存纠正")
                    : panel === "replay"
                      ? tr("Rehearse a new version", "排演新版本")
                      : tr("Continue in this direction", "按这个方向继续")}{" "}
                →
              </button>
            </form>
          )}
          {panel === "takeover" && (
            <>
              <p className="rh-muted">
                {tr(
                  "Choose one role. AI will perform only the other character and the environment.",
                  "选择一个角色，AI 只演对方和必要的环境。",
                )}
              </p>
              <div className="rh-takeover-picks">
                {actors.map((a) => (
                  <button
                    key={a.id}
                    disabled={busy}
                    onClick={() =>
                      task(async () => {
                        await send({ kind: "takeover", target_id: a.id });
                        setPanel(null);
                      })
                    }
                  >
                    <Avatar actor={a} size="large" />
                    <strong>{a.name}</strong>
                    <span>{tr("Play this role", "开始对戏")} →</span>
                  </button>
                ))}
              </div>
            </>
          )}
          {panel === "settings" && (
            <>
              <div className="rh-cast-strip">
                {actors.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => {
                      setActor(a);
                      setPanel("actor");
                    }}
                  >
                    <Avatar actor={a} />
                    <span>{a.name}</span>
                  </button>
                ))}
              </div>
              <details className="rh-details">
                <summary>
                  {tr(
                    "What has happened on this version",
                    "本版本已经发生的事实",
                  )}
                </summary>
                {state &&
                  (
                    [
                      "world_facts",
                      "beliefs",
                      "goals",
                      "relationships",
                      "threads",
                    ] as const
                  ).map((k) => (
                    <section key={k}>
                      <h3>{k.replace("_", " ")}</h3>
                      {state[k].map((f, i) => (
                        <p key={i}>
                          {f.text}
                          <small>
                            {tr("Known by", "知情人物")}:{" "}
                            {f.known_by
                              .map(
                                (id) => actors.find((a) => a.id === id)?.name,
                              )
                              .join(", ") || "—"}
                          </small>
                        </p>
                      ))}
                    </section>
                  ))}
              </details>
              {version?.instructions
                .filter((i) => i.active)
                .map((i) => (
                  <div className="rh-active-direction" key={i.id}>
                    <small>{tr("Ongoing direction", "持续导演指令")}</small>
                    <p>{i.text}</p>
                    <button
                      disabled={busy}
                      onClick={() =>
                        task(async () => {
                          await send({
                            kind: "stop_instruction",
                            target_id: i.id,
                          });
                        })
                      }
                    >
                      {tr("Stop for future segments", "停用，仅影响后续")}
                    </button>
                  </div>
                ))}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void task(async () => {
                    await send({
                      kind: "setup",
                      setup: {
                        ...form,
                        rules: form.rules.filter((r) => r.trim()),
                      },
                    });
                    setPanel(null);
                    setNotice(
                      tr(
                        "Settings applied in a new version.",
                        "设定已应用到新版本。",
                      ),
                    );
                  });
                }}
              >
                <SetupFields
                  value={form}
                  onChange={setForm}
                  actors={actors}
                  compact
                  tr={tr}
                />
                <p className="rh-muted">
                  {tr(
                    "Changes start in a new version. Existing text and saved results stay intact.",
                    "改动从新版本生效，原文和已认可结果保留。",
                  )}
                </p>
                <button className="rh-primary" disabled={busy || !online}>
                  {tr("Apply & continue from here", "应用并从这里继续")} →
                </button>
              </form>
              <div className="rh-font-control">
                <span>{tr("Reading size", "阅读字号")}</span>
                <button
                  onClick={() => {
                    setFont(Math.max(16, font - 1));
                    localPut("font", Math.max(16, font - 1));
                  }}
                >
                  A−
                </button>
                <button
                  onClick={() => {
                    setFont(Math.min(26, font + 1));
                    localPut("font", Math.min(26, font + 1));
                  }}
                >
                  A＋
                </button>
              </div>
            </>
          )}
          {panel === "versions" && doc && (
            <div className="rh-version-list">
              {Object.values(doc.versions).map((v) => (
                <article
                  className={version?.id === v.id ? "current" : ""}
                  key={v.id}
                >
                  <button
                    disabled={busy}
                    onClick={() =>
                      task(async () => {
                        await send({ kind: "switch", version_id: v.id });
                        setPanel(null);
                        if (page === "review") void enterReview();
                      })
                    }
                  >
                    <span className="rh-version-num">{v.label}</span>
                    <span>
                      <strong>
                        {tr("Version", "版本")} {v.label}
                      </strong>
                      <small>{v.reason}</small>
                      <span className="rh-version-tags">
                        {version?.id === v.id && tr("Viewing", "当前查看")}
                        {doc.result?.version_id === v.id &&
                          " · " + tr("Scene result", "本场结果")}
                        {job &&
                          localGet<string>("job-version:" + job, "") === v.id &&
                          " · " + tr("Rehearsing", "生成中")}
                      </span>
                    </span>
                  </button>
                  <div className="rh-inline">
                    <button
                      onClick={() => {
                        const name = prompt(
                          tr("Version name", "版本名"),
                          v.label,
                        );
                        if (name)
                          void task(async () => {
                            await send({
                              kind: "rename",
                              version_id: v.id,
                              name,
                            });
                          });
                      }}
                    >
                      {tr("Rename", "重命名")}
                    </button>
                    {version?.id !== v.id &&
                      doc.result?.version_id !== v.id && (
                        <button
                          onClick={() => {
                            if (
                              confirm(
                                tr(
                                  "Delete this version? Other versions stay.",
                                  "删除此版本？其他版本保留。",
                                ),
                              )
                            )
                              void task(async () => {
                                await send({
                                  kind: "delete_version",
                                  version_id: v.id,
                                });
                              });
                          }}
                        >
                          {tr("Delete", "删除")}
                        </button>
                      )}
                  </div>
                </article>
              ))}
            </div>
          )}
          {panel === "directions" && (
            <>
              <p className="rh-muted">
                {tr(
                  "Different choices, not just different words. Nothing changes until you choose.",
                  "不同的决定，而不只是不同的措辞。选择后才开始演出。",
                )}
              </p>
              {busy && !choices.length && (
                <p role="status">
                  {tr("Exploring two possibilities…", "正在探索两种走向…")}
                </p>
              )}
              {choices.map((c, i) => (
                <button
                  className="rh-direction-card"
                  key={c.id}
                  disabled={busy}
                  onClick={() =>
                    task(async () => {
                      await send({
                        kind: "branch",
                        node_id: selected?.node.id,
                        text: c.choice,
                        name: String(Object.keys(doc!.versions).length + 1),
                      });
                      setPanel(null);
                    })
                  }
                >
                  <span>
                    0{i + 1} <Glyph name="branch" />
                  </span>
                  <h3>{c.title}</h3>
                  <p>{c.choice}</p>
                  <small>{c.consequence}</small>
                  <strong>
                    {tr("Explore this version", "探索这个版本")} →
                  </strong>
                </button>
              ))}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const text = String(
                    new FormData(e.currentTarget).get("text"),
                  );
                  void task(async () => {
                    await send({
                      kind: "branch",
                      node_id: selected?.node.id,
                      text,
                    });
                    setPanel(null);
                  });
                }}
              >
                <label>
                  {tr("I have another idea", "我有别的想法")}
                  <textarea name="text" rows={3} required maxLength={1000} />
                </label>
                <button className="rh-secondary" disabled={busy || !online}>
                  {tr("Try my direction", "尝试我的走向")} →
                </button>
              </form>
            </>
          )}
          {panel === "paragraph" && selected && (
            <>
              <blockquote>{selected.block.text}</blockquote>
              <div className="rh-paragraph-menu">
                <button onClick={() => setPanel("edit")}>
                  <Glyph name="pen" />
                  {tr("Edit this paragraph", "编辑这段")}
                </button>
                <button onClick={() => setPanel("replay")}>
                  <Glyph name="star" />
                  {tr("Try another reaction", "换一种反应")}
                </button>
                <button
                  onClick={() =>
                    task(async () => {
                      await send({
                        kind: "replay",
                        node_id: selected.node.id,
                        block_id: selected.block.id,
                      });
                      setPanel(null);
                    })
                  }
                >
                  <Glyph name="branch" />
                  {tr("Rehearse from here", "从这里重演")}
                </button>
                <button onClick={() => void showDirections()}>
                  <Glyph name="branch" />
                  {tr("Other directions from here", "从这里探索其他走向")}
                </button>
                <button onClick={() => setPanel("feedback")}>
                  {tr("The character feels wrong", "人物反应不对")}
                </button>
              </div>
              <details className="rh-details">
                <summary>{tr("Where this came from", "查看来源")}</summary>
                <p>
                  {tr("Source", "来源")}: {selected.node.source} ·{" "}
                  {tr("Operation", "操作")}{" "}
                  {selected.node.operation_id.slice(0, 8)}
                </p>
                <p>{selected.node.reason}</p>
              </details>
            </>
          )}
          {panel === "edit" && selected && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void task(async () => {
                  await send({
                    kind: "edit",
                    node_id: selected.node.id,
                    block_id: selected.block.id,
                    text: editText,
                    edit_type: editType,
                  });
                  setPanel(null);
                });
              }}
            >
              <p className="rh-muted">
                {tr(
                  "A new version is created. Your original stays intact.",
                  "将创建新版本，原版本保留。",
                )}
              </p>
              <label>
                {tr("Your text", "你的文字")}
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={7}
                  required
                  maxLength={2000}
                />
              </label>
              <fieldset className="rh-edit-type">
                <legend>
                  {tr("What kind of edit is this?", "这次修改属于？")}
                </legend>
                <label>
                  <input
                    type="radio"
                    checked={editType === "wording"}
                    onChange={() => setEditType("wording")}
                  />
                  <span>
                    <strong>{tr("Wording only", "仅改文字")}</strong>
                    <small>
                      {tr(
                        "Keep later text. Review state for possible factual effects.",
                        "保留后文，复核可能的事实影响。",
                      )}
                    </small>
                  </span>
                </label>
                <label>
                  <input
                    type="radio"
                    checked={editType === "plot"}
                    onChange={() => setEditType("plot")}
                  />
                  <span>
                    <strong>{tr("Change the story", "改变剧情")}</strong>
                    <small>
                      {tr(
                        "Lock my edit and rehearse a new continuation.",
                        "锁定修改，从这里排演新的后续。",
                      )}
                    </small>
                  </span>
                </label>
              </fieldset>
              <button className="rh-primary" disabled={busy || !online}>
                {tr("Save in a new version", "保存为新版本")} →
              </button>
            </form>
          )}
          {panel === "organize" && (
            <>
              <p className="rh-muted">
                {tr(
                  "Only your explicit inputs, kept separate from assumptions. Nothing is added automatically.",
                  "这里只整理你明确输入的内容，不自动添加推测。",
                )}
              </p>
              {Object.entries(form)
                .filter(
                  ([k, v]) =>
                    !["language", "format"].includes(k) && String(v).trim(),
                )
                .map(([k, v]) => (
                  <div className="rh-extracted" key={k}>
                    <small>
                      {tr("YOUR INPUT", "明确输入")} · {k.replace("_", " ")}
                    </small>
                    <p>{Array.isArray(v) ? v.join("\n") : v}</p>
                  </div>
                ))}
              <button
                className="rh-primary"
                onClick={() => {
                  setPanel(null);
                  setNotice(
                    tr(
                      "Your original inputs are unchanged.",
                      "原始输入保持不变。",
                    ),
                  );
                }}
              >
                {tr("Looks right", "确认设定")} ✓
              </button>
            </>
          )}
          {panel === "export" && (
            <>
              <div className="rh-format">
                <button
                  className={exportFormat === "txt" ? "selected" : ""}
                  onClick={() => {
                    setExportFormat("txt");
                    setExportText("");
                  }}
                >
                  TXT
                </button>
                <button
                  className={exportFormat === "md" ? "selected" : ""}
                  onClick={() => {
                    setExportFormat("md");
                    setExportText("");
                  }}
                >
                  Markdown
                </button>
              </div>
              <label className="rh-check">
                <input
                  type="checkbox"
                  checked={exportTitle}
                  onChange={(e) => {
                    setExportTitle(e.target.checked);
                    setExportText("");
                  }}
                />
                {tr("Include scene title", "包含场景标题")}
              </label>
              <label className="rh-check">
                <input
                  type="checkbox"
                  checked={exportNames}
                  onChange={(e) => {
                    setExportNames(e.target.checked);
                    setExportText("");
                  }}
                />
                {tr("Include character names", "包含角色名")}
              </label>
              <p className="rh-muted">
                {tr(
                  "Current version only. No hidden notes or director instructions.",
                  "仅导出当前版本，不包含隐藏设定和内部导演指令。",
                )}
              </p>
              {exportText && (
                <pre className="rh-export-preview">{exportText}</pre>
              )}
              <button
                className="rh-secondary"
                disabled={busy}
                onClick={() =>
                  task(async () => {
                    await prepareExport();
                  })
                }
              >
                {tr("Preview export", "预览导出")}
              </button>
              <button
                className="rh-primary"
                disabled={busy}
                onClick={() =>
                  task(async () => {
                    const text = await prepareExport();
                    const blob = new Blob(["\ufeff", text], {
                      type: "text/plain;charset=utf-8",
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download =
                      (doc!.title.replace(/[<>:"/\\|?*\x00-\x1f]/g, "_") ||
                        "scene") +
                      "." +
                      exportFormat;
                    a.click();
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                  })
                }
              >
                {tr("Download", "下载")} {exportFormat.toUpperCase()} ↓
              </button>
              <button
                className="rh-text-button"
                onClick={() =>
                  task(async () => {
                    const text = exportText || (await prepareExport());
                    try {
                      await navigator.clipboard.writeText(text);
                      setNotice(tr("Copied to clipboard.", "已复制到剪贴板。"));
                    } catch {
                      setNotice(
                        tr(
                          "Select and copy the preview text.",
                          "请选中并复制预览文字。",
                        ),
                      );
                    }
                  })
                }
              >
                {tr("Copy scene text", "复制正文")}
              </button>
            </>
          )}
          {panel === "rename" && scene && (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const name = String(
                    new FormData(e.currentTarget).get("name"),
                  );
                  void task(async () => {
                    await send({ kind: "rename", target_id: "scene", name });
                    setPanel(null);
                  });
                }}
              >
                <label>
                  {tr("Scene title", "场景标题")}
                  <input
                    name="name"
                    defaultValue={doc!.title}
                    required
                    maxLength={100}
                  />
                </label>
                <button className="rh-primary" disabled={busy}>
                  {tr("Save name", "保存名字")}
                </button>
              </form>
              <button
                className="rh-danger"
                onClick={() => {
                  if (
                    confirm(
                      tr(
                        "Delete this scene and all its versions? Original characters stay.",
                        "删除本场及全部版本？原始角色不受影响。",
                      ),
                    )
                  )
                    void task(async () => {
                      await rehearsal(
                        "/scenes/" + scene.id,
                        undefined,
                        "DELETE",
                      );
                      clearSceneCache(scene.id);
                      setPanel(null);
                      navigate("list");
                      await refresh();
                    });
                }}
              >
                {tr("Delete scene", "删除本场")}
              </button>
            </>
          )}
          {panel === "more" && (
            <div className="rh-more-menu">
              {page === "stage" && (
                <>
                  <button
                    disabled={!!job}
                    onClick={() => {
                      setPanel(null);
                      void enterReview();
                    }}
                  >
                    {tr("End scene & review", "结束本场并回顾")} <span>→</span>
                  </button>
                  <button
                    onClick={() => {
                      setForm(version!.setup);
                      setPanel("settings");
                    }}
                  >
                    {tr("Cast & scene settings", "人物与本场设定")}{" "}
                    <span>→</span>
                  </button>
                  <button onClick={() => setPanel("versions")}>
                    {tr("Versions", "版本")} <span>→</span>
                  </button>
                  <button
                    onClick={() => {
                      setPanel("export");
                      setExportText("");
                    }}
                  >
                    {tr("Copy or export this version", "复制或导出当前版本")}{" "}
                    <span>→</span>
                  </button>
                  <button onClick={() => setPanel("rename")}>
                    {tr("Rename scene", "重命名本场")} <span>→</span>
                  </button>
                </>
              )}
              <label className="rh-language">
                {tr("Interface language", "界面语言")}
                <select
                  value={lang}
                  onChange={(e) => {
                    const l = e.target.value as "en" | "zh";
                    setLang(l);
                    localPut("language", l);
                    if (page === "setup") updateForm({ ...form, language: l });
                  }}
                >
                  <option value="en">English</option>
                  <option value="zh">中文</option>
                </select>
              </label>
              <button onClick={() => openCharacters()}>
                Your characters <span>→</span>
              </button>
              <button onClick={() => openCharacters(true)}>
                Create a character <span>＋</span>
              </button>
              <p className="rh-muted">
                {tr(
                  "Private by default. Rehearsals use character snapshots, never private chats.",
                  "默认私有。排戏使用人物快照，不读取私人聊天。",
                )}
              </p>
            </div>
          )}
        </Sheet>
      )}
    </main>
  );
}
