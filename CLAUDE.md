# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal Python toolkit built around an **OpenAI-powered chat system** (`ChatSystem/`) with
function-calling, four specialized **agents** (`agents/`), and twelve standalone CLI **utilities**
(`tools/`). The chat system exposes the utilities to the LLM as callable tools.

Two mental models that are not obvious from the file tree and drive almost every change:

1. **Tools are external CLI subprocesses, not Python imports.** The LLM never imports a tool class.
   `tool_executor.py` shells out to `python tools/<Tool>/<tool>.py …` with `shell=False` and a 60s
   timeout, parses stdout (JSON if possible), and wraps everything in a `ToolExecutionResult`.
2. **The hot paths are heavily cache-optimized and the caches are load-bearing.** `conversation.py`,
   `chat_engine.py`, `config.py`, and `tool_metrics.py` have been through many rounds of perf work
   (logged in `.jules/bolt.md`). Several invariants below exist only to keep those caches correct —
   breaking them silently reintroduces O(N²) behavior or corrupts history. **Read `.jules/bolt.md`
   before touching those four files.**

## Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt   # runtime + test deps
cp .env.example .env                                       # then set OPENAI_API_KEY

python -m ChatSystem            # launch the interactive Rich CLI
```

### Tests

`pytest.ini` sets `testpaths = tests`, and every real pytest suite lives under `tests/` (collected
recursively):

- `tests/test_*.py` — the 12 utility/tool suites + `test_tool_contracts.py` / `test_tool_result.py`
- `tests/agents/` — planner, reasoner, executor routing, agent manager/personas/switching
- `tests/chatsystem/` — config/conversation, I/O batching, ToolMetrics

The agent/ChatSystem suites are hermetic (fake API key + stubbed OpenAI client, `auto_save=False`
conversations); the tool suites shell out to the real utility subprocesses.

```bash
pytest -p no:flake8 -p no:mypy                  # whole suite (the plugin flags are required — see below)
pytest tests/agents/                            # one subdir
pytest tests/test_tool_contracts.py             # one file
pytest tests/test_tool_contracts.py::TestToolContracts::test_unknown_function_returns_execution_result
pytest -m "not slow"                            # markers: slow / integration / unit (strict-markers is on)
pytest --cov=. --cov-report=html                # coverage (pytest-cov installed; off by default)
```

Put new tests under the matching `tests/` subdir, not at the repo root (a bare root `test_*.py` is
outside `testpaths` and won't be collected).

**Two gotchas when running the full suite:**
- `requirements-dev.txt` pins `pytest-flake8` / `pytest-mypy`, which are **incompatible with current
  pytest** and abort collection with a `PluginValidationError`. Always pass `-p no:flake8 -p no:mypy`.
- `tests/test_duplicate_finder.py::test_case_sensitive_name_matching` fails on a **case-insensitive
  filesystem** (the macOS default) — it relies on `File.txt` ≠ `file.txt`. Pre-existing and
  environmental, not a regression.

### Lint / typecheck

`flake8` / `mypy` ship as dev deps but the repo has **no config and no enforced lint step** (and the
pytest plugins for them are broken — see above). Run `flake8 .` / `mypy .` ad hoc if wanted.

## Architecture

### Request lifecycle (`ChatSystem/core/chat_engine.py`)

`ChatEngine.chat()` returns an `Iterator[str]` (same path for streaming and non-streaming) and runs a
recursive loop: add user message → call OpenAI with full history → if the response has `tool_calls`,
execute them and call the API again with the results appended → yield assistant content.

- **Recursion is bounded** by `tool_call_depth` vs `max_tool_call_depth` (5) to stop tool-call loops.
- **Tools run in parallel** via a `ThreadPoolExecutor`, but only the subprocess call is threaded;
  results are collected in original order and metrics/history are mutated **sequentially on the main
  thread** to keep shared state race-free. Preserve this split if you touch `_handle_tool_calls`.
- **Reasoning models are special-cased** via the `REASONING_MODELS` tuple (`o1`/`o3*`), checked with
  `str.startswith(tuple)`. They use `max_completion_tokens` (not `max_tokens`) and reject `temperature`.
- Streaming reconstructs `tool_calls` from delta chunks manually, accumulating fragments in lists and
  `"".join()`-ing them (never `+=`) — this was an intentional O(N²) fix.

### Tool integration (`ChatSystem/tools/`) — static, not discovered

There is **no filesystem auto-discovery** despite older docs claiming otherwise. Three hand-maintained
pieces must agree:

- `tool_adapter.py` — `TOOL_DEFINITIONS` dict: the hardcoded OpenAI function schemas (name, description,
  JSON-Schema params). Source of truth for what the LLM sees.
- `tool_executor.py` — `function_to_util` dict maps each OpenAI function name → script path, and
  `_execute_utility()` translates the JSON args into CLI flags per tool. Returns a `ToolExecutionResult`
  (`tool_result.py`) with a `ToolStatus` (`SUCCESS`/`ERROR`/`TIMEOUT`/`MANUAL_REQUIRED`).
- `tool_registry.py` — wires adapter + executor; `enabled_tools` defaults to all `TOOL_DEFINITIONS`
  keys, otherwise is filtered by `config.yaml` `tools.enabled` (a list of **CamelCase util names**, not
  function names).

**To add a tool** you must edit all three: create `tools/<Name>/<name>.py`, add a `TOOL_DEFINITIONS`
entry, add a `function_to_util` mapping + an `_execute_utility()` case, and add the name to
`config.yaml`. Missing any step fails silently.

`MANUAL_REQUIRED` is not an error — interactive tools (e.g. BulkRename) can't read stdin as a
subprocess, so they return that status plus a payload the caller is expected to act on.

### Each utility tool (`tools/<Name>/`)

One repeating pattern, learn it once: PascalCase dir (`CodeWhisper`) → snake_case file
(`code_whisper.py`) → a `Colors` helper + a main class whose name need **not** match the dir
(`CodeWhisper/` contains `PythonAnalyzer`) + an argparse `main()`. Module docstrings carry an
`Author: Vishal Kumar` / `License: MIT` header. `tool_executor.py` appends `--no-color` to most calls.

### Conversation + state + caching (`ChatSystem/core/conversation.py`)

`ConversationManager` owns history (persisted to `~/.chatsystem_history.json` by default — a single
shared file unless overridden) and four invalidate-on-write caches: `_cached_openai_messages`,
`_cached_openai_messages_no_system`, `_cached_dumped_messages`, `_cached_summary`. Invariants:

- Any method that mutates the message list **must** keep `_invalidate_cache()`, the running
  `_total_tokens`, and `_role_counts` (a `defaultdict(int)`) consistent. `add_message` updates caches
  *incrementally* rather than rebuilding.
- `Message.tokens` is a **public** field (not a `PrivateAttr`) on purpose — token counts serialize to
  the history JSON so startup skips re-running tiktoken. Don't make it private.
- `batch_saves()` is a **reentrant** context manager that defers disk writes until the outermost exit;
  `_handle_tool_calls` wraps multi-message turns in it. Outside a batch, every `add_message` writes to
  disk.
- `model_dump(mode='json')` is required where it appears (datetime → ISO string); plain `model_dump`
  raises on save.
- `trim_context()` / summarization always keep system messages and drop oldest non-system first.
  **`trim_context` is not called automatically** anywhere in the message flow — it's manual.

### Agents (`agents/`)

`agent_manager.py` is the orchestrator: the `AgentType` enum + `AGENT_DESCRIPTIONS` dict are the source
of truth (used for fuzzy `/agent <name>` matching). Four agents — `task_executor`, `transcript_analyzer`,
`trillionaire_futurist`, `framework_teacher` — each defined by a long `SYSTEM_PERSONA` injected into the
conversation on creation. All agents **share one `ChatEngine`/history**; isolation between them is only
the persona text, so **swapping the engine requires re-adding the persona** (the CLI creates a fresh
`ConversationManager` + `ChatEngine` per switch to prevent persona bleed).

`task_executor` is the only multi-step agent: `executor.py` runs a planner→reason→act loop. `planner.py`
makes one LLM call to produce a `TaskPlan` of `TaskStep`s (falls back to regex parsing if the JSON is
malformed). `reasoner.py` records thought/action/observation/elapsed per step and attaches the trace
back into conversation history. Heuristic `_needs_planning()` (keyword match) decides single- vs
multi-step; override with `use_planning=`.

### Config (`ChatSystem/core/config.py`, `config.yaml`, `.env`)

`Settings` (Pydantic) loads `.env` for secrets/flags and caches the parsed `config.yaml` in a
`PrivateAttr` (`get_settings()` is itself `lru_cache`d). `config.yaml` holds `models` (task→model map),
`tools.enabled`, and per-agent blocks; lookups cascade agent-specific → `agent.*` defaults → `Settings`
defaults. Invalid model names are rejected by validation.

## Gotchas / footguns

- **Config drift — per-agent blocks barely wire up.** `agent_manager.py` passes **only
  `max_iterations`** from each `agents.<name>` block into the agent constructors; `enable_planning` /
  `enable_reasoning` set there never reach the executor (the constructor defaults win).
  `persist_reasoning`, `auto_summarize` / `summarize_threshold`, `conversation.auto_summarize_enabled`
  / `summarize_target_ratio`, and the entire `cli.*` block (`theme`, `show_timestamps`, …) are read by
  **no** code. The `models:` task→model map *is* live, but only for agents that call
  `chat_engine.chat(model=settings.get_model_for_task(...))` (e.g. the analyzer) — `task_executor`
  doesn't, so it runs on the default `MODEL_NAME`, not its configured `o3-mini`. **Grep for a key
  before assuming it does anything.**
- A bare `pytest` aborts collection until the broken lint plugins are disabled: `-p no:flake8 -p no:mypy` (see Tests).
- Tool stdout that isn't valid JSON is silently treated as plain text (`structured_payload=None`);
  validation messages can get swallowed.
- The hardcoded 60s subprocess timeout kills long tool runs (big repos / large scans) → `TIMEOUT`.

## Repo docs

- `AGENTS_README.md` — detailed agent behaviors and examples.
- `CHATSYSTEM_SETUP.md` — quick setup; `ChatSystem/README.md` — subsystem reference.
- `.jules/bolt.md` — chronological performance-optimization log; **the authoritative explanation of why
  the caching code looks the way it does.**
