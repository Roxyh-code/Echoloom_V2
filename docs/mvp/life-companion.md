# Life Companion v0.3 — local setup

Life Companion adds a visible **Sync my schedule** button beside **Do something together**, above the chat input. One selected character and conversation can receive occasional Google Calendar check-ins. Ordinary chats and independent stories continue to work.

This remains a local prototype, not a production identity or notification service. Keep both servers bound to `127.0.0.1`, run one backend worker, and open `http://127.0.0.1:3000`. Do not mix `localhost` and `127.0.0.1`: the session cookie and OAuth return must use the same hostname. Keep your existing model settings.

## Upgrade on Windows

Stop the backend and frontend with Ctrl+C before upgrading. In PowerShell at the repository root:

```powershell
git pull
# Back up all local data: database, portraits, and calendar encryption key.
Copy-Item work ("work-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")) -Recurse
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Do not replace `.env` or delete `work`. Migration `0003` adds calendar/account tables and nullable metadata without rebuilding characters or rewriting messages. The first local account claims existing characters, images, chats, and stories. Subsequent sign-ins are required to view them. Use a unique local password of at least 10 characters; this is separate from your Google account. There is no email password recovery in this prototype.

On macOS/Linux use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe` and back up `work` with your usual file backup tool.

## Configure Google Cloud

1. Open [Google Cloud Console](https://console.cloud.google.com/), select or create a project, and enable **Google Calendar API** in APIs & Services → Library.
2. In **Google Auth Platform**, configure Branding, Audience and Data Access. For a personal test choose External / Testing and add your Google account as a test user. An organization may restrict this; use an account permitted by its administrator.
3. Add the scopes `openid`, `email`, and `https://www.googleapis.com/auth/calendar.events.readonly`. EchoLoom reads only the primary calendar. It never requests write scopes.
4. Create an OAuth client of type **Web application**. Add this exact Authorized redirect URI:

   ```text
   http://127.0.0.1:8000/api/integrations/google-calendar/callback
   ```

5. Put the client ID and client secret in your existing backend `.env`. Never paste secrets into chat or frontend source:

   ```dotenv
   APP_ORIGIN=http://127.0.0.1:3000
   GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/google-calendar/callback
   CALENDAR_KEY_FILE=work/secrets/calendar.key
   COMPANION_WORKER_ENABLED=true
   ALLOW_ADDITIONAL_ACCOUNTS=false
   ```

The client ID and secret identify your Google Cloud application; they are **not** your OpenAI API key. OAuth consent grants read access to your own calendar. Google testing-mode authorizations can expire (commonly after seven days); reconnect when asked. Production public distribution requires Google's applicable consent verification and a proper hosted authentication design; that is outside this local build.

## Start and connect

Backend terminal, from repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

Frontend terminal:

```powershell
cd web
npm.cmd ci
npm.cmd run dev
```

Open a character's chat, choose **Sync my schedule**, create/sign in to the local account, and choose **Connect Google Calendar**. Read and grant the Google consent. You return to the original conversation. A successful authorization is only marked ready after a successful calendar sync. You return directly to chat, where the character starts replying immediately rather than waiting for the periodic worker. The short introduction uses the current character voice and, when appropriate, one upcoming non-private plan to ask a natural question. It is generated through your configured text provider and saved as an assistant-only message. AI failures show a retry in chat, never a fabricated success; retries and refreshes do not create a second introduction.

Keep the backend running for scheduling. Closing the browser does not stop the local worker, but stopping the backend does. The worker checks due work every 30 seconds; the active chat checks for saved messages every five seconds. This version has no browser push or operating-system notifications. No notification permission is requested, and in-app support works independently.

Use **Sync my schedule** to pause, sync, switch the active character/conversation, or disconnect. Quiet hours are under **Preferences**; privacy details are collapsed by default. Switching keeps the calendar connection and past messages; subsequent check-ins use the new character's current profile. Deleting the active character clears its active selection and prevents delivery without deleting the Google connection.

## Behavior and privacy

- Initial sync reads recent 24 hours and the next seven days. Sync runs every 15 minutes with incremental tokens and a fresh bounded window at least daily; expired sync tokens reset safely. Cancelled instances/series and changed times invalidate pending work. Before a check-in the event is fetched again to catch changes since the last sync.
- No descriptions, locations, guests, meeting URLs, or attachments are requested. Event titles are untrusted data, not model instructions. Private events and medical/legal/financial titles are masked and excluded from model context and check-ins. Sensitive-event opt-in is deliberately unavailable in this first release.
- Importance is conservative: non-recurring exams/interviews with a plausible duration, or all-day birthdays/anniversaries/graduations. A keyword alone, an ordinary meeting, or a recurring routine does not automatically justify a message. Classification is rules-based and imperfect; pause or disconnect whenever needed.
- Typical check-ins are 30 minutes before and 60 minutes after a scheduled event, with at most two non-introduction check-ins per local day. No preceding-day reminder in this version. Post-event messages ask optionally, never claim that attendance or an outcome occurred. English generation follows the current character profile. Semantic adherence remains a model behavior to validate with a real provider.
- Quiet hours default to 22:00–08:00 in the browser's IANA timezone. Equal start/end disables quiet hours. DST and all-day exclusive end dates are handled with `zoneinfo`/`tzdata`. Ongoing timed events and a four-hour snooze defer work; expired or no-longer-relevant work is dropped instead of creating a morning backlog.
- Recent explicit user discussion suppresses redundant check-ins. Ordinary chat gets at most three relevant events, only when discussing the schedule or naming an event; unrelated chat and stories receive no calendar snapshot. Explicit completed first-person statements naming an event can be retained as a bounded user quote; uncertain or future statements are not promoted to facts.
- Calendar snapshots expire after the event's end plus 24 hours; derived experience records also have a seven-day maximum and are removed with their snapshot. Retention cleanup runs during sync. Disconnect immediately deletes local tokens, snapshots, derived memories and tasks, and attempts to revoke the grant at Google. Already sent messages remain in normal chat history; remove the conversation/character to delete those too. If remote revocation fails, also remove EchoLoom from [Google Account permissions](https://myaccount.google.com/connections).
- Tokens and PKCE verifiers are Fernet-encrypted at rest. The key is outside the database in ignored `work/secrets/calendar.key`, created with restrictive POSIX permissions. On Windows use your user-only folder/ACL protection. Back up that key with the database privately; losing it requires reconnecting. Neither the key nor `.env` belongs in Git. Optionally provide `CALENDAR_ENCRYPTION_KEY` through a secret manager.
- Passwords use salted scrypt; session tokens are hashed in the database and sent only in HttpOnly, SameSite=Lax cookies. Resource ownership is checked for character, conversation, story, portrait and calendar routes. The initial account bootstrap is only appropriate on a trusted local installation. Additional account creation is off by default; it is enabled only in isolation tests.
- Persistent task status and unique message task IDs make normal retries/restarts idempotent. Failed generation has at most three attempts with increasing delays. Recovery never treats `running` as delivered: only the transaction that stores the assistant message marks delivery. A crash between an upstream paid AI response and local commit can still consume another paid call on recovery; it cannot guarantee billing-level exactly-once execution.

## Troubleshooting

- **Not configured:** add the OAuth client values and restart the backend.
- **redirect_uri_mismatch:** match the backend callback above exactly, including port, hostname and path.
- **Invalid state / returned without signing in:** use the same browser and hostname throughout; start authorization again. State expires after ten minutes and can be used only once.
- **Access denied:** add your Google account to test users, enable Calendar API, grant the calendar read scope, and check organization policy.
- **Sync needs attention:** retry or reconnect. No proactive work runs against a failed/revoked connection.
- **No check-ins:** ensure the character and this conversation are active, text AI credentials work, the backend is running, and the event qualifies. Quiet hours, already discussed events, daily caps, private events, expired reminders and cancellations can all intentionally suppress delivery. Sync alone is not a delivered message.

## Validation boundary

Automated tests use isolated databases, a fake Google adapter, a fake clock, and deterministic AI outputs. They do not authorize a real Google account or make paid model calls. A real-account OAuth/sync/revoke walkthrough and real-model tone/agency review remain required before calling the integration live-verified. Do not describe a mock consent screen as a real Google connection.
