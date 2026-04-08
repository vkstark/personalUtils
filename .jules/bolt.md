## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-10 - [Batching disk I/O for conversation history]
**Learning:** Found that the "auto-save after every message" pattern created O(N) disk writes for every interaction, which became particularly expensive during tool-intensive turns (assistant message + multiple tool results + final assistant response). Also learned that wrapping generator returns in context managers is ineffective as the context exits before the generator is consumed.
**Action:** Implemented a nested  context manager in `ConversationManager`. Applied a "Durability Pattern" in `ChatEngine._handle_tool_calls` where the batch is exited BEFORE the final LLM call to ensure tool results are persisted even if the last network call fails.

## 2026-04-10 - [Batching disk I/O for conversation history]
**Learning:** Found that the "auto-save after every message" pattern created O(N) disk writes for every interaction, which became particularly expensive during tool-intensive turns (assistant message + multiple tool results + final assistant response). Also learned that wrapping generator returns in context managers is ineffective as the context exits before the generator is consumed.
**Action:** Implemented a nested `batch_saves` context manager in `ConversationManager`. Applied a "Durability Pattern" in `ChatEngine._handle_tool_calls` where the batch is exited BEFORE the final LLM call to ensure tool results are persisted even if the last network call fails.
