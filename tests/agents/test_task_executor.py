#!/usr/bin/env python3
"""
Unit tests for the agent execution engine: TaskPlanner, Reasoner, AgentExecutor.

Consolidated into hermetic pytest form. LLM interactions use a fake chat engine
that yields canned responses, so nothing here touches the OpenAI API.
"""

import json

import pytest

from ChatSystem.core.conversation import ConversationManager, Message
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


class _ToolTurnEngine:
    """
    Fake engine whose step-execution chat() appends a tool-role message with a
    configurable outcome, simulating the engine running a tool internally. The
    first chat() call returns the plan JSON; subsequent calls are step turns.
    """

    def __init__(self, plan_json, tool_payload, preseed_payload=None):
        self.conversation = ConversationManager(model="gpt-4o", auto_save=False)
        self.tools = [{"function": {"name": "CodeWhisper"}}]
        self._plan_json = plan_json
        self._tool_payload = tool_payload
        self._planned = False
        self.prompts = []
        self.step_turns = 0  # count of step-execution chat() calls (post-plan)
        if preseed_payload is not None:
            # A tool message from an EARLIER turn, present before this step runs.
            self.conversation.add_message(
                role="tool",
                content=json.dumps(preseed_payload),
                tool_call_id="old_call",
                name="CodeWhisper",
            )

    def chat(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if not self._planned:
            self._planned = True
            yield self._plan_json
            return
        # Simulate the engine executing a tool during this turn.
        self.step_turns += 1
        self.conversation.add_message(
            role="tool",
            content=json.dumps(self._tool_payload),
            tool_call_id="call_1",
            name="CodeWhisper",
        )
        yield "Tool turn complete."


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

    def test_create_plan_renumbers_duplicate_step_numbers(self):
        # LLM restarts numbering: 1, 2, 1, 3 -> must become unique 1..4
        text = "1. first\n2. second\n1. another first\n3. third"
        planner = TaskPlanner(chat_engine=_FakeEngine(responses=[text]))
        plan = planner.create_plan("x", [])
        assert [s.step_number for s in plan.steps] == [1, 2, 3, 4]

    def test_create_plan_drops_hallucinated_dependency(self):
        plan_json = (
            '{"steps": ['
            '{"step_number": 1, "description": "a", "dependencies": [99]},'
            '{"step_number": 2, "description": "b", "dependencies": [1]}]}'
        )
        planner = TaskPlanner(chat_engine=_FakeEngine(responses=[plan_json]))
        plan = planner.create_plan("x", [])
        assert plan.steps[0].dependencies == []   # dep on non-existent step dropped
        assert plan.steps[1].dependencies == [1]  # real dep preserved

    def test_create_plan_breaks_dependency_cycle(self):
        plan_json = (
            '{"steps": ['
            '{"step_number": 1, "description": "a", "dependencies": [2]},'
            '{"step_number": 2, "description": "b", "dependencies": [1]}]}'
        )
        planner = TaskPlanner(chat_engine=_FakeEngine(responses=[plan_json]))
        plan = planner.create_plan("x", [])
        # forward-only deps break the cycle: step 1 runs first, step 2 depends on it
        assert plan.steps[0].dependencies == []
        assert plan.steps[1].dependencies == [1]


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

    def test_swapping_chat_engine_syncs_planner_engine(self):
        # AgentManager swaps a cached executor's engine on /agent switch; the
        # planner must follow so it doesn't plan against a stale engine.
        e1 = _FakeEngine()
        ex = AgentExecutor(chat_engine=e1)
        assert ex.planner.chat_engine is e1
        e2 = _FakeEngine()
        ex.chat_engine = e2
        assert ex.chat_engine is e2
        assert ex.planner.chat_engine is e2

    def test_execute_task_multi_step_builds_and_runs_plan(self):
        plan_json = (
            '{"steps": [{"step_number": 1, "description": "Step one", '
            '"tool_needed": null, "dependencies": []}]}'
        )
        ex = AgentExecutor(chat_engine=_FakeEngine(responses=[plan_json, "did step one"]))
        result = ex.execute_task("anything", use_planning=True)
        assert "Task Plan" in result
        assert "completed" in result.lower()


class TestStepToolOutcome:
    """Step status must reflect the actual tool execution outcome, not just
    that the LLM produced text."""

    PLAN_JSON = (
        '{"steps": [{"step_number": 1, "description": "Run analysis", '
        '"tool_needed": "CodeWhisper", "dependencies": []}]}'
    )

    def _run(self, tool_payload):
        engine = _ToolTurnEngine(self.PLAN_JSON, tool_payload)
        ex = AgentExecutor(chat_engine=engine)
        ex.execute_task("analyze all the files", use_planning=True)
        return ex.planner.plans[-1]

    def test_tool_error_marks_step_failed(self):
        plan = self._run({"success": False, "error": "boom: tool exploded"})
        assert plan.steps[0].status == "failed"
        assert "boom" in (plan.steps[0].error_message or "")
        assert plan.status == "failed"

    def test_tool_success_marks_step_done(self):
        plan = self._run({"success": True, "result": "analysis complete"})
        assert plan.steps[0].status == "done"
        assert plan.status == "done"

    def test_bare_error_envelope_marks_step_failed(self):
        # The engine writes {"error": ...} (no success key) on arg-parse/exec errors.
        plan = self._run({"error": "Error parsing tool arguments"})
        assert plan.steps[0].status == "failed"

    def test_manual_required_is_not_a_failure(self):
        # manual_required is a deferred-action signal, not an error.
        plan = self._run({
            "success": False,
            "error": "needs interactive input",
            "status": "manual_required",
            "requires_manual_action": True,
        })
        assert plan.steps[0].status == "done"

    def test_step1_tool_failure_halts_dependent_step2(self):
        # The payoff of marking a step "failed": a failed step 1 must stop the
        # multi-step loop so a dependent step 2 never runs.
        plan_json = (
            '{"steps": ['
            '{"step_number": 1, "description": "Run analysis", '
            '"tool_needed": "CodeWhisper", "dependencies": []},'
            '{"step_number": 2, "description": "Use the analysis", '
            '"tool_needed": "CodeWhisper", "dependencies": [1]}]}'
        )
        engine = _ToolTurnEngine(plan_json, {"success": False, "error": "boom"})
        ex = AgentExecutor(chat_engine=engine)
        ex.execute_task("first analyze and then summarize", use_planning=True)
        plan = ex.planner.plans[-1]

        assert plan.steps[0].status == "failed"
        assert plan.steps[1].status == "pending"  # never ran
        assert plan.status == "failed"
        assert engine.step_turns == 1  # only step 1 executed before the halt

    def test_stale_prior_tool_failure_does_not_bleed_into_current_step(self):
        # A failed tool message from an EARLIER turn must not mark this step
        # failed; only tool messages from THIS turn count (prior_ids snapshot).
        engine = _ToolTurnEngine(
            self.PLAN_JSON,
            {"success": True, "result": "fresh analysis ok"},
            preseed_payload={"success": False, "error": "OLD failure"},
        )
        ex = AgentExecutor(chat_engine=engine)
        ex.execute_task("analyze all the files", use_planning=True)
        plan = ex.planner.plans[-1]

        assert plan.steps[0].status == "done"
        assert plan.steps[0].error_message is None


class TestDetectToolFailure:
    """Direct unit coverage of the failure predicate over multiple messages."""

    @staticmethod
    def _tool_msgs(*payloads):
        return [
            Message(role="tool", content=json.dumps(p)) for p in payloads
        ]

    def test_first_failure_is_returned_regardless_of_order(self):
        msgs = self._tool_msgs(
            {"success": True, "result": "ok"},
            {"success": False, "error": "second failed"},
        )
        assert AgentExecutor._detect_tool_failure(msgs) == "second failed"

    def test_failure_before_success_still_fails(self):
        msgs = self._tool_msgs(
            {"success": False, "error": "first failed"},
            {"success": True, "result": "ok"},
        )
        assert AgentExecutor._detect_tool_failure(msgs) == "first failed"

    def test_all_success_returns_none(self):
        msgs = self._tool_msgs({"success": True, "result": "ok"})
        assert AgentExecutor._detect_tool_failure(msgs) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
