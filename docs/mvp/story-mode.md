# Interactive story mode

Implementation of the supplied [v1.2 story-mode PRD](story-mode-prd.md). The product remains English, local single-user, and single-worker. Ordinary conversations and stories have separate storage and model contexts.

## Upgrade on Windows

Stop both application terminals with Ctrl+C. From the existing repository root:

```powershell
git pull origin main
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

Keep the backend open; in a second terminal:

```powershell
cd web
npm.cmd run dev
```

Refresh the browser. No dependency changes are required for this feature. Preserve `.env`, `work/echoloom.db`, and `work/portraits/`. Do not recreate or delete the database. The **0002 migration is required**: it creates story tables, adds a conversation sequence counter and message ordering column, and backfills existing messages in their original deterministic order. The published 0001 migration is unchanged. An upgrade-and-restart test covers legacy messages and subsequent sequence allocation.

On macOS/Linux, use `.venv/bin/python -m alembic upgrade head`, then the existing backend/frontend startup commands.

## Use the feature

1. Open an existing character's chat. No minimum number of chat messages is required.
2. Click **＋ → Do something together**.
3. Describe a scene, optionally add your story name, relationship, atmosphere, and boundaries. Press **Send invitation**.
4. A neutral activity card appears in the same conversation. Creating the invitation makes **no model call** and does not claim the character accepted it.
5. Click **Begin**. The reader generates one complete, validated segment and then reveals saved blocks progressively. Model/provider configuration is the same as ordinary text chat.
6. Use **Pause**, **Play**, **Next**, or **Show all**. Reduced-motion users default to manual playback; Space toggles playback and Arrow Right reveals a block outside form controls.
7. At a decision, choose an intention or type a free response. Ordinary continuation cannot bypass the decision. Typing pauses playback. Contribution type distinguishes your dialogue, action, and direction.
8. A mid-scene contribution preserves the visible prefix and replaces its unread suffix only after successful generation. A decision already explicitly made by you is preserved even if none of its AI consequences has been revealed yet.
9. **Rewrite latest segment** uses the checkpoint before that segment; existing user-authored dialogue/actions remain user-authored. Failure keeps the old effective branch. **Undo last decision** restores the unresolved decision and removes consequences from the active branch.
10. **Back to chat** returns to the original conversation/card. Cards survive subsequent ordinary messages. **Past activities** in the same ＋ menu helps locate this conversation's cards.
11. **End story** requests a short closing scene. **End without epilogue** explicitly completes it without a model call, including after an ending request fails. Completed stories are read-only and cards show **Revisit**. Start another activity through a new invitation.
12. Deleting a story leaves a disabled card placeholder. Deleting the character removes its stories, events, segments, requests, and local portraits. A portrait referenced by a saved story cannot be discarded independently.

The invitation dialog supports Escape, focus restoration and conversation-specific local drafts. The reader preserves user drafts and request IDs for retries. Reading progress is stored on the backend per stable block ID; a network failure or abruptly closing a page may replay a few blocks. Closing the reader stops playback and client waiting, but cannot promise cancellation of an already submitted synchronous provider request; a fully generated response can still save and be available on return.

## Storage and state

- `Story`: frozen profile, profile version, selected portrait reference, setup/boundaries, player name, status, revision, effective branch head and reading position.
- `StorySegment`: immutable blocks with stable IDs, source tags, ending/decision IDs, input event, cumulative summary/facts, and parent checkpoint. The active parent chain defines the effective timeline; replaced segments remain archived.
- `StoryRequest`: canonical action payload, status and original result. Invitation deduplication lives on `ChatEvent` so deleting a story cannot make a retried old invitation create another one.
- `ChatEvent`: separate `story_card` event with a conversation sequence number. Its story reference becomes null on standalone deletion, preserving a placeholder.
- `Conversation.next_timeline_order` allocates order atomically for both messages and cards; timestamps and unrelated table IDs are not used as the mixed sort key. Legacy message endpoints remain compatible.

Statuses: `ready`, `generating`, `active`, `awaiting_choice`, `completed`. Failures retain the last stable status and set `last_error`. Generation is committed as pending before the remote call, so other windows can observe it with GET. GET never starts a model request. A single-worker startup marks abandoned requests interrupted and restores the stable status, enabling explicit retry with the original request.

Action idempotency is checked **before** revision conflicts. Reusing an ID with different content returns 409. Replaying an already successful but later undone request returns its original result plus the current story revision, without reactivating the old branch. All character mutations share the existing character lock; story writes also conditionally update the expected revision. There is no distributed locking or multi-worker guarantee.

Provider calls cannot be committed atomically with SQLite: a process failure after generation but before saving can lead to another paid call on retry. There is no exactly-once billing guarantee. Failed replacement generation never commits a partial segment. Database failures are reported as failures, retaining the existing effective branch whenever the database remains reachable.

## API mapping

| Endpoint | Purpose |
| --- | --- |
| `POST /api/characters/{cid}/stories` | Atomically create scene, frozen snapshot and originating conversation card; no AI call |
| `GET /api/conversations/{id}/timeline` | Typed `text`/`story_card` mixed timeline, ordered by conversation sequence |
| `GET /api/characters/{cid}/stories?conversation_id=...` | Conversation-filtered secondary activity lookup |
| `GET /api/stories/{sid}` | Effective branch, setup, status, revision, reading position and retry metadata |
| `POST /api/stories/{sid}/actions` | start, continue, decide, interject, rewrite, undo or end |
| `PATCH /api/stories/{sid}/progress` | Save a valid active segment/block at an expected revision |
| `DELETE /api/stories/{sid}` | Delete story and leave its chat event as a placeholder |

Ordinary chat context still reads only `Message`. Story context reads only the current story's frozen setup and active branch, never ordinary chat, another story, or inactive suffixes. Neither AI-assisted player lines nor fictional story events enter a real user profile or ordinary chat memory.

## Model contract and boundaries

`OpenAIText.story()` uses JSON mode and a strict `StoryOutput` schema, separate from plain `chat()`. The server generates all IDs/source tags. Allowed speakers are only player/character; narration has no speaker. Blocks, text, summaries and distinct decision options have length/count bounds. Output is rendered as escaped text, not HTML.

Prompts permit everyday dialogue and low-impact actions for both participants while requiring a pause before major player decisions: confessions, relationship changes, consent, secrets, payments, relocation, sacrifice or dangerous actions. Choice authorization is limited to its intention. The character can disagree. Checks inspect block flags, English output and several known agency violation patterns in player/narrative text, summaries and facts. **These rules and regexes do not prove semantic consent or narrative consistency.** Manual narrative review remains required; missed or over-sensitive checks are defects to refine, not a basis for a safety guarantee.

Generation, schema, language and agency corrections share at most one extra structured-output request; the SDK separately retains its existing bounded network retry. There is no per-block call, speculative branch generation or infinite continuation. No fake story mode is enabled in the application runtime.

Independent settings (optional; defaults shown):

```dotenv
STORY_MAX_OUTPUT_TOKENS=3500
STORY_MAX_CONTEXT_TOKENS=24000
```

Ordinary chat budgets do not change. Fixed context always contains the profile, scene, persistent constraints and explicit decisions. Recent effective segments and a cumulative earlier summary provide continuity. Earlier narrative context is reduced first; the latest segment and explicit decisions/boundaries are not silently dropped. If the remaining fixed context exceeds budget, the API returns 422. Original segments are never deleted by context budgeting.

## Verification and narrative evaluation

Required checks:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src/echoloom tests/mvp alembic scripts
cd web
npm run typecheck
npm run build
npm run test:e2e
```

Python integration tests cover invitation deduplication and snapshot isolation, mixed ordering, ordinary-chat isolation, decision blocking/ownership, visibly different branch outcomes, unread suffix/fact invalidation, rewrite failure and source preservation, undo and archived-request replay, concurrent starts, observable pending generation, restart recovery, progress, direct ending, deletion placeholders, portrait protection, schema/language/agency correction and budgets. Browser tests run the full invitation→reader→decision→contribution→rewrite→undo→return→refresh→revisit workflow, plus mobile/dialog keyboard checks and existing MVP regressions. Test servers and providers are ephemeral and cannot charge real APIs.

Twelve fixed cases are in [story-evaluation-cases.json](story-evaluation-cases.json). Their automated checks use **synthetic candidates** to exercise specific agency contracts. They are **not** evaluations of a real model. The cases cover everyday scenes, reunions, mysteries, conflict, relationship escalation, consent, secrets, payment, relocation, danger, and limited authorization.

Optional live evaluation from the repository root:

```bash
.venv/bin/python scripts/evaluate_story_mode.py
# Explicitly opt into 12 paid generation requests, each with at most one correction:
.venv/bin/python scripts/evaluate_story_mode.py --live
```

The script requires configured `LLM_API_KEY` and `LLM_MODEL`, saves results under ignored `work/story-evaluation.json`, and leaves human review fields pending. Review agency, character consistency, readable pacing and meaningful choice consequences before marking narrative acceptance complete. A valid JSON response alone is not a passed narrative evaluation. No real-model narrative evaluation was performed in this cloud task because it has no model credentials; the user's successful earlier local image/chat tests do not establish story quality.

## Known limits

Single local user/worker; synchronous provider calls; no streamed partial JSON, cross-device sync, voice/video, background generation queue, full branch-tree browser, arbitrary old-segment editing or masked portraits. Completed scenes are read-only. The first version uses cumulative model summaries rather than a separate incremental world-state engine. Server-side semantic checks are conservative and incomplete. Reading progress is best-effort during connection loss. Account access, current model support, quotas and actual narrative quality still need live acceptance.
