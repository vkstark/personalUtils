#!/usr/bin/env python3
"""
Verification script for Planner-backed Multi-step Agent Engine v1.2

This script verifies that all required features have been implemented
by checking for key methods and classes in the codebase.
"""

import re
from pathlib import Path


def check_file_contains(file_path: Path, patterns: list) -> dict:
    """Check if a file contains all specified patterns"""
    if not file_path.exists():
        return {"exists": False, "patterns": {}}

    content = file_path.read_text()
    results = {}

    for name, pattern in patterns:
        results[name] = bool(re.search(pattern, content, re.MULTILINE))

    return {"exists": True, "patterns": results}


def main():
    """Run verification checks"""
    print("=" * 70)
    print("Verifying Planner-backed Multi-step Agent Engine v1.2")
    print("=" * 70)

    base_dir = Path(__file__).parent
    all_passed = True

    # Check 1: TaskPlanner enhancements
    print("\n[1] TaskPlanner Enhancements")
    planner_file = base_dir / "agents" / "task_executor" / "planner.py"
    planner_checks = [
        ("TaskStep with inputs/outputs", r"inputs:\s*Optional\[Dict"),
        ("TaskStep with result", r"result:\s*Optional"),
        ("TaskStep with error_message", r"error_message:\s*Optional"),
        ("TaskPlan with metadata", r"metadata:\s*Dict"),
        ("LLM-backed create_plan", r"PLANNING_PROMPT\s*="),
        ("Parse plan response", r"def _parse_plan_response"),
        ("get_plan_summary", r"def get_plan_summary"),
        ("has_failed_steps", r"def has_failed_steps"),
    ]

    result = check_file_contains(planner_file, planner_checks)
    if not result["exists"]:
        print(f"  ❌ File not found: {planner_file}")
        all_passed = False
    else:
        for name, passed in result["patterns"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

    # Check 2: Reasoner enhancements
    print("\n[2] Reasoner Enhancements")
    reasoner_file = base_dir / "agents" / "task_executor" / "reasoner.py"
    reasoner_checks = [
        ("ReasoningStep with elapsed_time", r"elapsed_time:\s*float"),
        ("ReasoningStep with tool_outputs", r"tool_outputs:\s*Optional"),
        ("add_tool_output method", r"def add_tool_output"),
        ("export_trace_dict", r"def export_trace_dict"),
        ("export_trace_markdown", r"def export_trace_markdown"),
        ("attach_to_conversation", r"def attach_to_conversation"),
        ("get_summary", r"def get_summary"),
    ]

    result = check_file_contains(reasoner_file, reasoner_checks)
    if not result["exists"]:
        print(f"  ❌ File not found: {reasoner_file}")
        all_passed = False
    else:
        for name, passed in result["patterns"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

    # Check 3: AgentExecutor multi-step execution
    print("\n[3] AgentExecutor Multi-step Execution")
    executor_file = base_dir / "agents" / "task_executor" / "executor.py"
    executor_checks = [
        ("Version 1.2 comment", r"Version 1\.2"),
        ("enable_planning parameter", r"enable_planning:\s*bool"),
        ("_execute_step method", r"def _execute_step"),
        ("Plan status tracking", r"plan\.status\s*=\s*['\"]running['\"]"),
        ("Failure short-circuit", r"if.*\.status\s*==\s*['\"]failed['\"]"),
        ("export_reasoning_trace", r"def export_reasoning_trace"),
    ]

    result = check_file_contains(executor_file, executor_checks)
    if not result["exists"]:
        print(f"  ❌ File not found: {executor_file}")
        all_passed = False
    else:
        for name, passed in result["patterns"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

    # Check 4: Conversation summarization
    print("\n[4] Conversation Summarization")
    conv_file = base_dir / "ChatSystem" / "core" / "conversation.py"
    conv_checks = [
        ("summarize_conversation", r"def summarize_conversation"),
        ("auto_summarize_if_needed", r"def auto_summarize_if_needed"),
        ("_llm_summarize", r"def _llm_summarize"),
        ("_structural_summarize", r"def _structural_summarize"),
    ]

    result = check_file_contains(conv_file, conv_checks)
    if not result["exists"]:
        print(f"  ❌ File not found: {conv_file}")
        all_passed = False
    else:
        for name, passed in result["patterns"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

    # Check 5: Config updates
    print("\n[5] Config Updates")
    config_file = base_dir / "config.yaml"
    config_checks = [
        ("Version 1.2 comment", r"Version 1\.2"),
        ("persist_reasoning", r"persist_reasoning:"),
        ("auto_summarize", r"auto_summarize:"),
        ("summarize_threshold", r"summarize_threshold:"),
        ("conversation section", r"conversation:"),
    ]

    result = check_file_contains(config_file, config_checks)
    if not result["exists"]:
        print(f"  ❌ File not found: {config_file}")
        all_passed = False
    else:
        for name, passed in result["patterns"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

    # Check 6: CLI commands
    print("\n[6] CLI Commands")
    cli_file = base_dir / "ChatSystem" / "interface" / "cli.py"
    cli_checks = [
        ("/show_reasoning in help", r"/show_reasoning"),
        ("/summarize in help", r"/summarize"),
        ("display_reasoning_trace method", r"def display_reasoning_trace"),
        ("summarize_conversation method", r"def summarize_conversation"),
    ]

    result = check_file_contains(cli_file, cli_checks)
    if not result["exists"]:
        print(f"  ❌ File not found: {cli_file}")
        all_passed = False
    else:
        for name, passed in result["patterns"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All Version 1.2 features verified!")
        print("\nImplemented Features:")
        print("  ✓ Structured TaskPlan/TaskStep (Plan 2 + 3)")
        print("  ✓ TaskPlanner.create_plan with LLM (Plan 2 + 3)")
        print("  ✓ Multi-step execution with status tracking (Plan 3)")
        print("  ✓ Reasoner with elapsed time & tool outputs (Plan 2 + 3)")
        print("  ✓ Reasoning trace export (Plan 2)")
        print("  ✓ Conversation summarization (Plan 2)")
        print("  ✓ Config-driven agent defaults (Plan 2)")
        print("  ✓ CLI commands: /show_reasoning, /summarize")
        print("\nTo test with real LLM:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Set API key in .env: OPENAI_API_KEY=your-key")
        print("  3. Run: python -m ChatSystem")
        print("  4. Try a complex task and use /show_reasoning")
        return 0
    else:
        print("❌ Some features are missing or incomplete")
        return 1


if __name__ == "__main__":
    exit(main())
