## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-05 - [Batch history saves to optimize disk I/O]
**Learning:** Sequential `add_message` calls (e.g., in tool execution loops or user-assistant turns) caused O(N^2) write amplification because the entire history was re-serialized and written to disk on every call.
**Action:** Implemented a `batch_saves` context manager in `ConversationManager` using a depth counter. Applied it in `ChatEngine` to group message additions into single atomic disk writes, while ensuring context is closed before final network calls to maintain durability.
