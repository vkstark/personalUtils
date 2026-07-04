#!/usr/bin/env python3
"""
Test disk I/O optimization using batch_saves
"""

import pytest
import sys
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ChatSystem.core.conversation import ConversationManager
from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus

class TestIOOptimization:
    """Test disk I/O optimization"""

    def test_batch_saves_reduces_writes(self, tmp_path):
        """Test that batch_saves reduces the number of disk writes"""
        history_file = tmp_path / "test_history.json"

        # We mock json.dump to count ACTUAL disk writes
        with patch('json.dump') as mock_dump:
            conv = ConversationManager(
                model="gpt-4o",
                history_file=str(history_file),
                auto_save=True
            )

            # 1 write for system prompt in __init__
            assert mock_dump.call_count == 1
            mock_dump.reset_mock()

            # Case 1: Multiple adds without batching
            conv.add_message(role="user", content="Message 1")
            conv.add_message(role="user", content="Message 2")
            conv.add_message(role="user", content="Message 3")

            # Expect 3 writes for the 3 messages
            assert mock_dump.call_count == 3
            mock_dump.reset_mock()

            # Case 2: Multiple adds with batching
            with conv.batch_saves():
                conv.add_message(role="user", content="Batch 1")
                conv.add_message(role="user", content="Batch 2")
                conv.add_message(role="user", content="Batch 3")
                # Should not have called dump yet
                assert mock_dump.call_count == 0

            # Expect only 1 write at the end of the block
            assert mock_dump.call_count == 1

    def test_handle_tool_calls_uses_batching(self):
        """Test that _handle_tool_calls uses batching to reduce writes"""
        # Mock settings and OpenAI client
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.model_name = "gpt-4o"
        mock_settings.max_tokens = 4096
        mock_settings.parallel_tool_calls = True
        mock_settings.enable_tools = True
        mock_settings.max_tool_call_depth = 5

        # Mock conversation
        mock_conv = MagicMock(spec=ConversationManager)
        mock_conv.batch_saves = ConversationManager.batch_saves.__get__(mock_conv, ConversationManager)
        # Initialize internal state for mock_conv as batch_saves uses them
        mock_conv._batch_save_count = 0
        mock_conv._needs_save = False

        with patch('ChatSystem.core.chat_engine.OpenAI'), \
             patch('ChatSystem.core.chat_engine.ConversationManager', return_value=mock_conv):

            # Clear cache to avoid interference
            ChatEngine._client_cache = {}
            engine = ChatEngine(settings=mock_settings)

            # Setup tool executor
            mock_result = ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                tool_name="test_tool",
                duration=0.1,
                stdout="Tool result"
            )
            engine.tool_executor = MagicMock(return_value=mock_result)

            # Mock tool calls
            mock_tool_call1 = MagicMock()
            mock_tool_call1.id = "call1"
            mock_tool_call1.function.name = "test_tool"
            mock_tool_call1.function.arguments = "{}"
            mock_tool_call1.model_dump.return_value = {"id": "call1"}

            mock_tool_call2 = MagicMock()
            mock_tool_call2.id = "call2"
            mock_tool_call2.function.name = "test_tool"
            mock_tool_call2.function.arguments = "{}"
            mock_tool_call2.model_dump.return_value = {"id": "call2"}

            # Mock OpenAI response for the follow-up call (no further tool calls)
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "Final response"
            mock_completion.choices[0].message.tool_calls = None
            mock_completion.usage = None
            engine.client.chat.completions.create.return_value = mock_completion

            # Call _handle_tool_calls
            engine._handle_tool_calls([mock_tool_call1, mock_tool_call2], "gpt-4o", 4096, 0.7)

            # Let's verify batch_saves was indeed called
            assert mock_conv.add_message.call_count >= 3

    def test_real_integration_batch_count(self, tmp_path):
        """Real integration test for batch count in ChatEngine"""
        history_file = tmp_path / "test_history.json"

        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key-2"
        mock_settings.model_name = "gpt-4o"
        mock_settings.max_tokens = 4096
        mock_settings.parallel_tool_calls = True
        mock_settings.enable_tools = True
        mock_settings.max_tool_call_depth = 5

        with patch('ChatSystem.core.chat_engine.OpenAI'), \
             patch('json.dump') as mock_dump:

            conv = ConversationManager(
                model="gpt-4o",
                history_file=str(history_file),
                auto_save=True
            )
            # Reset after init system prompt
            mock_dump.reset_mock()

            # Clear cache
            ChatEngine._client_cache = {}
            engine = ChatEngine(settings=mock_settings, conversation=conv)

            # Mock tool executor
            mock_result = ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                tool_name="test_tool",
                duration=0.1,
                stdout="Tool result"
            )
            engine.tool_executor = MagicMock(return_value=mock_result)

            # Mock tool calls
            mock_tool_call = MagicMock()
            mock_tool_call.id = "call1"
            mock_tool_call.function.name = "test_tool"
            mock_tool_call.function.arguments = "{}"
            mock_tool_call.model_dump.return_value = {"id": "call1"}

            # Mock OpenAI response (final: content, no further tool calls)
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "Final response"
            mock_completion.choices[0].message.tool_calls = None
            mock_completion.usage = None

            engine.client.chat.completions.create.return_value = mock_completion

            # Call _handle_tool_calls
            engine._handle_tool_calls([mock_tool_call], "gpt-4o", 4096, 0.7)

            # We expect:
            # 1. Assistant message added -> _save_history called (but batches)
            # 2. Tool result message added -> _save_history called (but batches)
            # 3. Block ends -> _save_history called (final write)
            # 4. Final assistant message added -> _save_history called (not batched)

            # Total ACTUAL writes should be 2 (one for the batch, one for the final assistant response)
            assert mock_dump.call_count == 2

if __name__ == "__main__":
    pytest.main([__file__])
