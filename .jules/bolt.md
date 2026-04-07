## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-07 - [Deferred Disk I/O with batch_saves]
**Learning:** Sequential message additions in a chat system (especially with tool calls) cause O(N^2) write amplification as the history file grows. Deferring saves until the end of a logical interaction significantly reduces disk I/O.
**Action:** Implemented a nested `batch_saves` context manager in `ConversationManager` and applied it to high-frequency write sites in `ChatEngine`. Reduced disk writes by ~60% in tool-heavy interactions.
