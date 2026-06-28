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

## 2026-04-16 - [Caching OpenAI formatted messages in ConversationManager]
**Learning:** Identified that `ConversationManager.get_messages()` was an O(N) operation that re-serialized every message in the history on every turn. In large conversations (2000+ messages), this consumed ~1.3ms per call, which adds up in agentic loops or multi-turn reasoning.
**Action:** Implemented a high-level list cache `_cached_openai_messages` in `ConversationManager`. Added `_invalidate_cache()` to all methods that modify the message history. Measured a ~150x speedup for `get_messages()` calls (from 1.3ms to 0.008ms).

## 2026-04-18 - [Caching YAML configuration in Settings]
**Learning:** `Settings.load_yaml_config()` was being called multiple times per turn (by `get_model_for_task`, `get_enabled_tools`, and `get_agent_config`), causing redundant disk I/O and YAML parsing. This added ~0.44ms of overhead to many core operations.
**Action:** Implemented instance-level caching using `PrivateAttr`. This reduced latency to ~0.004ms per call (a ~100x improvement).

## 2026-06-01 - [Optimized ConversationManager serialization and caching]
**Learning:** Identified that `get_messages()` and `_save_history()` were O(N) operations due to full re-serialization of the conversation history on every turn. In large conversations, this caused significant latency.
**Action:** Implemented incremental caching for both OpenAI-formatted and JSON-dumped messages. Optimized `_save_history` to use the pre-dumped cache and compact JSON serialization. Reduced `add_message` (inc. save) latency by ~38% and `get_messages` latency by ~80% for 2000 messages.
## 2026-06-03 - [Optimize streaming and model identification in ChatEngine]
**Learning:** Found O(N^2) string concatenation patterns in streaming response generation and tool call argument building. Also identified duplicated, inefficient reasoning model identification logic using `any()` with lists.
**Action:** Replaced `+=` string concatenation with list accumulation and `"".join()` in `_chat_generator` and `_chat_stream`. Centralized reasoning model check using a `REASONING_MODELS` tuple and `str.startswith(tuple)`, which is optimized in C. Measured ~98% improvement in argument building for large payloads.

## 2026-06-05 - [Optimize get_messages(include_system=False) and get_summary caching]
**Learning:** `get_messages(include_system=False)` was an O(N) operation due to filtering, taking ~0.26ms for 4k messages. `get_summary()` was also O(N) taking ~0.74ms. Moving `mkdir` out of `_save_history` also reduces filesystem overhead in the hot path.
**Action:** Implemented incremental caching for the no-system message list and lazy caching for conversation summary. Moved history directory creation to `__init__`. Measured ~18x speedup for `get_messages(include_system=False)` and ~460x speedup for `get_summary()`.

## 2026-06-10 - [Optimize history loading with bulk validation]
**Learning:** Pydantic V2's `TypeAdapter.validate_python()` is significantly faster than manual loops for bulk initialization. Reusing raw JSON data for caches when loading can also bypass expensive `model_dump()` calls.
**Action:** Implemented bulk validation in `ConversationManager._load_history` and optimized cache rebuilding.

## 2026-06-15 - [Optimize get_summary with incremental role tracking]
**Learning:** `get_summary` was an O(N) operation due to manual role counting, which added overhead to every stats retrieval call.
**Action:** Implemented `_role_counts` using `collections.defaultdict(int)` to track roles incrementally in `add_message` and `trim_context`. Optimized `_load_history` to rebuild all state in a single pass. Measured ~22x speedup for 4,000 messages.

## 2026-06-20 - [Optimize ToolMetrics with lazy caching and deque]
**Learning:** `ToolMetrics.to_dict()` was being called frequently in `ChatEngine.get_stats()`, causing redundant calculations and string formatting. Also, manual list slicing for `error_history` was O(N) for each update.
**Action:** Implemented lazy caching for `to_dict()` and replaced the list-based `error_history` with `collections.deque(maxlen=10)`. Measured a ~32x speedup for `get_stats()` (from ~0.16ms to ~0.005ms). Always return a shallow copy (`.copy()`) when caching dictionaries to prevent external mutation of the internal state.

## 2026-06-25 - [Optimize ToolExecutionResult serialization]
**Learning:** Found that `ToolExecutionResult.get_output()` was using pretty-printed JSON (`indent=2`) and a local import of `json`. Pretty-printing increases token usage by ~35% for structured tool outputs.
**Action:** Moved `import json` to module level and switched to compact JSON serialization (`separators=(',', ':')`). This reduces LLM token costs and improves serialization speed in the tool execution hot path.
