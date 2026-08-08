"""
Persona marker shared by every persona injection path.

Every persona system message carries a stable first line
`[Agent Persona: <agent_type.value>]` so it can be recognized and evicted when
another agent is activated. Both injection paths — each agent's `__init__` and
AgentManager's re-injection after an engine swap — must build the message via
`persona_message()` so the two paths stay byte-identical and the
`ensure_system_message` idempotency (#114) keeps holding.
"""

# First line of every marked persona system message; also the eviction prefix.
PERSONA_MARKER_PREFIX = "[Agent Persona:"

# Stable opening text of each persona exactly as pre-marker versions persisted
# it — for the task executor, the portion of SYSTEM_PERSONA before the {tools}
# placeholder. The futurist/teacher personas start with a literal newline
# (their triple-quoted strings open on the quote line), so the prefixes keep
# it. Lets eviction heal history files written before the marker existed.
LEGACY_PERSONA_PREFIXES = (
    "You are a task execution agent with access to powerful utilities.",
    "You are an elite Transcript Intelligence Analyst",
    "\nYou are a FRAMEWORK ARCHITECT, META-LEARNING ENGINE, and SOVEREIGN SHADOW STRATEGIST",
    "\nYou are a FRAMEWORK ARCHITECT and META-LEARNING ENGINE.",
)

# Everything set_current_agent evicts before injecting the active persona.
PERSONA_EVICTION_PREFIXES = (PERSONA_MARKER_PREFIX,) + LEGACY_PERSONA_PREFIXES


def persona_message(agent_key: str, text: str) -> str:
    """
    Build the marked persona system message for an agent.

    Args:
        agent_key (str): The agent's AgentType value (e.g. "task_executor").
        text (str): The persona text (tools-formatted for the task executor).

    Returns:
        str: The persona prefixed with its `[Agent Persona: <key>]` marker line.
    """
    return f"{PERSONA_MARKER_PREFIX} {agent_key}]\n{text}"
