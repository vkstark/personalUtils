#!/usr/bin/env python3
"""
Tests for Settings: new engine knobs, model validation, and the config-block
accessors that wire previously-dead config.yaml sections to runtime behavior.
"""

import pytest
from pydantic import ValidationError

from ChatSystem.core.config import Settings
from ChatSystem.core.chat_engine import ChatEngine


def _settings(**kwargs):
    # Point at a non-existent YAML so accessors return their built-in defaults
    # (decoupled from the repo's actual config.yaml).
    return Settings(openai_api_key="test-key", config_yaml_path="/nonexistent-config.yaml", **kwargs)


class TestSettingsFields:
    def test_new_engine_knobs_have_defaults(self):
        s = _settings()
        assert s.tool_timeout_seconds == 60
        assert s.max_tool_call_depth == 5
        assert s.history_file is None

    def test_gpt5_is_a_valid_model(self):
        assert _settings(model_name="gpt-5").model_name == "gpt-5"

    def test_invalid_model_rejected(self):
        with pytest.raises(ValidationError):
            _settings(model_name="not-a-real-model")


class TestConfigAccessors:
    def test_conversation_config_defaults(self):
        c = _settings().get_conversation_config()
        assert c["auto_summarize_enabled"] is True
        assert c["summarize_threshold"] == 0.85
        assert c["summarize_target_ratio"] == 0.6
        assert c["max_tokens_default"] == 128000

    def test_cli_config_defaults(self):
        c = _settings().get_cli_config()
        assert c["theme"] == "monokai"
        assert c["show_token_usage"] is True
        assert c["show_timestamps"] is True

    def test_agent_config_for_defaults(self):
        a = _settings().get_agent_config_for("task_executor")
        assert a["model"] is None  # no YAML -> agent picks its own tier
        assert a["enable_planning"] is True
        assert "max_iterations" in a
        # Only wired keys are exposed; previously-unused knobs were removed so
        # the config surface reflects what the runtime actually honors.
        assert set(a.keys()) == {"max_iterations", "enable_planning", "model"}

    def test_agent_config_for_rejects_invalid_model(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("agents:\n  task_executor:\n    model: not-a-real-model\n")
        monkeypatch.chdir(tmp_path)
        settings = Settings(openai_api_key="test-key", config_yaml_path=str(cfg))
        with pytest.raises(ValueError, match="not a supported model"):
            settings.get_agent_config_for("task_executor")


class TestReasoningModelDetection:
    def test_gpt5_is_reasoning_style(self):
        assert "gpt-5".startswith(ChatEngine.REASONING_MODELS)

    def test_o3_is_reasoning_style(self):
        assert "o3-mini".startswith(ChatEngine.REASONING_MODELS)

    def test_gpt4o_is_not_reasoning_style(self):
        assert not "gpt-4o".startswith(ChatEngine.REASONING_MODELS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
