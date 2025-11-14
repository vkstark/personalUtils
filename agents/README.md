# Agents Directory

This directory contains specialized agents that can be accessed by the main ChatSystem.

## Available Agents

### task_executor
Multi-step task execution agent with planning and reasoning capabilities.

**Components:**
- `executor.py` - AgentExecutor class for managing multi-step task execution
- `planner.py` - TaskPlanner for breaking down complex tasks into steps
- `reasoner.py` - Reasoner for tracking reasoning and thought processes

**Usage:**
```python
from agents.task_executor import AgentExecutor
from ChatSystem.core.chat_engine import ChatEngine

chat_engine = ChatEngine(settings=settings)
agent = AgentExecutor(chat_engine=chat_engine, max_iterations=5)

result = agent.execute_task("Your complex multi-step task here")
```

## Adding New Agents

To add a new agent:

1. Create a new directory under `agents/` with your agent name (e.g., `agents/my_agent/`)
2. Implement your agent logic in Python files
3. Create an `__init__.py` that exports your main classes
4. Update `agents/__init__.py` to include your new agent
5. Document your agent in this README

### Agent Structure Example

```
agents/
├── __init__.py
├── README.md
├── my_agent/
│   ├── __init__.py
│   ├── agent.py          # Main agent logic
│   ├── helper.py         # Helper functions
│   └── README.md         # Agent-specific docs
└── task_executor/
    ├── __init__.py
    ├── executor.py
    ├── planner.py
    └── reasoner.py
```

### Agent Requirements

All agents should:
- Be self-contained within their directory
- Export main classes via `__init__.py`
- Accept configuration via constructor
- Provide clear documentation
- Work with the main ChatSystem interface

## Integration with ChatSystem

The main ChatSystem can discover and use agents from this directory. Agents can:
- Use the ChatEngine for LLM interactions
- Access registered tools via ToolRegistry
- Maintain their own state and context
- Implement specialized workflows and behaviors
