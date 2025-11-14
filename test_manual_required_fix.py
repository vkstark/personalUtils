#!/usr/bin/env python3
"""
Test P1 Bug Fix: MANUAL_REQUIRED status preserves messages

Verifies that tools returning MANUAL_REQUIRED show the actual
instruction message instead of "Unknown error".
"""

from ChatSystem.tools.tool_executor import ToolExecutor
from ChatSystem.tools.tool_result import ToolStatus

def test_bulk_rename_manual_required():
    """Test that BulkRename shows instruction message, not 'Unknown error'"""
    print("=" * 70)
    print("P1 Bug Fix Test: MANUAL_REQUIRED Message Preservation")
    print("=" * 70)

    executor = ToolExecutor()

    # Execute BulkRename (should return MANUAL_REQUIRED)
    print("\n1. Executing bulk_rename_files...")
    result = executor.execute("bulk_rename_files", {
        "path": "/tmp",
        "pattern": "*.txt",
        "replacement": "renamed",
        "dry_run": True
    })

    print(f"   Status: {result.status}")
    print(f"   Tool: {result.tool_name}")
    print(f"   Duration: {result.duration:.3f}s")

    # Check status
    assert result.status == ToolStatus.MANUAL_REQUIRED, \
        f"Expected MANUAL_REQUIRED, got {result.status}"
    print("   ✓ Status is MANUAL_REQUIRED")

    # Check stdout has the message
    assert result.stdout is not None, "stdout should not be None"
    print(f"   ✓ stdout contains message: {result.stdout[:50]}...")

    # Convert to legacy format (this is what ChatEngine uses)
    print("\n2. Converting to legacy dict format...")
    legacy = result.to_legacy_dict()

    print(f"   success: {legacy['success']}")
    print(f"   error: {legacy['error']}")
    print(f"   status: {legacy.get('status', 'N/A')}")
    print(f"   requires_manual_action: {legacy.get('requires_manual_action', False)}")

    # CRITICAL: error field should NOT be "Unknown error"
    assert legacy["error"] != "Unknown error", \
        "❌ BUG: Manual message lost! Got 'Unknown error'"
    print("   ✓ Error message is NOT 'Unknown error'")

    assert "BulkRename" in legacy["error"] or "interactive" in legacy["error"], \
        f"Message should mention tool or action, got: {legacy['error']}"
    print("   ✓ Error message contains instruction")

    assert legacy.get("requires_manual_action") is True, \
        "Should flag that manual action is required"
    print("   ✓ requires_manual_action flag is set")

    # Test EnvManager as well
    print("\n3. Testing EnvManager (another MANUAL_REQUIRED tool)...")
    result2 = executor.execute("manage_env_files", {
        "action": "validate",
        "file_path": ".env"
    })

    print(f"   Status: {result2.status}")
    legacy2 = result2.to_legacy_dict()
    print(f"   Error: {legacy2['error']}")

    assert legacy2["error"] != "Unknown error", \
        "❌ BUG: EnvManager message lost!"
    print("   ✓ EnvManager message preserved")

    print("\n" + "=" * 70)
    print("✅ P1 BUG FIX VERIFIED!")
    print("=" * 70)
    print("\nBefore fix: MANUAL_REQUIRED tools showed 'Unknown error'")
    print("After fix:  MANUAL_REQUIRED tools show actual instruction messages")
    print("\nImpact: Users can now see what manual action they need to take.")
    print("=" * 70)

if __name__ == "__main__":
    test_bulk_rename_manual_required()
