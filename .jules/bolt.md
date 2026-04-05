## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-05 - [Batch conversation history saves to reduce disk I/O]
**Learning:** Sequential message additions in `ConversationManager` (common in tool-intensive loops) were causing $O(N^2)$ disk I/O because the entire history was rewritten every time. This made tool-intensive interactions significantly slower as history grew.
**Action:** Implemented a `batch_saves` context manager in `ConversationManager` to defer disk writes until the end of a logical block. Applied this to `ChatEngine._handle_tool_calls`, achieving a ~22x performance improvement in message processing for tool-intensive loops.
