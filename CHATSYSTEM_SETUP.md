# 🚀 ChatSystem Quick Setup Guide

## Prerequisites
- Python 3.9+
- OpenAI API key

## Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or use your preferred editor
```

Add your API key:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
MODEL_NAME=gpt-4o
```

### 3. Test Installation
```bash
# Run basic test
python -c "from ChatSystem import get_settings; print('✓ ChatSystem imported successfully!')"

# Run example
python ChatSystem/examples/basic_chat.py
```

### 4. Start Interactive Chat
```bash
python -m ChatSystem
```

## 🎯 First Steps

Once in the chat, try these commands:

```
/help          # Show all commands
/tools         # See available tools
/stats         # View usage statistics
```

## 📝 Example Queries

Try asking:

1. **"What can you help me with?"** - Learn about capabilities
2. **"Analyze the code in ChatSystem/core"** - Use CodeWhisper tool
3. **"Find duplicate files in the current directory"** - Use DuplicateFinder
4. **"Extract all TODO comments from my code"** - Use TodoExtractor

## 💡 Tips

- Start with simple queries to understand the system
- Use `/tools` to see what utilities are available
- The agent will automatically choose the right tools
- Check `/stats` to monitor token usage and costs

## 🐛 Common Issues

### "OpenAI API key not configured"
**Solution**: Make sure you've set `OPENAI_API_KEY` in `.env`

### "Module not found"
**Solution**: Run `pip install -r requirements.txt`

### Rate limit errors
**Solution**: The free tier has limits. Use gpt-4o-mini for cost-effective testing.

## 📚 Next Steps

1. Read the full documentation: `ChatSystem/README.md`
2. Try the examples in `ChatSystem/examples/`
3. Customize `config.yaml` for your needs
4. Build custom tools by extending the tool system

## 🎉 You're Ready!

The ChatSystem is now configured and ready to use. Enjoy exploring the agentic capabilities!
