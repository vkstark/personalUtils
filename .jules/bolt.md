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

## 2026-06-25 - [Optimize ToolAdapter with class-level caching]
**Learning:** `ToolAdapter` methods were re-formatting and re-creating dictionary structures for all tool definitions on every call. This was especially wasteful in `get_enabled_tools` which also used linear list filtering.
**Action:** Implemented a private class-level cache `_formatted_cache` and a `_get_formatted_tool` helper. Updated retrieval methods to use the cache and return shallow copies to prevent external mutation. Optimized filtering in `get_enabled_tools` using a `set`. Measured a ~2.8x speedup in tool registration.

## 2026-06-25 - [Optimize tool result serialization and token counting]
**Learning:** Found that tool results were being serialized with indentation or standard whitespace, and token counting was using the slower `encode()` method. Compact JSON serialization reduces token usage and latency when passing tool outputs back to the LLM.
**Action:** Implemented compact JSON serialization (`separators=(',', ':')`) in `ToolExecutionResult.get_output` and `ChatEngine`. Optimized `Message.get_token_count` by switching to `encoding.encode_ordinary()` and compact JSON for tool call counting.

## 2026-07-07 - [Shared OpenAI client cache in ChatEngine]
**Learning:** Found that each `ChatEngine` instantiation (which happens frequently in agentic loops) was creating a new `OpenAI` client, adding ~33ms of overhead and missing out on HTTP connection pooling.
**Action:** Implemented a class-level `_client_cache` in `ChatEngine` to reuse clients based on API key. Added `clear_client_cache()` for test isolation. Measured a ~74% reduction in instantiation latency (from ~41.6ms to ~10.8ms).

## 2026-07-14 - [Optimize CodeWhisper AST traversal and directory scanning]
**Learning:** Found multiple major performance opportunities in `CodeWhisper`: 1) O(N^2) nested AST walks for determining top-level functions, 2) redundant four-pass AST walks of each function body for extracting complexity, calls, prints, and logs, and 3) recursive directory scanning with rglob which traverses heavy excluded directories like `.git` and `.venv`. Also resolved a subtle AST double-counting bug in complexity calculation for boolean operations and a directory-pruning substring collision bug by using `should_exclude` safely on directory walks.
**Action:** Implemented O(1) set-based class method lookups to find top-level functions, consolidated four redundant traversals into a single-pass `_analyze_function_body` helper, and used `os.walk` to prune directories in-place during directory analysis.

## 2026-07-10 - [Optimize TodoExtractor with precompiled regexes and set lookups]
**Learning:** Found a massive performance bottleneck in `TodoExtractor` where regex patterns for tags, authors, and priorities were eagerly compiled in `_extract_todos_from_line` on every single line scanned (over 23,000 times). Also found linear lookup overhead in directory/file scanning.
**Action:** Pre-compiled tag, author, and priority regex patterns in `__init__`, converted lookup fields like `extensions` and `exclude_dirs` to sets for O(1) membership lookups, and pruned directory walk paths directly. This achieved a ~6.5x speedup, reducing scanning duration from ~1.02s to ~0.15s.

## 2026-07-08 - [Optimize ImportOptimizer directory scanning and pruning]
**Learning:** Found that `ImportOptimizer`'s `find_unused_in_directory` recursively traversed the entire directory tree including `.venv`, `.git`, and `node_modules` without any early pruning. This caused significant delays in repositories with large virtual environments.
**Action:** Implemented class-level `DEFAULT_EXCLUDE_DIRS` in `ImportAnalyzer` and added early directory pruning using `os.walk` (modifying `dirs[:]` in-place). Also optimized non-recursive scanning by using `os.scandir` to avoid glob overhead.

## 2026-07-08 - [Optimize GitStats file statistics collection to be single-pass]
**Learning:** Found a massive O(N) subprocess bottleneck in `GitStats._analyze_files` where up to 100 separate `git log --follow` subprocesses were spawned to compile file statistics. This was highly expensive and limited analysis to only the first 100 alphabetically sorted files.
**Action:** Aggregated file statistics on the fly in `_analyze_commits` from the primary `git log --numstat` stream and resolved rename-path patterns (e.g. `{old => new}/file`) using a regex helper. Updated `_analyze_files` to simply filter the cached stats against the `git ls-files` set. This completely eliminated all extra git subprocesses and allows analyzing ALL files in the repository.

## 2026-07-08 - [Optimize DuplicateFinder directory traversal and hashing]
**Learning:** Found that `DuplicateFinder._get_files` used `Path.rglob('*')` to traverse directories recursively and then filtered out files in excluded directories (like `.git` and `node_modules`). This caused immense disk I/O and CPU overhead because the system physically entered and scanned thousands of files inside those ignored directories.
**Action:** Implemented early directory pruning using `os.walk` (modifying `dirs[:]` in-place) to avoid entering excluded subdirectories, switched `exclude_dirs` and `extensions` to set-based lookups for O(1) checks, cached direct hashlib functions, and increased disk read buffer chunk size from 8KB to 128KB.

## 2026-07-09 - [Optimize agent settings instantiation and lazy config retrieval]
**Learning:** Found that `AgentManager` and each specialized agent were constructing new Pydantic `Settings` objects via `or Settings()` when no settings were provided, incurring redundant `.env` file parsing and Pydantic validation overhead (~0.9ms per instantiation). In addition, `AgentManager.get_agent` was eagerly fetching configuration blocks for all four agent types on every single retrieval.
**Action:** Replaced direct `Settings()` instantiations with the LRU cached `get_settings()`. Refactored `AgentManager.get_agent` to use lazy conditional blocks that only resolve configuration and instantiate the requested `AgentType` on-demand, reducing lookup/instantiation latency by ~47% (from ~12.6ms to ~6.7ms).
