#!/usr/bin/env python3
"""
Conversation Manager - Handle message history and context
"""

import os
import json
import tiktoken
import contextlib
import collections
from typing import DefaultDict, List, Dict, Any, Optional, Literal, TYPE_CHECKING
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field, TypeAdapter

if TYPE_CHECKING:
    from ChatSystem.core.chat_engine import ChatEngine


class Message(BaseModel):
    """
    Represents a single message in a chat conversation, conforming to the
    structure required by the OpenAI API.

    Attributes:
        role (Literal["system", "user", "assistant", "tool"]): The role of the
            message sender.
        content (Optional[str]): The textual content of the message.
        name (Optional[str]): The name of the function that was called, if the
            role is 'tool'.
        tool_calls (Optional[List[Dict[str, Any]]]): A list of tool calls made
            by the assistant.
        tool_call_id (Optional[str]): The ID of the tool call, used for responses
            from a 'tool' role.
        timestamp (datetime): The timestamp of when the message was created.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tokens: Optional[int] = None

    def get_token_count(self, encoding: Any) -> int:
        """
        Calculates and caches the token count for this message.

        Args:
            encoding: The tiktoken encoding to use.

        Returns:
            int: The token count for this message.
        """
        if self.tokens is not None:
            return self.tokens

        tokens = 0
        # Count tokens in content
        if self.content:
            tokens += len(encoding.encode(self.content))

        # Count tokens in tool calls
        if self.tool_calls:
            for tool_call in self.tool_calls:
                tool_str = json.dumps(tool_call)
                tokens += len(encoding.encode(tool_str))

        # Add overhead for message structure (approximate)
        tokens += 4

        self.tokens = tokens
        return tokens

    def to_openai_format(self) -> Dict[str, Any]:
        """
        Converts the Message object to a dictionary format compatible with the
        OpenAI API.

        This method selectively includes fields that are not None to create a
        clean dictionary for the API request.

        Returns:
            Dict[str, Any]: A dictionary representing the message in the format
            expected by the OpenAI API.
        """
        msg: Dict[str, Any] = {"role": self.role}

        if self.content is not None:
            msg["content"] = self.content

        if self.name is not None:
            msg["name"] = self.name

        if self.tool_calls is not None:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id is not None:
            msg["tool_call_id"] = self.tool_call_id

        return msg


class ConversationManager:
    """
    Manages the conversation history, context, and persistence for the chat system.

    This class is responsible for adding messages, tracking token usage,
    trimming the context window, and saving/loading the conversation history.

    Attributes:
        model (str): The name of the GPT model being used.
        max_tokens (int): The maximum number of tokens allowed in the context window.
        messages (List[Message]): A list of Message objects representing the
            conversation.
        auto_save (bool): A flag indicating whether to automatically save the
            history after each message.
        history_file (Path): The file path for storing the conversation history.
        encoding: The tiktoken encoding instance for the specified model.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        max_tokens: int = 128000,
        system_prompt: Optional[str] = None,
        auto_save: bool = True,
        history_file: Optional[str] = None,
        auto_summarize_enabled: bool = True,
        summarize_threshold: float = 0.85,
        summarize_target_ratio: float = 0.6,
    ):
        """
        Initializes the ConversationManager.

        Args:
            model (str, optional): The GPT model name. Defaults to "gpt-4o".
            max_tokens (int, optional): The maximum context window size.
                Defaults to 128000.
            system_prompt (Optional[str], optional): An initial system prompt.
                Defaults to None.
            auto_save (bool, optional): Whether to auto-save the history.
                Defaults to True.
            history_file (Optional[str], optional): The path to the history
                file. Defaults to "~/.chatsystem_history.json".
        """
        self.model = model
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
        self.auto_save = auto_save
        self.auto_summarize_enabled = auto_summarize_enabled
        self.summarize_threshold = summarize_threshold
        self.summarize_target_ratio = summarize_target_ratio
        self._total_tokens = 0
        self._role_counts: DefaultDict[str, int] = collections.defaultdict(int)
        self._batch_save_count = 0
        self._needs_save = False
        self._cached_openai_messages: Optional[List[Dict[str, Any]]] = None
        self._cached_openai_messages_no_system: Optional[List[Dict[str, Any]]] = None
        self._cached_dumped_messages: Optional[List[Dict[str, Any]]] = None
        self._cached_summary: Optional[Dict[str, Any]] = None

        # Set up history file
        if history_file:
            self.history_file = Path(history_file)
        else:
            self.history_file = Path.home() / ".chatsystem_history.json"

        # Ensure history directory exists (restrict perms on any dir we create —
        # the history can contain conversation content and tool output)
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        except Exception as e:
            print(f"Warning: Could not create history directory: {e}")

        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback for unknown/unsupported models - use latest encoding
            self.encoding = tiktoken.get_encoding("o200k_base")

        # Defer default system prompt if history will be loaded
        history_exists = self.auto_save and self.history_file.exists()

        if system_prompt:
            self.add_message(role="system", content=system_prompt)
        elif not history_exists:
            self._add_default_system_prompt()

        # Load previous history if available
        if history_exists:
            self._load_history()

    def _reset_state(self):
        """
        Resets and recalculates the internal state from the current message list.

        This includes total tokens, role counts, and cache invalidation.
        This is an O(N) operation and should be used after bulk message modifications.
        """
        self._total_tokens = 0
        self._role_counts = collections.defaultdict(int)

        for msg in self.messages:
            self._total_tokens += msg.get_token_count(self.encoding)
            self._role_counts[msg.role] += 1

        self._invalidate_cache()

    def _add_default_system_prompt(self):
        """
        Adds a default system prompt to the conversation history.

        This prompt informs the AI about its capabilities and the available tools,
        guiding its behavior and responses.
        """
        system_prompt = """You are an advanced AI assistant with access to powerful utilities:

1. **CodeWhisper** - Analyze Python code structure and complexity
2. **APITester** - Test HTTP API endpoints
3. **DuplicateFinder** - Find duplicate files by hash or name
4. **SnippetManager** - Store and retrieve code snippets
5. **BulkRename** - Batch rename files with patterns
6. **EnvManager** - Manage .env configuration files
7. **FileDiff** - Compare and diff files
8. **GitStats** - Analyze git repository statistics
9. **ImportOptimizer** - Optimize Python imports
10. **PathSketch** - Visualize directory tree structure
11. **TodoExtractor** - Extract TODO comments from code
12. **DataConvert** - Convert between data formats

When users ask you to perform tasks, analyze if any tools can help. Break complex tasks into steps and execute them systematically. Always explain what you're doing and provide clear results."""

        self.add_message(role="system", content=system_prompt)

    def _invalidate_cache(self):
        """Invalidates the cached conversation history representations."""
        self._cached_openai_messages = None
        self._cached_openai_messages_no_system = None
        self._cached_dumped_messages = None
        self._cached_summary = None

    def add_message(
        self,
        role: Literal["system", "user", "assistant", "tool"],
        content: Optional[str] = None,
        name: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
    ) -> Message:
        """
        Adds a new message to the conversation history.

        This method creates a Message object and appends it to the internal
        list of messages. It also triggers an auto-save if enabled.

        Args:
            role (Literal["system", "user", "assistant", "tool"]): The role of
                the message sender.
            content (Optional[str], optional): The text content of the message.
                Defaults to None.
            name (Optional[str], optional): The name of the function called, for
                'tool' roles. Defaults to None.
            tool_calls (Optional[List[Dict[str, Any]]], optional): A list of
                tool calls. Defaults to None.
            tool_call_id (Optional[str], optional): The ID of the tool call.
                Defaults to None.

        Returns:
            Message: The newly created and added Message object.
        """
        message = Message(
            role=role,
            content=content,
            name=name,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
        )

        self.messages.append(message)
        self._total_tokens += message.get_token_count(self.encoding)
        self._role_counts[role] += 1

        # Update caches incrementally if they are already populated
        if self._cached_openai_messages is not None:
            openai_msg = message.to_openai_format()
            self._cached_openai_messages.append(openai_msg)
            # Update no-system cache if it's already populated and new message isn't system
            if self._cached_openai_messages_no_system is not None and role != "system":
                self._cached_openai_messages_no_system.append(openai_msg)

        if self._cached_dumped_messages is not None:
            # use model_dump(mode='json') to pre-serialize complex types (e.g. datetime)
            self._cached_dumped_messages.append(message.model_dump(mode='json'))

        # Invalidate summary cache
        self._cached_summary = None

        # Auto-save if enabled
        if self.auto_save:
            self._save_history()

        return message

    def get_messages(self, include_system: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves the list of messages in a format compatible with the OpenAI API.

        Args:
            include_system (bool, optional): Whether to include the system
                prompt in the returned list. Defaults to True.

        Returns:
            List[Dict[str, Any]]: A list of message dictionaries.
        """
        # Ensure base cache is populated
        if self._cached_openai_messages is None:
            self._cached_openai_messages = [
                msg.to_openai_format() for msg in self.messages
            ]

        # If including system prompt, return a shallow copy of the full cached list
        if include_system:
            return self._cached_openai_messages[:]

        # Ensure no-system cache is populated
        if self._cached_openai_messages_no_system is None:
            self._cached_openai_messages_no_system = [
                msg for msg in self._cached_openai_messages if msg.get("role") != "system"
            ]

        # Return a shallow copy of the cached no-system list
        return self._cached_openai_messages_no_system[:]

    def count_tokens(self, messages: Optional[List[Message]] = None) -> int:
        """
        Counts the number of tokens in a list of messages.

        This method uses the tiktoken library to accurately count the tokens
        based on the model's encoding. It includes tokens from message content
        and tool calls.

        Args:
            messages (Optional[List[Message]], optional): A list of messages to
                count. If None, the entire conversation history is used.
                Defaults to None.

        Returns:
            int: The total number of tokens.
        """
        if messages is None:
            return self._total_tokens

        # Approximate token count for specified messages
        total_tokens = 0

        for message in messages:
            total_tokens += message.get_token_count(self.encoding)

        return total_tokens

    def get_context_window_usage(self) -> Dict[str, Any]:
        """
        Calculates and returns statistics about the context window usage.

        Returns:
            Dict[str, Any]: A dictionary containing the total tokens, max tokens,
            remaining tokens, and the usage percentage.
        """
        total_tokens = self.count_tokens()
        usage_percent = (total_tokens / self.max_tokens) * 100

        return {
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "remaining_tokens": self.max_tokens - total_tokens,
            "usage_percent": round(usage_percent, 2),
        }

    def trim_context(self, target_tokens: Optional[int] = None):
        """
        Trims the conversation history to a specified number of tokens.

        This method removes the oldest messages (excluding the system prompt)
        until the total token count is below the target. This is crucial for
        managing the context window and preventing overflow.

        Args:
            target_tokens (Optional[int], optional): The target number of tokens
                to trim down to. If None, it defaults to 80% of `max_tokens`.
                Defaults to None.
        """
        if target_tokens is None:
            target_tokens = int(self.max_tokens * 0.8)  # Leave 20% headroom

        # If current usage is within limits, do nothing
        if self._total_tokens <= target_tokens:
            return

        # Always keep system message
        system_messages = [m for m in self.messages if m.role == "system"]
        other_messages = [m for m in self.messages if m.role != "system"]

        # Track tokens as we remove messages
        current_tokens = self._total_tokens

        # Identify how many messages to remove
        num_to_remove = 0
        while current_tokens > target_tokens and num_to_remove < len(other_messages) - 1:
            msg_to_remove = other_messages[num_to_remove]
            current_tokens -= msg_to_remove.get_token_count(self.encoding)
            self._role_counts[msg_to_remove.role] -= 1
            num_to_remove += 1

        # Don't leave the kept history starting with orphaned tool messages
        # (a role=="tool" with no preceding assistant tool_calls is rejected by
        # the API). Drop any leading tool messages too.
        while (num_to_remove < len(other_messages) - 1
               and other_messages[num_to_remove].role == "tool"):
            msg_to_remove = other_messages[num_to_remove]
            current_tokens -= msg_to_remove.get_token_count(self.encoding)
            self._role_counts[msg_to_remove.role] -= 1
            num_to_remove += 1

        if num_to_remove > 0:
            self.messages = system_messages + other_messages[num_to_remove:]
            self._invalidate_cache()

        self._total_tokens = current_tokens

    def clear_history(self, keep_system: bool = True):
        """
        Clears the conversation history.

        By default, this method keeps the system prompt while removing all other
        messages.

        Args:
            keep_system (bool, optional): If True, the system prompt is
                retained. If False, the entire history is cleared and a new
                default system prompt is added. Defaults to True.
        """
        if keep_system:
            self.messages = [m for m in self.messages if m.role == "system"]
        else:
            self.messages = []
            self._add_default_system_prompt()

        self._reset_state()

        if self.auto_save:
            self._save_history()

    def _save_history(self):
        """
        Saves the current conversation history to a JSON file.

        The history is saved to the path specified by `self.history_file`.
        Any exceptions during the save process are caught and printed as
        warnings.
        """
        if self._batch_save_count > 0:
            self._needs_save = True
            return

        self._needs_save = False

        try:
            # Ensure dumped messages cache is populated
            if self._cached_dumped_messages is None:
                self._cached_dumped_messages = [
                    msg.model_dump(mode='json') for msg in self.messages
                ]
            history_data = {
                "model": self.model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "messages": self._cached_dumped_messages,
            }

            # Restrict to owner-only (0600) before writing secrets-bearing content.
            # Open with O_CREAT|O_WRONLY|O_TRUNC and mode 0o600 so the file is never
            # briefly world-readable on creation; re-chmod handles pre-existing files.
            fd = os.open(self.history_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            try:
                os.chmod(self.history_file, 0o600)
            except OSError:
                pass
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                # Use compact serialization (no indent, separators=(',', ':')) for speed and size
                # We already used mode='json' in model_dump, so default=str is no longer needed
                json.dump(history_data, f, separators=(',', ':'))

        except Exception as e:
            print(f"Warning: Could not save history: {e}")

    def _load_history(self):
        """
        Loads the conversation history from the JSON file.

        This method reads the file specified by `self.history_file`, parses
        the JSON content, and populates the `self.messages` list using optimized
        bulk validation. Any exceptions during the loading process are caught
        and printed as warnings.
        """
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            raw_messages = history_data.get("messages", [])
            if not raw_messages:
                return

            # Bolt: Optimize history loading using bulk validation
            # TypeAdapter.validate_python is significantly faster than manual loop with Message(**data)
            adapter = TypeAdapter(List[Message])
            new_messages = adapter.validate_python(raw_messages)

            # Bolt: Use extend to preserve existing additive behavior
            self.messages.extend(new_messages)

            # Bolt: Rebuild state and caches in a single optimized pass
            self._total_tokens = 0
            self._role_counts = collections.defaultdict(int)
            self._cached_openai_messages = []

            for msg in self.messages:
                self._total_tokens += msg.get_token_count(self.encoding)
                self._role_counts[msg.role] += 1
                self._cached_openai_messages.append(msg.to_openai_format())

            # Bolt: Optimize dumped cache by reusing raw loaded data for the new part
            # This avoids redundant model_dump calls on the entire history
            # Dump the validated Message objects (not the raw dicts) for the
            # loaded slice, so the cached-dump token counts match what
            # get_token_count just computed rather than whatever was on disk.
            existing_count = len(self.messages) - len(new_messages)
            existing_dumped = [msg.model_dump(mode='json') for msg in self.messages[:existing_count]]
            self._cached_dumped_messages = existing_dumped + [
                msg.model_dump(mode='json') for msg in new_messages
            ]

        except Exception as e:
            print(f"Warning: Could not load history: {e}")

    def export_conversation(self, filepath: str, format: str = "json"):
        """
        Exports the current conversation to a file.

        The conversation can be exported in either JSON or plain text format.

        Args:
            filepath (str): The path to the file where the conversation will be
                exported.
            format (str, optional): The format for the export ('json' or 'text').
                Defaults to "json".

        Raises:
            ValueError: If an unsupported format is specified.
        """
        # Exports carry the same conversation content as the history file, so
        # create them 0600 too rather than at the umask default.
        if format == "json":
            if self._cached_dumped_messages is None:
                self._cached_dumped_messages = [
                    msg.model_dump(mode='json') for msg in self.messages
                ]
            with self._open_private_write(filepath) as f:
                json.dump(
                    self._cached_dumped_messages,
                    f,
                    indent=2,
                )
        elif format == "text":
            with self._open_private_write(filepath) as f:
                for msg in self.messages:
                    f.write(f"[{msg.role.upper()}] {msg.timestamp}\n")
                    f.write(f"{msg.content}\n\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    def _open_private_write(filepath: str):
        """Open a file for writing with owner-only (0600) permissions."""
        fd = os.open(filepath, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        return os.fdopen(fd, "w", encoding="utf-8")

    def get_summary(self) -> Dict[str, Any]:
        """
        Generates a summary of the conversation statistics.

        This summary includes the total number of messages, a breakdown of
        messages by role, context window usage, and the start and end times
        of the conversation.

        Returns:
            Dict[str, Any]: A dictionary containing the summary statistics.
        """
        if self._cached_summary is not None:
            return self._cached_summary.copy()

        self._cached_summary = {
            "total_messages": len(self.messages),
            "messages_by_role": dict(self._role_counts),
            "context_usage": self.get_context_window_usage(),
            "started_at": self.messages[0].timestamp if self.messages else None,
            "last_message_at": self.messages[-1].timestamp if self.messages else None,
        }
        return self._cached_summary

    @contextlib.contextmanager
    def batch_saves(self):
        """
        Context manager to batch multiple history saves into a single write.

        This is useful when adding multiple messages in a row (e.g., during tool calls)
        to avoid redundant disk I/O.
        """
        self._batch_save_count += 1
        try:
            yield
        finally:
            self._batch_save_count -= 1
            if self._batch_save_count == 0 and self._needs_save:
                self._save_history()

    @staticmethod
    def _keep_count_without_orphan_tools(other_messages: List['Message'], keep_recent_count: int) -> int:
        """Grow keep_recent_count until the kept slice doesn't start on a tool msg.

        Keeps an assistant(tool_calls) message together with its tool responses so
        the post-summary history never leads with an orphaned role=="tool" message.
        """
        total = len(other_messages)
        while keep_recent_count < total and other_messages[-keep_recent_count].role == "tool":
            keep_recent_count += 1
        return keep_recent_count

    def summarize_conversation(self, chat_engine: Optional['ChatEngine'] = None, target_ratio: float = 0.5) -> str:
        """
        Summarize the conversation to reduce token usage.

        This method uses an LLM to create a concise summary of the conversation
        history, replacing older messages with a summary while keeping recent
        messages intact.

        Args:
            chat_engine: Optional ChatEngine to use for summarization.
                If None, creates a summary without LLM (structural only).
            target_ratio (float): Target ratio of original tokens to keep (0.0 to 1.0).
                Default 0.5 means compress to ~50% of current size.

        Returns:
            str: The summary text that was created
        """
        if not self.messages:
            return "No messages to summarize"

        # Keep system messages and recent messages
        system_messages = [m for m in self.messages if m.role == "system"]
        other_messages = [m for m in self.messages if m.role != "system"]

        if len(other_messages) < 5:
            # Too few messages to summarize meaningfully
            return "Conversation too short to summarize"

        # Determine split point. target_ratio is the fraction of recent messages
        # to keep verbatim; the older remainder is compressed into a summary.
        keep_fraction = min(0.9, max(0.1, target_ratio))
        keep_recent_count = max(3, int(len(other_messages) * keep_fraction))
        keep_recent_count = min(keep_recent_count, len(other_messages) - 1)
        # Never split an assistant(tool_calls) group from its tool responses: a
        # kept history that starts with a role=="tool" message is rejected by the
        # OpenAI API. Move the boundary back to include the owning assistant msg.
        keep_recent_count = self._keep_count_without_orphan_tools(other_messages, keep_recent_count)
        messages_to_summarize = other_messages[:-keep_recent_count]
        messages_to_keep = other_messages[-keep_recent_count:]

        if chat_engine:
            # Use LLM to create intelligent summary
            summary_text = self._llm_summarize(chat_engine, messages_to_summarize)
        else:
            # Create structural summary without LLM
            summary_text = self._structural_summarize(messages_to_summarize)

        # Create summary message
        summary_message = Message(
            role="system",
            content=f"[Conversation Summary - {len(messages_to_summarize)} messages compressed]\n{summary_text}"
        )

        # Replace messages with summary + kept messages
        self.messages = system_messages + [summary_message] + messages_to_keep
        self._reset_state()

        if self.auto_save:
            self._save_history()

        return summary_text

    def _llm_summarize(self, chat_engine: 'ChatEngine', messages: List[Message]) -> str:
        """
        Use LLM to create an intelligent summary of messages.

        Args:
            chat_engine: ChatEngine to use for summarization
            messages: Messages to summarize

        Returns:
            Summary text
        """
        # Build conversation text
        conversation_text = []
        for msg in messages:
            role_label = msg.role.upper()
            content = msg.content or "[tool call]"
            conversation_text.append(f"[{role_label}] {content[:500]}")

        # Create summarization prompt
        prompt = f"""Summarize the following conversation concisely, preserving key information, decisions, and context:

{chr(10).join(conversation_text)}

Provide a concise summary in 3-5 paragraphs that captures:
1. Main topics discussed
2. Key decisions or conclusions
3. Important facts or data mentioned
4. Any ongoing tasks or action items"""

        # Get summary from LLM
        response_parts = []
        for chunk in chat_engine.chat(prompt):
            response_parts.append(chunk)

        return "".join(response_parts)

    def _structural_summarize(self, messages: List[Message]) -> str:
        """
        Create a structural summary without using LLM.

        Args:
            messages: Messages to summarize

        Returns:
            Summary text
        """
        summary_lines = []
        summary_lines.append(f"Summarized {len(messages)} messages:")

        # Count by role
        role_counts: Dict[str, int] = {}
        for msg in messages:
            role_counts[msg.role] = role_counts.get(msg.role, 0) + 1

        summary_lines.append(f"  - User messages: {role_counts.get('user', 0)}")
        summary_lines.append(f"  - Assistant messages: {role_counts.get('assistant', 0)}")
        summary_lines.append(f"  - Tool messages: {role_counts.get('tool', 0)}")

        # Include first and last message snippets
        if messages:
            first_msg = messages[0]
            last_msg = messages[-1]

            if first_msg.content:
                summary_lines.append(f"\nFirst message: {first_msg.content[:200]}...")
            if last_msg.content:
                summary_lines.append(f"Last message: {last_msg.content[:200]}...")

        return "\n".join(summary_lines)

    def auto_summarize_if_needed(self, chat_engine: Optional['ChatEngine'] = None, threshold: float = 0.85) -> bool:
        """
        Automatically summarize conversation if token usage exceeds threshold.

        Args:
            chat_engine: Optional ChatEngine for LLM-based summarization
            threshold (float): Token usage threshold (0.0 to 1.0) to trigger summarization.
                Default 0.85 means summarize at 85% capacity.

        Returns:
            bool: True if summarization was performed, False otherwise
        """
        usage = self.get_context_window_usage()

        # Avoid division by zero
        if usage["max_tokens"] == 0:
            return False

        usage_ratio = usage["total_tokens"] / usage["max_tokens"]

        if usage_ratio >= threshold:
            # Trigger summarization
            self.summarize_conversation(chat_engine=chat_engine, target_ratio=self.summarize_target_ratio)
            return True

        return False

    def maybe_auto_summarize(self, chat_engine: Optional['ChatEngine'] = None) -> bool:
        """
        Auto-summarize using this manager's configured settings.

        Honors ``auto_summarize_enabled`` and ``summarize_threshold`` from config.
        Defaults to a structural (non-LLM) summary so it is cheap and
        recursion-free when called inside the live chat loop; pass ``chat_engine``
        for an LLM-based summary (used by the explicit ``/summarize`` command).

        Returns:
            bool: True if summarization was performed.
        """
        if not self.auto_summarize_enabled:
            return False
        return self.auto_summarize_if_needed(
            chat_engine=chat_engine, threshold=self.summarize_threshold
        )
