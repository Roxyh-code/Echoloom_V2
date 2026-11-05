# Story-mode validation record

This records executed checks for the v1.2 story-mode implementation. It does not claim real-model narrative acceptance.

| Check | Observed result |
| --- | --- |
| Full Python suite | 50 passed; includes existing MVP, migrations, concurrency, branch rollback and 12 synthetic agency cases |
| Ruff lint | Passed for backend, tests, migrations and evaluation script |
| Ruff formatting | Passed |
| TypeScript | Passed |
| Next.js production build | Passed, including `/characters/[id]/stories/[storyId]` |
| Chromium browser suite | 5 passed: 2 story workflows and 3 original MVP workflows |
| Real cloud database upgrade | 0001 → 0002; current head verified |
| Production-mode local smoke | Library page, API proxy, story table readiness, real story route 404 and safe missing-provider behavior passed |
| Narrative evaluation harness | Dry run enumerated 12 cases without AI calls |
| Real-provider story evaluation | Not run: this cloud task has no LLM credentials or model configuration |
| Human review of generated narrative quality | Pending; not replaced by synthetic fixtures or JSON validation |

Browser story coverage: create/edit character → chat ＋ → invitation → one neutral card without generation → Begin → automatic first generation → staged blocks and hidden choices → explicit decision → user contribution with suffix replacement → rewrite → undo → original conversation/card → ordinary chat without card loss → refresh and resume → alternate choice → end → revisit. Mobile widths, Escape/draft retention, and invitation focus restoration were checked.

Legacy preservation coverage: migration from frozen 0001 preserves message contents and deterministic order, initializes the next shared timeline number, and is repeatable; existing profile/chat/portrait restart tests still pass. No migration changes the published 0001 or translates existing content.

Known quality limits remain documented in [story-mode.md](story-mode.md): semantic guardrails are incomplete, progress is best-effort during connection loss, API billing is not exactly-once across process crashes, and only local single-worker operation is supported.
