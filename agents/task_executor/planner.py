#!/usr/bin/env python3
"""
TaskPlanner - Break down complex tasks into steps

Version 1.2: Enhanced with LLM-backed planning and rich step tracking
"""

import re
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ChatSystem.core.chat_engine import ChatEngine


class TaskStep(BaseModel):
    """
    Represents a single step in a task plan.

    Attributes:
        step_number: Sequential step number
        description: Human-readable description of what this step does
        tool_needed: Name of the tool to execute (if any)
        dependencies: List of step numbers that must complete before this step
        status: Current execution status (pending/running/done/failed/skipped)
        inputs: Input data for this step (from dependencies or user)
        outputs: Output data produced by this step
        result: Execution result from ToolExecutionResult
        error_message: Error message if step failed
    """

    step_number: int
    description: str
    tool_needed: Optional[str] = None
    dependencies: List[int] = Field(default_factory=list)
    status: str = "pending"  # pending, running, done, failed, skipped
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None


class TaskPlan(BaseModel):
    """
    Represents a complete task plan.

    Attributes:
        goal: The high-level goal this plan achieves
        steps: List of TaskStep objects to execute
        current_step: Current step number being executed
        status: Overall plan status (pending/running/done/failed)
        metadata: Additional metadata about the plan
    """

    goal: str
    steps: List[TaskStep]
    current_step: int = 0
    status: str = "pending"  # pending, running, done, failed
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskPlanner:
    """
    Plans multi-step tasks using LLM intelligence.

    Version 1.2: Uses single LLM call to generate structured plans
    with numbered steps, required tools, and dependencies.
    """

    PLANNING_PROMPT = """You are a task planning expert. Break down the following goal into a detailed execution plan.

Goal: {goal}

Available tools:
{available_tools}

Create a numbered plan with the following for each step:
1. Clear description of what needs to be done
2. Which tool to use (if any) - must be from the available tools list
3. Dependencies on previous steps (by step number)

Format your response as a JSON object with this structure:
{{
  "steps": [
    {{
      "step_number": 1,
      "description": "Clear description",
      "tool_needed": "tool_name or null",
      "dependencies": []
    }},
    ...
  ]
}}

Important:
- Be specific and actionable in step descriptions
- Only use tools from the available tools list
- Dependencies should reference step numbers that must complete first
- Keep steps atomic - one clear action per step
- If no tool is needed, set tool_needed to null
"""

    def __init__(self, chat_engine: Optional[ChatEngine] = None):
        """
        Initialize the TaskPlanner.

        Args:
            chat_engine: Optional ChatEngine for LLM-backed planning
        """
        self.plans: List[TaskPlan] = []
        self.chat_engine = chat_engine

    def create_plan(self, goal: str, available_tools: List[str]) -> TaskPlan:
        """
        Create a task plan based on the goal using LLM intelligence.

        This method makes a single LLM call to generate a structured plan
        with numbered steps, required tools, and dependencies.

        Args:
            goal: The high-level task goal
            available_tools: List of available tool names

        Returns:
            TaskPlan object with structured steps
        """

        # If no chat engine, create a simple heuristic plan
        if not self.chat_engine:
            return self._create_simple_plan(goal, available_tools)

        # Format the planning prompt
        tools_list = "\n".join([f"- {tool}" for tool in available_tools])
        prompt = self.PLANNING_PROMPT.format(
            goal=goal,
            available_tools=tools_list
        )

        # Get plan from LLM
        response_parts = []
        for chunk in self.chat_engine.chat(prompt, disable_tools=True):
            response_parts.append(chunk)

        response = "".join(response_parts)

        # Parse the JSON response
        steps = self._parse_plan_response(response, available_tools)

        # Create TaskPlan
        plan = TaskPlan(
            goal=goal,
            steps=steps,
            metadata={
                "planning_method": "llm",
                "available_tools": available_tools,
                "raw_response": response
            }
        )

        self.plans.append(plan)
        return plan

    def _parse_plan_response(self, response: str, available_tools: List[str]) -> List[TaskStep]:
        """
        Parse LLM response into structured TaskStep objects.

        Args:
            response: Raw LLM response
            available_tools: List of valid tool names

        Returns:
            List of TaskStep objects
        """
        steps = []

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())

                for step_data in plan_data.get("steps", []):
                    # Validate tool exists
                    tool_needed = step_data.get("tool_needed")
                    if tool_needed and tool_needed not in available_tools:
                        tool_needed = None

                    step = TaskStep(
                        step_number=step_data.get("step_number", len(steps) + 1),
                        description=step_data.get("description", ""),
                        tool_needed=tool_needed,
                        dependencies=step_data.get("dependencies", []),
                        status="pending"
                    )
                    steps.append(step)

            else:
                # Fallback: parse numbered list format
                steps = self._parse_numbered_list(response, available_tools)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: parse numbered list format
            steps = self._parse_numbered_list(response, available_tools)

        return steps

    def _parse_numbered_list(self, response: str, available_tools: List[str]) -> List[TaskStep]:
        """
        Parse a numbered list format plan.

        Args:
            response: Raw LLM response with numbered list
            available_tools: List of valid tool names

        Returns:
            List of TaskStep objects
        """
        steps = []
        lines = response.split('\n')

        for line in lines:
            # Match numbered items: "1. Description" or "1) Description"
            match = re.match(r'^(\d+)[\.\)]\s+(.+)', line.strip())
            if match:
                step_num = int(match.group(1))
                description = match.group(2)

                # Try to detect tool mentions in description
                tool_needed = None
                for tool in available_tools:
                    if tool.lower() in description.lower():
                        tool_needed = tool
                        break

                step = TaskStep(
                    step_number=step_num,
                    description=description,
                    tool_needed=tool_needed,
                    dependencies=[],
                    status="pending"
                )
                steps.append(step)

        return steps

    def _create_simple_plan(self, goal: str, available_tools: List[str]) -> TaskPlan:
        """
        Create a simple single-step plan when no LLM is available.

        Args:
            goal: The task goal
            available_tools: List of available tools

        Returns:
            TaskPlan with a single step
        """
        step = TaskStep(
            step_number=1,
            description=goal,
            tool_needed=None,
            dependencies=[],
            status="pending"
        )

        plan = TaskPlan(
            goal=goal,
            steps=[step],
            metadata={"planning_method": "simple"}
        )

        self.plans.append(plan)
        return plan

    def update_step_status(
        self,
        plan: TaskPlan,
        step_number: int,
        status: str,
        result: Optional[Any] = None,
        error_message: Optional[str] = None
    ):
        """
        Update the status of a step.

        Args:
            plan: The TaskPlan containing the step
            step_number: Step number to update
            status: New status (pending/running/done/failed/skipped)
            result: Optional execution result
            error_message: Optional error message if failed
        """
        for step in plan.steps:
            if step.step_number == step_number:
                step.status = status
                if result is not None:
                    step.result = result
                if error_message is not None:
                    step.error_message = error_message
                break

    def get_next_step(self, plan: TaskPlan) -> Optional[TaskStep]:
        """
        Get the next step to execute based on dependencies.

        Args:
            plan: The TaskPlan to get next step from

        Returns:
            Next TaskStep to execute, or None if no steps available
        """
        for step in plan.steps:
            if step.status == "pending":
                # Check if dependencies are met
                deps_met = all(
                    any(s.step_number == dep and s.status == "done" for s in plan.steps)
                    for dep in step.dependencies
                )

                if deps_met or not step.dependencies:
                    return step

        return None

    def is_plan_complete(self, plan: TaskPlan) -> bool:
        """
        Check if all steps are completed.

        Args:
            plan: The TaskPlan to check

        Returns:
            True if all steps are done, False otherwise
        """
        return all(step.status in ["done", "skipped"] for step in plan.steps)

    def has_failed_steps(self, plan: TaskPlan) -> bool:
        """
        Check if any steps have failed.

        Args:
            plan: The TaskPlan to check

        Returns:
            True if any step failed, False otherwise
        """
        return any(step.status == "failed" for step in plan.steps)

    def get_plan_summary(self, plan: TaskPlan) -> str:
        """
        Get a formatted summary of the plan.

        Args:
            plan: The TaskPlan to summarize

        Returns:
            Formatted string with plan summary
        """
        lines = [f"📋 Task Plan: {plan.goal}", ""]

        for step in plan.steps:
            status_icon = {
                "pending": "⏸️",
                "running": "▶️",
                "done": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(step.status, "❓")

            tool_info = f" [{step.tool_needed}]" if step.tool_needed else ""
            deps_info = f" (deps: {step.dependencies})" if step.dependencies else ""

            lines.append(f"{status_icon} {step.step_number}. {step.description}{tool_info}{deps_info}")

        return "\n".join(lines)
