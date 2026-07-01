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

## 🔒 Security & Costs (read before first run)

This is a local, single-user tool that lets an LLM drive real utilities on your
machine. Understand what that means before pointing it at anything sensitive:

- **File access.** Tools can read and write files **under the directory you launch
  it from** (the sandbox is rooted at your current working directory). Paths outside
  that root are rejected, and known secret files (`.env`, `*.pem`, `id_*`, `.netrc`)
  are refused by the generic file tools — but everything else under the cwd is fair
  game. **Run it from a dedicated scratch directory that contains no credentials.**
- **Network access.** The API-tester tool can make outbound HTTP(S) requests. Requests
  to private/loopback/link-local addresses and cloud-metadata IPs are blocked (including
  across redirects), but any public host is allowed. Treat it like giving the model a
  restricted `curl`.
- **Cost.** Every message and tool round is a paid OpenAI API call. Long, tool-heavy
  sessions cost more. Use `gpt-4o-mini` and watch `/stats`.
- **Side effects.** Some tools change state (write files, store snippets). Destructive
  ones require explicit confirmation: BulkRename and env writes are never executed
  headlessly, DuplicateFinder deletion is a dry run unless you pass `--force`, and
  DataConvert refuses to overwrite an existing file without `--overwrite`.

**What is guaranteed:** subprocesses run with `shell=False` (no shell injection), path
arguments are sandboxed to the cwd, secrets are stripped from the child environment,
private-IP network targets are blocked, and conversation history is written `0600`.
**What is not:** the model's judgment. A prompt injection in content you feed it (a
transcript, a file) can still cause it to call tools you didn't intend within those
limits, so don't run it against untrusted input on a machine that holds secrets.

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
