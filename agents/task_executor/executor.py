#!/usr/bin/env python3
"""
AgentExecutor - Execute complex multi-step tasks

Version 1.2: Planner-backed execution with reasoning traces
"""

from typing import Optional, List
from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.core.config import Settings
from ChatSystem.tools.tool_executor import ToolExecutor
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus
from .planner import TaskPlanner, TaskPlan, TaskStep
from .reasoner import Reasoner


class AgentExecutor:
    """
    Executes complex, multi-step tasks by breaking them down into a plan and
    leveraging tool execution with introspectable reasoning.

    Version 1.2 Features:
    - LLM-backed plan generation
    - Step-by-step execution with status tracking
    - Reasoning trace export
    - Graceful failure handling with context

    Attributes:
        chat_engine (ChatEngine): The chat engine used for interacting with the LLM.
        settings (Optional[Settings]): The application settings.
        max_iterations (int): The maximum number of iterations for the agent.
        enable_planning (bool): Whether to use planning for multi-step tasks.
        planner (TaskPlanner): An instance of the task planner.
        reasoner (Reasoner): An instance of the reasoner to track the agent's
            thought process.
        tool_executor (ToolExecutor): Executor for running tools directly.
    """

    SYSTEM_PERSONA = """You are a task execution agent with access to powerful utilities.

Your capabilities:
- Break down complex tasks into step-by-step plans
- Execute tasks systematically using available tools
- Track reasoning and provide transparent execution traces
- Handle failures gracefully and provide clear context

Available tools: {tools}

When executing tasks:
1. Understand the goal clearly
2. Create a detailed plan if the task is complex
3. Execute each step carefully
4. Track progress and handle errors
5. Provide clear results with reasoning"""

    def __init__(
        self,
        chat_engine: ChatEngine,
        settings: Optional[Settings] = None,
        max_iterations: int = 5,
        enable_planning: bool = True,
    ):
        """
        Initializes the AgentExecutor.

        Args:
            chat_engine (ChatEngine): The chat engine for LLM interactions.
            settings (Optional[Settings], optional): Application settings.
                Defaults to None.
            max_iterations (int, optional): The maximum number of iterations.
                Defaults to 5.
            enable_planning (bool, optional): Whether to enable planning.
                Defaults to True.
        """
        self.chat_engine = chat_engine
        self.settings = settings
        self.max_iterations = max_iterations
        self.enable_planning = enable_planning

        self.planner = TaskPlanner(chat_engine=chat_engine)
        self.reasoner = Reasoner()
        self.tool_executor = ToolExecutor()

        # Add system persona to conversation
        tool_names = [tool.get("function", {}).get("name", "unknown")
                      for tool in chat_engine.tools] if chat_engine.tools else []
        persona = self.SYSTEM_PERSONA.format(tools=", ".join(tool_names))
        self.chat_engine.conversation.add_message("system", persona)

    def execute_task(self, user_request: str, use_planning: Optional[bool] = None) -> str:
        """
        Executes a given task.

        This method serves as the main entry point for the agent. It assesses the
        user's request, decides whether to use a single or multi-step approach,
        and returns the final result.

        Args:
            user_request (str): The user's request or task description.
            use_planning (Optional[bool]): Override for planning decision.
                If None, uses heuristics.

        Returns:
            str: The final result or response from the agent.
        """

        # Clear previous reasoning
        self.reasoner.clear()

        # Step 1: Understand the task
        self.reasoner.add_thought(f"User wants: {user_request}")

        # Step 2: Determine if planning is needed
        if use_planning is None:
            is_multi_step = self.enable_planning and self._needs_planning(user_request)
        else:
            is_multi_step = use_planning

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

        self.reasoner.add_thought("Executing as single-step task")

        # Use chat engine to handle the request
        response_parts = []

        for chunk in self.chat_engine.chat(request):
            response_parts.append(chunk)

        response = "".join(response_parts)
        self.reasoner.add_observation(f"Completed: {response[:100]}...")

        return response

    def _execute_multi_step(self, request: str) -> str:
        """
        Executes a multi-step task using structured planning and execution.

        Version 1.2: Creates a TaskPlan, executes each step with ToolExecutor,
        updates statuses, handles failures, and provides reasoning traces.

        Args:
            request (str): The user's request.

        Returns:
            str: The consolidated result of the multi-step execution.
        """

        results = []

        # Get available tools
        available_tools = [
            tool.get("function", {}).get("name", "unknown")
            for tool in self.chat_engine.tools
        ] if self.chat_engine.tools else []

        # Step 1: Create plan
        self.reasoner.add_thought("Creating structured plan")
        plan = self.planner.create_plan(request, available_tools)

        # Display plan
        plan_summary = self.planner.get_plan_summary(plan)
        results.append(plan_summary)
        results.append("")

        self.reasoner.add_observation(f"Created plan with {len(plan.steps)} steps")

        # Step 2: Execute plan step by step
        results.append("🚀 Execution:")
        results.append("")

        plan.status = "running"
        iteration = 0

        while not self.planner.is_plan_complete(plan) and iteration < self.max_iterations:
            iteration += 1

            # Get next step
            next_step = self.planner.get_next_step(plan)
            if not next_step:
                # Check if we failed
                if self.planner.has_failed_steps(plan):
                    break
                # No more steps available
                break

            # Execute step
            self.reasoner.add_thought(f"Executing step {next_step.step_number}: {next_step.description}")

            step_result = self._execute_step(plan, next_step)
            results.append(step_result)

            # Check for failure
            if next_step.status == "failed":
                results.append(f"\n❌ Execution failed at step {next_step.step_number}")
                results.append(f"Error: {next_step.error_message}")
                results.append(f"\nContext: {next_step.description}")
                plan.status = "failed"
                break

        # Check final status
        if self.planner.is_plan_complete(plan):
            plan.status = "done"
            results.append("\n✅ All steps completed successfully!")
        elif iteration >= self.max_iterations:
            results.append(f"\n⚠️  Max iterations ({self.max_iterations}) reached")
            plan.status = "failed"

        # Attach reasoning trace to conversation
        self.reasoner.attach_to_conversation(self.chat_engine.conversation)

        return "\n".join(results)

    def _execute_step(self, plan: TaskPlan, step: TaskStep) -> str:
        """
        Execute a single step in the plan.

        Args:
            plan: The TaskPlan containing this step
            step: The TaskStep to execute

        Returns:
            Formatted string with step execution result
        """
        # Update status to running
        self.planner.update_step_status(plan, step.step_number, "running")
        self.reasoner.add_action(f"Running step {step.step_number}")

        result_lines = [f"▶️  Step {step.step_number}: {step.description}"]

        try:
            # If step needs a tool, execute it
            if step.tool_needed:
                # Execute tool via chat engine (let it handle tool calling)
                tool_request = f"Execute step {step.step_number}: {step.description}"

                response_parts = []
                for chunk in self.chat_engine.chat(tool_request):
                    response_parts.append(chunk)

                result = "".join(response_parts)

                # Update step with result
                self.planner.update_step_status(
                    plan,
                    step.step_number,
                    "done",
                    result=result
                )

                result_lines.append(f"   ✓ {result[:200]}{'...' if len(result) > 200 else ''}")
                self.reasoner.add_observation(f"Step {step.step_number} completed")
                self.reasoner.add_tool_output(step.tool_needed or "chat", result)

            else:
                # No tool needed, just use LLM
                response_parts = []
                for chunk in self.chat_engine.chat(step.description):
                    response_parts.append(chunk)

                result = "".join(response_parts)

                # Update step with result
                self.planner.update_step_status(
                    plan,
                    step.step_number,
                    "done",
                    result=result
                )

                result_lines.append(f"   ✓ {result[:200]}{'...' if len(result) > 200 else ''}")
                self.reasoner.add_observation(f"Step {step.step_number} completed")

        except Exception as e:
            error_msg = str(e)
            self.planner.update_step_status(
                plan,
                step.step_number,
                "failed",
                error_message=error_msg
            )

            result_lines.append(f"   ✗ Error: {error_msg}")
            self.reasoner.add_observation(f"Step {step.step_number} failed: {error_msg}")

        return "\n".join(result_lines)

    def get_reasoning_trace(self, include_metadata: bool = False) -> str:
        """
        Retrieves the reasoning trace for the last executed task.

        Args:
            include_metadata: Whether to include tool outputs and metadata

        Returns:
            str: A string detailing the agent's thought process.
        """
        return self.reasoner.get_reasoning_trace(include_metadata=include_metadata)

    def export_reasoning_trace(self) -> dict:
        """
        Export reasoning trace as dictionary.

        Returns:
            Dictionary representation of reasoning trace
        """
        return self.reasoner.export_trace_dict()
