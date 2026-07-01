#!/usr/bin/env python3
"""
Tool-calling behavior in ChatEngine: the parallel ThreadPoolExecutor path's
error handling (ordering, no double-execution) and the fail-closed
max_tool_call_depth guard.

Hermetic: OpenAI client is stubbed, tools are a MagicMock; a real
ConversationManager (auto_save=False) records history so we can assert on it.
"""

from unittest.mock import MagicMock, patch

import pytest

from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.core.conversation import ConversationManager
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus


def _settings():
    s = MagicMock()
    s.openai_api_key = "test-key"
    s.model_name = "gpt-4o"
    s.max_tokens = 4096
    s.enable_tools = True
    s.parallel_tool_calls = True
    s.max_tool_call_depth = 5
    return s


def _engine():
    with patch("ChatSystem.core.chat_engine.OpenAI"):
        conv = ConversationManager(model="gpt-4o", auto_save=False)
        engine = ChatEngine(settings=_settings(), conversation=conv)
    # Follow-up completion: plain content, no further tool calls.
    followup = MagicMock()
    followup.choices = [MagicMock()]
    followup.choices[0].message.content = "done"
    followup.choices[0].message.tool_calls = None
    followup.usage = None
    engine.client.chat.completions.create.return_value = followup
    return engine


def _tool_call(call_id, arguments):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = "test_tool"
    tc.function.arguments = arguments
    tc.model_dump.return_value = {"id": call_id}
    return tc


class TestParallelToolPath:
    def test_malformed_json_does_not_execute_or_reorder(self):
        engine = _engine()
        executor = MagicMock(return_value=ToolExecutionResult(
            status=ToolStatus.SUCCESS, tool_name="test_tool", duration=0.1, stdout="ok"
        ))
        engine.tool_executor = executor

        good = _tool_call("good", "{}")
        bad = _tool_call("bad", "{not valid json")

        engine._handle_tool_calls([good, bad], "gpt-4o", 4096, 0.7)

        tool_msgs = [m for m in engine.conversation.messages if m.role == "tool"]
        # One tool message per call, in the original order.
        assert [m.tool_call_id for m in tool_msgs] == ["good", "bad"]
        # The malformed call never reached the executor (no double / spurious run).
        assert executor.call_count == 1
        # Metrics recorded once, only for the call that actually ran.
        assert engine.tool_metrics["test_tool"].total_calls == 1
        # The bad call surfaced an error rather than being silently dropped.
        bad_msg = next(m for m in tool_msgs if m.tool_call_id == "bad")
        assert "error" in (bad_msg.content or "").lower()


class TestMultiRound:
    def test_second_round_tool_calls_are_executed(self):
        engine = _engine()
        engine.tool_executor = MagicMock(return_value=ToolExecutionResult(
            status=ToolStatus.SUCCESS, tool_name="test_tool", duration=0.1, stdout="ok"
        ))
        # First follow-up asks for another tool; second follow-up is final text.
        round2 = MagicMock()
        round2.choices = [MagicMock()]
        round2.choices[0].message.content = None
        round2.choices[0].message.tool_calls = [_tool_call("r2", "{}")]
        round2.usage = None
        final = MagicMock()
        final.choices = [MagicMock()]
        final.choices[0].message.content = "all done"
        final.choices[0].message.tool_calls = None
        final.usage = None
        engine.client.chat.completions.create.side_effect = [round2, final]

        result = engine._handle_tool_calls([_tool_call("r1", "{}")], "gpt-4o", 4096, 0.7)

        assert result == "all done"
        # Both the first-round and second-round tool calls actually executed.
        assert engine.tool_executor.call_count == 2
        assert engine.tool_call_depth == 0  # fully unwound


class TestDepthGuard:
    def test_depth_limit_is_enforced_and_restored(self):
        engine = _engine()
        engine.tool_executor = MagicMock()
        engine.tool_call_depth = engine.max_tool_call_depth  # already at the ceiling

        result = engine._handle_tool_calls([_tool_call("x", "{}")], "gpt-4o", 4096, 0.7)

        assert "Maximum tool call depth" in result
        # The tool never ran, and the counter is restored (no leak).
        engine.tool_executor.assert_not_called()
        assert engine.tool_call_depth == engine.max_tool_call_depth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
