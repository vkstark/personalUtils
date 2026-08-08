#!/usr/bin/env python3
"""
Tests for the Item-5 core robustness batch:
- atomic history writes (temp file + fsync + os.replace, failure cleanup)
- rolling summarization (single summary message, commit-only-if-smaller,
  honest Optional[str] return propagated through the auto-summarize wrappers)
- get_summary cache-miss path returning a copy
"""

import collections
import json
import stat

import pytest

from ChatSystem.core import conversation as conversation_module
from ChatSystem.core.conversation import ConversationManager


SUMMARY_PREFIX = "[Conversation Summary -"


def _fresh_recount(conv):
    """Recount tokens/roles from scratch, bypassing the cached tokens fields."""
    total = 0
    counts = collections.defaultdict(int)
    for msg in conv.messages:
        clone = msg.model_copy(update={"tokens": None})
        total += clone.get_token_count(conv.encoding)
        counts[msg.role] += 1
    return total, dict(counts)


class TestAtomicHistoryWrites:
    """5a: _save_history writes via mkstemp + fsync + os.replace."""

    def test_save_writes_content_mode_0600_no_temp_left(self, tmp_path):
        path = tmp_path / "hist.json"
        conv = ConversationManager(
            model="gpt-4o", history_file=str(path), auto_save=True
        )
        conv.add_message(role="user", content="hello atomic world")

        data = json.loads(path.read_text())
        assert any(
            m.get("content") == "hello atomic world" for m in data["messages"]
        )
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        # No stray temp files left behind next to the live file
        assert [p.name for p in tmp_path.iterdir()] == ["hist.json"]

    def test_failed_save_leaves_live_file_intact_and_cleans_temp(
        self, tmp_path, monkeypatch
    ):
        path = tmp_path / "hist.json"
        conv = ConversationManager(
            model="gpt-4o", history_file=str(path), auto_save=True
        )
        conv.add_message(role="user", content="survives the crash")
        original = path.read_text()

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(conversation_module.json, "dump", boom)
        # Save fails (swallowed warning) — the live file must be untouched
        conv.add_message(role="user", content="lost message")
        monkeypatch.undo()

        assert path.read_text() == original
        json.loads(path.read_text())  # still parseable
        assert [p.name for p in tmp_path.iterdir()] == ["hist.json"]


class TestRollingSummary:
    """5b: single rolling summary, commit-only-if-smaller, honest returns."""

    def test_repeated_auto_summarize_converges_to_single_summary(self):
        conv = ConversationManager(
            model="gpt-4o",
            max_tokens=400,
            auto_save=False,
            auto_summarize_enabled=True,
            summarize_threshold=0.5,
            summarize_target_ratio=0.5,
        )
        for i in range(30):
            conv.add_message(
                role="user", content=f"user message {i} with several words here"
            )
            conv.add_message(
                role="assistant", content=f"assistant reply {i} with content"
            )
            before = conv.count_tokens()
            did = conv.maybe_auto_summarize()  # structural (no LLM)
            after = conv.count_tokens()
            if did:
                # Commit-only-if-smaller: a performed summarize must shrink
                assert after < before
            else:
                assert after == before

        summaries = [
            m for m in conv.messages
            if m.role == "system"
            and (m.content or "").startswith(SUMMARY_PREFIX)
        ]
        assert len(summaries) <= 1

    def test_too_short_returns_none(self):
        conv = ConversationManager(model="gpt-4o", auto_save=False)
        conv.add_message(role="user", content="hi")
        assert conv.summarize_conversation() is None

    def test_zero_compression_window_returns_none_and_reports_false(self):
        # All non-system messages except the first are tool responses, so the
        # orphan-tools walk consumes the entire compression window.
        conv = ConversationManager(
            model="gpt-4o", max_tokens=400, auto_save=False
        )
        conv.add_message(
            role="assistant",
            content=None,
            tool_calls=[{
                "id": "c1", "type": "function",
                "function": {"name": "t", "arguments": "{}"},
            }],
        )
        for i in range(6):
            conv.add_message(
                role="tool", content=f"tool result {i}", tool_call_id="c1"
            )
        before_messages = list(conv.messages)
        before_tokens = conv.count_tokens()

        assert conv.summarize_conversation() is None
        assert conv.messages == before_messages
        assert conv.count_tokens() == before_tokens
        # The wrapper must propagate the miss instead of reporting success
        assert conv.auto_summarize_if_needed(threshold=0.0) is False

    def test_candidate_not_smaller_leaves_state_unmutated(self):
        # Tiny messages: the structural summary is larger than the two
        # messages it would replace, so nothing must be committed.
        conv = ConversationManager(
            model="gpt-4o", max_tokens=100000, auto_save=False
        )
        for _ in range(5):
            conv.add_message(role="user", content="a")
        before_messages = list(conv.messages)
        before_tokens = conv.count_tokens()

        assert conv.summarize_conversation() is None
        assert conv.messages == before_messages
        assert conv.count_tokens() == before_tokens
        assert not any(
            (m.content or "").startswith(SUMMARY_PREFIX) for m in conv.messages
        )

    def test_committed_summarize_invariants(self):
        conv = ConversationManager(
            model="gpt-4o", max_tokens=100000, auto_save=False
        )
        for i in range(10):
            conv.add_message(
                role="user", content=f"user message {i} " + "filler words " * 10
            )
            conv.add_message(
                role="assistant", content=f"reply {i} " + "more filler " * 10
            )
        conv.get_messages()  # populate caches pre-summarize
        conv.get_summary()

        result = conv.summarize_conversation()

        assert result is not None
        total, counts = _fresh_recount(conv)
        assert conv.count_tokens() == total
        assert dict(conv._role_counts) == counts
        # Caches invalidated: get_messages reflects the replacement
        assert len(conv.get_messages()) == len(conv.messages)
        assert conv.get_summary()["total_messages"] == len(conv.messages)
        summaries = [
            m for m in conv.messages
            if (m.content or "").startswith(SUMMARY_PREFIX)
        ]
        assert len(summaries) == 1


class TestGetSummaryCopy:
    """5c: the cache-miss path must return a copy of the internal dict."""

    def test_cache_miss_returns_copy(self):
        conv = ConversationManager(model="gpt-4o", auto_save=False)
        first = conv.get_summary()  # miss path (cache just built)
        first["total_messages"] = 999
        assert conv.get_summary()["total_messages"] != 999


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
