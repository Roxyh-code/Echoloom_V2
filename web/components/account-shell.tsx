"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
export type AccountState = {
  authenticated: boolean;
  setup_required: boolean;
  username: string | null;
};
export function AccountForm({
  setup,
  onDone,
  compact = false,
}: {
  compact?: boolean;
  setup: boolean;
  onDone: () => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="account-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        try {
          await api(`/account/${setup ? "register" : "login"}`, {
            username,
            password,
          });
          window.dispatchEvent(new Event("echoloom-account-change"));
          onDone();
        } catch (e) {
          setError((e as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h2>
        {setup
          ? compact
            ? "Create your local account"
            : "Protect your personal calendar"
          : "Welcome back"}
      </h2>
      {!compact && (
        <p>
          {setup
            ? "Create an account for this local installation. Your existing characters and conversations will belong to this account."
            : "Sign in to this EchoLoom installation."}
        </p>
      )}
      <label>
        Local username
        <input
          required
          minLength={3}
          maxLength={80}
          pattern={"[a-zA-Z0-9_.\\-]+"}
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </label>
      <label>
        Local password
        <input
          required
          type="password"
          minLength={10}
          maxLength={128}
          autoComplete={setup ? "new-password" : "current-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      <p className="small muted">
        {compact
          ? "10+ characters. Use a different password from Google."
          : "Use a separate password, not your Google password. This is a local prototype account, without email recovery. Keep the app on your own computer."}
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button className="button primary" disabled={busy}>
        {busy ? "Please wait…" : setup ? "Create local account" : "Sign in"}
      </button>
    </form>
  );
}
export function AccountShell({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<AccountState | null>(null);
  useEffect(() => {
    const refresh = () => {
      void api<AccountState>("/account/session")
        .then(setAccount)
        .catch(() => {});
    };
    refresh();
    window.addEventListener("echoloom-account-change", refresh);
    window.addEventListener("echoloom-auth-required", refresh);
    return () => {
      window.removeEventListener("echoloom-account-change", refresh);
      window.removeEventListener("echoloom-auth-required", refresh);
    };
  }, []);
  if (account && !account.authenticated && !account.setup_required)
    return (
      <main className="container account-gate">
        <AccountForm setup={false} onDone={() => location.reload()} />
      </main>
    );
  return (
    <>
      {account?.authenticated && (
        <div className="account-status">
          <span>Local account: {account.username}</span>
          <button
            onClick={async () => {
              await api("/account/logout", {});
              location.reload();
            }}
          >
            Sign out
          </button>
        </div>
      )}
      {children}
    </>
  );
}
