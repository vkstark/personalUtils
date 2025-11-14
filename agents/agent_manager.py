"""
Agent Manager

Centralized management for all AI agents in the system.
Allows selection and switching between different specialized agents.
"""

from typing import Dict, Optional, Any
from enum import Enum

from ChatSystem.core.chat_engine import ChatEngine
from ChatSystem.core.config import Settings

from .task_executor.executor import AgentExecutor
from .transcript_analyzer.analyzer import TranscriptAnalyzer
from .trillionaire_futurist.futurist import TrillionaireFuturist
from .framework_teacher.teacher import FrameworkTeacher


class AgentType(Enum):
    """Available agent types."""
    TASK_EXECUTOR = "task_executor"
    TRANSCRIPT_ANALYZER = "transcript_analyzer"
    TRILLIONAIRE_FUTURIST = "trillionaire_futurist"
    FRAMEWORK_TEACHER = "framework_teacher"


class AgentManager:
    """
    Manages multiple AI agents and provides unified interface for agent selection
    and execution.
    """

    AGENT_DESCRIPTIONS = {
        AgentType.TASK_EXECUTOR: {
            "name": "Task Executor",
            "short_name": "executor",
            "description": "General-purpose task execution agent with planning and reasoning capabilities",
            "use_cases": [
                "Multi-step task execution",
                "Tool-based operations",
                "General problem solving"
            ]
        },
        AgentType.TRANSCRIPT_ANALYZER: {
            "name": "Transcript Analyzer",
            "short_name": "analyzer",
            "description": "Expert analyst that extracts business value, frameworks, skills, and actionable insights from transcripts",
            "use_cases": [
                "Analyze podcast transcripts",
                "Extract lessons from interviews",
                "Identify skills and frameworks from content",
                "Generate 10-step action plans from insights"
            ]
        },
        AgentType.TRILLIONAIRE_FUTURIST: {
            "name": "Trillionaire Futurist",
            "short_name": "futurist",
            "description": "Strategic advisor operating at trillionaire scale - data-driven, proof-based, creates the future",
            "use_cases": [
                "Strategic business decisions",
                "Opportunity analysis",
                "High-stakes planning",
                "Reality-bending resource allocation"
            ]
        },
        AgentType.FRAMEWORK_TEACHER: {
            "name": "Framework Teacher",
            "short_name": "teacher",
            "description": "Meta-learning specialist that teaches through frameworks and mental models, not specific steps",
            "use_cases": [
                "Learn generalized skills",
                "Develop mental models",
                "Build transferable capabilities",
                "Master trillionaire-level meta-skills"
            ]
        }
    }

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the Agent Manager.

        Args:
            settings: Optional settings object (will create default if not provided)
        """
        self.settings = settings or Settings()
        self.agents: Dict[AgentType, Any] = {}
        self.current_agent_type: Optional[AgentType] = None
        self.current_agent: Optional[Any] = None

    def get_agent(self, agent_type: AgentType, chat_engine: Optional[ChatEngine] = None) -> Any:
        """
        Get or create an agent of the specified type.

        Args:
            agent_type: The type of agent to get
            chat_engine: Optional chat engine (creates new if not provided)

        Returns:
            The requested agent instance
        """
        # Return cached agent if available
        if agent_type in self.agents:
            return self.agents[agent_type]

        # Create new agent based on type
        chat_engine = chat_engine or ChatEngine()

        # Get agent-specific configuration from YAML
        yaml_config = self.settings.load_yaml_config()
        agents_config = yaml_config.get("agents", {})

        # Get max_iterations for each specific agent type from config
        # Fall back to general agent config if agent-specific config doesn't exist
        agent_config = self.settings.get_agent_config()
        default_max_iterations = agent_config.get("max_iterations", 5)

        # Get agent-specific max_iterations or use defaults
        executor_config = agents_config.get("task_executor", {})
        analyzer_config = agents_config.get("transcript_analyzer", {})
        futurist_config = agents_config.get("trillionaire_futurist", {})
        teacher_config = agents_config.get("framework_teacher", {})

        agent_map = {
            AgentType.TASK_EXECUTOR: lambda: AgentExecutor(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=executor_config.get("max_iterations", default_max_iterations)
            ),
            AgentType.TRANSCRIPT_ANALYZER: lambda: TranscriptAnalyzer(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=analyzer_config.get("max_iterations", 3)
            ),
            AgentType.TRILLIONAIRE_FUTURIST: lambda: TrillionaireFuturist(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=futurist_config.get("max_iterations", 5)
            ),
            AgentType.FRAMEWORK_TEACHER: lambda: FrameworkTeacher(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=teacher_config.get("max_iterations", 3)
            )
        }

        if agent_type not in agent_map:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Create and cache the agent
        agent = agent_map[agent_type]()
        self.agents[agent_type] = agent
        return agent

    def set_current_agent(self, agent_type: AgentType, chat_engine: Optional[ChatEngine] = None):
        """
        Set the current active agent.

        Args:
            agent_type: The type of agent to activate
            chat_engine: Optional chat engine
        """
        self.current_agent_type = agent_type
        self.current_agent = self.get_agent(agent_type, chat_engine)

    def get_current_agent(self) -> Optional[Any]:
        """Get the currently active agent."""
        return self.current_agent

    def list_agents(self) -> Dict[str, Any]:
        """
        List all available agents with their descriptions.

        Returns:
            Dictionary of agent information
        """
        return {
            agent_type.value: {
                "name": info["name"],
                "short_name": info["short_name"],
                "description": info["description"],
                "use_cases": info["use_cases"]
            }
            for agent_type, info in self.AGENT_DESCRIPTIONS.items()
        }

    def get_agent_info(self, agent_type: AgentType) -> Dict[str, Any]:
        """
        Get information about a specific agent type.

        Args:
            agent_type: The agent type to get info for

        Returns:
            Agent information dictionary
        """
        return self.AGENT_DESCRIPTIONS.get(agent_type, {})

    @staticmethod
    def parse_agent_type(agent_string: str) -> Optional[AgentType]:
        """
        Parse a string into an AgentType enum.

        Args:
            agent_string: String representation of agent type

        Returns:
            AgentType enum or None if not found
        """
        agent_string = agent_string.lower().strip()

        # Direct enum value match
        for agent_type in AgentType:
            if agent_type.value == agent_string:
                return agent_type

        # Short name match
        for agent_type, info in AgentManager.AGENT_DESCRIPTIONS.items():
            if info["short_name"] == agent_string:
                return agent_type

        # Fuzzy matching
        fuzzy_map = {
            "task": AgentType.TASK_EXECUTOR,
            "executor": AgentType.TASK_EXECUTOR,
            "transcript": AgentType.TRANSCRIPT_ANALYZER,
            "analyzer": AgentType.TRANSCRIPT_ANALYZER,
            "analysis": AgentType.TRANSCRIPT_ANALYZER,
            "trillionaire": AgentType.TRILLIONAIRE_FUTURIST,
            "futurist": AgentType.TRILLIONAIRE_FUTURIST,
            "strategic": AgentType.TRILLIONAIRE_FUTURIST,
            "framework": AgentType.FRAMEWORK_TEACHER,
            "teacher": AgentType.FRAMEWORK_TEACHER,
            "learning": AgentType.FRAMEWORK_TEACHER,
        }

        return fuzzy_map.get(agent_string)

    def format_agent_list(self) -> str:
        """
        Format the agent list for display.

        Returns:
            Formatted string of available agents
        """
        output = ["Available Agents:", "=" * 60, ""]

        for agent_type in AgentType:
            info = self.AGENT_DESCRIPTIONS[agent_type]
            output.append(f"📌 {info['name']} ({info['short_name']})")
            output.append(f"   {info['description']}")
            output.append("")
            output.append("   Use cases:")
            for use_case in info['use_cases']:
                output.append(f"   • {use_case}")
            output.append("")
            output.append("-" * 60)
            output.append("")

        return "\n".join(output)


# Convenience function for creating agent manager
def create_agent_manager(settings: Optional[Settings] = None) -> AgentManager:
    """
    Create a new AgentManager instance.

    Args:
        settings: Optional settings object

    Returns:
        AgentManager instance
    """
    return AgentManager(settings=settings)
