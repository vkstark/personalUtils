#!/usr/bin/env python3
"""
Tests for persona eviction on agent switch.

The CLI builds a fresh ConversationManager per /agent switch, reloading a
history file that already carries the previous agent's persona as a plain
system message. AgentManager.set_current_agent must evict foreign/stale
personas (marked via `[Agent Persona: <key>]`, or matched by legacy prefix for
histories written before the marker existed) immediately before injecting the
active agent's persona, so exactly one persona survives any switch.

Hermetic: stub engines with real (temp-file-backed) ConversationManagers, no
OpenAI calls.
"""

import collections
import json

import pytest

from ChatSystem.core.config import Settings
from ChatSystem.core.conversation import ConversationManager, Message
from agents.agent_manager import AgentManager, AgentType
from agents.framework_teacher.teacher import FrameworkTeacher
from agents.task_executor.executor import AgentExecutor
from agents.transcript_analyzer.analyzer import TranscriptAnalyzer
from agents.trillionaire_futurist.futurist import TrillionaireFuturist


class _StubEngine:
    """Hermetic ChatEngine stand-in: real conversation, empty tool list."""

    def __init__(self):
        self.conversation = ConversationManager(model="gpt-4o", auto_save=False)
        self.tools = []


class _HistoryStubEngine:
    """Stub engine whose conversation persists to (and reloads) a history file,
    mirroring the CLI's per-switch engine rebuild on the same file."""

    def __init__(self, history_file):
        self.conversation = ConversationManager(
            model="gpt-4o", auto_save=True, history_file=str(history_file)
        )
        self.tools = []


@pytest.fixture
def manager():
    return AgentManager(settings=Settings(openai_api_key="test-key"))


def _system_contents(conversation):
    return [m.content or "" for m in conversation.messages if m.role == "system"]


class TestPersonaEvictionOnSwitch:
    def test_switch_evicts_previous_agent_persona(self, manager, tmp_path):
        hist = tmp_path / "history.json"
        engine_a = _HistoryStubEngine(hist)
        manager.set_current_agent(AgentType.TRANSCRIPT_ANALYZER, chat_engine=engine_a)

        # Fresh engine on the same file — the reloaded history already carries
        # the analyzer persona; the switch must remove it.
        engine_b = _HistoryStubEngine(hist)
        manager.set_current_agent(AgentType.FRAMEWORK_TEACHER, chat_engine=engine_b)

        system_texts = _system_contents(engine_b.conversation)
        assert not any("Transcript Intelligence Analyst" in t for t in system_texts)
        assert any("FRAMEWORK ARCHITECT and META-LEARNING ENGINE" in t for t in system_texts)

    def test_cycling_leaves_exactly_one_marked_persona(self, manager, tmp_path):
        from agents.persona import PERSONA_MARKER_PREFIX

        hist = tmp_path / "history.json"
        engine = None
        for agent_type in (
            AgentType.TRANSCRIPT_ANALYZER,
            AgentType.FRAMEWORK_TEACHER,
            AgentType.TRANSCRIPT_ANALYZER,
        ):
            engine = _HistoryStubEngine(hist)
            manager.set_current_agent(agent_type, chat_engine=engine)

        personas = [
            t for t in _system_contents(engine.conversation)
            if t.startswith(PERSONA_MARKER_PREFIX)
        ]
        assert len(personas) == 1
        assert personas[0].startswith(f"{PERSONA_MARKER_PREFIX} transcript_analyzer]")

    @pytest.mark.parametrize("agent_type", list(AgentType))
    def test_each_agent_injects_marked_persona(self, manager, agent_type):
        from agents.persona import PERSONA_MARKER_PREFIX

        engine = _StubEngine()
        manager.set_current_agent(agent_type, chat_engine=engine)

        personas = [
            t for t in _system_contents(engine.conversation)
            if t.startswith(PERSONA_MARKER_PREFIX)
        ]
        assert len(personas) == 1
        # The __init__ injection path must use the same key AgentManager uses.
        assert personas[0].startswith(f"{PERSONA_MARKER_PREFIX} {agent_type.value}]")

    def test_engine_swap_reinjection_stays_idempotent(self, manager):
        from agents.persona import PERSONA_MARKER_PREFIX

        # __init__ injects on creation; the engine-swap path re-injects — both
        # must produce byte-identical strings so #114 idempotency holds.
        engine = _StubEngine()
        manager.get_agent(AgentType.TASK_EXECUTOR, chat_engine=engine)
        manager.get_agent(AgentType.TASK_EXECUTOR, chat_engine=engine)

        personas = [
            t for t in _system_contents(engine.conversation)
            if t.startswith(PERSONA_MARKER_PREFIX)
        ]
        assert len(personas) == 1


class TestLegacyPersonaHealing:
    def test_polluted_legacy_history_healed_on_activation(self, manager, tmp_path):
        from agents.persona import PERSONA_MARKER_PREFIX

        hist = tmp_path / "history.json"
        # Seed a history exactly as pre-marker versions persisted it: unmarked
        # personas (the executor's with the tool list formatted in).
        seed = ConversationManager(model="gpt-4o", auto_save=True, history_file=str(hist))
        seed.add_message(
            role="system",
            content=AgentExecutor.SYSTEM_PERSONA.format(tools="code_whisper, api_tester"),
        )
        seed.add_message(role="system", content=TranscriptAnalyzer.SYSTEM_PERSONA)
        seed.add_message(role="user", content="hello there")

        engine = _HistoryStubEngine(hist)
        manager.set_current_agent(AgentType.FRAMEWORK_TEACHER, chat_engine=engine)

        system_texts = _system_contents(engine.conversation)
        assert not any("task execution agent" in t for t in system_texts)
        assert not any("Transcript Intelligence Analyst" in t for t in system_texts)
        marked = [t for t in system_texts if t.startswith(PERSONA_MARKER_PREFIX)]
        assert len(marked) == 1
        assert marked[0].startswith(f"{PERSONA_MARKER_PREFIX} framework_teacher]")
        # Non-persona content is untouched.
        assert any(t.startswith("You are an advanced AI assistant") for t in system_texts)
        assert any(
            m.role == "user" and m.content == "hello there"
            for m in engine.conversation.messages
        )

    def test_legacy_prefixes_match_persisted_persona_forms(self):
        from agents.persona import LEGACY_PERSONA_PREFIXES

        # Each legacy prefix must match the form actually persisted by
        # pre-marker versions — for the executor, the tools-formatted persona.
        persisted_forms = [
            AgentExecutor.SYSTEM_PERSONA.format(tools="code_whisper, api_tester"),
            TranscriptAnalyzer.SYSTEM_PERSONA,
            TrillionaireFuturist.SYSTEM_PERSONA,
            FrameworkTeacher.SYSTEM_PERSONA,
        ]
        for form in persisted_forms:
            assert form.startswith(tuple(LEGACY_PERSONA_PREFIXES))


class TestEvictionInvariants:
    def test_conversation_state_consistent_after_eviction(self, manager, tmp_path):
        hist = tmp_path / "history.json"
        engine_a = _HistoryStubEngine(hist)
        manager.set_current_agent(AgentType.TRANSCRIPT_ANALYZER, chat_engine=engine_a)
        engine_a.conversation.add_message(role="user", content="a question")

        engine_b = _HistoryStubEngine(hist)
        conv = engine_b.conversation
        conv.get_messages()  # populate the OpenAI-format cache pre-eviction
        conv.get_summary()  # populate the summary cache pre-eviction
        manager.set_current_agent(AgentType.FRAMEWORK_TEACHER, chat_engine=engine_b)

        # _total_tokens must equal a fresh recount (no cached .tokens reuse).
        fresh_total = sum(
            Message(role=m.role, content=m.content, tool_calls=m.tool_calls)
            .get_token_count(conv.encoding)
            for m in conv.messages
        )
        assert conv._total_tokens == fresh_total

        # _role_counts must match the message list.
        expected_counts = collections.Counter(m.role for m in conv.messages)
        assert dict(conv._role_counts) == dict(expected_counts)

        # Caches were invalidated: get_messages reflects the removal.
        cached = conv.get_messages()
        assert not any(
            "Transcript Intelligence Analyst" in (m.get("content") or "") for m in cached
        )
        assert conv.get_summary()["total_messages"] == len(conv.messages)

        # Persisted messages retain their token counts.
        data = json.loads(hist.read_text())
        assert data["messages"]
        assert all(m.get("tokens") is not None for m in data["messages"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
