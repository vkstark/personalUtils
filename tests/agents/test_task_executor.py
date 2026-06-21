#!/usr/bin/env python3
"""
Unit tests for the agent execution engine: TaskPlanner, Reasoner, AgentExecutor.

Consolidated into hermetic pytest form. LLM interactions use a fake chat engine
that yields canned responses, so nothing here touches the OpenAI API.
"""

import pytest

from ChatSystem.core.conversation import ConversationManager
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus
from agents.task_executor.planner import TaskPlanner, TaskPlan, TaskStep
from agents.task_executor.reasoner import Reasoner
from agents.task_executor.executor import AgentExecutor


class _FakeEngine:
    """Minimal hermetic stand-in for ChatEngine (no OpenAI client)."""

    def __init__(self, responses=None, tools=None):
        self.conversation = ConversationManager(model="gpt-4o", auto_save=False)
        self.tools = tools or []
        self._responses = list(responses or [])
        self.prompts = []

    def chat(self, prompt, **kwargs):
        self.prompts.append(prompt)
        yield self._responses.pop(0) if self._responses else "ok"


class TestTaskPlanModels:
    """TaskStep / TaskPlan Pydantic models."""

    def test_taskstep_defaults(self):
        step = TaskStep(step_number=1, description="do x")
        assert step.status == "pending"
        assert step.dependencies == []
        assert step.tool_needed is None

    def test_taskstep_with_dependencies(self):
        step = TaskStep(step_number=3, description="z", dependencies=[1, 2])
        assert step.dependencies == [1, 2]

    def test_taskplan_holds_steps(self):
        plan = TaskPlan(goal="g", steps=[TaskStep(step_number=1, description="a")])
        assert plan.goal == "g"
        assert plan.status == "pending"
        assert len(plan.steps) == 1


class TestTaskPlanner:
    """Planning, status transitions, dependency ordering, completion."""

    def test_simple_plan_without_engine(self):
        plan = TaskPlanner().create_plan("My goal", [])
        assert plan.metadata["planning_method"] == "simple"
        assert len(plan.steps) == 1
        assert plan.steps[0].description == "My goal"

    def test_update_step_status_transitions(self):
        planner = TaskPlanner()
        plan = TaskPlan(goal="g", steps=[TaskStep(step_number=1, description="a")])
        planner.update_step_status(plan, 1, "running")
        assert plan.steps[0].status == "running"
        planner.update_step_status(plan, 1, "done", result="r")
        assert plan.steps[0].status == "done"
        assert plan.steps[0].result == "r"

    def test_get_next_step_respects_dependencies(self):
        planner = TaskPlanner()
        plan = TaskPlan(goal="g", steps=[
            TaskStep(step_number=1, description="a"),
            TaskStep(step_number=2, description="b", dependencies=[1]),
        ])
        assert planner.get_next_step(plan).step_number == 1
        planner.update_step_status(plan, 1, "done")
        assert planner.get_next_step(plan).step_number == 2

    def test_get_next_step_blocks_until_dependency_done(self):
        planner = TaskPlanner()
        plan = TaskPlan(goal="g", steps=[
            TaskStep(step_number=1, description="a", status="running"),
            TaskStep(step_number=2, description="b", dependencies=[1]),
        ])
        # step 1 is not pending and not done; step 2's dependency is unmet
        assert planner.get_next_step(plan) is None

    def test_is_plan_complete_with_done_and_skipped(self):
        planner = TaskPlanner()
        plan = TaskPlan(goal="g", steps=[
            TaskStep(step_number=1, description="a", status="done"),
            TaskStep(step_number=2, description="b", status="skipped"),
        ])
        assert planner.is_plan_complete(plan) is True

    def test_is_plan_complete_false_when_pending(self):
        planner = TaskPlanner()
        plan = TaskPlan(goal="g", steps=[TaskStep(step_number=1, description="a")])
        assert planner.is_plan_complete(plan) is False

    def test_has_failed_steps(self):
        planner = TaskPlanner()
        plan = TaskPlan(goal="g", steps=[TaskStep(step_number=1, description="a", status="failed")])
        assert planner.has_failed_steps(plan) is True

    def test_create_plan_llm_json(self):
        plan_json = (
            '{"steps": [{"step_number": 1, "description": "Analyze code", '
            '"tool_needed": "CodeWhisper", "dependencies": []}]}'
        )
        planner = TaskPlanner(chat_engine=_FakeEngine(responses=[plan_json]))
        plan = planner.create_plan("Analyze", ["CodeWhisper"])
        assert plan.metadata["planning_method"] == "llm"
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_needed == "CodeWhisper"

    def test_create_plan_drops_unknown_tool(self):
        plan_json = (
            '{"steps": [{"step_number": 1, "description": "x", '
            '"tool_needed": "NotATool", "dependencies": []}]}'
        )
        planner = TaskPlanner(chat_engine=_FakeEngine(responses=[plan_json]))
        plan = planner.create_plan("x", ["CodeWhisper"])
        assert plan.steps[0].tool_needed is None

    def test_create_plan_fallback_to_numbered_list(self):
        text = "1. First do this\n2. Then do that"
        planner = TaskPlanner(chat_engine=_FakeEngine(responses=[text]))
        plan = planner.create_plan("x", [])
        assert len(plan.steps) == 2
        assert plan.steps[0].step_number == 1


class TestReasoner:
    """Chain-of-thought tracking and trace export."""

    def test_add_thought_creates_step(self):
        r = Reasoner()
        r.add_thought("thinking")
        assert len(r.reasoning_chain) == 1
        assert r.reasoning_chain[0].thought == "thinking"

    def test_action_and_observation_append_to_current_step(self):
        r = Reasoner()
        r.add_thought("t")
        r.add_action("a")
        r.add_observation("o")
        assert r.reasoning_chain[-1].action == "a"
        assert r.reasoning_chain[-1].observation == "o"

    def test_add_tool_output_serializes_result(self):
        r = Reasoner()
        r.add_thought("t")
        res = ToolExecutionResult(status=ToolStatus.SUCCESS, duration=0.1, tool_name="x")
        r.add_tool_output("x", res)
        assert isinstance(r.reasoning_chain[-1].tool_outputs["x"], dict)

    def test_export_trace_dict_structure(self):
        r = Reasoner()
        r.add_thought("t1")
        r.add_thought("t2")
        d = r.export_trace_dict()
        assert d["total_steps"] == 2
        assert len(d["reasoning_trace"]) == 2
        assert "total_time" in d
        assert "exported_at" in d

    def test_export_trace_markdown_has_headers(self):
        r = Reasoner()
        r.add_thought("my thought")
        md = r.export_trace_markdown()
        assert "# Reasoning Trace" in md
        assert "my thought" in md

    def test_get_summary_counts(self):
        r = Reasoner()
        r.add_thought("t1")
        r.add_action("a")
        r.add_thought("t2")
        summary = r.get_summary()
        assert summary["total_steps"] == 2
        assert summary["steps_with_actions"] == 1

    def test_clear_resets_chain(self):
        r = Reasoner()
        r.add_thought("t")
        r.clear()
        assert r.reasoning_chain == []


class TestAgentExecutorRouting:
    """_needs_planning heuristic and execute_task single/multi routing."""

    def test_needs_planning_detects_keywords(self):
        ex = AgentExecutor(chat_engine=_FakeEngine())
        assert ex._needs_planning("do this and then that") is True
        assert ex._needs_planning("analyze all the files") is True

    def test_needs_planning_false_for_simple_request(self):
        ex = AgentExecutor(chat_engine=_FakeEngine())
        assert ex._needs_planning("hello there") is False

    def test_needs_planning_case_insensitive(self):
        ex = AgentExecutor(chat_engine=_FakeEngine())
        assert ex._needs_planning("FIRST do X") is True

    def test_execute_task_single_step_returns_response(self):
        ex = AgentExecutor(chat_engine=_FakeEngine(responses=["the answer"]))
        result = ex.execute_task("say hi", use_planning=False)
        assert "the answer" in result

    def test_execute_task_multi_step_builds_and_runs_plan(self):
        plan_json = (
            '{"steps": [{"step_number": 1, "description": "Step one", '
            '"tool_needed": null, "dependencies": []}]}'
        )
        ex = AgentExecutor(chat_engine=_FakeEngine(responses=[plan_json, "did step one"]))
        result = ex.execute_task("anything", use_planning=True)
        assert "Task Plan" in result
        assert "completed" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
