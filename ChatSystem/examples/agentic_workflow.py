#!/usr/bin/env python3
"""
Example: Complex agentic workflow with planning
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ChatSystem.core.config import get_settings
from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.tools.tool_registry import ToolRegistry
from agents.task_executor.executor import AgentExecutor


def main():
    """Agentic workflow example"""
    print("🤖 Agentic Workflow Example\n")

    # Initialize components
    settings = get_settings()
    chat_engine = ChatEngine(settings=settings)

    # Register tools
    enabled_tools = settings.get_enabled_tools()
    tool_registry = ToolRegistry(enabled_tools=enabled_tools)

    tools = tool_registry.get_tools()
    executor = tool_registry.get_tool_executor()
    chat_engine.register_tools(
        tools,
        executor,
        result_serializer=tool_registry.serialize_result,
    )

    # Initialize agent
    agent_config = settings.get_agent_config()
    agent = AgentExecutor(
        chat_engine=chat_engine,
        settings=settings,
        max_iterations=agent_config["max_iterations"],
    )

    print(f"✓ Agent initialized with {len(tools)} tools\n")

    # Complex multi-step tasks
    complex_tasks = [
        "First analyze the code structure in ChatSystem/core, then find any duplicate files, and finally extract all TODO comments",
        "Check the ChatSystem directory for Python files and analyze their complexity",
    ]

    for task in complex_tasks:
        print(f"\n{'='*70}")
        print(f"👤 Complex Task: {task}")
        print(f"{'='*70}\n")

        # Execute with agent
        result = agent.execute_task(task)
        print(f"🤖 Agent Result:\n{result}\n")

        # Show reasoning trace
        print("\n🧠 Reasoning Trace:")
        print(agent.get_reasoning_trace())

    # Show final stats
    print(f"\n{'='*70}")
    print("📊 Final Statistics:")
    stats = chat_engine.get_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Tool calls made: {stats['tool_calls_made']}")
    print(f"Input tokens: {stats['total_input_tokens']:,}")
    print(f"Output tokens: {stats['total_output_tokens']:,}")
    print(f"Total cost: ${stats['total_cost']:.4f}")


if __name__ == "__main__":
    main()
