# 🤖 ChatSystem - GPT-Powered Chat with Function Calling

A production-ready chat system powered by OpenAI's GPT models with **12 integrated utility tools** and **agentic capabilities**.

## ✨ Features

- 🎯 **OpenAI GPT-4o/GPT-4.1** integration with streaming support
- 🛠️ **12 Utility Tools** integrated as native function calling
- 🤖 **Agentic Workflows** with planning and reasoning
- 💬 **Conversation Memory** with context management
- 🎨 **Beautiful CLI** powered by Rich
- 📊 **Token Tracking** and cost calculation
- ⚙️ **Structured Outputs** with 100% schema compliance
- 💾 **Auto-save** conversation history

---

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 2. Configuration

Edit `.env`:
```env
OPENAI_API_KEY=your-api-key-here
MODEL_NAME=gpt-4o
```

Edit `config.yaml` to customize tools and behavior.

### 3. Run Interactive Chat

```bash
# Run the CLI
python -m ChatSystem

# Or directly
python ChatSystem/interface/cli.py
```

---

## 🛠️ Integrated Tools

All **12 personalUtils** are available as function calling tools:

| # | Tool | Description |
|---|------|-------------|
| 1 | **CodeWhisper** | Analyze Python code structure, complexity, functions, classes |
| 2 | **APITester** | Test HTTP API endpoints (GET, POST, PUT, DELETE) |
| 3 | **DuplicateFinder** | Find duplicate files by hash or filename |
| 4 | **SnippetManager** | Store and retrieve code snippets with tags |
| 5 | **BulkRename** | Batch rename files with patterns/regex |
| 6 | **EnvManager** | Manage .env configuration files |
| 7 | **FileDiff** | Compare files and show differences |
| 8 | **GitStats** | Analyze git repository statistics |
| 9 | **ImportOptimizer** | Optimize Python import statements |
| 10 | **PathSketch** | Path operations (normalize, resolve, join) |
| 11 | **TodoExtractor** | Extract TODO/FIXME comments from code |
| 12 | **DataConvert** | Convert between JSON, YAML, CSV, XML |

---

## 📚 Usage Examples

### Basic Chat
```python
from ChatSystem import ChatEngine, get_settings

settings = get_settings()
engine = ChatEngine(settings=settings)

for chunk in engine.chat("Hello! What can you do?"):
    print(chunk, end="")
```

### Using Tools
```python
from ChatSystem.tools import ToolRegistry

# Register tools
registry = ToolRegistry(enabled_tools=["CodeWhisper", "APITester"])
tools = registry.get_tools()
engine.register_tools(tools, registry.get_tool_executor())

# Chat will automatically use tools
response = engine.chat("Analyze the code in ./myproject")
```

### Agentic Workflow
```python
from ChatSystem.agent import AgentExecutor

agent = AgentExecutor(chat_engine=engine, max_iterations=5)

# Complex multi-step task
result = agent.execute_task(
    "Find all duplicate Python files, analyze their complexity, "
    "and extract TODO comments from them"
)

print(result)
print(agent.get_reasoning_trace())
```

---

## 🎨 CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/tools` | List all available tools |
| `/stats` | Show usage statistics (tokens, cost) |
| `/context` | Show context window usage |
| `/clear` | Clear conversation history |
| `/export` | Export conversation to file |
| `/model` | View current model |
| `/exit` | Exit the chat |

---

## 📖 Example Sessions

### Code Analysis
```
You: Analyze the ChatSystem/core directory

🤖 Assistant: I'll analyze the code structure for you.
[Uses analyze_python_code tool]

Found 3 Python files:
- chat_engine.py: 200 LOC, 5 classes, complexity: 45
- conversation.py: 150 LOC, 2 classes, complexity: 28
- config.py: 100 LOC, 1 class, complexity: 12

Total complexity: 85
...
```

### Multi-Step Task
```
You: Find duplicate files and then analyze any Python duplicates

🤖 Assistant: I'll break this down into steps.

📋 Plan:
1. Find duplicate files
2. Filter Python files
3. Analyze their code

🚀 Executing:
[Step 1] Finding duplicates...
Found 3 sets of duplicates

[Step 2] Filtering .py files...
2 Python file duplicates found

[Step 3] Analyzing code...
[Detailed analysis]
```

---

## ⚙️ Configuration

### Model Selection

In `config.yaml`:
```yaml
models:
  simple: gpt-4o-mini        # $0.15/$0.60 per 1M tokens
  general: gpt-4o            # $2.50/$10.00 per 1M tokens
  long_context: gpt-4.1      # 1M token context
  reasoning: o3-mini         # Advanced reasoning
```

### Enable/Disable Tools

```yaml
tools:
  enabled:
    - CodeWhisper
    - APITester
    # Add or remove as needed
```

### Agent Settings

```yaml
agent:
  max_iterations: 5
  enable_planning: true
  enable_reasoning: true
  timeout_seconds: 300
```

---

## 🏗️ Architecture

```
ChatSystem/
├── core/
│   ├── config.py          # Pydantic settings
│   ├── chat_engine.py     # OpenAI integration
│   └── conversation.py    # Memory management
│
├── tools/
│   ├── tool_adapter.py    # Convert utilities to OpenAI schema
│   ├── tool_registry.py   # Tool discovery and registration
│   └── tool_executor.py   # Safe tool execution
│
├── agent/
│   ├── planner.py         # Task planning
│   ├── executor.py        # Multi-step execution
│   └── reasoner.py        # Chain-of-thought
│
├── interface/
│   └── cli.py             # Rich-powered CLI
│
└── examples/
    ├── basic_chat.py
    ├── tool_usage.py
    └── agentic_workflow.py
```

---

## 💰 Cost Optimization

The system tracks token usage and costs in real-time:

```python
stats = engine.get_stats()
print(f"Total cost: ${stats['total_cost']:.4f}")
print(f"Input tokens: {stats['total_input_tokens']:,}")
print(f"Output tokens: {stats['total_output_tokens']:,}")
```

**Model Costs (per 1M tokens):**
- gpt-4o-mini: $0.15 / $0.60 (cheapest, fast)
- gpt-4o: $2.50 / $10.00 (best general purpose)
- gpt-4.1: $2.00 / $8.00 (long context)
- o3-mini: $1.00 / $4.00 (reasoning)

---

## 🧪 Running Examples

```bash
# Basic chat
python ChatSystem/examples/basic_chat.py

# Tool usage demonstration
python ChatSystem/examples/tool_usage.py

# Agentic workflow
python ChatSystem/examples/agentic_workflow.py
```

---

## 🔧 Advanced Usage

### Custom System Prompt

```python
from ChatSystem.core import ConversationManager

conversation = ConversationManager(
    model="gpt-4o",
    system_prompt="You are a helpful coding assistant..."
)

engine = ChatEngine(conversation=conversation)
```

### Streaming Responses

```python
# Stream tokens in real-time
for chunk in engine.chat("Hello!", stream=True):
    print(chunk, end="", flush=True)
```

### Context Management

```python
# Check context usage
usage = conversation.get_context_window_usage()
print(f"Using {usage['usage_percent']}% of context")

# Trim if needed
conversation.trim_context(target_tokens=50000)
```

---

## 📊 Features Comparison

| Feature | ChatSystem | Basic OpenAI |
|---------|------------|--------------|
| Function Calling | ✅ 12 tools | ❌ Manual setup |
| Structured Outputs | ✅ 100% compliance | ⚠️ ~95% |
| Streaming | ✅ Real-time | ✅ |
| Context Management | ✅ Auto-trim | ❌ Manual |
| Cost Tracking | ✅ Real-time | ❌ |
| Agentic Workflows | ✅ Built-in | ❌ |
| Conversation Memory | ✅ Auto-save | ❌ |
| Beautiful CLI | ✅ Rich UI | ❌ |

---

## 🤝 Contributing

The system is modular and extensible:

1. **Add New Tools**: Extend `tool_adapter.py` with new tool definitions
2. **Custom Agents**: Create new agent behaviors in `agent/`
3. **New Interfaces**: Build web/API interfaces alongside CLI

---

## 📝 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- **OpenAI** - GPT models and API
- **Pydantic** - Data validation
- **Rich** - Beautiful terminal UI
- **Tiktoken** - Token counting

---

## 🐛 Troubleshooting

### API Key Error
```
Error: OpenAI API key not configured
```
**Solution**: Set `OPENAI_API_KEY` in `.env` file

### Module Not Found
```
ModuleNotFoundError: No module named 'openai'
```
**Solution**: Run `pip install -r requirements.txt`

### Context Window Full
```
Warning: Context window at 95%
```
**Solution**: Use `/clear` command or conversation will auto-trim

---

**Built with ❤️ for the personalUtils project**
