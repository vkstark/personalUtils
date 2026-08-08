#!/usr/bin/env python3
"""
Tests for ConversationManager.remove_system_messages_by_prefix — the persona
eviction mutator. Verifies prefix-based removal is limited to system messages,
returns the removed count, and keeps the token / role-count / cache invariants
consistent (rebuilt via _reset_state + one save, not hand-maintained caches).
"""

import collections
import json

import pytest

from ChatSystem.core.conversation import ConversationManager, Message


def _make_conv(**kwargs):
    kwargs.setdefault("model", "gpt-4o")
    kwargs.setdefault("auto_save", False)
    return ConversationManager(**kwargs)


def test_removes_only_matching_system_messages():
    conv = _make_conv()
    conv.add_message(role="system", content="[Agent Persona: a]\npersona text")
    conv.add_message(role="system", content="unrelated system note")
    conv.add_message(role="user", content="hi")

    removed = conv.remove_system_messages_by_prefix(("[Agent Persona:",))

    assert removed == 1
    contents = [m.content for m in conv.messages]
    assert "[Agent Persona: a]\npersona text" not in contents
    assert "unrelated system note" in contents
    assert "hi" in contents


def test_no_match_returns_zero_and_leaves_messages():
    conv = _make_conv()
    conv.add_message(role="user", content="hi")
    before = list(conv.messages)

    assert conv.remove_system_messages_by_prefix(("[Agent Persona:",)) == 0
    assert conv.messages == before


def test_user_message_with_matching_prefix_survives():
    conv = _make_conv()
    conv.add_message(role="user", content="[Agent Persona: a] quoted by the user")

    assert conv.remove_system_messages_by_prefix(("[Agent Persona:",)) == 0
    assert any(
        m.content == "[Agent Persona: a] quoted by the user" for m in conv.messages
    )


def test_state_and_caches_consistent_after_removal():
    conv = _make_conv()
    conv.add_message(role="system", content="[Agent Persona: a]\npersona text")
    conv.add_message(role="user", content="a question with several words")
    conv.get_messages()  # populate the OpenAI-format cache
    conv.get_summary()  # populate the summary cache

    conv.remove_system_messages_by_prefix(("[Agent Persona:",))

    fresh_total = sum(
        Message(role=m.role, content=m.content, tool_calls=m.tool_calls)
        .get_token_count(conv.encoding)
        for m in conv.messages
    )
    assert conv._total_tokens == fresh_total
    assert dict(conv._role_counts) == dict(
        collections.Counter(m.role for m in conv.messages)
    )
    assert not any(
        (m.get("content") or "").startswith("[Agent Persona:")
        for m in conv.get_messages()
    )
    assert conv.get_summary()["total_messages"] == len(conv.messages)


def test_persisted_history_after_removal_retains_tokens(tmp_path):
    hist = tmp_path / "history.json"
    conv = _make_conv(auto_save=True, history_file=str(hist))
    conv.add_message(role="system", content="[Agent Persona: a]\npersona text")
    conv.add_message(role="user", content="hi")

    conv.remove_system_messages_by_prefix(("[Agent Persona:",))

    data = json.loads(hist.read_text())
    contents = [m.get("content") for m in data["messages"]]
    assert not any((c or "").startswith("[Agent Persona:") for c in contents)
    assert data["messages"]
    assert all(m.get("tokens") is not None for m in data["messages"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
