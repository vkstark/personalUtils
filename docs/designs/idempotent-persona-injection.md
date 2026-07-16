# Idempotent Persona Injection

## Problem & goals

Agent personas are injected into the conversation with a bare `add_message("system", …)`
at five sites: `AgentManager.get_agent` (the engine-swap path used by `/agent` and
`/session` switches) and each of the four agent constructors. When the conversation was
reloaded from a history file that already contains the persona — which is now the normal
case with named sessions — every reactivation appends another copy. Session files grow a
duplicate persona per switch, inflating tokens and diluting instructions. This is the
follow-up flagged when PR #108 was closed and deferred during the named-sessions review.

Secondary cleanup from that same review: `ConversationManager` treats a `~/…` history
path literally (`Path(history_file)` without `expanduser()`), creating a literal `~`
directory if `HISTORY_FILE=~/...` is set in `.env`.

## Proposed approach

- New `ConversationManager.ensure_system_message(content)` — adds a system message only
  if an identical one (role + content) isn't already in history. Purely additive; built
  on the existing `add_message`, so all cache/token invariants hold unchanged.
- The five injection sites call `ensure_system_message` instead of `add_message`.
  `AgentExecutor.get_formatted_persona()` substitutes the live tool list, so a changed
  tool set produces different content and is intentionally re-added.
- `ConversationManager.__init__` applies `.expanduser()` to a provided `history_file`;
  the CLI's `display_sessions` default-path mirror does the same.

## Files/components affected

- `ChatSystem/core/conversation.py` — `ensure_system_message` + `expanduser()`.
- `agents/agent_manager.py`, `agents/task_executor/executor.py`,
  `agents/trillionaire_futurist/futurist.py`, `agents/transcript_analyzer/analyzer.py`,
  `agents/framework_teacher/teacher.py` — swap injection call.
- `ChatSystem/interface/cli.py` — one `expanduser()`.
- `tests/chatsystem/test_sessions.py` — regressions: persona count stable across session
  roundtrips, `ensure_system_message` idempotency, `~` expansion.

## Tradeoffs & alternatives

- Inline `if not any(…)` checks at each site (rejected): the same predicate duplicated
  five times; a single helper with five callers is the smaller surface.
- Deduplicating inside `add_message` itself (rejected): would silently change semantics
  for every caller and touch the incremental-cache hot path.

## Open questions

None.
