# EchoLoom

**Let your characters play it out.**

A mobile scene rehearsal studio for fiction creators. Choose two characters, describe a situation, and watch a short performance. Give a direction, introduce an event, take over a role, or try a different version. Save the scene you believe in and rehearse what comes next.

**New default entrance:** `http://127.0.0.1:3000/rehearsal` (the root URL opens it too). Starry indigo theatre, champagne controls, serif headings, English by default. Existing characters and private data are preserved; describing a new character automatically creates both their profile and portrait in the same mobile interface.

- **[Windows update and rehearsal walkthrough](docs/product/scene-rehearsal.md)** — stop both services, back up `work`, pull, run migration **0005**, restart.
- [User-provided rehearsal PRD](docs/product/scene-rehearsal-prd.md) · [Current positioning and next steps](docs/product/README.md)
- [First installation and model configuration](docs/mvp/README.md)

Try **The station reunion · Demo** without model keys. It is clearly labeled and uses prepared performances; saving, versions, exports and source-linked next scenes really persist. Custom rehearsals use your server's text model. Actual model quality, costs and physical-phone behavior still need separate validation.

The previous Creator remains at `/creator`, and the companion archive at `/companion`: saved chats, portraits, **Do something together** stories and optional Google Calendar. [Previous Creator guide](docs/product/creator-mvp.md) · [Companion demo](demo/README.md) · [Calendar setup](docs/mvp/life-companion.md). `/characters` and `/characters/new` now open the unified mobile character studio. No old work is silently converted or deleted.

## Project structure

```text
src/echoloom/   Backend API, validated profiles, database models, provider adapters
web/           Next.js mobile rehearsal studio, previous Creator, and companion
alembic/       Database migrations
tests/mvp/     Backend regression tests
docs/mvp/      MVP requirements and development guide
work/          Ignored local database, portraits, and scratch files
literature/    Original research, source records, reading notes, and reports
schemas/       Research-driven schema design
data/          Future original character fixtures and annotations
experiments/   Method comparisons and research evaluations
```

## Existing records survive updates

Keep `.env`, `work/echoloom.db`, `work/portraits/`, `work/secrets/calendar.key`, and the same database/storage settings. Pulling code, restarting the application, or refreshing the browser does not delete saved characters, messages, versions, or portraits. Back up data with the application stopped. Run `alembic upgrade head` after upgrading dependencies. Migration 0002 adds story tables and timeline ordering; migration 0003 adds accounts and calendar support. Migration 0004 adds Creator works and recovery requests, and a character archive flag. Migration 0005 adds rehearsal scenes and durable operations. These migrations preserve existing records. The first local account claims existing characters, history, Creator works and rehearsals.

## Research foundations

The original research track remains available: reconstruct fictional characters from incomplete, multiple-source text and link judgments to source evidence. Role-play performance is not equivalent to reconstruction accuracy. This project is not a psychological assessment tool for real people; multi-document extraction is not implemented in the MVP.

- [Literature entry point](literature/README.md)
- [Schema foundations report](literature/output/schema-foundations/report.md)
- [Field-to-evidence matrix](literature/organization/schema-field-matrix.md)
- [Research next steps](literature/plans/next-steps.md)
- [Original research roadmap](docs/roadmap.md)

Research documents and the originally supplied PRD are retained in their source languages. Downloaded papers and extracted full text stay local and are not committed.
