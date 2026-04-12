## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-05 - [Batching disk I/O for conversation history]
**Learning:** Identified a "write amplification" anti-pattern where every message addition triggered a synchronous disk write. During tool calls, this resulted in 3-5+ redundant writes per turn.
**Action:** Implemented a `batch_saves` context manager in `ConversationManager` using a reentrant counter. Wrapped `ChatEngine._handle_tool_calls` in this context to group tool-related message additions. This reduces disk I/O operations by ~60-80% for tool-heavy turns.
