# EchoLoom

Create a fictional character, shape their identity, and return to an ongoing conversation.

**MVP v0.1:** a local character studio using FastAPI, SQLite, and Next.js. It includes structured profiles, editing, persistent chat, AI refinement previews, profile history, portrait generation/editing, and independent image revisions. Interactive activities are now available from the chat composer: **＋ → Do something together**. See the [story-mode guide](docs/mvp/story-mode.md). The interface and new generated text use English. Existing character content and conversations remain unchanged.

Start with the **[MVP development and startup guide](docs/mvp/README.md)**. It includes Windows PowerShell and macOS/Linux commands, model configuration, safe updates, and tests. Provider credentials are configured on the server; real AI operations require an API account with available credits and model access.

## Project structure

```text
src/echoloom/   Backend API, validated profiles, database models, provider adapters
web/           Next.js character studio and browser tests
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

Keep `.env`, `work/echoloom.db`, `work/portraits/`, and the same database/storage settings. Pulling code, restarting the application, or refreshing the browser does not delete saved characters, messages, versions, or portraits. Back up data with the application stopped. The current story-mode release requires `alembic upgrade head`; migration 0002 preserves old records while adding story tables and stable mixed-timeline order.

## Research foundations

The original research track remains available: reconstruct fictional characters from incomplete, multiple-source text and link judgments to source evidence. Role-play performance is not equivalent to reconstruction accuracy. This project is not a psychological assessment tool for real people; multi-document extraction is not implemented in the MVP.

- [Literature entry point](literature/README.md)
- [Schema foundations report](literature/output/schema-foundations/report.md)
- [Field-to-evidence matrix](literature/organization/schema-field-matrix.md)
- [Research next steps](literature/plans/next-steps.md)
- [Original roadmap](docs/roadmap.md)

Research documents and the originally supplied PRD are retained in their source languages. Downloaded papers and extracted full text stay local and are not committed.
