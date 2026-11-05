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
type Event = {
  title: string;
  starts_at: string;
  all_day: boolean;
  category: string;
};
export function LifeCompanion({
  character,
  conversation,
  onStatus,
}: {
  character: Character;
  conversation: string;
  onStatus: (status: CompanionStatus | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [account, setAccount] = useState<AccountState | null>(null);
  const [status, setStatus] = useState<CompanionStatus | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
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
      if (s.connected) setEvents(await api<Event[]>("/companion/upcoming"));
      else setEvents([]);
    } else {
      setStatus(null);
      onStatus(null);
    }
  }
  useEffect(() => {
    let active = true;
    const load = async () => {
      if (active)
        try {
          await refresh();
        } catch {
          /* background status does not interrupt chat */
        }
    };
    void load();
    const timer = setInterval(() => void load(), 15000);
    const result = new URLSearchParams(location.search).get("calendar");
    if (result) {
      setOpen(true);
      setNotice(
        result === "connected"
          ? "Calendar connected and synchronized. Your companion will introduce the new connection shortly."
          : result === "cancelled"
            ? "Connection cancelled. Your calendar was not changed."
            : "Calendar connection needs attention. Retry or reconnect below.",
      );
      const url = new URL(location.href);
      url.searchParams.delete("calendar");
      history.replaceState(null, "", url);
    }
    return () => {
      active = false;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [character.id, conversation]);
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else dialog.current?.close();
  }, [open]);
  const activeHere =
    !!status?.enabled &&
    status.character_id === character.id &&
    status.conversation_id === conversation;
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
  function close() {
    setOpen(false);
    requestAnimationFrame(() => trigger.current?.focus());
  }
  return (
    <>
      <section className="life-companion-entry" aria-label="Life Companion">
        <strong>
          Life Companion <span aria-hidden="true">✧</span>
        </strong>
        <p>
          Let this character understand your daily plans and be there for
          important moments.
        </p>
        <button
          ref={trigger}
          className="button companion-cta"
          aria-haspopup="dialog"
          onClick={() => setOpen(true)}
        >
          {activeHere ? "Manage Life Companion" : "Bring into My Life"}
          <span aria-hidden="true"> →</span>
        </button>
        {activeHere && (
          <span className="small">
            {status?.status === "ready"
              ? "Calendar connected · In-app support"
              : "Calendar needs attention"}
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
          <span className="eyebrow">LIFE COMPANION</span>
          <button
            className="button"
            aria-label="Close Life Companion"
            onClick={close}
          >
            ×
          </button>
        </div>
        <h2>Let {character.profile.name} become part of your everyday life.</h2>
        <p>
          Gentle encouragement before important plans, and a little space to
          talk afterward. Always optional.
        </p>
        <div className="privacy-note">
          <strong>Your calendar, your choice.</strong>
          <p>
            Read-only access to your primary Google Calendar. EchoLoom cannot
            create, edit or delete events. Private and sensitive events are
            excluded from AI context. Relevant event titles and times may be
            sent to your configured AI provider.
          </p>
          <p>
            Up to two unprompted check-ins per day. Quiet hours apply in your
            timezone. Calendar plans are never treated as proof of what
            happened.
          </p>
        </div>
        {notice && (
          <p role="status" className="notice">
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {!account?.authenticated ? (
          <AccountForm
            setup={!!account?.setup_required}
            onDone={() => void refresh()}
          />
        ) : (
          <>
            {status?.connected ? (
              <>
                <p>
                  <strong>{status.email || "Google Calendar"}</strong>
                  <br />
                  <span className="small">
                    {status.status === "ready"
                      ? "Connected · Read-only"
                      : "Sync needs attention"}
                    {status.last_sync &&
                      ` · Last sync ${new Date(status.last_sync).toLocaleString("en-US")}`}
                  </span>
                </p>
                {!activeHere && (
                  <p>
                    {status.enabled
                      ? "Another character or conversation is currently active. Switching preserves its messages and moves future check-ins here."
                      : "Choose this conversation for future check-ins."}
                  </p>
                )}
                <div className="companion-actions">
                  {!activeHere && (
                    <button
                      className="button primary"
                      disabled={busy}
                      onClick={() =>
                        void action(() => api("/companion/activate", body))
                      }
                    >
                      Make {character.profile.name} my companion
                    </button>
                  )}
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
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      void action(() =>
                        api("/integrations/google-calendar/sync", {}),
                      )
                    }
                  >
                    Sync now
                  </button>
                </div>
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
                  Timezone: {status.timezone}. Browser notifications are not
                  enabled in this local version. In-app messages still work.
                </p>
                <details>
                  <summary>Upcoming plans ({events.length})</summary>
                  <ul className="upcoming-plans">
                    {events.map((event, index) => (
                      <li key={index}>
                        <strong>{event.title}</strong>
                        <br />
                        <span>
                          {event.all_day ? "All day · " : ""}
                          {new Date(event.starts_at).toLocaleString("en-US", {
                            timeZone: status.timezone,
                          })}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {!events.length && (
                    <p>No upcoming events in the next seven days.</p>
                  )}
                </details>
                <details>
                  <summary>Disconnect Google Calendar</summary>
                  <p>
                    This removes stored credentials, calendar snapshots, derived
                    calendar memories and pending check-ins. Previously sent
                    chat messages remain in your history.
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
                        setNotice(
                          "Disconnected. Your existing chat history is preserved.",
                        );
                      })
                    }
                  >
                    Disconnect and clear calendar data
                  </button>
                </details>
              </>
            ) : (
              <p>
                One character can be your active companion at a time. Connecting
                does not change your calendar.
              </p>
            )}
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
                {status?.connected
                  ? "Reconnect Google Calendar"
                  : "Connect Google Calendar"}
              </button>
            )}
            {!status?.configured && (
              <p className="notice">
                Google Calendar is not configured yet. Follow
                docs/mvp/life-companion.md to add your Google OAuth credentials
                to the backend .env file, then restart the backend.
              </p>
            )}
          </>
        )}
        <button className="button full" onClick={close}>
          Not now
        </button>
      </dialog>
    </>
  );
}
