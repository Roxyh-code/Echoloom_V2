# EchoLoom

**Create characters. Discover their stories.**

A mobile-first character-driven story studio. Describe a character to generate their profile and portrait together, shape their motivations, then play a role or direct two characters. Explore, edit and branch a story, save named versions, and export a draft.

**Creator MVP:** open `http://127.0.0.1:3000/creator`. The root URL now opens Creator. Try **The Last Train** without model keys, or use your configured text and image providers for original characters and free-form stories. Demo mode is explicitly labeled.

- **[Windows update and Creator walkthrough](docs/product/creator-mvp.md)** — stop both services, back up `work`, pull, run migration **0004**, then restart.
- [Full Creator PRD](docs/product/creator-mobile-mvp-prd.md) · [Current positioning and next steps](docs/product/README.md) · [Validation and remaining checks](docs/product/creator-validation.md)
- [First installation and model configuration](docs/mvp/README.md)

The existing companion remains at `/characters`: saved chats, portraits, **Do something together** stories and optional Google Calendar. [Previous companion demo](demo/README.md) · [Story guide](docs/mvp/story-mode.md) · [Calendar setup](docs/mvp/life-companion.md). Existing records are not translated or deleted. Real AI operations require an API account with model access and available credits.

## Project structure

```text
src/echoloom/   Backend API, validated profiles, database models, provider adapters
web/           Next.js mobile Creator, companion, and browser tests
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

Keep `.env`, `work/echoloom.db`, `work/portraits/`, `work/secrets/calendar.key`, and the same database/storage settings. Pulling code, restarting the application, or refreshing the browser does not delete saved characters, messages, versions, or portraits. Back up data with the application stopped. Run `alembic upgrade head` after upgrading dependencies. Migration 0002 adds story tables and timeline ordering; migration 0003 adds accounts and calendar support. Migration 0004 adds Creator works and recovery requests, and a character archive flag. These migrations preserve existing records. The first local account claims existing characters, history and Creator works.

## Research foundations

The original research track remains available: reconstruct fictional characters from incomplete, multiple-source text and link judgments to source evidence. Role-play performance is not equivalent to reconstruction accuracy. This project is not a psychological assessment tool for real people; multi-document extraction is not implemented in the MVP.

- [Literature entry point](literature/README.md)
- [Schema foundations report](literature/output/schema-foundations/report.md)
- [Field-to-evidence matrix](literature/organization/schema-field-matrix.md)
- [Research next steps](literature/plans/next-steps.md)
- [Original research roadmap](docs/roadmap.md)

Research documents and the originally supplied PRD are retained in their source languages. Downloaded papers and extracted full text stay local and are not committed.
