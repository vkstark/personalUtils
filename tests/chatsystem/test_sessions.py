"""
Tests for named conversation sessions (ChatSystem/core/sessions.py)
"""
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ChatSystem.core import sessions


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Point the sessions module at a temp directory (not created yet)."""
    d = tmp_path / "sessions"
    monkeypatch.setattr(sessions, "SESSIONS_DIR", d)
    return d


class TestSessionNames:
    """Name validation and path mapping"""

    def test_valid_name_maps_into_sessions_dir(self, sessions_dir):
        path = sessions.session_path("work-notes_1")
        assert path == sessions_dir / "work-notes_1.json"

    @pytest.mark.parametrize("bad", ["../evil", "a/b", "", "a b", "x" * 65, "café"])
    def test_invalid_names_rejected(self, sessions_dir, bad):
        with pytest.raises(ValueError):
            sessions.session_path(bad)

    def test_reserved_default_rejected(self, sessions_dir):
        """'default' maps to the legacy history file, never a session file."""
        with pytest.raises(ValueError):
            sessions.session_path("default")


class TestSessionListing:
    """Listing sessions"""

    def test_missing_dir_lists_empty(self, sessions_dir):
        assert sessions.list_sessions() == []

    def test_lists_sorted_json_stems_only(self, sessions_dir):
        sessions_dir.mkdir()
        (sessions_dir / "beta.json").write_text("{}")
        (sessions_dir / "alpha.json").write_text("{}")
        (sessions_dir / "notes.txt").write_text("x")
        (sessions_dir / "adir.json").mkdir()

        assert sessions.list_sessions() == ["alpha", "beta"]


class TestSessionDelete:
    """Deleting sessions"""

    def test_delete_removes_file(self, sessions_dir):
        sessions_dir.mkdir()
        target = sessions_dir / "old.json"
        target.write_text("{}")

        sessions.delete_session("old")

        assert not target.exists()

    def test_delete_missing_raises(self, sessions_dir):
        with pytest.raises(FileNotFoundError):
            sessions.delete_session("ghost")

    def test_delete_directory_raises_not_crashes(self, sessions_dir):
        sessions_dir.mkdir()
        (sessions_dir / "adir.json").mkdir()

        with pytest.raises(FileNotFoundError):
            sessions.delete_session("adir")


class TestSessionPersistence:
    """Session files ride the existing ConversationManager persistence guarantees."""

    def test_messages_persist_across_managers(self, sessions_dir):
        from ChatSystem.core.conversation import ConversationManager

        path = sessions.session_path("persist")
        first = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)
        first.add_message(role="user", content="remember me")

        second = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)

        assert any(
            m.role == "user" and m.content == "remember me" for m in second.messages
        )

    def test_session_file_and_dir_permissions(self, sessions_dir):
        from ChatSystem.core.conversation import ConversationManager

        path = sessions.session_path("private")
        mgr = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)
        mgr.add_message(role="user", content="secret")

        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


class TestHistoryPreservation:
    """Regression: init must not clobber an existing history or duplicate the seed prompt."""

    def test_no_duplicate_system_prompt_on_reload(self, sessions_dir):
        from ChatSystem.core.conversation import ConversationManager

        path = sessions.session_path("clean")
        first = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)
        assert sum(1 for m in first.messages if m.role == "system") == 1

        second = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)
        assert sum(1 for m in second.messages if m.role == "system") == 1

    def test_reload_preserves_full_turn_order(self, sessions_dir):
        from ChatSystem.core.conversation import ConversationManager

        path = sessions.session_path("turns")
        first = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)
        first.add_message(role="user", content="q1")
        first.add_message(role="assistant", content="a1")

        second = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)

        assert [m.role for m in second.messages] == ["system", "user", "assistant"]
        assert [m.content for m in second.messages[1:]] == ["q1", "a1"]

    def test_empty_history_file_still_seeds_system_prompt(self, sessions_dir):
        import json

        from ChatSystem.core.conversation import ConversationManager

        path = sessions.session_path("empty")
        path.parent.mkdir(mode=0o700)
        path.write_text(json.dumps({"model": "gpt-4o", "messages": []}))

        mgr = ConversationManager(model="gpt-4o", history_file=str(path), auto_save=True)

        assert [m.role for m in mgr.messages] == ["system"]


class TestSessionCLI:
    """Hermetic CLI-level tests for the /session command family (no API calls)."""

    @pytest.fixture
    def cli(self, sessions_dir, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from ChatSystem.core import chat_engine as ce

        monkeypatch.setattr(ce, "OpenAI", MagicMock())
        ce.ChatEngine.clear_client_cache()

        from ChatSystem.core.config import Settings
        from ChatSystem.interface.cli import ChatCLI

        settings = Settings(
            openai_api_key="test-key-session-cli",
            history_file=str(tmp_path / "default_history.json"),
        )
        yield ChatCLI(settings=settings)
        ce.ChatEngine.clear_client_cache()

    def test_new_switch_roundtrip_isolates_and_restores(self, cli):
        cli.handle_session_command("new work")
        assert cli.session_name == "work"
        cli.conversation.add_message(role="user", content="project X notes")

        cli.handle_session_command("switch default")
        assert cli.session_name == "default"
        assert not any(
            "project X" in (m.content or "") for m in cli.conversation.messages
        )

        cli.handle_session_command("switch work")
        assert any(
            "project X" in (m.content or "") for m in cli.conversation.messages
        )

    def test_agent_switch_stays_on_session_file(self, cli, sessions_dir):
        cli.handle_session_command("new work")
        cli.switch_agent("teacher")

        assert cli.conversation.history_file == sessions_dir / "work.json"

    def test_delete_active_session_refused_even_case_aliased(self, cli, sessions_dir, monkeypatch):
        cli.handle_session_command("new work")

        from ChatSystem.interface import cli as cli_mod

        monkeypatch.setattr(cli_mod.Confirm, "ask", staticmethod(lambda *a, **k: True))
        cli.handle_session_command("delete WORK")

        assert (sessions_dir / "work.json").exists()
        assert cli.session_name == "work"

    def test_session_commands_refused_without_auto_save(self, cli, sessions_dir):
        cli.conversation.auto_save = False

        cli.handle_session_command("new work")

        assert cli.session_name == "default"
        assert not (sessions_dir / "work.json").exists()

    def test_invalid_name_rejected_at_cli(self, cli, sessions_dir):
        cli.handle_session_command("new ../evil")

        assert cli.session_name == "default"
        assert sessions.list_sessions() == []

    def test_persona_not_duplicated_across_session_roundtrips(self, cli):
        """Regression: each /session reactivation must not append another persona copy."""
        cli.handle_session_command("new work")
        baseline = sum(1 for m in cli.conversation.messages if m.role == "system")

        cli.handle_session_command("switch default")
        cli.handle_session_command("switch work")
        cli.handle_session_command("switch default")
        cli.handle_session_command("switch work")

        assert (
            sum(1 for m in cli.conversation.messages if m.role == "system") == baseline
        )


class TestEnsureSystemMessage:
    """ensure_system_message adds a system message exactly once."""

    def test_second_call_is_noop(self, tmp_path):
        from ChatSystem.core.conversation import ConversationManager

        mgr = ConversationManager(
            model="gpt-4o",
            history_file=str(tmp_path / "h.json"),
            auto_save=False,
        )
        before = len(mgr.messages)

        mgr.ensure_system_message("You are the persona.")
        mgr.ensure_system_message("You are the persona.")

        assert len(mgr.messages) == before + 1

    def test_different_content_still_added(self, tmp_path):
        from ChatSystem.core.conversation import ConversationManager

        mgr = ConversationManager(
            model="gpt-4o",
            history_file=str(tmp_path / "h.json"),
            auto_save=False,
        )
        mgr.ensure_system_message("persona A")
        mgr.ensure_system_message("persona B")

        assert sum(1 for m in mgr.messages if m.content == "persona A") == 1
        assert sum(1 for m in mgr.messages if m.content == "persona B") == 1


class TestTildeExpansion:
    """A ~/… history path must expand to the home directory, not a literal '~' dir."""

    def test_history_file_tilde_expanded(self, tmp_path, monkeypatch):
        from ChatSystem.core.conversation import ConversationManager

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)  # a regression would create ./~ here, not in the repo
        mgr = ConversationManager(
            model="gpt-4o", history_file="~/hist.json", auto_save=True
        )
        mgr.add_message(role="user", content="hi")

        assert mgr.history_file == tmp_path / "hist.json"
        assert (tmp_path / "hist.json").exists()
        assert not (tmp_path / "~").exists()


class TestChatEngineHistoryOverride:
    """ChatEngine(history_file=...) binds its conversation to the session file."""

    def test_history_file_param_overrides_default(self, sessions_dir, monkeypatch):
        from unittest.mock import MagicMock

        from ChatSystem.core import chat_engine as ce
        from ChatSystem.core.config import Settings

        monkeypatch.setattr(ce, "OpenAI", MagicMock())
        ce.ChatEngine.clear_client_cache()
        try:
            path = sessions.session_path("engine")
            engine = ce.ChatEngine(
                settings=Settings(openai_api_key="test-key-sessions"),
                history_file=str(path),
            )
            assert engine.conversation.history_file == path
        finally:
            ce.ChatEngine.clear_client_cache()
