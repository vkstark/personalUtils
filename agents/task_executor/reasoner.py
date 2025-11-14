#!/usr/bin/env python3
"""
Reasoner - Chain-of-thought reasoning with performance tracking

Version 1.2: Enhanced with elapsed time, tool outputs, and trace export
"""

import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    """
    A step in the reasoning chain.

    Attributes:
        thought: The reasoning thought at this step
        action: The action taken (if any)
        observation: The observation/result from the action
        elapsed_time: Time taken for this step in seconds
        tool_outputs: Structured output from tool execution
        timestamp: When this step occurred
        metadata: Additional metadata about the step
    """

    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None
    elapsed_time: float = 0.0
    tool_outputs: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Reasoner:
    """
    Implements chain-of-thought reasoning with performance tracking.

    Version 1.2: Captures per-step thought, action, observation, elapsed time,
    and tool outputs. Supports exporting traces for conversation history.
    """

    def __init__(self):
        """Initialize the Reasoner."""
        self.reasoning_chain: List[ReasoningStep] = []
        self._current_step_start: Optional[float] = None

    def add_thought(self, thought: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a new reasoning step.

        Args:
            thought: The reasoning thought
            metadata: Optional metadata for this step
        """
        # If there's a previous step, calculate elapsed time
        if self.reasoning_chain and self._current_step_start is not None:
            elapsed = time.time() - self._current_step_start
            self.reasoning_chain[-1].elapsed_time = elapsed

        # Start timing new step
        self._current_step_start = time.time()

        step = ReasoningStep(
            thought=thought,
            metadata=metadata or {}
        )
        self.reasoning_chain.append(step)

    def add_action(self, action: str):
        """
        Add action to current reasoning step.

        Args:
            action: The action being taken
        """
        if self.reasoning_chain:
            self.reasoning_chain[-1].action = action

    def add_observation(self, observation: str):
        """
        Add observation to current reasoning step.

        Args:
            observation: The observation/result
        """
        if self.reasoning_chain:
            self.reasoning_chain[-1].observation = observation

    def add_tool_output(self, tool_name: str, output: Any):
        """
        Add structured tool output to current reasoning step.

        Args:
            tool_name: Name of the tool that was executed
            output: The output from the tool (ToolExecutionResult or dict)
        """
        if self.reasoning_chain:
            if self.reasoning_chain[-1].tool_outputs is None:
                self.reasoning_chain[-1].tool_outputs = {}

            # If output is a ToolExecutionResult, extract relevant data
            if hasattr(output, 'model_dump'):
                self.reasoning_chain[-1].tool_outputs[tool_name] = output.model_dump()
            elif isinstance(output, dict):
                self.reasoning_chain[-1].tool_outputs[tool_name] = output
            else:
                self.reasoning_chain[-1].tool_outputs[tool_name] = str(output)

    def finalize_current_step(self):
        """Finalize the current step by calculating elapsed time."""
        if self.reasoning_chain and self._current_step_start is not None:
            elapsed = time.time() - self._current_step_start
            self.reasoning_chain[-1].elapsed_time = elapsed
            self._current_step_start = None

    def get_reasoning_trace(self, include_metadata: bool = False) -> str:
        """
        Get formatted reasoning trace.

        Args:
            include_metadata: Whether to include metadata in the trace

        Returns:
            Formatted string with reasoning trace
        """
        # Finalize current step if needed
        self.finalize_current_step()

        trace = []
        trace.append("🧠 Reasoning Trace")
        trace.append("=" * 60)

        for i, step in enumerate(self.reasoning_chain, 1):
            trace.append(f"\n[Step {i}] ({step.elapsed_time:.2f}s)")
            trace.append(f"💭 Thought: {step.thought}")

            if step.action:
                trace.append(f"⚡ Action: {step.action}")

            if step.observation:
                trace.append(f"👁️  Observation: {step.observation}")

            if step.tool_outputs and include_metadata:
                trace.append("🔧 Tool Outputs:")
                for tool_name, output in step.tool_outputs.items():
                    if isinstance(output, dict):
                        trace.append(f"  - {tool_name}: {json.dumps(output, indent=4)}")
                    else:
                        trace.append(f"  - {tool_name}: {output}")

        trace.append("\n" + "=" * 60)
        total_time = sum(step.elapsed_time for step in self.reasoning_chain)
        trace.append(f"Total reasoning time: {total_time:.2f}s")

        return "\n".join(trace)

    def export_trace_dict(self) -> Dict[str, Any]:
        """
        Export reasoning trace as a dictionary for conversation history.

        Returns:
            Dictionary representation of the reasoning trace
        """
        # Finalize current step if needed
        self.finalize_current_step()

        return {
            "reasoning_trace": [step.model_dump() for step in self.reasoning_chain],
            "total_steps": len(self.reasoning_chain),
            "total_time": sum(step.elapsed_time for step in self.reasoning_chain),
            "exported_at": datetime.now().isoformat()
        }

    def export_trace_markdown(self) -> str:
        """
        Export reasoning trace as markdown for documentation.

        Returns:
            Markdown-formatted reasoning trace
        """
        # Finalize current step if needed
        self.finalize_current_step()

        md = ["# Reasoning Trace", ""]

        for i, step in enumerate(self.reasoning_chain, 1):
            md.append(f"## Step {i} ({step.elapsed_time:.2f}s)")
            md.append("")
            md.append(f"**Thought:** {step.thought}")
            md.append("")

            if step.action:
                md.append(f"**Action:** {step.action}")
                md.append("")

            if step.observation:
                md.append(f"**Observation:**")
                md.append(f"```")
                md.append(step.observation)
                md.append(f"```")
                md.append("")

            if step.tool_outputs:
                md.append(f"**Tool Outputs:**")
                for tool_name, output in step.tool_outputs.items():
                    md.append(f"- **{tool_name}:**")
                    if isinstance(output, dict):
                        md.append(f"  ```json")
                        md.append(f"  {json.dumps(output, indent=2)}")
                        md.append(f"  ```")
                    else:
                        md.append(f"  {output}")
                md.append("")

        total_time = sum(step.elapsed_time for step in self.reasoning_chain)
        md.append(f"**Total Time:** {total_time:.2f}s")

        return "\n".join(md)

    def attach_to_conversation(self, conversation_manager) -> str:
        """
        Attach reasoning trace to conversation history.

        Args:
            conversation_manager: The ConversationManager to attach to

        Returns:
            Summary message that was added to conversation
        """
        trace_dict = self.export_trace_dict()
        summary = f"Reasoning trace: {len(self.reasoning_chain)} steps, {trace_dict['total_time']:.2f}s total"

        # Add as system message with metadata
        conversation_manager.add_message(
            role="system",
            content=f"[Reasoning Trace]\n{self.get_reasoning_trace()}"
        )

        return summary

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the reasoning chain.

        Returns:
            Dictionary with summary statistics
        """
        # Finalize current step if needed
        self.finalize_current_step()

        total_time = sum(step.elapsed_time for step in self.reasoning_chain)
        steps_with_actions = sum(1 for step in self.reasoning_chain if step.action)
        steps_with_tools = sum(1 for step in self.reasoning_chain if step.tool_outputs)

        return {
            "total_steps": len(self.reasoning_chain),
            "total_time": total_time,
            "avg_time_per_step": total_time / len(self.reasoning_chain) if self.reasoning_chain else 0,
            "steps_with_actions": steps_with_actions,
            "steps_with_tools": steps_with_tools
        }

    def clear(self):
        """Clear reasoning chain."""
        self.reasoning_chain = []
        self._current_step_start = None
