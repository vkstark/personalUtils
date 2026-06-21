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
- `tests/agents/` — planner (incl. step normalization), reasoner, executor routing, agent manager/personas/switching
- `tests/chatsystem/` — config accessors, conversation/summarization, I/O batching, ToolMetrics, security

The agent/ChatSystem suites are hermetic (fake API key + stubbed OpenAI client, `auto_save=False`
conversations); the tool suites shell out to the real utility subprocesses.

```bash
pytest                                          # whole suite
pytest -m "not network"                         # skip the few live-httpbin tests (offline/fast)
pytest tests/agents/                            # one subdir
pytest tests/test_tool_contracts.py::TestToolContracts::test_unknown_function_returns_execution_result
pytest -m "not slow"                            # markers: slow / integration / unit / network (strict-markers is on)
pytest --cov=. --cov-report=html                # coverage (pytest-cov installed; off by default)
```

Put new tests under the matching `tests/` subdir, not at the repo root (a bare root `test_*.py` is
outside `testpaths` and won't be collected). `test_case_sensitive_name_matching` auto-skips on a
case-insensitive filesystem (the macOS default).

### Lint / typecheck

`ruff` and `mypy` are dev deps (run ad hoc — no enforced step / no config file yet):

```bash
ruff check ChatSystem agents      # F-checks are clean; keep them that way
mypy ChatSystem agents            # optional
```

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
`PrivateAttr` (`get_settings()` is itself `lru_cache`d). Config is read through typed accessors that
merge YAML over defaults and **are actually wired to runtime**:
- `get_conversation_config()` → `ConversationManager` (context window `max_tokens_default`, auto-save,
  auto-summarize threshold/ratio). `ChatEngine` builds the conversation from this and calls
  `conversation.maybe_auto_summarize()` after each turn.
- `get_agent_config_for(name)` → per-agent `model` + `enable_planning` + `max_iterations` passed into
  each agent constructor (so `task_executor` now honors its configured model).
- `get_cli_config()` → CLI theme / `show_token_usage`. `Settings.tool_timeout_seconds` /
  `max_tool_call_depth` / `history_file` wire the previously-hardcoded knobs.

Invalid model names are rejected by validation; `gpt-5` and the `o1`/`o3` family are treated as
reasoning-style (no `temperature`, `max_completion_tokens`) via `ChatEngine.REASONING_MODELS`.

### Security model (local, single-user)

`ToolExecutor` accepts `sandbox_root` (path args must resolve inside it — the CLI roots this at the cwd)
and an `allowed_url_hosts` SSRF allow-list (non-http(s) schemes and loopback/link-local/RFC1918
destinations are rejected for the API-tester tool). Conversation history is written `0600` with a `0700`
parent dir. Subprocess timeout is `Settings.tool_timeout_seconds`. Tools still run with `shell=False`.

## Gotchas / footguns

- Tool stdout that isn't valid JSON is silently treated as plain text (`structured_payload=None`);
  validation messages can get swallowed.
- Auto-summarization in the live loop is **structural** (no LLM, no cost/recursion); the explicit
  `/summarize` command uses the LLM. `trim_context()` is still manual-only.
- `_handle_tool_calls` re-raises nothing on a worker-thread failure — it records a per-call error
  rather than re-running the tool (avoids double-running side-effecting tools).

## Repo docs

- `AGENTS_README.md` — detailed agent behaviors and examples.
- `CHATSYSTEM_SETUP.md` — quick setup; `ChatSystem/README.md` — subsystem reference.
- `.jules/bolt.md` — chronological performance-optimization log; **the authoritative explanation of why
  the caching code looks the way it does.**
