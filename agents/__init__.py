"""
Agents - Specialized agents for complex task execution

Available agents:
- task_executor: Multi-step task execution with planning and reasoning
- transcript_analyzer: Extract business value, skills, and frameworks from transcripts
- trillionaire_futurist: Strategic advisor operating at trillionaire scale
- framework_teacher: Meta-learning specialist teaching through frameworks
"""

from .agent_manager import AgentManager, AgentType, create_agent_manager
from .task_executor.executor import AgentExecutor
from .transcript_analyzer.analyzer import TranscriptAnalyzer
from .trillionaire_futurist.futurist import TrillionaireFuturist
from .framework_teacher.teacher import FrameworkTeacher

__all__ = [
    "task_executor",
    "transcript_analyzer",
    "trillionaire_futurist",
    "framework_teacher",
    "AgentManager",
    "AgentType",
    "create_agent_manager",
    "AgentExecutor",
    "TranscriptAnalyzer",
    "TrillionaireFuturist",
    "FrameworkTeacher",
]
