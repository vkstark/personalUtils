#!/usr/bin/env python3
"""
Conversation Manager - Handle message history and context
"""

import json
import tiktoken
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field


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
    timestamp: datetime = Field(default_factory=datetime.now)

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
        msg = {"role": self.role}

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

        # Set up history file
        if history_file:
            self.history_file = Path(history_file)
        else:
            self.history_file = Path.home() / ".chatsystem_history.json"

        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback for unknown/unsupported models - use latest encoding
            self.encoding = tiktoken.get_encoding("o200k_base")

        # Add system prompt if provided
        if system_prompt:
            self.add_message(role="system", content=system_prompt)
        else:
            self._add_default_system_prompt()

        # Load previous history if available
        if self.auto_save and self.history_file.exists():
            self._load_history()

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
10. **PathSketch** - Path manipulation utilities
11. **TodoExtractor** - Extract TODO comments from code
12. **DataConvert** - Convert between data formats

When users ask you to perform tasks, analyze if any tools can help. Break complex tasks into steps and execute them systematically. Always explain what you're doing and provide clear results."""

        self.add_message(role="system", content=system_prompt)

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
        messages = self.messages

        if not include_system:
            messages = [m for m in messages if m.role != "system"]

        return [msg.to_openai_format() for msg in messages]

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
            messages = self.messages

        # Approximate token count for messages
        total_tokens = 0

        for message in messages:
            # Count tokens in content
            if message.content:
                total_tokens += len(self.encoding.encode(message.content))

            # Count tokens in tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_str = json.dumps(tool_call)
                    total_tokens += len(self.encoding.encode(tool_str))

            # Add overhead for message structure (approximate)
            total_tokens += 4

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

        # Always keep system message
        system_messages = [m for m in self.messages if m.role == "system"]
        other_messages = [m for m in self.messages if m.role != "system"]

        # Remove oldest messages until we fit
        while self.count_tokens() > target_tokens and len(other_messages) > 1:
            other_messages.pop(0)

        self.messages = system_messages + other_messages

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

        if self.auto_save:
            self._save_history()

    def _save_history(self):
        """
        Saves the current conversation history to a JSON file.

        The history is saved to the path specified by `self.history_file`.
        This method handles the creation of the parent directory if it does not
        exist. Any exceptions during the save process are caught and printed as
        warnings.
        """
        try:
            # Create directory if it doesn't exist
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert messages to dict format
            history_data = {
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "messages": [msg.model_dump() for msg in self.messages],
            }

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, default=str)

        except Exception as e:
            print(f"Warning: Could not save history: {e}")

    def _load_history(self):
        """
        Loads the conversation history from the JSON file.

        This method reads the file specified by `self.history_file`, parses
        the JSON content, and populates the `self.messages` list. Any
        exceptions during the loading process are caught and printed as
        warnings.
        """
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            # Load messages
            for msg_data in history_data.get("messages", []):
                # Convert timestamp string back to datetime
                if "timestamp" in msg_data and isinstance(msg_data["timestamp"], str):
                    msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])

                message = Message(**msg_data)
                self.messages.append(message)

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
        if format == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    [msg.model_dump() for msg in self.messages],
                    f,
                    indent=2,
                    default=str,
                )
        elif format == "text":
            with open(filepath, "w", encoding="utf-8") as f:
                for msg in self.messages:
                    f.write(f"[{msg.role.upper()}] {msg.timestamp}\n")
                    f.write(f"{msg.content}\n\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Generates a summary of the conversation statistics.

        This summary includes the total number of messages, a breakdown of
        messages by role, context window usage, and the start and end times
        of the conversation.

        Returns:
            Dict[str, Any]: A dictionary containing the summary statistics.
        """
        role_counts = {}
        for msg in self.messages:
            role_counts[msg.role] = role_counts.get(msg.role, 0) + 1

        return {
            "total_messages": len(self.messages),
            "messages_by_role": role_counts,
            "context_usage": self.get_context_window_usage(),
            "started_at": self.messages[0].timestamp if self.messages else None,
            "last_message_at": self.messages[-1].timestamp if self.messages else None,
        }

    def summarize_conversation(self, chat_engine=None, target_ratio: float = 0.5) -> str:
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

        # Calculate current token count
        current_tokens = self.count_tokens()
        target_tokens = int(current_tokens * target_ratio)

        # Determine split point - keep recent 30% of messages, summarize the rest
        keep_recent_count = max(3, int(len(other_messages) * 0.3))
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

        if self.auto_save:
            self._save_history()

        return summary_text

    def _llm_summarize(self, chat_engine, messages: List[Message]) -> str:
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

        # Get summary from LLM (disable tools for this)
        response_parts = []
        for chunk in chat_engine.chat(prompt, stream=False):
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
        role_counts = {}
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

    def auto_summarize_if_needed(self, chat_engine=None, threshold: float = 0.85) -> bool:
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
        usage_ratio = usage["total_tokens"] / usage["max_tokens"]

        if usage_ratio >= threshold:
            # Trigger summarization
            self.summarize_conversation(chat_engine=chat_engine, target_ratio=0.6)
            return True

        return False
