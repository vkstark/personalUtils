#!/usr/bin/env python3
"""
Test to verify system persona is preserved when switching between agents.

This tests the fix for the caching issue where switching agents would
lose the system persona.
"""

from ChatSystem.core.config import get_settings
from ChatSystem.core.chat_engine import ChatEngine
from agents.agent_manager import AgentManager, AgentType


def test_agent_switching():
    """Test that system persona is preserved when switching between agents."""
    print("\n" + "="*80)
    print("Testing Agent Switching - System Persona Preservation")
    print("="*80 + "\n")

    settings = get_settings()
    manager = AgentManager(settings=settings)

    # Step 1: Get Analyzer with engine_A
    print("1. Creating Analyzer with ChatEngine A...")
    engine_a = ChatEngine(settings=settings)
    analyzer_1 = manager.get_agent(AgentType.TRANSCRIPT_ANALYZER, chat_engine=engine_a)

    # Check that system persona was added
    messages_a = analyzer_1.chat_engine.conversation.get_messages()
    persona_in_a = any(msg.get("role") == "system" and "Transcript Intelligence Analyst" in msg.get("content", "")
                       for msg in messages_a)

    print(f"   - Analyzer has system persona: {'✓' if persona_in_a else '✗ FAILED'}")
    print(f"   - Messages in conversation: {len(messages_a)}")

    # Step 2: Get Futurist with engine_B
    print("\n2. Switching to Futurist with ChatEngine B...")
    engine_b = ChatEngine(settings=settings)
    futurist = manager.get_agent(AgentType.TRILLIONAIRE_FUTURIST, chat_engine=engine_b)

    messages_b = futurist.chat_engine.conversation.get_messages()
    persona_in_b = any(msg.get("role") == "system" and "TRILLIONAIRE" in msg.get("content", "")
                       for msg in messages_b)

    print(f"   - Futurist has system persona: {'✓' if persona_in_b else '✗ FAILED'}")
    print(f"   - Messages in conversation: {len(messages_b)}")

    # Step 3: Switch BACK to Analyzer with engine_C (this is the critical test)
    print("\n3. Switching BACK to Analyzer with fresh ChatEngine C...")
    engine_c = ChatEngine(settings=settings)
    analyzer_2 = manager.get_agent(AgentType.TRANSCRIPT_ANALYZER, chat_engine=engine_c)

    # Verify it's the same cached agent instance
    same_instance = analyzer_1 is analyzer_2
    print(f"   - Same agent instance returned: {'✓' if same_instance else '✗ FAILED'}")

    # Verify the chat engine was updated
    engine_updated = analyzer_2.chat_engine is engine_c
    print(f"   - ChatEngine updated to engine_c: {'✓' if engine_updated else '✗ FAILED'}")

    # THE CRITICAL TEST: Verify system persona exists in the new engine
    messages_c = analyzer_2.chat_engine.conversation.get_messages()
    persona_in_c = any(msg.get("role") == "system" and "Transcript Intelligence Analyst" in msg.get("content", "")
                       for msg in messages_c)

    print(f"   - System persona preserved in new engine: {'✓ FIXED' if persona_in_c else '✗ FAILED - PERSONA LOST!'}")
    print(f"   - Messages in conversation: {len(messages_c)}")

    # Print the actual system messages for verification
    print(f"\n   System messages in engine_c:")
    for i, msg in enumerate(messages_c):
        if msg.get("role") == "system":
            content_preview = msg.get("content", "")[:80]
            print(f"     [{i}] {content_preview}...")

    # Summary
    print("\n" + "="*80)
    all_passed = persona_in_a and persona_in_b and same_instance and engine_updated and persona_in_c
    if all_passed:
        print("✓ ALL TESTS PASSED - System persona is correctly preserved!")
    else:
        print("✗ TESTS FAILED - System persona preservation is broken!")
    print("="*80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = test_agent_switching()
    exit(0 if success else 1)
