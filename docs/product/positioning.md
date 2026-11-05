# EchoLoom product positioning

Updated: November 4, 2026. Product direction for the current companion prototype.

## Your favorite character. By your side.

EchoLoom is an AI character companion for everyday conversations, shared stories, and the plans that matter to you. Create someone original or describe a favorite fictional character, shape their personality and appearance, and return to a familiar presence over time.

The experience should feel warm, playful, and easy to enter: say something, do something together, or share a little of your schedule. The character has a recognizable voice; the user chooses how the relationship and activities develop.

Homepage supporting line:

> Chat, share stories, and feel a little closer through everyday life.

## Who it is for

People who enjoy fictional characters, imaginative role-play, and a familiar conversational companion. A useful first session lets someone create a character they care about, exchange a few messages, and experience a shared moment they can shape.

An ongoing session offers a simple reason to return: continue a conversation, revisit a saved story, try a new activity, or talk about an upcoming plan.

## Three parts of the experience

| Part | User experience | Current foundation |
| --- | --- | --- |
| A familiar presence | A character with a consistent personality, appearance and way of speaking | Editable profiles, portrait generation/editing, saved revisions, ongoing chat |
| Shared moments | Spend time together in a scene that responds to the user's choices | Story invitations, staged reading, custom dialogue, decisions, direction changes and rewrites |
| Everyday connection | Share selected calendar context and talk about meaningful plans | Optional read-only primary-calendar connection, immediate conversation after connection/sync, conservative event-related check-ins |

## Interaction principles

- Put useful actions beside the conversation. **Do something together** and **Sync my schedule** sit above the message input.
- Keep the default surface short. Use one clear action and one useful sentence; place preferences and detailed explanations behind disclosure controls.
- Let successful actions lead into the experience. Calendar connection returns directly to chat with a replying state, a brief character-led acknowledgment, and a relevant question when there is an appropriate upcoming plan.
- Preserve the user's voice and choices. Offer decisions, accept their own dialogue, allow changes of direction, and keep the current scene recoverable when a rewrite fails.
- Make warmth specific. Respond to what the user actually shares, remember the current character's style, and ask one natural question at a time.
- Keep companionship low-pressure. Check-ins can be paused or disconnected, respect quiet hours, and avoid guilt, pressure or assumptions about feelings and outcomes.
- Make return visits easy. Keep characters, portraits, conversations and story progress available after refresh and restart.

## Calendar conversation example

The November demo uses a prepared physics exam as an example. Evelyn briefly acknowledges that she has more context about the user's days, offers occasional in-chat support, and asks what topics the exam covers. The user mentions circuits and sign conventions; she responds with gentle humor and offers to work through a small practice problem.

The calendar supplies a scheduled plan. The user's messages supply personal details and preferences. A scheduled exam is never evidence that the user attended it, passed it or felt a particular way.

## Current scope and evidence

The current application is a local English-language prototype with saved character data, chat, interactive stories and optional calendar support. It uses a local account for personal calendar ownership; public hosted identity, browser push and in-product spoken conversation remain planned work.

Story events are stored as fictional activities. Calendar experiences and ordinary conversation are separate data sources; a unified, user-controlled long-term memory is a future capability, not a current promise.

The [companion walkthrough](../../demo/README.md) records the actual UI and persistence with prepared AI text, portraits, calendar events and simulated consent. It demonstrates the intended interaction flow. Real Google authorization and live-model quality require separate validation; the recording does not establish live integration performance.

## Product language

Use direct, friendly English. Prefer **Do something together**, **Sync my schedule**, **Your calendar**, and a natural character question over repeated product explanations.

Keep the character voice recognizable and the product controls predictable. The synthetic narrator in the demo explains the workflow; it does not represent a shipped character-voice feature.

See the [product roadmap](roadmap.md) for priorities and acceptance criteria.
