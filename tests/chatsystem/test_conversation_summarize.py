#!/usr/bin/env python3
"""
Tests that the conversation auto-summarization config is actually wired:
`maybe_auto_summarize` honors `auto_summarize_enabled` / `summarize_threshold`
and performs a structural (no-LLM) summary when the threshold is exceeded.
"""

import pytest

from ChatSystem.core.conversation import ConversationManager


def test_maybe_auto_summarize_triggers_structurally():
    conv = ConversationManager(
        model="gpt-4o",
        max_tokens=200,  # tiny window so the threshold is crossed quickly
        auto_save=False,
        auto_summarize_enabled=True,
        summarize_threshold=0.5,
        summarize_target_ratio=0.5,
    )
    for i in range(12):
        conv.add_message(role="user", content=f"message number {i} with several words here")
        conv.add_message(role="assistant", content=f"assistant reply number {i} with content")

    before = len(conv.messages)
    did = conv.maybe_auto_summarize()  # no chat_engine -> structural summary

    assert did is True
    assert len(conv.messages) < before
    assert any("Conversation Summary" in (m.content or "") for m in conv.messages)


def test_maybe_auto_summarize_respects_disabled_flag():
    conv = ConversationManager(
        model="gpt-4o",
        max_tokens=20,
        auto_save=False,
        auto_summarize_enabled=False,  # disabled -> never summarizes
        summarize_threshold=0.1,
    )
    for _ in range(8):
        conv.add_message(role="user", content="x" * 40)

    assert conv.maybe_auto_summarize() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
