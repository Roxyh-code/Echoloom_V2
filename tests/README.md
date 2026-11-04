# Validation and regression tests

MVP API, data, and provider tests live in `tests/mvp/`. From the repository root, run `.venv/bin/python -m pytest -q`. Browser tests live in `web/e2e/`: run `cd web && npm run test:e2e`. They use a temporary database and mocked paid providers. See the [MVP guide](../docs/mvp/README.md) for prerequisites.

Prioritize failures that damage results: incorrect source scope, dangling evidence IDs, cross-character ownership, silently overwritten conflicts, mixed versions, and unknown information presented as fact. Use small original fixtures rather than duplicating every implementation detail.

Keep deterministic constraints separate from paid-model research evaluations. Record the latter in `experiments/`; normal tests should not call paid APIs.
