#!/usr/bin/env python3
"""
Example: Using tools (utilities) via chat
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ChatSystem.core.config import get_settings
from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.tools.tool_registry import ToolRegistry


def main():
    """Tool usage example"""
    print("🛠️  Tool Usage Example\n")

    # Initialize components
    settings = get_settings()
    chat_engine = ChatEngine(settings=settings)

    # Initialize and register tools
    enabled_tools = settings.get_enabled_tools()
    tool_registry = ToolRegistry(enabled_tools=enabled_tools)

    tools = tool_registry.get_tools()
    executor = tool_registry.get_tool_executor()
    chat_engine.register_tools(
        tools,
        executor,
        result_serializer=tool_registry.serialize_result,
    )

    print(f"✓ Loaded {len(tools)} tools\n")

    # Example requests that will use tools
    requests = [
        "Find all duplicate Python files in the current directory",
        "Analyze the code in the ChatSystem/core directory",
        "Extract all TODO comments from the codebase",
    ]

    for request in requests:
        print(f"\n{'='*60}")
        print(f"👤 User: {request}")
        print(f"{'='*60}\n")
        print("🤖 Assistant: ", end="")

        # Get response (stream parameter uses Settings default)
        for chunk in chat_engine.chat(request):
            print(chunk, end="", flush=True)

        print("\n")

    # Show stats
    print(f"\n{'='*60}")
    print("📊 Statistics:")
    stats = chat_engine.get_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Tool calls made: {stats['tool_calls_made']}")
    print(f"Total cost: ${stats['total_cost']:.4f}")


if __name__ == "__main__":
    main()
