#!/usr/bin/env python3
"""
ToolRegistry - Register and manage available tools
"""

from typing import List, Dict, Any, Optional, Callable

from .tool_adapter import ToolAdapter
from .tool_executor import ToolExecutor


class ToolRegistry:
    """
    Manages the registration and execution of tools available to the ChatSystem.

    This class acts as a central point for accessing tool definitions and
    executing them. It uses a `ToolAdapter` to get the OpenAI-compatible
    schemas and a `ToolExecutor` to run the tools.

    Attributes:
        utils_dir (Optional[str]): The directory where the utility tools are located.
        executor (ToolExecutor): An instance of the tool executor.
        adapter (ToolAdapter): An instance of the tool adapter.
        enabled_tools (List[str]): A list of the names of the enabled tools.
        tools (List[Dict[str, Any]]): A list of the OpenAI-formatted
            definitions for the enabled tools.
    """

    def __init__(self, utils_dir: Optional[str] = None, enabled_tools: Optional[List[str]] = None):
        """
        Initializes the ToolRegistry.

        Args:
            utils_dir (Optional[str], optional): The directory containing the
                utility tools. Defaults to None.
            enabled_tools (Optional[List[str]], optional): A list of tool names
                to enable. If None, all tools are enabled. Defaults to None.
        """
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
        """
        Gets the OpenAI-formatted definitions for all enabled tools.

        Returns:
            List[Dict[str, Any]]: A list of tool definitions.
        """
        return self.tools

    def execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a tool by its function name with the given arguments.

        Args:
            function_name (str): The name of the function to execute.
            arguments (Dict[str, Any]): The arguments for the function.

        Returns:
            Dict[str, Any]: The result of the tool's execution.
        """
        return self.executor.execute(function_name, arguments)

    def get_tool_executor(self) -> Callable:
        """
        Returns the executor function.

        This method provides a direct reference to the `execute` method of the
        `ToolExecutor`, which can be passed to the `ChatEngine` for handling
        tool calls.

        Returns:
            Callable: The tool execution function.
        """
        return self.executor.execute

    def list_available_tools(self) -> List[str]:
        """
        Lists the names of all enabled tools.

        Returns:
            List[str]: A list of the function names of the enabled tools.
        """
        return [tool["function"]["name"] for tool in self.tools]

    def get_tool_description(self, function_name: str) -> Optional[str]:
        """
        Gets the description of a specific tool.

        Args:
            function_name (str): The name of the tool's function.

        Returns:
            Optional[str]: The description of the tool, or None if the tool
            is not found.
        """
        for tool in self.tools:
            if tool["function"]["name"] == function_name:
                return tool["function"]["description"]
        return None
