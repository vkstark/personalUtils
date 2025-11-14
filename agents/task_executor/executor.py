#!/usr/bin/env python3
"""
AgentExecutor - Execute complex multi-step tasks
"""

from typing import Optional
from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.core.config import Settings
from .planner import TaskPlanner
from .reasoner import Reasoner


class AgentExecutor:
    """Execute multi-step agentic tasks"""

    def __init__(
        self,
        chat_engine: ChatEngine,
        settings: Optional[Settings] = None,
        max_iterations: int = 5,
    ):
        self.chat_engine = chat_engine
        self.settings = settings
        self.max_iterations = max_iterations

        self.planner = TaskPlanner()
        self.reasoner = Reasoner()

    def execute_task(self, user_request: str) -> str:
        """Execute a complex task with planning and reasoning"""

        # Clear previous reasoning
        self.reasoner.clear()

        # Step 1: Understand the task
        self.reasoner.add_thought(f"User wants: {user_request}")

        # Step 2: Determine if planning is needed
        # Get planning decision using simple heuristics

        is_multi_step = self._needs_planning(user_request)

        if is_multi_step:
            self.reasoner.add_action("Creating multi-step plan")
            return self._execute_multi_step(user_request)
        else:
            self.reasoner.add_action("Executing single-step task")
            return self._execute_single_step(user_request)

    def _needs_planning(self, request: str) -> bool:
        """Simple heuristic to determine if planning is needed"""
        multi_step_keywords = [
            "and then", "after", "first", "second", "finally",
            "multiple", "all", "each", "every",
            "analyze and", "find and", "create and"
        ]

        request_lower = request.lower()
        return any(keyword in request_lower for keyword in multi_step_keywords)

    def _execute_single_step(self, request: str) -> str:
        """Execute a simple single-step task"""

        # Use chat engine to handle the request
        response_parts = []

        for chunk in self.chat_engine.chat(request):
            response_parts.append(chunk)

        return "".join(response_parts)

    def _execute_multi_step(self, request: str) -> str:
        """Execute a multi-step task with planning"""

        results = []

        # Ask LLM to break down the task
        planning_request = f"""Break down this task into clear steps:

{request}

For each step, specify:
1. What needs to be done
2. Which tool might help (if any)
3. Dependencies on previous steps"""

        # Get plan from LLM
        plan_response = []
        for chunk in self.chat_engine.chat(planning_request):
            plan_response.append(chunk)

        plan_text = "".join(plan_response)
        results.append(f"📋 Plan:\n{plan_text}\n")

        # Execute the original request
        # The chat engine will handle tool calls automatically
        results.append("\n🚀 Executing:\n")

        execution_response = []
        for chunk in self.chat_engine.chat(
            f"Now execute this plan: {request}"
        ):
            execution_response.append(chunk)

        execution_text = "".join(execution_response)
        results.append(execution_text)

        return "\n".join(results)

    def get_reasoning_trace(self) -> str:
        """Get the reasoning trace"""
        return self.reasoner.get_reasoning_trace()
