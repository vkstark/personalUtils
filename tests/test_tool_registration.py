#!/usr/bin/env python3
"""
Registration-Drift Tests for Tool Wiring

The tool integration is static, not discovered: TOOL_DEFINITIONS
(tool_adapter.py, keyed by CamelCase utility name with the OpenAI function
name nested at definition["name"]), function_to_util (tool_executor.py, keyed
by function name), and config.yaml's tools.enabled list are three
hand-maintained pieces that must agree (see CLAUDE.md "To add a tool").
These tests fail loudly when one of them drifts.
"""

import yaml
from pathlib import Path

from ChatSystem.tools.tool_adapter import ToolAdapter
from ChatSystem.tools.tool_executor import ToolExecutor

REPO_ROOT = Path(__file__).parent.parent


class TestToolRegistration:
    """Cross-checks between adapter, executor, and config.yaml"""

    def test_every_definition_has_executor_mapping(self):
        """Every advertised function name must have a function_to_util entry"""
        executor = ToolExecutor()
        for util_name, definition in ToolAdapter.TOOL_DEFINITIONS.items():
            assert definition["name"] in executor.function_to_util, \
                f"{util_name} advertises '{definition['name']}' but the executor cannot run it"

    def test_every_mapped_script_exists(self):
        """Every mapped script path must exist relative to executor.utils_dir"""
        executor = ToolExecutor()
        for function_name, rel_path in executor.function_to_util.items():
            script = executor.utils_dir / rel_path
            assert script.exists(), \
                f"{function_name} maps to a missing script: {script}"

    def test_config_enabled_names_are_known_utils(self):
        """Every config.yaml tools.enabled entry must be a known CamelCase util name"""
        config = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
        enabled = config.get("tools", {}).get("enabled", [])
        for name in enabled:
            assert name in ToolAdapter.TOOL_DEFINITIONS, \
                f"config.yaml tools.enabled entry '{name}' is not a registered utility"
