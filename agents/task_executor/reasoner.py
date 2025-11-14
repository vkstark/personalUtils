#!/usr/bin/env python3
"""
Reasoner - Chain-of-thought reasoning
"""

from typing import List, Optional


class ReasoningStep:
    """A step in the reasoning chain"""

    def __init__(self, thought: str, action: Optional[str] = None, observation: Optional[str] = None):
        self.thought = thought
        self.action = action
        self.observation = observation


class Reasoner:
    """Implements chain-of-thought reasoning"""

    def __init__(self):
        self.reasoning_chain: List[ReasoningStep] = []

    def add_thought(self, thought: str):
        """Add a reasoning step"""
        step = ReasoningStep(thought=thought)
        self.reasoning_chain.append(step)

    def add_action(self, action: str):
        """Add action to current reasoning step"""
        if self.reasoning_chain:
            self.reasoning_chain[-1].action = action

    def add_observation(self, observation: str):
        """Add observation to current reasoning step"""
        if self.reasoning_chain:
            self.reasoning_chain[-1].observation = observation

    def get_reasoning_trace(self) -> str:
        """Get formatted reasoning trace"""
        trace = []

        for i, step in enumerate(self.reasoning_chain, 1):
            trace.append(f"\n[Step {i}]")
            trace.append(f"Thought: {step.thought}")

            if step.action:
                trace.append(f"Action: {step.action}")

            if step.observation:
                trace.append(f"Observation: {step.observation}")

        return "\n".join(trace)

    def clear(self):
        """Clear reasoning chain"""
        self.reasoning_chain = []
