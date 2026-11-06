# EchoLoom product roadmap

> 历史陪伴方向（2026-11-04）。当前主方向已切换为 Character + Interactive Story Creator；请看 [当前定位与计划](README.md) 和 [Creator PRD](creator-mobile-mvp-prd.md)。本文保留作原有陪伴功能参考。

Updated: November 4, 2026. Priorities for the companion experience; these are proposed stages, not release-date commitments.

Product north star: **Your favorite character. By your side.** The next work should strengthen recognizable character identity, user-led shared experiences and useful everyday continuity.

## Current baseline

Implemented in the local prototype:

- Character creation, profile editing, AI refinement and saved profile versions.
- Portrait generation, selection, editing and image-version restoration.
- Persistent ordinary chat and saved interactive story cards.
- Story dialogue contributions, choices, direction changes, rewriting and progress recovery.
- Side-by-side **Do something together** and **Sync my schedule** actions.
- Optional read-only Google primary-calendar connection, account ownership and encrypted credentials.
- Immediate in-chat calendar acknowledgment, a relevant upcoming-plan question, and persisted check-ins with quiet hours, caps, cancellation checks and deduplication.

The updated [demo](../../demo/README.md) shows these flows using prepared data. The existing 65 backend tests and seven browser scenarios cover the implemented workflows; passing mock tests is distinct from real-account and live-model validation.

## Next: make the complete loop dependable

| Priority | Work | Acceptance criteria |
| --- | --- | --- |
| P0 | Real Google Calendar walkthrough | On an explicitly authorized test account, verify consent, initial/incremental sync, new/changed/cancelled events, recurring and all-day events, refresh/revocation and disconnect. Record outcomes without publishing personal event data or credentials. |
| P0 | Calendar conversation recovery | A failed AI greeting can recover after provider/quota/configuration issues are fixed, without disconnecting the calendar or duplicating saved replies. Manual sync finds new events promptly; unchanged snapshots and retries stay deduplicated. |
| P0 | Live character-tone evaluation | Review multiple character styles across chat, first calendar greeting, follow-up and story redirection. Replies stay brief, character-specific, relevant, and free of invented attendance or outcomes. |
| P0 | First-session usability | Observe a small set of new users creating a character, sending a message, finding both activity buttons and making a story choice. Fix points where people need an explanation or lose their place. Calendar connection remains optional. |
| P0 | Runtime and upgrade reliability | Verify Windows startup, data backup, migration, provider-error recovery, restarts and task recovery on the actual local setup. Settings and records survive an ordinary update. |

Gate: finish the create → talk → shared activity → calendar conversation loop with real services before expanding to additional integrations.

## Then: strengthen continuity and shared experiences

| Priority | Work | Acceptance criteria |
| --- | --- | --- |
| P1 | User-controlled companion memory | Users can inspect, correct and forget remembered details. Explicit personal statements stay distinct from calendar plans, model suggestions and fictional story events. |
| P1 | Recall shared activities | With user approval, the character can refer to an appropriate saved story summary in later chat. Fictional experiences remain labeled as fictional, and story summaries never become real-life facts automatically. |
| P1 | More natural story controls | Test a simpler presentation for contributing dialogue, choosing a direction and rewriting. Preserve agency, visible consequences, safe undo/recovery and saved progress. |
| P1 | Useful, adjustable check-ins | Learn which event categories and check-in styles users actually value. Offer simple relevance controls, clear pause/snooze feedback, and fewer unwanted repetitions while retaining conservative defaults. |
| P1 | Better return visits | Make recent conversations and unfinished activities easy to resume, including on small screens. Verify drafts, scroll position and active-conversation handling as messages arrive. |

Gate: demonstrate continuity users can understand and control, with reliable correction and deletion.

## Later: broaden access and expression

| Priority | Candidate | Required before release |
| --- | --- | --- |
| P2 | Optional spoken conversation | Evaluate character voice, latency, cost, consent and accessibility. Provide text equivalents and an obvious mute/stop control. Demo narration is separate from this feature. |
| P2 | Opt-in browser/OS notifications | Add delivery infrastructure, permission handling and useful fallback behavior. In-app support continues to work when notifications are declined. |
| P2 | Hosted access or packaged local launch | Design production-grade authentication/recovery, session security, ownership, encrypted-secret operations and worker deployment before public multi-user access. Keep local installation and data migration understandable. |
| P2 | Additional activity formats | Explore a small number of user-requested shared activities after the current story loop is validated. Reuse the same character identity, user controls and persistence. |

Each candidate needs its own scope, privacy review where applicable, cost estimate and acceptance tests. No additional calendar provider or external messaging integration is committed here.

## How we will judge progress

- Can a first-time user find the two activity actions without a tutorial?
- Does a character's voice remain recognizable after a choice, rewrite and calendar follow-up?
- Does a calendar conversation feel specific and welcome? Can the user pause it easily?
- Can people resume a conversation or story without losing their work?
- Are there zero duplicate deliveries, cross-account data exposures or invented event outcomes in the evaluated cases?
- Do users choose to return because they value the interaction? Use qualitative feedback and voluntary return visits alongside reliability and cost measurements.

## Relationship to the research track

This is the active product roadmap. The [original research roadmap](../roadmap.md), literature, schemas and evidence-based character-reconstruction work remain available as a separate research track. Research can inform character quality and evaluation without being presented as an already shipped companion capability.
