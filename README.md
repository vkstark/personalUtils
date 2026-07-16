# personalUtils

Personal Python toolkit: an OpenAI-powered chat system (`ChatSystem/`) with function
calling, four specialized agents (`agents/`), and twelve standalone CLI utilities
(`tools/`). The chat system exposes the utilities to the LLM as callable tools.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # then set OPENAI_API_KEY
python -m ChatSystem          # launch the interactive CLI
```

See [CHATSYSTEM_SETUP.md](CHATSYSTEM_SETUP.md) for the full setup guide,
[AGENTS_README.md](AGENTS_README.md) for agent behaviors, and `ChatSystem/README.md`
for the subsystem reference.

## Security note

This tool lets an LLM read/write files under your working directory, make outbound
HTTP requests, and spend money per API call. Run it from a dedicated scratch directory
that holds no credentials, and don't point it at untrusted input on a machine with
secrets. See the **Security & Costs** section of
[CHATSYSTEM_SETUP.md](CHATSYSTEM_SETUP.md) for the exact guarantees and limits.

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest                            # run the suite
pytest -m "not network"           # offline/fast subset
ruff check ChatSystem agents      # lint
mypy ChatSystem agents            # typecheck
```
