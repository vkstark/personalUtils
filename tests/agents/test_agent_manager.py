#!/usr/bin/env python3
"""
Unit tests for AgentManager: agent instantiation/caching, persona injection,
fuzzy name parsing, engine switching, and current-agent tracking.

Consolidated into hermetic pytest form. A stub engine with a real (non-persisting)
ConversationManager stands in for ChatEngine, so no OpenAI calls are made.
"""

import pytest

from ChatSystem.core.config import Settings
from ChatSystem.core.conversation import ConversationManager
from agents.agent_manager import AgentManager, AgentType


class _StubEngine:
    """Hermetic ChatEngine stand-in: real conversation, empty tool list."""

    def __init__(self):
        self.conversation = ConversationManager(model="gpt-4o", auto_save=False)
        self.tools = []


@pytest.fixture
def manager():
    return AgentManager(settings=Settings(openai_api_key="test-key"))


def _system_text(engine):
    msgs = engine.conversation.get_messages(include_system=True)
    return " ".join(m.get("content") or "" for m in msgs if m.get("role") == "system")


class TestParseAgentType:
    def test_enum_value(self):
        assert AgentManager.parse_agent_type("task_executor") == AgentType.TASK_EXECUTOR

    def test_short_name(self):
        assert AgentManager.parse_agent_type("analyzer") == AgentType.TRANSCRIPT_ANALYZER

    def test_fuzzy_keyword(self):
        assert AgentManager.parse_agent_type("strategic") == AgentType.TRILLIONAIRE_FUTURIST

    def test_case_insensitive_and_trimmed(self):
        assert AgentManager.parse_agent_type("  TEACHER ") == AgentType.FRAMEWORK_TEACHER

    def test_invalid_returns_none(self):
        assert AgentManager.parse_agent_type("nonsense") is None


class TestAgentMetadata:
    def test_descriptions_cover_all_types(self):
        for agent_type in AgentType:
            info = AgentManager.AGENT_DESCRIPTIONS[agent_type]
            assert "name" in info
            assert "short_name" in info

    def test_list_agents_returns_all(self, manager):
        assert len(manager.list_agents()) == len(list(AgentType))


class TestAgentLifecycle:
    @pytest.mark.parametrize("agent_type", list(AgentType))
    def test_get_agent_instantiates_each_type(self, manager, agent_type):
        agent = manager.get_agent(agent_type, chat_engine=_StubEngine())
        assert agent is not None
        assert agent_type in manager.agents

    def test_get_agent_caches_instance(self, manager):
        first = manager.get_agent(AgentType.TASK_EXECUTOR, chat_engine=_StubEngine())
        second = manager.get_agent(AgentType.TASK_EXECUTOR)
        assert first is second

    def test_persona_injected_into_conversation(self, manager):
        engine = _StubEngine()
        manager.get_agent(AgentType.TASK_EXECUTOR, chat_engine=engine)
        assert "task execution agent" in _system_text(engine).lower()

    def test_switching_engine_reinjects_persona(self, manager):
        engine_a = _StubEngine()
        agent = manager.get_agent(AgentType.TRANSCRIPT_ANALYZER, chat_engine=engine_a)

        engine_b = _StubEngine()
        agent_again = manager.get_agent(AgentType.TRANSCRIPT_ANALYZER, chat_engine=engine_b)

        # Same cached instance, now bound to the new engine, persona re-added
        assert agent_again is agent
        assert agent_again.chat_engine is engine_b
        assert _system_text(engine_b).strip() != ""

    def test_set_and_get_current_agent(self, manager):
        manager.set_current_agent(AgentType.FRAMEWORK_TEACHER, chat_engine=_StubEngine())
        assert manager.current_agent_type == AgentType.FRAMEWORK_TEACHER
        assert manager.get_current_agent() is not None


class TestDispatch:
    """dispatch() routes a user turn to the active agent's primary method."""

    def test_dispatch_calls_primary_method_of_current_agent(self, manager):
        seen = {}

        class _FakeFuturist:
            def respond(self, text):
                seen["arg"] = text
                return "future answer"

        manager.current_agent = _FakeFuturist()
        manager.current_agent_type = AgentType.TRILLIONAIRE_FUTURIST

        out = manager.dispatch("what is next")
        assert out == "future answer"
        assert seen["arg"] == "what is next"

    def test_primary_method_map_covers_all_agent_types(self):
        for agent_type in AgentType:
            assert agent_type in AgentManager._PRIMARY_METHOD

    def test_primary_method_exists_on_each_real_agent(self, manager):
        # Guard against a typo in _PRIMARY_METHOD: each named method must exist.
        for agent_type, method_name in AgentManager._PRIMARY_METHOD.items():
            agent = manager.get_agent(agent_type, chat_engine=_StubEngine())
            assert callable(getattr(agent, method_name, None)), (
                f"{agent_type} has no callable {method_name}"
            )

    def test_dispatch_without_active_agent_raises(self):
        mgr = AgentManager(settings=Settings(openai_api_key="test-key"))
        with pytest.raises(RuntimeError):
            mgr.dispatch("hello")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
