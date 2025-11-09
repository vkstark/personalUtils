#!/usr/bin/env python3
"""
TaskPlanner - Break down complex tasks into steps
"""

from typing import List, Optional
from pydantic import BaseModel


class TaskStep(BaseModel):
    """Represents a single step in a task plan"""

    step_number: int
    description: str
    tool_needed: Optional[str] = None
    dependencies: List[int] = []
    status: str = "pending"  # pending, in_progress, completed, failed


class TaskPlan(BaseModel):
    """Represents a complete task plan"""

    goal: str
    steps: List[TaskStep]
    current_step: int = 0
    status: str = "pending"


class TaskPlanner:
    """Plans multi-step tasks"""

    def __init__(self):
        self.plans: List[TaskPlan] = []

    def create_plan(self, goal: str, available_tools: List[str]) -> TaskPlan:
        """Create a task plan based on the goal"""

        # This is a simplified planner
        # In production, you'd use the LLM to generate the plan

        steps = []

        # Analyze goal and create steps
        # This is where you'd use GPT to intelligently plan

        plan = TaskPlan(
            goal=goal,
            steps=steps
        )

        self.plans.append(plan)
        return plan

    def update_step_status(self, plan: TaskPlan, step_number: int, status: str):
        """Update the status of a step"""
        for step in plan.steps:
            if step.step_number == step_number:
                step.status = status
                break

    def get_next_step(self, plan: TaskPlan) -> Optional[TaskStep]:
        """Get the next step to execute"""
        for step in plan.steps:
            if step.status == "pending":
                # Check if dependencies are met
                deps_met = all(
                    any(s.step_number == dep and s.status == "completed" for s in plan.steps)
                    for dep in step.dependencies
                )

                if deps_met or not step.dependencies:
                    return step

        return None

    def is_plan_complete(self, plan: TaskPlan) -> bool:
        """Check if all steps are completed"""
        return all(step.status == "completed" for step in plan.steps)
