"use client";
import { useEffect, useRef, useState } from "react";
import { api, Character } from "./api";
import { AccountForm, AccountState } from "./account-shell";
export type CompanionStatus = {
  configured: boolean;
  connected: boolean;
  status: string;
  email: string | null;
  enabled: boolean;
  character_id: string | null;
  conversation_id: string | null;
  timezone: string;
  quiet_start: string;
  quiet_end: string;
  last_sync: string | null;
};
type Plan = { title: string; starts_at: string; all_day: boolean };
export function LifeCompanion({
  character,
  conversation,
  onStatus,
  onWelcome,
}: {
  character: Character;
  conversation: string;
  onStatus: (status: CompanionStatus | null) => void;
  onWelcome: (pending: boolean, error?: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [account, setAccount] = useState<AccountState | null>(null);
  const [status, setStatus] = useState<CompanionStatus | null>(null);
  const [events, setEvents] = useState<Plan[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const welcomeGuard = useRef(false);
  const pendingWelcome = useRef(false);
  const body = {
    character_id: character.id,
    conversation_id: conversation,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  };
  async function refresh() {
    const a = await api<AccountState>("/account/session");
    setAccount(a);
    if (a.authenticated) {
      const s = await api<CompanionStatus>("/companion/settings");
      setStatus(s);
      onStatus(s);
      if (s.connected && open)
        setEvents(await api<Plan[]>("/companion/upcoming"));
      return s;
    }
    setStatus(null);
    onStatus(null);
    return null;
  }
  async function greet(refresh = false) {
    if (welcomeGuard.current) return;
    welcomeGuard.current = true;
    onWelcome(true);
    try {
      await api("/companion/welcome", { refresh });
      onWelcome(false);
    } catch (e) {
      onWelcome(false, (e as Error).message);
    } finally {
      welcomeGuard.current = false;
    }
  }
  useEffect(() => {
    let active = true;
    const result = new URLSearchParams(location.search).get("calendar");
    if (result === "connected") pendingWelcome.current = true;
    if (result) {
      setOpen(result !== "connected");
      setNotice(
        result === "cancelled"
          ? "Connection cancelled."
          : result === "connected"
            ? ""
            : "Couldn't connect. Please try again.",
      );
      const url = new URL(location.href);
      url.searchParams.delete("calendar");
      history.replaceState(null, "", url);
    }
    const load = async () => {
      try {
        const s = await refresh();
        if (
          active &&
          pendingWelcome.current &&
          s?.status === "ready" &&
          s.conversation_id === conversation
        ) {
          pendingWelcome.current = false;
          await greet();
        }
      } catch {
        /* Chat remains usable during a status failure. */
      }
    };
    void load();
    const timer = setInterval(() => {
      if (active) void refresh().catch(() => {});
    }, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [character.id, conversation]);
  useEffect(() => {
    if (open) {
      dialog.current?.showModal();
      void refresh().catch((e) => setError(e.message));
    } else dialog.current?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  const activeHere =
    !!status?.enabled &&
    status.character_id === character.id &&
    status.conversation_id === conversation;
  function close() {
    setOpen(false);
    requestAnimationFrame(() => trigger.current?.focus());
  }
  async function action(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="life-companion-entry" aria-label="Life Companion">
        <button
          ref={trigger}
          className="button companion-cta"
          aria-haspopup="dialog"
          onClick={() => setOpen(true)}
        >
          <span aria-hidden="true">✧ </span>
          {activeHere
            ? "My calendar"
            : status?.connected
              ? "Use my calendar"
              : "Connect calendar"}
          <span aria-hidden="true"> →</span>
        </button>
        {activeHere && (
          <span className="small">
            {status?.status === "ready" ? "Connected" : "Needs attention"}
          </span>
        )}
      </section>
      <dialog
        ref={dialog}
        className="companion-dialog"
        onCancel={(e) => {
          e.preventDefault();
          close();
        }}
      >
        <div className="companion-heading">
          <h2>{status?.connected ? "Your calendar" : "Share your calendar"}</h2>
          <button
            className="button"
            aria-label="Close Life Companion"
            onClick={close}
          >
            ×
          </button>
        </div>
        {!status?.connected && (
          <p>{character.profile.name} can be there for your important plans.</p>
        )}
        {notice && (
          <p className="notice" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {!account ? (
          <p role="status">Loading…</p>
        ) : !account.authenticated ? (
          <AccountForm
            compact
            setup={account.setup_required}
            onDone={() => void refresh()}
          />
        ) : (
          <>
            {status?.connected ? (
              <>
                <p className="small muted">
                  {status.email} ·{" "}
                  {status.status === "ready" ? "Connected" : "Needs attention"}
                </p>
                {!activeHere && (
                  <button
                    className="button primary full"
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        await api("/companion/activate", body);
                        close();
                        await greet();
                      })
                    }
                  >
                    Make {character.profile.name} my companion
                  </button>
                )}
                <div className="companion-actions">
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        await api("/integrations/google-calendar/sync", {});
                        close();
                        if (activeHere) await greet(true);
                      })
                    }
                  >
                    {busy ? "Syncing…" : "Sync now"}
                  </button>
                  {activeHere && (
                    <button
                      className="button"
                      disabled={busy}
                      onClick={() =>
                        void action(() => api("/companion/deactivate", {}))
                      }
                    >
                      Pause check-ins
                    </button>
                  )}
                </div>
                <details>
                  <summary>Preferences</summary>
                  <label>
                    Quiet hours start
                    <input
                      type="time"
                      value={status.quiet_start}
                      disabled={busy}
                      onChange={(e) =>
                        void action(() =>
                          api(
                            "/companion/settings",
                            { quiet_start: e.target.value },
                            "PATCH",
                          ),
                        )
                      }
                    />
                  </label>
                  <label>
                    Quiet hours end
                    <input
                      type="time"
                      value={status.quiet_end}
                      disabled={busy}
                      onChange={(e) =>
                        void action(() =>
                          api(
                            "/companion/settings",
                            { quiet_end: e.target.value },
                            "PATCH",
                          ),
                        )
                      }
                    />
                  </label>
                  <p className="small muted">
                    {status.timezone} · Up to two check-ins a day, in this chat.
                  </p>
                </details>
                <details>
                  <summary>Upcoming plans</summary>
                  <ul className="upcoming-plans">
                    {events.map((plan, i) => (
                      <li key={i}>
                        <strong>{plan.title}</strong>
                        <br />
                        {new Date(plan.starts_at).toLocaleString("en-US", {
                          timeZone: status.timezone,
                        })}
                      </li>
                    ))}
                  </ul>
                  {events.length === 0 && <p>No upcoming plans.</p>}
                </details>
                <details>
                  <summary>Disconnect Google Calendar</summary>
                  <p className="small">
                    Clears calendar data and stops check-ins. Your chat history
                    stays.
                  </p>
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        await api(
                          "/integrations/google-calendar/connection",
                          undefined,
                          "DELETE",
                        );
                        setNotice("Calendar disconnected.");
                      })
                    }
                  >
                    Disconnect calendar
                  </button>
                </details>
              </>
            ) : null}
            {(!status?.connected || status.status !== "ready") && (
              <button
                className="button primary full"
                disabled={busy || !status?.configured}
                onClick={() =>
                  void action(async () => {
                    const response = await api<{ authorization_url: string }>(
                      "/integrations/google-calendar/connect",
                      body,
                    );
                    location.assign(response.authorization_url);
                  })
                }
              >
                {busy
                  ? "Connecting…"
                  : status?.connected
                    ? "Reconnect Google Calendar"
                    : "Connect Google Calendar"}
              </button>
            )}
            {!status?.configured && (
              <p className="small muted">
                Calendar setup needed.{" "}
                <a
                  href="https://github.com/Roxyh-code/Echoloom_V2/blob/main/docs/mvp/life-companion.md"
                  target="_blank"
                  rel="noreferrer"
                >
                  Setup guide ↗
                </a>
              </p>
            )}
          </>
        )}
        <p className="small muted companion-privacy-brief">
          Read-only. Relevant plans are shared with your AI provider.
        </p>
        <details className="companion-privacy-details">
          <summary>Privacy</summary>
          <p className="small">
            Private and sensitive events are excluded. EchoLoom cannot change
            your calendar. You can pause or disconnect anytime; existing chat
            messages remain.
          </p>
        </details>
      </dialog>
    </>
  );
}
