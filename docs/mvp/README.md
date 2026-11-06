# EchoLoom MVP v0.1

> 当前默认产品是移动排练工作室：见 [新版本更新与使用](../product/scene-rehearsal.md)。首次安装仍可沿用下面的依赖与启动命令，数据库请升级到最新迁移 0005。

A local, single-user fictional character studio: describe → create → edit → chat → refine. The interface, system messages, and new AI-generated text use English. Existing character content and conversations remain unchanged. Original research assets remain under `literature/`.

## Requirements

Python 3.12+, Node.js 20.9+, and npm. Tested in the cloud on Python 3.12 and Node 24. Provider credentials are needed for real AI operations, but not for viewing the interface.

## Windows PowerShell

Run these commands from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
# First installation only: do not overwrite an existing .env.
Copy-Item .env.example .env
# Edit .env to configure models and API credentials.
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

Keep the backend terminal open. In a second terminal, from the repository root:

```powershell
cd web
npm.cmd ci
npm.cmd run dev
```

Windows startup commands have not been tested on a Windows machine by the developer. The lockfile excludes `uvloop` on Windows. Using `npm.cmd` avoids PowerShell script execution policy errors.

## macOS and Linux

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
# First installation only: preserve an existing .env.
cp .env.example .env
# Configure credentials and models in .env.
.venv/bin/alembic upgrade head
.venv/bin/uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```bash
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:3000/characters` in your local browser. Backend API documentation is at `http://127.0.0.1:8000/docs`. Both processes must remain running. Production-mode local startup: `cd web && npm run build && npm start`.

The frontend proxies `/api/*` to the backend; browser JavaScript never receives provider keys. Set `API_BASE_URL` before frontend startup to change the backend address. Production rewrites use the value present at **build time**.

## Provider configuration

Server-side `.env` settings:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=<account-supported-text-model>
LLM_API_KEY=<your-api-key>
IMAGE_PROVIDER=openai
IMAGE_MODEL=<account-supported-image-model>
IMAGE_API_KEY=
```

The text model must support Chat Completions, JSON mode, and `max_completion_tokens`. The image model must support image generation and editing, `1024x1024` output, and base64 image responses. Model IDs are configured rather than hardcoded. Check current availability and pricing before selecting a model; old model IDs may be retired. In particular, the official SDK marks `gpt-image-1` as shut down on October 23, 2026 and names `gpt-image-2.5-sunburst` and `gpt-image-2.5-flare` as replacements. Account access still needs verification.

Leave `IMAGE_API_KEY` empty to reuse `LLM_API_KEY`. Both operations incur their respective API usage charges; ChatGPT subscriptions do not include API usage. Restart the backend after editing `.env`.

Never commit `.env`, send credentials in chat, or put keys in `NEXT_PUBLIC_*` variables. Cloud environments need HTTPS access to `api.openai.com` and secure credential bindings. Missing credentials return a clear 503 instead of simulated AI responses. Health configuration flags indicate presence, not remote authorization. Read, manually edit, and restore existing data without provider credentials.

OpenAI is the first image adapter because its SDK covers generation and source-image editing. Ideogram and FLUX adapters and a paid quality comparison are not implemented. Replaceable `TextProvider` and `ImageProvider` interfaces isolate business logic from SDK response formats. Official definitions checked: [Chat Completions](https://github.com/openai/openai-python/blob/main/src/openai/resources/chat/completions/completions.py), [Images](https://github.com/openai/openai-python/blob/main/src/openai/resources/images.py), and [image model IDs](https://github.com/openai/openai-python/blob/main/src/openai/types/image_model.py).

## Interactive story mode

The new activity workflow starts inside chat: **Do something together → Send invitation → Begin** above the chat input. It includes staged reading, decisions, free contributions, latest-segment rewrites, undo, progress and independent persistence. See the [story-mode guide](story-mode.md) for usage, data boundaries and verification.

**This release requires `alembic upgrade head` before restarting the backend.** Migration 0002 preserves existing messages while adding mixed-timeline ordering and separate story tables. No new provider or dependency installation is required.

## Updating without losing data

Keep the same local checkout, `.env`, `DATABASE_URL`, and `IMAGE_DIRECTORY`. By default, records live in `work/echoloom.db` and portraits in `work/portraits/`. These paths are ignored by Git; `git pull`, a server restart, and a browser refresh do not delete them.

Stop both application processes before updating, then run `git pull origin main`. Restart the backend and frontend using the commands above. If dependency files changed, rerun the corresponding locked installation. Run `alembic upgrade head` when a release adds migrations. The earlier English-interface update added no migration. Story mode now adds migration 0002; it preserves existing character content, message text and portraits. Legacy system revision labels are translated only when displayed.

Do not delete `work/`, recreate the project in a different directory without copying its data, or change the database URL if you want to keep existing records. Back up the database and portraits together while the application is stopped; copying only a live `.db` file may miss writes in SQLite WAL files. Test databases are temporary and separate from user data.

## Implemented behavior

- Responsive English library, creation form, structured profile editor, chat, empty states, loading indicators, and retry handling.
- Pydantic profile validation; original descriptions remain available for review. Unknown history can stay empty. Suggestions are editable, but generated additions are not yet individually attributed to source facts.
- Stable character IDs, SQLite persistence, multiple conversations, and profile-version metadata on messages.
- Manual edits make no model call. AI refinement proposes only explicit leaf fields and waits for approval. Stale edits and suggestions return 409.
- Profile restoration creates another version without deleting history or changing portraits or old messages. Future chat uses the latest profile.
- Portrait generation, editing from the selected original image, local storage, candidate preview, selection/restoration, and discard. Editing an image does not automatically change text fields.
- Character deletion cascades to profiles, suggestions, conversations, messages, image records, and local portrait files.

## Data and concurrency

Backend: `src/echoloom/`; frontend: `web/`; frozen initial database migration: `alembic/`. SQLAlchemy provides the database access layer. Confirmed profile changes create immutable revision records. Unaccepted proposals persist until character deletion, but there is no cross-page proposal inbox.

Use a single backend worker: character-level locks serialize mutations within one process. Optimistic version checks prevent stale profile overwrites. Selecting an image does not advance the editor form's profile version. Chat saves the complete user/assistant turn in one transaction, with a client UUID for retry deduplication. If a process dies after a remote response but before commit, a retry may still incur another remote charge.

Candidates do not replace the selected portrait until accepted. A non-current image can be discarded only if it is not the parent of another revision. Source images remain available for the revision chain.

## Budgets and failure handling

Settings in `.env.example` bound inputs, output/context budgets, timeouts, hourly image requests per character, and image sizes. Failed image attempts count toward the hourly budget, which survives restarts. Image requests are not automatically retried. Text SDK calls retry at most once using SDK backoff.

Chat language rules explicitly override the language of legacy profiles and conversations. Replies containing CJK ideographs trigger at most one corrective model call, which may incur an additional API charge. If correction still fails, the request returns an English error and no new messages are saved. Existing profiles and messages are never translated in place. English replies require no corrective call.

Chat includes the current profile and reads at most 100 recent messages. A conservative UTF-8 byte estimate reserves output and framing space, retaining a contiguous suffix of whole turns; older messages stay saved. A profile too large for the budget returns 422 rather than being silently dropped.

Images use synchronous requests with visible loading states. The frontend proxy timeout is 240 seconds. There is no background image queue or cross-refresh job progress. AI editing may change unintended details; preview before selecting. Region-mask editing is deferred.

Logs record provider/model, operation, elapsed time, result, and available token usage, without keys or conversation/prompt content. Image failures show fixed English explanations for organization verification, moderation, quota, permissions, invalid models, and connectivity. Diagnostic metadata is allowlisted; raw provider responses are not exposed. Costs are not estimated from an unverified price table.

## Tests

From the repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src/echoloom tests/mvp alembic
```

On Windows replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`.

From `web/`:

```bash
npm run typecheck
npm run build
# Reuse /usr/bin/chromium or set CHROMIUM_PATH when available.
# Otherwise, install a test browser once:
npx playwright install chromium
npm run test:e2e
```

The Python lockfile pins tested backend/development dependencies; `web/package-lock.json` pins frontend dependencies. Playwright runs the actual frontend and backend with test-only AI adapters and an ephemeral database on ports 3001/8001. It neither uses real user data nor charges AI providers. There is no mock-provider mode in the application runtime.

Tests cover creation/restart persistence, field edits, bounded context, preview/approval, stale conflicts, profile/portrait restoration, source-image editing, request failures, retries and concurrent deduplication, image budgets, deletion/ownership, and safe error reporting. Browser tests exercise the full journey and mobile-width layout.

Real provider acceptance requires credentials: verify explicit character facts, conversational consistency, changed future behavior after refinement, and image identity preservation after edits. Mock tests validate application behavior and adapter contracts, not provider output quality or account permissions.

## Current limits

This is a local single-user prototype bound to loopback, not a public multi-user service. Authentication, authorization, moderation, rate limits, and user isolation need separate work before public deployment. Streaming replies, image background jobs, voice/video, vector memory, production deployment, and advanced evidence reconstruction are deferred. Original research remains in `literature/` and other research documentation.

## Life Companion v0.3

Optional read-only Google Calendar support, local account protection, and persisted in-app check-ins are documented in [Life Companion setup](life-companion.md). Upgrading requires installing the updated lockfile and running `alembic upgrade head`; existing records are preserved. Google OAuth credentials and a real consent flow are required for live calendar use.
