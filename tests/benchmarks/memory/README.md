# Echoloom Memory A/B Runner v1.0

A runnable, **standard-library-only Python 3.12** benchmark for the **currently published** `Roxyh-code/Echoloom_V2` backend. All user and character content is fictional. It does **not** modify the repository; it calls its existing HTTP API. Unlike unit tests with mocked AI, this runner makes **real paid model API calls** through your running backend. It does **not** know your keys or connect to a remote production server.

## What it actually tests

**Character Chat** (`/api/conversations/.../messages`): seeds 6 sessions (12 user messages), then probes 15 questions in the **same** thread and 15 in **fresh** conversations. Saves every response and a conservative **keyword-coverage indicator**, not a reliable semantic correctness grade. When same-session questions are asked in sequence, later probes see earlier probe turns; use the `fresh` condition for strictly independent question evaluation. The server retrieves up to 100 recent messages from the **current** conversation; a fresh conversation does not inherit its messages by default. `--chat-seed-mode separate` explicitly distributes seed sessions among six independent conversations, probing the final one (expect information loss unless future cross-thread memory exists).

**Rehearsal** (`/api/rehearsal/...`): creates two fresh actors and a fresh non-demo scene, plants a secret with a `known_by` instruction in the first **model-generated** scene, generates four follow-up scene segments, then reads `memory.status`, `items`, `used_ids`, `pending_sources` from each job and saves the entire scene + responses. **Mem0 is only used here** and only when `MEMORY_ENABLED=true` in the backend. Whether the first event yields a genuine source-indexed fact is model-dependent and is NOT guaranteed. Telemetry `empty`, `partial`, `degraded` and `pending_sources > 0` must **not** be scored as successful memory retrieval. An `ORION-47` string in the final story alone does not establish that Mem0 helped: baseline history may still contain it. Inspect `rehearsal_jobs.json` and `rehearsal_scene.json` for knowledge leaks and semantic continuity.

**Important**: these are two separate *modules*, not the two arms of the same experiment. The genuine A/B comparison is Rehearsal **memory off vs on** using the same test script and fixed model. Chat same-thread vs fresh-thread is a separate architecture diagnostic. Switching `MEMORY_ENABLED` will **not** add Mem0 to Character Chat.

## Prepare once

1. Extract ZIP anywhere on your computer. Ensure Echoloom backend is installed, migrations are current, `.env` has your working `LLM_API_KEY` / `LLM_MODEL`, and backend running on `http://127.0.0.1:8000`. **Don't upload your `.env` or share keys.** Use a **disposable local test database/account** if possible: this script creates characters, conversations, and scenes that will persist.
2. Sign in to your existing local account. The benchmark script logs in independently via username/password. If your test database has **no account** yet, first create one from the app; you can explicitly use `--create-account` but that will establish its first account and claim legacy data.
3. In PowerShell, `cd` to the extracted folder. Store your password in an environment variable without committing it to a file:

```powershell
$env:ECHOLOOM_TEST_USERNAME = 'YOUR_LOCAL_ACCOUNT'
$env:ECHOLOOM_TEST_PASSWORD = Read-Host 'Local Echoloom password'
py -3.12 .\run_benchmark.py --mode chat --label chat_baseline
```

The first example creates **12 seed turns + 30 probe turns = 42 real text-model calls**, plus one character-generation call. For shorter/cheaper smoke testing, supply `--chat-conditions fresh` (**27 total text responses including character generation**). Cost depends on model/tokens.

## Rehearsal A/B (recommended first)

For genuinely comparable results, **A and B need the same backend code, model, consistency-review settings, exact prompts and fresh scenes.** No production data should be used. The script creates new characters/scenes in each run.

**Arm A: Mem0 disabled**. Stop backend; in `.env` set `MEMORY_ENABLED=false`; restart backend. Then execute:

```powershell
py -3.12 .\run_benchmark.py --mode rehearsal --label memory_off
```

**Arm B: Mem0 enabled**. Stop backend; back up `work/` if needed; install optional memory dependencies according to `docs/mvp/rehearsal-memory.md` (`python -m pip install -e ".[memory]"`), set `MEMORY_ENABLED=true` and the other `MEMORY_*` settings on the backend; restart backend. Then execute:

```powershell
py -3.12 .\run_benchmark.py --mode rehearsal --label memory_on
```

To summarize both arms:

```powershell
py -3.12 .\compare_runs.py .\benchmark_results\memory_off .\benchmark_results\memory_on
```

Results include `rehearsal_results.csv`, `rehearsal_jobs.json`, `rehearsal_scene.json`, `rehearsal_metadata.json`, `run_config.json`. **Manually record whether the backend was actually running with `MEMORY_ENABLED=true/false`**: the `/api/health` endpoint does not expose that flag. The job response provides the actual runtime memory telemetry. `memory_on` may index in background, so you may see `partial`/`empty`; indexing is eventually consistent. For a strict A/B, ensure the generated source exists and was indexed before judging B, or repeat with a new independent run. Do **not** claim positive or negative model-quality effect from one trial; repeat with multiple runs and compare evidence.

## Chat experiments

```powershell
# Same-thread vs fresh-thread diagnostic, within one run
py -3.12 .\run_benchmark.py --mode chat --label chat_same_vs_fresh

# Seed sessions split over six conversations; test fresh-thread portability
py -3.12 .\run_benchmark.py --mode chat --label chat_cross_session --chat-seed-mode separate --chat-conditions fresh

# Add 60 neutral distractor turns to last seed conversation to test history truncation (expensive)
py -3.12 .\run_benchmark.py --mode chat --label chat_long --filler-turns 60 --chat-conditions same
```

Each `--label` must be unique (the runner refuses to overwrite existing results). The program never sends users' real messages; it only uses included synthetic fixtures. For objective cross-thread measurement, manually score `chat_results.csv` against `expected`: 0 wrong/unsupported, 1 partly right, 2 fully correct. Keyword hints can miss correct paraphrases and can accept wrong/negated answers. The runner intentionally does not issue separate LLM-as-judge API calls. `compare_runs.py` compares **only provisional keyword coverage**.

## Safety / troubleshooting

- Run against **localhost** only; the script rejects non-local hosts and never includes the API key in HTTP requests or reports.
- Never use production accounts or production data for these experiments; the runner does not delete created resources automatically.
- For login failure, make sure your local username/password are set. For `HTTP 503` confirm `LLM_API_KEY`, model availability and migrations.
- For long rehearsal jobs increase `--job-timeout 600`; default is 300 seconds per job. For provider timeouts, adjust backend settings separately.
- **No observed scores are included in this package**; running the script is necessary for real-world observations.
