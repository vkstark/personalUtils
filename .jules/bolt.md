## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-05 - [Optimize disk I/O with batch_saves context manager]
**Learning:** Sequential message additions (e.g., during tool calls) caused redundant disk writes (O(N) writes for N messages), impacting performance and disk longevity.
**Action:** Implemented a nested  context manager in  using a counter and a deferred save flag. Used it in  to group tool result writes, reducing writes from 3+ down to 2 for a typical tool call cycle.

## 2026-04-05 - [Optimize disk I/O with batch_saves context manager]
**Learning:** Sequential message additions (e.g., during tool calls) caused redundant disk writes (O(N) writes for N messages), impacting performance and disk longevity.
**Action:** Implemented a nested `batch_saves` context manager in `ConversationManager` using a counter and a deferred save flag. Used it in `ChatEngine._handle_tool_calls` to group tool result writes, reducing writes from 3+ down to 2 for a typical tool call cycle.
