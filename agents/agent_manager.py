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
    Manages multiple AI agents, providing a unified interface for their selection
    and execution.

    This class acts as a factory and registry for all specialized agents within
    the system. It allows for dynamic switching between agents and centralizes
    agent configuration and instantiation.

    Attributes:
        settings (Settings): The application settings object.
        agents (Dict[AgentType, Any]): A cache of instantiated agents.
        current_agent_type (Optional[AgentType]): The type of the currently
            active agent.
        current_agent (Optional[Any]): The instance of the currently active agent.
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

    # Each agent exposes one "handle a user turn" entry point. The CLI routes
    # raw input (anything that isn't a /command) through the active agent's
    # method via dispatch(), so e.g. the task_executor actually runs its
    # plan→reason→act loop instead of being bypassed by a direct chat call.
    _PRIMARY_METHOD = {
        AgentType.TASK_EXECUTOR: "execute_task",
        AgentType.TRANSCRIPT_ANALYZER: "analyze",
        AgentType.TRILLIONAIRE_FUTURIST: "respond",
        AgentType.FRAMEWORK_TEACHER: "teach",
    }

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initializes the AgentManager.

        Args:
            settings (Optional[Settings], optional): An instance of the Settings
                class. If None, default settings are loaded. Defaults to None.
        """
        self.settings = settings or Settings()  # type: ignore[call-arg]  # key loaded from env
        self.agents: Dict[AgentType, Any] = {}
        self.current_agent_type: Optional[AgentType] = None
        self.current_agent: Optional[Any] = None

    def get_agent(self, agent_type: AgentType, chat_engine: Optional[ChatEngine] = None) -> Any:
        """
        Retrieves or creates an agent of the specified type.

        This method first checks for a cached instance of the agent. If not found,
        it creates a new one. If a `chat_engine` is provided, it will be attached
        to the agent, replacing any existing one.

        Args:
            agent_type (AgentType): The type of agent to retrieve or create.
            chat_engine (Optional[ChatEngine], optional): An instance of the
                ChatEngine to associate with the agent. Defaults to None.

        Returns:
            Any: An instance of the requested agent.
        """
        # If agent exists and a new chat_engine is provided, update the cached agent's engine
        if agent_type in self.agents and chat_engine is not None:
            agent = self.agents[agent_type]
            agent.chat_engine = chat_engine

            # Re-add the system persona to the new chat engine's conversation
            # This is critical because the new engine has a fresh conversation without the persona.
            # Prefer get_formatted_persona() so placeholders (e.g. AgentExecutor's
            # {tools}) are substituted exactly as they are at construction time.
            if hasattr(agent, 'get_formatted_persona'):
                agent.chat_engine.conversation.add_message("system", agent.get_formatted_persona())
            elif hasattr(agent, 'SYSTEM_PERSONA'):
                agent.chat_engine.conversation.add_message("system", agent.SYSTEM_PERSONA)

            return agent

        # Return cached agent if available and no new chat_engine provided
        if agent_type in self.agents:
            return self.agents[agent_type]

        # Create new agent based on type
        chat_engine = chat_engine or ChatEngine()

        # Resolve per-agent configuration (model, flags, iterations) from YAML,
        # merging each agents.<name> block over the general agent defaults.
        executor_cfg = self.settings.get_agent_config_for("task_executor")
        analyzer_cfg = self.settings.get_agent_config_for("transcript_analyzer")
        futurist_cfg = self.settings.get_agent_config_for("trillionaire_futurist")
        teacher_cfg = self.settings.get_agent_config_for("framework_teacher")

        agent_map = {
            AgentType.TASK_EXECUTOR: lambda: AgentExecutor(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=executor_cfg["max_iterations"],
                enable_planning=executor_cfg["enable_planning"],
                model=executor_cfg["model"],
            ),
            AgentType.TRANSCRIPT_ANALYZER: lambda: TranscriptAnalyzer(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=analyzer_cfg["max_iterations"],
                model=analyzer_cfg["model"],
            ),
            AgentType.TRILLIONAIRE_FUTURIST: lambda: TrillionaireFuturist(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=futurist_cfg["max_iterations"],
                model=futurist_cfg["model"],
            ),
            AgentType.FRAMEWORK_TEACHER: lambda: FrameworkTeacher(
                chat_engine=chat_engine,
                settings=self.settings,
                max_iterations=teacher_cfg["max_iterations"],
                model=teacher_cfg["model"],
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
        Sets the currently active agent.

        This method updates the `current_agent` and `current_agent_type`
        attributes, making the specified agent the active one for subsequent
        operations.

        Args:
            agent_type (AgentType): The type of agent to activate.
            chat_engine (Optional[ChatEngine], optional): The ChatEngine for
                the agent. Defaults to None.
        """
        self.current_agent_type = agent_type
        self.current_agent = self.get_agent(agent_type, chat_engine)

    def get_current_agent(self) -> Optional[Any]:
        """
        Gets the currently active agent.

        Returns:
            Optional[Any]: The instance of the current agent, or None if no
            agent is active.
        """
        return self.current_agent

    def dispatch(self, user_input: str) -> str:
        """
        Route a user turn to the current agent's primary method.

        Looks up the active agent's entry point (`execute_task`/`analyze`/
        `respond`/`teach`) via `_PRIMARY_METHOD` and calls it with the raw user
        input, returning the agent's full response string.

        Args:
            user_input (str): The raw user message (not a slash command).

        Returns:
            str: The active agent's complete response.

        Raises:
            RuntimeError: If no agent is currently active.
        """
        if self.current_agent is None or self.current_agent_type is None:
            raise RuntimeError("No active agent to handle the request")

        method_name = self._PRIMARY_METHOD[self.current_agent_type]
        return getattr(self.current_agent, method_name)(user_input)

    def list_agents(self) -> Dict[str, Any]:
        """
        Lists all available agents along with their descriptions and use cases.

        Returns:
            Dict[str, Any]: A dictionary where keys are the agent type values
            and values are dictionaries of agent information.
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

    def get_agent_info(self, agent_type: Optional[AgentType]) -> Dict[str, Any]:
        """
        Gets the descriptive information for a specific agent type.

        Args:
            agent_type (Optional[AgentType]): The type of the agent.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's information,
            or an empty dictionary if the agent type is not found.
        """
        if agent_type is None:
            return {}
        return self.AGENT_DESCRIPTIONS.get(agent_type, {})

    @staticmethod
    def parse_agent_type(agent_string: str) -> Optional[AgentType]:
        """
        Parses a string to determine the corresponding AgentType.

        This method supports matching by the agent's full name, short name, or
        other fuzzy keywords.

        Args:
            agent_string (str): The string to parse.

        Returns:
            Optional[AgentType]: The matching AgentType, or None if no match
            is found.
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
        Formats the list of available agents into a human-readable string.

        This method is suitable for displaying the agent list in a command-line
        interface.

        Returns:
            str: A formatted string detailing the available agents.
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
    A convenience function to create a new instance of AgentManager.

    Args:
        settings (Optional[Settings], optional): An instance of the Settings
            class. If None, default settings are loaded. Defaults to None.

    Returns:
        AgentManager: A new instance of the AgentManager.
    """
    return AgentManager(settings=settings)
