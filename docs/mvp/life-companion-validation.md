# Life Companion validation

The supplied [v0.3 PRD](life-companion-prd.md) is preserved. This implementation extends the existing local prototype; it does not claim hosted-production authentication or live Google verification.

## Checks completed

- 65 Python tests pass, including 15 companion tests. Calendar acceptance checks cover local account claiming and ownership, cross-account access, encrypted tokens, one-use/expired/cancelled OAuth state and PKCE, official Google HTTP contracts and minimal fields, refresh/410/revocation, cancellation recheck, before/after delivery, user-day caps, quiet-hour expiry, DST, all-day events, private events, switching, pausing, active-character deletion, context relevance, explicit-experience memory, disconnect cleanup, bounded failures and restart recovery.
- 7 Chromium browser scenarios pass together: 5 existing character/story workflows and 2 new companion workflows. The new tests cover visible desktop/mobile entry, account setup, fake consent and cancellation, persisted pre/post messages, preservation of a typed draft during polling, switching, disconnect and preserved history. After tightening the desktop layout, both companion tests were rerun and pass, including initial-viewport discovery.
- Ruff, TypeScript, production `next build`, fresh/legacy Alembic migration, repeat upgrade, downgrade, and schema/ORM comparison pass. Migration tests preserve old message content and sequence. The cloud's existing database was backed up and upgraded to `0003`; its schema matches ORM metadata.
- Desktop and mobile screenshots were inspected. The desktop portrait was reduced so the companion entry is visible without first scrolling the profile panel. Mobile has no horizontal overflow.

Run locally:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src tests/mvp alembic/versions/0003_life_companion.py
cd web
npm run typecheck
npm run build
npm run test:e2e
```

Browser tests use `tests/mvp/browser_server.py`, gated by `ECHOLOOM_TEST_SERVER=1`, temporary databases and fake providers. Its reset/clock controls are registered only in that separate test executable, not in the runtime application. No test-control endpoints or fake OAuth mode are shipped in production source.

## Real integration still pending

No Google OAuth client credentials are configured in the development environment. A real user's authorization is not something an automated fake can replace. Follow [setup](life-companion.md), then verify consent, primary-calendar sync, a changed/cancelled test event, token refresh/reconnect, revocation and disconnect on your own account. Real-provider profile tone, optional phrasing, event agency and sensitive-title classification also need human review. No paid model calls were made for these tests.

## Deliberate local scope

No external push/OS notifications, calendar writes, secondary-calendar picker, preceding-day reminders, sensitive-event opt-in, public multi-user signup or email password recovery. Check-ins and quiet hours work in-app without browser notification permission. Rules are conservative rather than an assertion that a title reveals the user's importance or experience. The operational guide documents retention, encryption-key backup, cancellation limits, one-worker scheduling and the upstream billing retry boundary.

## Conversation-first connection update

The sidebar now uses a single action without an explanatory card. The connection dialog keeps one short description and an essential read-only/AI-data notice; privacy and preferences are collapsed. Successful OAuth closes the dialog and starts the durable welcome task through an authenticated request immediately. The chat shows a replying state while the model runs and offers an error/retry if it fails. One upcoming non-private event (prioritizing meaningful plans) is revalidated and supplied to the greeting prompt; no events means a brief general invitation instead. An explicit Sync now can start one brief conversation about the latest synchronized plans; repeated requests for the same sync snapshot are deduplicated. Background sync does not create additional greetings.

Two added backend tests cover immediate delivery with the scheduler disabled, a next-week exam and character profile in the prompt, repeat requests, private/cancelled events, and no fake success on AI failure. The full seven-scenario browser suite now verifies an in-chat welcome and event question immediately after authorization without any scheduler advance, and no success modal. Existing Google live-verification limits still apply.
