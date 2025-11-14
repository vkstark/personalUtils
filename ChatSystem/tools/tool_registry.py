#!/usr/bin/env python3
"""ToolRegistry - Register and manage available tools"""

from typing import List, Dict, Any, Optional, Callable

from .execution_result import ToolExecutionResult
from .tool_adapter import ToolAdapter
from .tool_executor import ToolExecutor


class ToolRegistry:
    """Registry for all available tools"""

    def __init__(self, utils_dir: Optional[str] = None, enabled_tools: Optional[List[str]] = None):
        self.utils_dir = utils_dir
        self.executor = ToolExecutor(utils_dir)
        self.adapter = ToolAdapter()

        # Get enabled tools
        if enabled_tools is None:
            # Enable all tools by default
            self.enabled_tools = list(self.adapter.TOOL_DEFINITIONS.keys())
        else:
            self.enabled_tools = enabled_tools

        # Get tool schemas
        self.tools = self.adapter.get_enabled_tools(self.enabled_tools)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools in OpenAI format"""
        return self.tools

    def execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a tool by function name"""
        return self.executor.execute(function_name, arguments)

    def get_tool_executor(self) -> Callable[[str, Dict[str, Any]], ToolExecutionResult]:
        """Get executor function for ChatEngine"""
        return self.executor.execute

    @staticmethod
    def serialize_result(result: ToolExecutionResult | Dict[str, Any]) -> Dict[str, Any]:
        """Serialize a tool execution result for conversation storage."""

        if isinstance(result, ToolExecutionResult):
            return result.to_dict()
        return result

    @staticmethod
    def to_legacy_payload(result: ToolExecutionResult) -> Dict[str, Any]:
        """Convert a normalized result to the legacy format."""

        return result.to_legacy_response()

    def list_available_tools(self) -> List[str]:
        """List all available tool names"""
        return [tool["function"]["name"] for tool in self.tools]

    def get_tool_description(self, function_name: str) -> Optional[str]:
        """Get description of a specific tool"""
        for tool in self.tools:
            if tool["function"]["name"] == function_name:
                return tool["function"]["description"]
        return None
