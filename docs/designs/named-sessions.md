# Named Conversation Sessions

## Problem & goals

The ChatSystem CLI persists every conversation to a single shared file
(`~/.chatsystem_history.json`). Starting a new topic means either clearing the old
conversation or letting unrelated turns pile into one ever-growing history. There is no
way to keep separate conversations or return to an earlier one.

Goal: named sessions the user can create, switch between, list, and delete from inside
the CLI — like browser tabs for conversations — with zero behavior change for anyone who
never touches the feature.

## Proposed approach

Sessions are **history-file paths, nothing more**. Each named session is a JSON file at
`~/.chatsystem_sessions/<name>.json`, written by the existing `ConversationManager`
persistence (which already guarantees a `0700` parent directory and `0600` files). The
cache-critical internals of `conversation.py` are not touched.

- A new module `ChatSystem/core/sessions.py` holds pure helpers:
  - `session_path(name)` — validates the name against `^[A-Za-z0-9_-]{1,64}$` (rejecting
    path traversal and the reserved name `default`) and returns the file path.
  - `list_sessions()` — sorted stems of `*.json` in the sessions directory (empty list if
    the directory doesn't exist).
  - `delete_session(name)` — removes the file; raises `FileNotFoundError` if absent.

  Functions read the module-level `SESSIONS_DIR` at call time so tests can point it at a
  temp directory.
- `ChatEngine.__init__` gains an optional `history_file` parameter that overrides
  `settings.history_file` when building its default `ConversationManager`. Init-time
  only; no hot-path change.
- **Prerequisite fix — init clobbered existing history.** `ConversationManager.__init__`
  added the seed system prompt via `add_message` (which auto-saves with `O_TRUNC`)
  *before* loading the existing file, so every construction on an existing history
  truncated it to just the system prompt — and on a fresh file, the immediate
  save-then-load duplicated the prompt. Present since the original ChatSystem commit;
  fatal for sessions (switching back would wipe them). Fixed by wrapping init seeding +
  loading in the existing reentrant `batch_saves()` (no disk write until after the load)
  and skipping the default prompt when history exists, since the loaded history already
  carries its system message. A guard re-seeds the prompt if an existing file has an
  empty message list.
- The CLI tracks `self.session_name` (starts as `default`) and routes **all** engine
  construction — startup, `/agent` switches, and session switches — through one
  `_build_engine()` helper so the active session's history file can never be dropped by
  an agent switch.

### Commands

| Command | Behavior |
| --- | --- |
| `/session` or `/session list` | Show the active session and list all sessions (name, last modified). |
| `/session new <name>` | Create an empty session and switch to it. Errors if it already exists. |
| `/session switch <name>` | Switch to an existing session (or `default`). If missing, offer to create it. |
| `/session delete <name>` | Delete a session file after confirmation. Refuses the active session and `default`. |

### Semantics

- The reserved name `default` maps to the legacy `~/.chatsystem_history.json`. Users who
  never run `/session` see byte-identical behavior; no migration.
- Switching sessions rebuilds the engine the same way `/agent` already does (fresh
  `ChatEngine`, tools re-registered, current agent persona re-applied via
  `AgentManager.set_current_agent`). Auto-save means the outgoing session is already on
  disk; nothing to flush.
- Session names keep their case as typed; validation is strict enough that no name can
  escape the sessions directory.

## Files/components affected

- `ChatSystem/core/sessions.py` — new (~50 lines).
- `ChatSystem/core/conversation.py` — init-time seed/load reordering (the clobber fix);
  no cache or hot-path changes.
- `ChatSystem/core/chat_engine.py` — one optional `history_file` constructor parameter.
- `ChatSystem/interface/cli.py` — `/session` command family, `_build_engine()` helper
  (also adopted by `switch_agent`), help/welcome text.
- `tests/chatsystem/test_sessions.py` — new hermetic suite (no API calls).

## Tradeoffs & alternatives

- **SessionManager class owning the conversation lifecycle (rejected):** cleaner OO
  story, but duplicates lifecycle logic the CLI already has and adds an abstraction with
  a single caller.
- **All sessions inside one JSON file (rejected):** requires a history-format change in
  cache-sensitive `conversation.py` plus migration of the existing file — most invasive,
  least benefit.
- **No rename command:** trivially added later if wanted; omitted now (YAGNI).

## Open questions

- Persona re-injection on engine rebuild can duplicate system messages in a reloaded
  history. This is pre-existing behavior (`/agent` has it today), tracked separately as
  the PR #108 follow-up, and deliberately out of scope here.
