#!/usr/bin/env python3
"""
Basic tests for ChatSystem
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConfiguration:
    """Test configuration system"""

    def test_settings_load(self):
        """Test settings can be loaded"""
        from ChatSystem.core.config import Settings

        # Should not raise with default values
        settings = Settings(openai_api_key="test-key")
        assert settings.model_name == "gpt-4o"
        assert settings.max_tokens == 4096

    def test_model_validation(self):
        """Test model name validation"""
        from ChatSystem.core.config import Settings
        from pydantic import ValidationError

        # Valid model
        settings = Settings(openai_api_key="test-key", model_name="gpt-4o")
        assert settings.model_name == "gpt-4o"

        # Invalid model should raise
        with pytest.raises(ValidationError):
            Settings(openai_api_key="test-key", model_name="invalid-model")


class TestConversation:
    """Test conversation management"""

    def test_conversation_init(self):
        """Test conversation initialization"""
        from ChatSystem.core.conversation import ConversationManager

        conv = ConversationManager(model="gpt-4o")
        assert len(conv.messages) > 0  # Should have system message

    def test_add_message(self):
        """Test adding messages"""
        from ChatSystem.core.conversation import ConversationManager

        conv = ConversationManager(model="gpt-4o")
        initial_count = len(conv.messages)

        conv.add_message(role="user", content="Hello")
        assert len(conv.messages) == initial_count + 1

    def test_token_counting(self):
        """Test token counting"""
        from ChatSystem.core.conversation import ConversationManager

        conv = ConversationManager(model="gpt-4o")
        conv.add_message(role="user", content="Hello world")

        tokens = conv.count_tokens()
        assert tokens > 0

    def test_context_usage(self):
        """Test context window usage calculation"""
        from ChatSystem.core.conversation import ConversationManager

        conv = ConversationManager(model="gpt-4o")
        usage = conv.get_context_window_usage()

        assert "total_tokens" in usage
        assert "max_tokens" in usage
        assert "usage_percent" in usage


class TestTools:
    """Test tool system"""

    def test_tool_adapter(self):
        """Test tool adapter"""
        from ChatSystem.tools.tool_adapter import ToolAdapter

        tools = ToolAdapter.get_all_tools()
        # Should have all defined utilities
        assert len(tools) == len(ToolAdapter.TOOL_DEFINITIONS)

        # Check structure
        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_tool_registry(self):
        """Test tool registry"""
        from ChatSystem.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        tools = registry.get_tools()

        assert len(tools) > 0
        assert callable(registry.get_tool_executor())

    def test_enabled_tools_filter(self):
        """Test filtering enabled tools"""
        from ChatSystem.tools.tool_registry import ToolRegistry

        # Enable only specific tools
        registry = ToolRegistry(enabled_tools=["CodeWhisper", "APITester"])
        tools = registry.get_tools()

        assert len(tools) == 2

        tool_names = [t["function"]["name"] for t in tools]
        assert "analyze_python_code" in tool_names
        assert "test_api_endpoint" in tool_names


class TestAgent:
    """Test agent system"""

    def test_task_planner(self):
        """Test task planner"""
        from ChatSystem.agent.planner import TaskPlanner

        planner = TaskPlanner()
        plan = planner.create_plan("Test goal", [])

        assert plan.goal == "Test goal"
        assert plan.status == "pending"

    def test_reasoner(self):
        """Test reasoner"""
        from ChatSystem.agent.reasoner import Reasoner

        reasoner = Reasoner()
        reasoner.add_thought("First thought")
        reasoner.add_action("First action")
        reasoner.add_observation("First observation")

        trace = reasoner.get_reasoning_trace()
        assert "First thought" in trace
        assert "First action" in trace
        assert "First observation" in trace


def test_imports():
    """Test that all modules can be imported"""
    import ChatSystem
    from ChatSystem.core import ChatEngine, ConversationManager, Settings
    from ChatSystem.tools import ToolRegistry, ToolAdapter
    from ChatSystem.agent import TaskPlanner, AgentExecutor, Reasoner

    assert ChatEngine is not None
    assert ConversationManager is not None
    assert Settings is not None
    assert ToolRegistry is not None
    assert ToolAdapter is not None
    assert TaskPlanner is not None
    assert AgentExecutor is not None
    assert Reasoner is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
