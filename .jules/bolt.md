## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-05 - [Reduce redundant disk writes during tool execution]
**Learning:** Found a significant disk I/O performance bottleneck where every call to `add_message` triggered a full history write if `auto_save` was enabled. During multi-tool chat turns, this resulted in 4-6 redundant sequential disk writes.
**Action:** Implemented a `batch_saves` context manager in `ConversationManager` using a nesting counter and a `_needs_save` flag. Applied this in `ChatEngine._handle_tool_calls` to group assistant tool call intent and all tool results into a single write. Ensured the block exits BEFORE the final API call to maintain durability for tool execution results. This reduced disk write operations by 40-60% for typical tool interactions.
