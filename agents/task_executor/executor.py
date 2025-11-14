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
    """
    Executes complex, multi-step tasks by breaking them down into a plan and
    leveraging a chat engine with tools.

    This agent is designed for general-purpose problem-solving. It uses a simple
    heuristic to decide whether a task requires a multi-step plan or can be
    executed in a single step.

    Attributes:
        chat_engine (ChatEngine): The chat engine used for interacting with the LLM.
        settings (Optional[Settings]): The application settings.
        max_iterations (int): The maximum number of iterations for the agent.
        planner (TaskPlanner): An instance of the task planner.
        reasoner (Reasoner): An instance of the reasoner to track the agent's
            thought process.
    """

    def __init__(
        self,
        chat_engine: ChatEngine,
        settings: Optional[Settings] = None,
        max_iterations: int = 5,
    ):
        """
        Initializes the AgentExecutor.

        Args:
            chat_engine (ChatEngine): The chat engine for LLM interactions.
            settings (Optional[Settings], optional): Application settings.
                Defaults to None.
            max_iterations (int, optional): The maximum number of iterations.
                Defaults to 5.
        """
        self.chat_engine = chat_engine
        self.settings = settings
        self.max_iterations = max_iterations

        self.planner = TaskPlanner()
        self.reasoner = Reasoner()

    def execute_task(self, user_request: str) -> str:
        """
        Executes a given task.

        This method serves as the main entry point for the agent. It assesses the
        user's request, decides whether to use a single or multi-step approach,
        and returns the final result.

        Args:
            user_request (str): The user's request or task description.

        Returns:
            str: The final result or response from the agent.
        """

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
        """
        Determines if a task requires planning using a simple heuristic.

        This method checks for keywords that typically indicate a multi-step
        process.

        Args:
            request (str): The user's request.

        Returns:
            bool: True if planning is likely needed, otherwise False.
        """
        multi_step_keywords = [
            "and then", "after", "first", "second", "finally",
            "multiple", "all", "each", "every",
            "analyze and", "find and", "create and"
        ]

        request_lower = request.lower()
        return any(keyword in request_lower for keyword in multi_step_keywords)

    def _execute_single_step(self, request: str) -> str:
        """
        Executes a simple, single-step task.

        This method directly passes the request to the chat engine to handle.

        Args:
            request (str): The user's request.

        Returns:
            str: The response from the chat engine.
        """

        # Use chat engine to handle the request
        response_parts = []

        for chunk in self.chat_engine.chat(request):
            response_parts.append(chunk)

        return "".join(response_parts)

    def _execute_multi_step(self, request: str) -> str:
        """
        Executes a multi-step task.

        This method first asks the LLM to create a plan for the task. Then, it
        instructs the chat engine to execute the original request, relying on the
        engine's tool-calling capabilities to follow the plan.

        Args:
            request (str): The user's request.

        Returns:
            str: The consolidated result of the multi-step execution.
        """

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
        """
        Retrieves the reasoning trace for the last executed task.

        Returns:
            str: A string detailing the agent's thought process.
        """
        return self.reasoner.get_reasoning_trace()
