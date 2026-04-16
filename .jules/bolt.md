## 2026-04-04 - [Optimize token counting and fix context trimming]
**Learning:** Found a critical O(N^2) performance bottleneck in the `ConversationManager.trim_context` method where `count_tokens()` was called in a loop. Also identified a logic bug where it would over-trim because it was counting the pre-trimmed messages in each iteration.
**Action:** Implemented per-message token caching using Pydantic's `PrivateAttr` and maintained a running `_total_tokens` count in `ConversationManager`. This reduced complexity from O(N^2) to O(N) and made common `count_tokens()` calls O(1).

## 2026-04-05 - [Batching disk I/O for conversation history]
**Learning:** Identified a "write amplification" anti-pattern where every message addition triggered a synchronous disk write. During tool calls, this resulted in 3-5+ redundant writes per turn.
**Action:** Implemented a `batch_saves` context manager in `ConversationManager` using a reentrant counter. Wrapped `ChatEngine._handle_tool_calls` in this context to group tool-related message additions. This reduces disk I/O operations by ~60-80% for tool-heavy turns.

## 2026-04-06 - [Persisting token counts for instant history loads]
**Learning:** Even with O(1) token count lookups, loading a large history file still required re-calculating tokens for every message using `tiktoken` upon startup. This created a linear startup delay that grew with history size.
**Action:** Migrated the `tokens` cache from a `PrivateAttr` to a public field in the `Message` model. This allows token counts to be saved to disk and reused on subsequent loads. Measured a 99.8% reduction in startup load time for a 2,000-message history (from ~0.6s to <0.001s).
## 2026-04-14 - [Parallel tool execution in ChatEngine]
**Learning:** Found that sequential tool execution was a major latency bottleneck during multi-tool calls. While the LLM can request parallel tools, the engine was executing them one-by-one.
**Action:** Implemented a `ThreadPoolExecutor` in `ChatEngine._handle_tool_calls` to execute I/O bound tools concurrently. Refactored the logic into `_execute_single_tool_call` to avoid code duplication and ensure thread-safe, ordered state updates (metrics and conversation history) by processing results sequentially in the main thread. Measured a ~3x speedup for 3 parallel 1s tasks.

## 2026-04-15 - [Caching message serialization results]
**Learning:** Found that Pydantic's `model_dump()` and custom `to_openai_format()` were significant CPU bottlenecks when processing large conversation histories (e.g., 1000+ messages), as they were called repeatedly during history saves and API request preparation. Pydantic's `__setattr__` has a measurable overhead, especially when overridden.
**Action:** Implemented per-message caching for both `model_dump()` and `to_openai_format()` using `PrivateAttr`. Optimized cache invalidation in `__setattr__` by using `self.__dict__` and early checks to minimize overhead. Measured a ~80% reduction in serialization time for a 1000-message history.
