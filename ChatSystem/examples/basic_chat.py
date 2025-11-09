#!/usr/bin/env python3
"""
Example: Basic chat interaction without tools
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ChatSystem.core.config import get_settings
from ChatSystem.core.chat_engine import ChatEngine


def main():
    """Simple chat example"""
    print("🤖 Basic Chat Example\n")

    # Initialize chat engine
    settings = get_settings()
    chat_engine = ChatEngine(settings=settings)

    # Simple conversation
    messages = [
        "Hello! Who are you?",
        "What can you help me with?",
        "Tell me a joke about programming",
    ]

    for user_msg in messages:
        print(f"\n👤 User: {user_msg}")
        print("🤖 Assistant: ", end="")

        # Get response (streaming)
        response_parts = []
        for chunk in chat_engine.chat(user_msg, stream=False):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        print()  # New line

    # Show stats
    print("\n" + "="*50)
    print("📊 Statistics:")
    stats = chat_engine.get_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Input tokens: {stats['total_input_tokens']}")
    print(f"Output tokens: {stats['total_output_tokens']}")
    print(f"Total cost: ${stats['total_cost']:.4f}")


if __name__ == "__main__":
    main()
