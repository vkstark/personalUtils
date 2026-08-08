# Health-Review Remediation

## Problem & goals

The 2026-08-04 codebase review (three independent read-only review passes plus empirical
reproduction) found that while the test suite is green (320 passed), several verified defects
ship anyway: two of the twelve LLM-callable tools fail on every invocation, the task executor
can report success after executing nothing, agent personas accumulate permanently across
`/agent` switches, and the context-summarization subsystem can reach a dead fixed point.
Goal: fix the verified defects in five scoped work items, with tests that would have caught
each one, without disturbing the load-bearing caching/security invariants documented in
`.jules/bolt.md`.

Non-goals: logging overhaul, dead-code removal beyond the lint-flagged write-only variables,
`_needs_planning` heuristic redesign, and the other deferred findings (bundled in "Deferred
follow-ups" below).

---

## Item 0 — Preparatory lint cleanup

The 14 pre-existing ruff findings (2×F401 unused imports, 4×F541 placeholder-less f-strings,
6×F841 write-only variables in tests, `tools/FileDiff/file_diff.py:248`'s dead
`in_added = True`, `tools/EnvManager/env_manager.py:17`'s unused `defaultdict`) land as a
separate preparatory commit *before* everything else, so the "ruff clean" gate holds from the
first real commit onward. Mechanical: `ruff check --fix` for the auto-fixable 7, manual
deletion for the F841s (each verified write-only first). No behavior change intended; full
suite must stay green.

---

## Item 1 — Make the contract tests falsifiable

**Problem.** `tests/test_tool_contracts.py` asserts `result.status in [ToolStatus.SUCCESS,
ToolStatus.ERROR]` in eight places (lines 123, 135, 169, 197, 225, 243, 258, 306) and type-only
checks at :81. Two tools that exit 2 on *every* invocation (`manage_code_snippets` at :160,
`optimize_python_imports` at :246) pass today.

**Approach.**
- Pin each of the eight assertions to the status its fixture should actually produce —
  `SUCCESS` for the happy-path fixtures, `ERROR` for the invalid-URL fixture at :126 (the
  SSRF/parse layer rejects it; implementation verifies the concrete status before pinning).
  The `@pytest.mark.network` test at :113 keeps its permissive assertion deliberately — it is
  allowed to fail on connectivity and is excluded from the offline gate anyway.
- Where cheap, add one content-bearing assertion per fixture (a stdout substring or parsed
  `structured_payload` key) so the test proves the tool did something.
- In the parametrized `test_all_tools_return_execution_result`, assert
  `"unrecognized arguments" not in (result.stderr or "")` directly, regardless of status — a
  guard against the argparse-translation failure class for every registered tool.
- Add one registration-drift test. Note the keying: `TOOL_DEFINITIONS` is keyed by CamelCase
  utility name with the OpenAI function name nested at `definition["name"]`
  (tool_adapter.py:23), while the executor maps *function names* (tool_executor.py:119). The
  test asserts: every `definition["name"]` has a `function_to_util` entry; every mapped script
  path exists when resolved against `executor.utils_dir` (tool_executor.py:107, matching
  executor behavior); every `config.yaml` `tools.enabled` entry (config.yaml:13) is a known
  outer CamelCase key.

**Ordering note.** Tightened tests go red against current main for the Item-2 defects; Items 1
and 2 therefore land in the same change, tests written first (red), fixes second (green).

**Files.** `tests/test_tool_contracts.py`, new `tests/test_tool_registration.py` (or a class in
the contracts file — implementer's choice, keep it under `tests/`).

**Test plan.** The item *is* tests. Success: the new assertions fail on unfixed main and pass
after Item 2.

**Tradeoffs.** Exact-status assertions are more brittle against intentional convention changes
(e.g. Item 2 changes what exit 1 means for two tools) — acceptable: that brittleness is the
point of a contract test.

---

## Item 2 — Tool-translation fix batch (ChatSystem/tools/tool_executor.py + schema)

Eight verified defects, all in the hand-maintained translation layer. All were reproduced
empirically before being listed here.

**2a. `--no-color` ordering breaks two tools on 100% of calls (HIGH).**
`optimize_python_imports` (tool_executor.py:409-419) and `manage_code_snippets` (:314-336)
append `--no-color` after the subcommand, but both tools register the flag on the *top-level*
parser (import_optimizer.py:205, snippet_manager.py:358-359), so argparse rejects it → exit 2
every call. Fix: insert `--no-color` immediately after the script path, before the subcommand —
exactly the rule the EnvManager branch already documents and follows (tool_executor.py:361-364).
Mirror that comment at both sites.

**2b. `compare_files` advertises `side-by-side`; FileDiff accepts `side_by_side` (HIGH).**
The schema property is `format` with enum `["unified", "context", "side-by-side"]`
(tool_adapter.py:226-231); the executor translates it to FileDiff's `--mode` flag at
tool_executor.py:382-383; the CLI's choices use underscores (file_diff.py:495). Fix at the
translation site: `cmd.extend(["--mode", args["format"].replace("-", "_")])`. Schema stays
hyphenated (reads naturally to the model); the CLI is untouched.

**2c. `find_duplicate_files` loses its advertised `recursive: true` default (MED).**
Schema declares `default: true` (tool_adapter.py:97) but the executor appends `--recursive`
only when the key is present and truthy (:306). Models omit defaulted fields, so the normal
case scans non-recursively. Fix: `if args.get("recursive", True): cmd.append("--recursive")`,
matching how the `no_color` defaults are already read (:406, :418, :435).

**2d. Exit 1 reported as ERROR for two tools whose exit 1 means success (MED).**
`extract_todos` exits 1 when TODOs are found; `compare_files` exits 1 when files differ
(file_diff.py:580) — both deliberate CI conventions, both mapped to `ToolStatus.ERROR` by the
generic exit-code check (tool_executor.py:499-507). The model is told the tool failed on its
most common successful outcome. Fix: a small per-function success-exit-code table in the
executor, `{"extract_todos": {0, 1}, "compare_files": {0, 1}}`, defaulting to `{0}`. The
utilities' own CLI conventions are untouched.

**2e. `manage_code_snippets` show/delete pass a title where the CLI wants an ID (MED).**
tool_executor.py:325-326 sends `args.get("title", "")` as the positional, but both CLI
positionals are exact snippet IDs (snippet_manager.py:383-390). Fix: add an `id` property to
the `manage_code_snippets` schema ("Snippet ID (for show/delete); IDs are returned by
list/search"), narrow `title`'s description to add/search, and have the executor pass
`args.get("id", "")` for show/delete. No title→ID lookup magic — the model lists first, then
addresses by ID, which matches how the CLI is actually used.

**2f. `delete` blocks on a hidden `input()` prompt for up to 60 s (MED).**
snippet_manager.py:470-473 prompts unless `-y/--yes` is passed; the executor never passes it
and the subprocess inherits the CLI's stdin. The prompt is an intentional destructive-action
confirmation, and no model-suppliable schema field can prove user consent (the model could
self-authorize `confirm=true` on its first call). Fix: `delete` becomes manual-only — the
executor returns `ToolStatus.MANUAL_REQUIRED` before spawning any subprocess, with a payload
naming the snippet ID and the exact CLI command to run
(`python tools/SnippetManager/snippet_manager.py delete <id>`), exactly the existing
BulkRename convention (tool_executor.py:338-345). The hang is eliminated (no subprocess), the
destructive action stays human-gated, and the schema's `action` description is updated so the
model sets user expectations correctly. add/search/list/show remain fully functional.

**2g. `compare_with` missing from `_PATH_ARG_KEYS` (LOW).**
It is a path-typed arg (tool_adapter.py:202) not covered by sandbox resolution
(tool_executor.py:135). Currently unreachable (the compare action returns `MANUAL_REQUIRED`
first) but the guard must not depend on that. Fix: add the key to `_PATH_ARG_KEYS`.

**2h. CodeWhisper: one broken symlink aborts the whole directory scan (MED/HIGH).**
code_whisper.py:578 walks with `os.walk`, which yields dangling symlinks in `files`;
`analyze_file`'s initial read catches only `UnicodeDecodeError` (:425), so `FileNotFoundError`
/ `PermissionError` propagate to the top-level handler and the process exits 1 with zero
results. Fix, mirroring the DuplicateFinder patch (duplicate_finder.py:124-127): skip
non-`is_file()` entries inside the walk loop, and add a *separate* `except OSError` on the
initial utf-8 read that degrades to a per-file error `FileAnalysis` (same shape as the
existing unreadable-file path). The existing latin-1 fallback for `UnicodeDecodeError`
(:426-429) is preserved untouched — the new handler must not swallow the decode-error path.

**Files.** `ChatSystem/tools/tool_executor.py`, `ChatSystem/tools/tool_adapter.py`,
`tools/CodeWhisper/code_whisper.py`.

**Test plan (written first, red on main).**
- Executor-level tests calling `ToolExecutor().execute(...)` for: `optimize_python_imports`
  happy path (SUCCESS, no "unrecognized arguments"), `manage_code_snippets` list (SUCCESS),
  `compare_files` with `format="side-by-side"` (SUCCESS), `find_duplicate_files` with
  `recursive` omitted finding a nested duplicate, `extract_todos` on a file containing a TODO
  (SUCCESS), `compare_files` on differing files (SUCCESS), `manage_code_snippets` delete
  returning MANUAL_REQUIRED with the CLI command in the payload and no subprocess spawned.
- A CodeWhisper directory-scan test with one valid `.py` and one dangling symlink asserting the
  valid file is analyzed (also closes the CodeWhisper zero-coverage gap for this path).

**Tradeoffs / alternatives.**
- 2b alternative — change the schema enum to underscores: rejected; models already emitted the
  hyphenated form and the executor is the designated translation layer.
- 2d alternative — change the tools to exit 0: rejected; their exit conventions are documented
  CLI behavior users may script against. The executor is where LLM-facing semantics live.
- 2e alternative — resolve title→ID via a `list` pre-call inside the executor: rejected as
  hidden multi-step magic in a layer that should stay a dumb translator.
- 2f alternative — silently append `-y`: rejected; it would let the model delete data without
  any confirmation step. A `confirm: true` schema field was also rejected: it is
  model-suppliable, so it proves nothing about user consent. Manual-only matches BulkRename.

---

## Item 3 — Empty plan must not report success (agents/task_executor)

**Problem.** `TaskPlanner.is_plan_complete` (planner.py:362) is `all(...)` over steps, which is
vacuously True for zero steps; `_execute_multi_step`'s while-loop (executor.py:244) never runs
and lines 271-273 print "✅ All steps completed successfully!" having executed nothing. Three
reproduced routes to a zero-step plan: refusal prose, valid `{"steps": []}` JSON, and a valid
plan embedded in prose containing *multiple brace-bearing sections*, which makes the greedy
`re.search(r'\{.*\}', ..., re.DOTALL)` at planner.py:176-178 span non-JSON text.

**Approach.** Guard at the `create_plan` boundary — degenerate LLM output is the planner's
problem, not the executor's:
1. In `create_plan`, if parsing produces zero steps, fall back to a single-step plan whose one
   step uses the *original goal verbatim* as its `description` (so the step genuinely executes
   the task — a tool-less step sends its description through the engine at executor.py:318).
   Record `fallback_reason="empty_or_unparseable_plan"` in the plan metadata so the trace
   shows the degradation fired.
2. Harden extraction minimally: before the greedy regex, try fenced ```json blocks; then the
   greedy regex + `json.loads` as today. No parser rewrite.
3. Defense in depth: `is_plan_complete` returns False for empty plans. Nothing should reach it
   with one post-fix, but a vacuous-truth success check is wrong on its own terms.

**Files.** `agents/task_executor/planner.py` (create_plan, extraction, is_plan_complete);
no executor.py changes expected.

**Test plan (first, red on main).** Unit tests in `tests/agents/` feeding the planner the
degenerate responses via the stubbed engine — refusal prose, `{"steps": []}`, and a fixture
with a fenced JSON plan surrounded by multiple brace-bearing prose sections — asserting: plan
has ≥1 step, `metadata["fallback_reason"] == "empty_or_unparseable_plan"` where the fallback
fired, the fenced-block case recovers the actual steps (no fallback), and
`is_plan_complete(empty_plan)` is False.

**Tradeoffs.** Raising instead of degrading was rejected: `execute_task` has no caller-level
retry, so a raise turns a recoverable degenerate output into a user-facing failure; single-step
fallback preserves the agent's contract ("do the task") and is already the behavior for
`use_planning=False`.

---

## Item 4 — Evict foreign personas on agent switch

**Problem.** The CLI builds a fresh `ConversationManager` per `/agent` switch to prevent
persona bleed, but it reloads the same history file (cli.py:505), which already holds the
previous persona as a `role="system"` message; `set_current_agent()` then injects another
persona (:514), and nothing ever removes system messages, so personas accumulate permanently
(reproduced independently by two reviewers). Cycling all four agents pins ~9.5k tokens of
mutually contradictory instructions on every later request. The #114 idempotency fix
(`ensure_system_message`, conversation.py:314) prevents same-persona duplicates only.

**Constraint discovered in review.** Personas are not statically recognizable today: the task
executor's persisted persona is dynamically formatted with the live tool list
(executor.py:88-96 `get_formatted_persona()` substitutes `{tools}`), so a registry of raw
`SYSTEM_PERSONA` constants cannot exact-match persisted content, and no marker prefix exists
anywhere in the repo.

**Approach — stable marker + eviction, with legacy matchers.**
1. **Marker.** Every persona system message gains a first line
   `[Agent Persona: <agent_type.value>]`. Single source of truth: a small helper (e.g.
   `persona_message(agent_key, text)` in `agents/`) used by *both* injection paths — each
   agent's `__init__` `ensure_system_message(...)` call and AgentManager's re-injection at
   agent_manager.py:140-143 — so the two paths keep producing byte-identical strings and #114
   idempotency continues to hold.
2. **Eviction mutator.** `ConversationManager.remove_system_messages_by_prefix(prefixes) ->
   int`: removes system messages whose content starts with any given prefix. Implementation
   rebuilds the list and calls the existing `_reset_state()` (conversation.py:203) followed by
   one save — the same full-rebuild path `summarize_conversation` already uses — rather than
   hand-maintaining the four caches / `_total_tokens` / `_role_counts` incrementally.
3. **Call site — centralized in the injection path.** Eviction runs inside
   `AgentManager.set_current_agent()` (agent_manager.py:136-143), immediately *before* the
   `ensure_system_message(...)` injection, against the target engine's conversation. This
   covers every activation path with one call: CLI construction (cli.py:64), session
   activation (:374), and `/agent` switch (:505) — including the startup-with-polluted-
   default-history case that per-call-site eviction would miss. The agents' own
   `__init__` injection can leave a foreign persona in place for at most the interval until
   `set_current_agent` runs, and every CLI path calls it before any user turn.
4. **Legacy healing.** Existing history files hold unmarked personas. Add a legacy-matcher
   tuple: the stable opening text of each of the four personas (for the executor, the portion
   of `SYSTEM_PERSONA` *before* the `{tools}` placeholder). The eviction call takes
   `prefixes = ("[Agent Persona:",) + LEGACY_PERSONA_PREFIXES`, so polluted histories
   self-heal on next activation.

**Files.** `ChatSystem/core/conversation.py` (one new mutator), `agents/agent_manager.py`
(marker helper + injection), the four agent `__init__`s (use the helper),
`ChatSystem/interface/cli.py` (eviction calls).

**Test plan (first, red on main).** Extend `tests/agents/` switching tests: build manager A on
a temp history, switch to B (same file), assert exactly one persona system message remains and
it is B's (marker present); assert a pre-polluted history file (unmarked A+B personas written
directly, exercising the legacy matchers) is healed to the active persona on activation;
invariant check after eviction — `_total_tokens` equals a fresh recount, `_role_counts`
matches the message list, `get_messages()` reflects the removal (caches invalidated), and
persisted messages retain their `tokens` fields.

**Tradeoffs.** A model-visible marker line is added to each persona (few tokens, self-
describing). The alternative — never persisting personas — touches `_save_history` and the
incremental dump-cache path (the most invariant-dense code in the repo per `.jules/bolt.md`)
and does nothing for already-polluted histories; rejected.

---

## Item 5 — Core robustness batch (conversation.py, cli.py)

**5a. Atomic history writes (MED).** `_save_history` opens the live file with `O_TRUNC`
(conversation.py:501-513): a crash or full disk mid-write destroys history, the failure is a
swallowed one-line warning, and the next startup's auto-save truncates what's left. Fix:
`tempfile.mkstemp(dir=<history dir>, prefix=...)` — unique name (no fixed-path/symlink race),
0600 by default — write, flush + `os.fsync`, close, then `os.replace()` onto the target
(atomic on POSIX). On any pre-replace failure: close and unlink the temp file, leave the live
file untouched. This also removes the fd-leak window the old `os.open`/`os.fdopen` pair had.

**5b. Summarization fixed point + zero-compression (HIGH/MED, pre-existing).**
Two coupled defects in `summarize_conversation` (conversation.py:660-720):
  1. Each call appends a new summary `system` message (:706); system messages are always
     retained (:679-680), so summaries accumulate until `len(other_messages) < 5` bails
     forever while `auto_summarize_if_needed` still reports success (:791) — a dead fixed
     point (reproduced: converged at 533 tokens against a 400 window, reporting success each
     turn).
  2. `_keep_count_without_orphan_tools` runs *after* the `len(other_messages) - 1` ceiling
     (:695) and can walk `keep_recent_count` back up to `len(other_messages)`, producing
     "Summarized 0 messages" and a net token *increase* (reproduced: 64 → 107 tokens).
Fix:
  - **Rolling summary.** Identify prior summary messages by their `[Conversation Summary -`
    prefix (generated in exactly one place; format unchanged). On summarize, pull prior
    summary messages out of `system_messages`, prepend their content to the material being
    compressed, and emit a single fresh summary message — at most one summary message exists
    after any summarize call. Real system prompts/personas are still never touched.
  - **Commit-only-if-smaller.** Before mutating, compute the candidate message list's token
    total; if it is not strictly smaller than the current total (LLM/structural output can be
    larger than what it replaces), do not mutate and report "not summarized". Additionally
    bound the merged summary text so the single summary message cannot grow without limit:
    the current truncation bounds are inline slice literals (`[:200]` in
    `_structural_summarize`, `[:500]` in `_llm_summarize`), so implementation extracts one
    named module-level constant for the merged-summary cap and uses it in both places.
  - **Honest return.** `summarize_conversation` returns `Optional[str]` — `None` means
    nothing was compressed (too short, empty compression window after the orphan-tools walk,
    or candidate not smaller). `maybe_auto_summarize` / `auto_summarize_if_needed` propagate
    False in that case instead of unconditional True; the CLI `/summarize` prints a "nothing
    to summarize" message on `None`. No caller infers success from magic strings.
**5c. `get_summary` cache-miss path returns the internal dict bare** (conversation.py:629;
the hit path at :619-620 copies). One-word fix: `.copy()`. Matches the `.jules/bolt.md`
2026-06-20 rule.
**5d. mypy narrowing in cli.py (3 errors, introduced by #113).** `:379-380` — explicit
`if ... is None` guard (not `assert`) before `set_current_agent`; None is unreachable in
practice (set in `__init__`), the guard makes it explicit at a runtime boundary. `:466`/`:478`
— narrow `path` with an explicit `if path is None: return` mirroring the existing guard style
at :483, instead of relying on branch reachability mypy can't see. Success:
`python -m mypy ChatSystem agents` → 0 errors.

**Files.** `ChatSystem/core/conversation.py`, `ChatSystem/interface/cli.py`.

**Test plan (first where meaningful).**
- 5a: happy path → same content, mode 0600, no stray temp files; failure path (monkeypatch
  `json.dump` to raise) → original file intact and parseable, temp file cleaned up.
- 5b: repeated auto-summarize over a small window converges to ≤1 summary message with
  monotonically non-increasing totals; the zero-compression scenario returns None, adds no
  message, and `auto_summarize_if_needed` reports False; a candidate-not-smaller scenario
  (summary larger than compressed material) leaves the conversation unmutated; invariant
  check after a committed summarize — `_total_tokens` equals fresh recount, `_role_counts`
  matches, caches invalidated; existing summarization tests keep passing.
- 5c: mutate the returned dict on the miss path; second call unaffected.
- 5d is gate-verified (mypy 0 errors) rather than unit-tested.

**Tradeoffs.** Rolling-summary by content-prefix couples identification to the message format —
same accepted tradeoff as Item 4, same mitigation (the prefix is generated in exactly one
place). Adding a persisted `is_summary` field to `Message` was rejected: it changes the
serialized history schema and the invariant-dense dump-cache path for a problem prefix
matching solves locally. Changing `summarize_conversation`'s return type is safe: its only
callers are the two auto-summarize wrappers and the CLI command, all updated in this item.

---

## Delivery & ordering

Single branch, five commits in dependency order (tests-first within each):
1. Item 0 — lint prep (makes the ruff gate clean from here on).
2. Items 1 + 2 — contract/regression tests red → translation fixes green.
3. Item 3 — planner guard (independent).
4. Item 4 — persona marker + eviction (touches conversation.py mutators before 5b).
5. Item 5 — core robustness.
Gates after every commit: `python -m pytest -q -m "not network"`, `ruff check ChatSystem
agents tools tests` (add `--no-cache` if running in a sandbox that blocks `.ruff_cache`), and
`python -m mypy ChatSystem agents` (verified working in this environment; mypy is invoked via
`python -m` because the console-script shebang is broken on this machine).
Final gate re-runs the original empirical reproductions: executor calls for 2a/2c/2d, 2b via
`format="side-by-side"`, snippet delete returning MANUAL_REQUIRED without a subprocess, the
symlink directory for 2h, the three degenerate planner outputs, and persona-switch history
inspection
(exactly one persona after A→B→A cycling, polluted legacy file healed).
No commits or pushes without explicit per-turn approval.

## Deferred follow-ups (bundled, not in scope)

- Planner runs with tools attached + planning prompt pollutes history (needs a per-call
  `tools=None` opt-out in `ChatEngine.chat` — an engine API change deserving its own design).
- `/summarize` LLM path doubles input tokens (same engine-API dependency).
- Zero logging despite configured logger; broad `except: print` pattern.
- `_needs_planning` keyword heuristic; `max_iterations`/`enable_planning` config no-ops for
  3 of 4 agents; `parse_agent_type` display-name matching; dead methods across agents.
- DataConvert has no overwrite path; config `tools:` absent-key silently disables all tools.
- Non-blocking streamed tool-call index robustness (chat_engine.py:390).

## Open questions

1. Item 2d: is exit-1-means-success acceptable to encode in the executor table, or should the
   two utilities gain a `--exit-zero` style flag instead? (Table recommended; flags change
   user-facing CLI behavior.)
2. Item 4: the marker is now designed in from the start; the remaining question is legacy-
   matcher coverage — implementation must verify each legacy prefix actually matches the
   persisted form (especially the executor's tool-list-formatted persona) against a real
   polluted history before relying on it.
3. (Resolved) Item 5b truncation bounds: the existing bounds are inline slice literals, so
   implementation extracts one named module-level constant for the merged-summary cap.
