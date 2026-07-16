#!/usr/bin/env python3
"""
ChatCLI - Interactive CLI interface with Rich formatting
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import TextColumn

from pydantic import ValidationError

from ..core.config import Settings, get_settings
from ..core.chat_engine import ChatEngine
from ..core import sessions
from ..tools.tool_registry import ToolRegistry
from agents.agent_manager import AgentManager, AgentType


class ChatCLI:
    """Interactive chat CLI with Rich formatting"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.console = Console()
        self.cli_config = self.settings.get_cli_config()

        # Initialize tools: sandbox path args to the working directory and apply
        # the configured per-tool timeout (full security hardening).
        enabled_tools = self.settings.get_enabled_tools()
        self.tool_registry = ToolRegistry(
            enabled_tools=enabled_tools,
            timeout=self.settings.tool_timeout_seconds,
            sandbox_root=os.getcwd(),
        )

        # Active session. "default" maps to the legacy history path (None ->
        # ChatEngine falls back to settings/config); named sessions carry their
        # own history file under ~/.chatsystem_sessions/.
        self.session_name = sessions.DEFAULT_SESSION
        self._session_history: Optional[str] = None

        # Let ChatEngine build the conversation from the conversation config
        # (correct context window, auto-save, auto-summarize, history path).
        self.chat_engine = self._build_engine(self._session_history)
        self.conversation = self.chat_engine.conversation

        # Initialize agent manager
        self.agent_manager = AgentManager(settings=self.settings)

        # Get default agent from config
        agent_config = self.settings.get_agent_config()
        default_agent_name = agent_config.get("default_agent", "task_executor")
        default_agent_type = AgentManager.parse_agent_type(default_agent_name) or AgentType.TASK_EXECUTOR

        # Set current agent
        self.agent_manager.set_current_agent(default_agent_type, chat_engine=self.chat_engine)
        self.agent = self.agent_manager.get_current_agent()

    def display_welcome(self):
        """Display welcome message"""
        current_agent_info = self.agent_manager.get_agent_info(self.agent_manager.current_agent_type)

        welcome_text = f"""
# 🤖 ChatSystem v2.0

**Powered by:** {self.settings.model_name}
**Current Agent:** {current_agent_info.get('name', 'Unknown')}
**Tools Available:** {len(self.tool_registry.tools)}
**Context window:** {self.chat_engine.conversation.max_tokens:,} tokens
**Max response:** {self.settings.max_tokens:,} tokens

Type your message or try these commands:
- `/help` - Show available commands
- `/agents` - List available agents
- `/agent` - Switch agent
- `/tools` - List available tools
- `/session` - Manage named conversation sessions
- `/stats` - Show usage statistics
- `/health` - Tool health dashboard
- `/clear` - Clear conversation
- `/exit` - Exit the chat
        """

        self.console.print(Panel(
            Markdown(welcome_text, code_theme=self.cli_config["theme"]),
            style="bold cyan", border_style="cyan"
        ))

    def display_help(self):
        """Display help information"""
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        commands = [
            ("/help", "Show this help message"),
            ("/agents", "List all available agents"),
            ("/agent", "Switch to a different agent"),
            ("/tools", "List all available tools"),
            ("/session", "Manage named sessions (list/new/switch/delete)"),
            ("/stats", "Show usage statistics"),
            ("/health", "Show tool health metrics"),
            ("/context", "Show context window usage"),
            ("/show_reasoning", "Display reasoning trace from last task"),
            ("/summarize", "Manually trigger conversation summarization"),
            ("/clear", "Clear conversation history"),
            ("/export", "Export conversation to file"),
            ("/model", "Change model"),
            ("/exit or /quit", "Exit the chat"),
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)

        self.console.print(table)

    def display_tools(self):
        """Display available tools"""
        table = Table(title="Available Tools", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Function Name", style="green", no_wrap=True)
        table.add_column("Description", style="white")

        tools = self.tool_registry.get_tools()

        for i, tool in enumerate(tools, 1):
            func = tool["function"]
            table.add_row(
                str(i),
                func["name"],
                func["description"][:80] + "..." if len(func["description"]) > 80 else func["description"]
            )

        self.console.print(table)

    def display_stats(self):
        """Display usage statistics"""
        stats = self.chat_engine.get_stats()

        # Create stats table
        table = Table(title="Usage Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow", justify="right")

        table.add_row("Total Requests", str(stats["total_requests"]))
        table.add_row("Input Tokens", f"{stats['total_input_tokens']:,}")
        table.add_row("Output Tokens", f"{stats['total_output_tokens']:,}")
        table.add_row("Total Cost", f"${stats['total_cost']:.4f}")
        table.add_row("Tool Calls", str(stats["tool_calls_made"]))

        # Add conversation stats
        conv_summary = stats["conversation_summary"]
        table.add_row("Messages", str(conv_summary["total_messages"]))

        # Context usage
        context_usage = conv_summary["context_usage"]
        table.add_row("Context Used", f"{context_usage['usage_percent']:.1f}%")
        table.add_row("Tokens Used", f"{context_usage['total_tokens']:,} / {context_usage['max_tokens']:,}")

        self.console.print(table)

        # Show tool metrics summary if available
        tool_metrics = stats.get("tool_metrics", {})
        if tool_metrics:
            self.console.print("\n[dim]Use /health to see detailed tool metrics[/dim]")

    def display_context_usage(self):
        """Display context window usage"""
        usage = self.conversation.get_context_window_usage()

        # Create progress bar
        from rich.progress import BarColumn, Progress

        progress = Progress(
            TextColumn("[bold blue]Context Window"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )

        progress.add_task(
            "usage",
            total=usage["max_tokens"],
            completed=usage["total_tokens"]
        )

        self.console.print(progress)
        self.console.print(f"\n[cyan]Tokens:[/cyan] {usage['total_tokens']:,} / {usage['max_tokens']:,}")
        self.console.print(f"[cyan]Remaining:[/cyan] {usage['remaining_tokens']:,}")

    def display_agents(self):
        """Display available agents"""
        table = Table(title="Available Agents", show_header=True, border_style="cyan")
        table.add_column("Agent", style="cyan", no_wrap=True, width=25)
        table.add_column("Description", style="white", width=40)
        table.add_column("Use Cases", style="yellow", width=35)

        agents_info = self.agent_manager.list_agents()
        current_agent = self.agent_manager.current_agent_type.value

        for agent_type, info in agents_info.items():
            # Mark current agent
            agent_name = f"[bold green]✓ {info['name']}[/bold green]" if agent_type == current_agent else info['name']
            short_name = f"({info['short_name']})"
            use_cases = "\n".join([f"• {uc}" for uc in info['use_cases'][:2]])  # Show first 2

            table.add_row(
                f"{agent_name}\n{short_name}",
                info['description'],
                use_cases
            )

        self.console.print(table)
        self.console.print("\n[dim]Use `/agent <name>` to switch agents[/dim]")

    def display_health(self):
        """Display tool health metrics"""
        stats = self.chat_engine.get_stats()
        tool_metrics = stats.get("tool_metrics", {})

        if not tool_metrics:
            self.console.print("[yellow]No tool metrics available yet. Tools will appear here after first use.[/yellow]")
            return

        # Create health table
        table = Table(title="Tool Health Dashboard", show_header=True, border_style="cyan")
        table.add_column("Tool", style="cyan", no_wrap=True, width=25)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Calls", justify="right", width=8)
        table.add_column("Success Rate", justify="right", width=13)
        table.add_column("Avg Latency", justify="right", width=12)
        table.add_column("Last Error", style="red", width=40)

        # Sort by total calls (most used first)
        sorted_tools = sorted(
            tool_metrics.items(),
            key=lambda x: x[1]["total_calls"],
            reverse=True
        )

        for tool_name, metrics in sorted_tools:
            # Determine health status and color
            health_status = metrics.get("health_status", "unknown")
            if health_status == "healthy":
                status_icon = "[green]✓ Healthy[/green]"
            elif health_status == "degraded":
                status_icon = "[yellow]⚠ Degraded[/yellow]"
            elif health_status == "unhealthy":
                status_icon = "[red]✗ Unhealthy[/red]"
            else:
                status_icon = "[dim]? Unknown[/dim]"

            # Color code success rate
            success_rate = metrics.get("success_rate", "0.0%")
            success_val = float(success_rate.rstrip('%'))
            if success_val >= 90:
                rate_display = f"[green]{success_rate}[/green]"
            elif success_val >= 70:
                rate_display = f"[yellow]{success_rate}[/yellow]"
            else:
                rate_display = f"[red]{success_rate}[/red]"

            # Get last error (truncate if too long)
            last_error = metrics.get("last_error") or ""
            if len(last_error) > 40:
                last_error = last_error[:37] + "..."

            table.add_row(
                tool_name,
                status_icon,
                str(metrics.get("total_calls", 0)),
                rate_display,
                metrics.get("avg_duration", "N/A"),
                last_error
            )

        self.console.print(table)

        # Show summary statistics
        total_tools_used = len(tool_metrics)
        healthy_tools = sum(1 for m in tool_metrics.values() if m.get("health_status") == "healthy")
        degraded_tools = sum(1 for m in tool_metrics.values() if m.get("health_status") == "degraded")
        unhealthy_tools = sum(1 for m in tool_metrics.values() if m.get("health_status") == "unhealthy")

        summary = f"\n[cyan]Summary:[/cyan] {total_tools_used} tools used"
        if healthy_tools > 0:
            summary += f" | [green]{healthy_tools} healthy[/green]"
        if degraded_tools > 0:
            summary += f" | [yellow]{degraded_tools} degraded[/yellow]"
        if unhealthy_tools > 0:
            summary += f" | [red]{unhealthy_tools} unhealthy[/red]"

        self.console.print(summary)

    def display_reasoning_trace(self):
        """Display reasoning trace from the current agent (if available)"""
        # Check if current agent has reasoning capabilities
        if hasattr(self.agent, 'get_reasoning_trace'):
            try:
                trace = self.agent.get_reasoning_trace(include_metadata=True)

                if trace and "🧠 Reasoning Trace" in trace:
                    panel = Panel(
                        trace,
                        title="🧠 Reasoning Trace",
                        border_style="magenta",
                        expand=False
                    )
                    self.console.print(panel)
                else:
                    self.console.print("[yellow]No reasoning trace available. Execute a task first.[/yellow]")

            except Exception as e:
                self.console.print(f"[red]Error retrieving reasoning trace:[/red] {e}")
        else:
            self.console.print("[yellow]Current agent does not support reasoning traces.[/yellow]")

    def summarize_conversation(self):
        """Manually trigger conversation summarization"""
        usage = self.conversation.get_context_window_usage()
        current_tokens = usage["total_tokens"]
        max_tokens = usage["max_tokens"]
        usage_percent = usage["usage_percent"]

        self.console.print(f"\n[cyan]Current token usage:[/cyan] {current_tokens:,} / {max_tokens:,} ({usage_percent:.1f}%)")

        if usage_percent < 30:
            self.console.print("[yellow]Warning: Conversation is quite short. Summarization may not be beneficial.[/yellow]")

        if not Confirm.ask("Proceed with summarization?", default=True):
            return

        try:
            with self.console.status("[cyan]Generating summary...", spinner="dots"):
                summary = self.conversation.summarize_conversation(
                    chat_engine=self.chat_engine,
                    target_ratio=0.6
                )

            # Show new token usage
            new_usage = self.conversation.get_context_window_usage()
            saved_tokens = current_tokens - new_usage["total_tokens"]
            saved_percent = (saved_tokens / current_tokens * 100) if current_tokens > 0 else 0

            panel = Panel(
                f"[green]✓[/green] Conversation summarized!\n\n"
                f"[cyan]Before:[/cyan] {current_tokens:,} tokens ({usage_percent:.1f}%)\n"
                f"[cyan]After:[/cyan] {new_usage['total_tokens']:,} tokens ({new_usage['usage_percent']:.1f}%)\n"
                f"[green]Saved:[/green] {saved_tokens:,} tokens ({saved_percent:.1f}%)\n\n"
                f"[dim]{summary[:300]}{'...' if len(summary) > 300 else ''}[/dim]",
                title="Summarization Complete",
                border_style="green"
            )
            self.console.print(panel)

        except Exception as e:
            self.console.print(f"[red]Error during summarization:[/red] {e}")

    def _build_engine(self, history_file: Optional[str]) -> ChatEngine:
        """Build a ChatEngine on the given history file, tools registered."""
        engine = ChatEngine(settings=self.settings, history_file=history_file)
        engine.register_tools(
            self.tool_registry.get_tools(), self.tool_registry.get_tool_executor()
        )
        return engine

    def _activate_session(self, name: str, path: Optional[str]):
        """Point the CLI at a session's history file and rebuild engine + agent on it."""
        # Build first, mutate after — a failed rebuild must not leave the CLI
        # claiming a session it never activated.
        engine = self._build_engine(path)
        self.agent_manager.set_current_agent(
            self.agent_manager.current_agent_type, chat_engine=engine
        )
        self.agent = self.agent_manager.get_current_agent()
        self.chat_engine = engine
        self.conversation = engine.conversation
        self.session_name = name
        self._session_history = path
        self.console.print(f"\n[green]✓ Session:[/green] {name}")

    def display_sessions(self):
        """Show the active session and all saved sessions"""
        table = Table(title="Sessions", show_header=True)
        table.add_column("Session", style="cyan", no_wrap=True)
        table.add_column("Last Modified", style="white")

        from datetime import datetime

        # Same fallback ConversationManager uses when no history path is configured
        default_path = Path(self.settings.history_file).expanduser() if self.settings.history_file \
            else Path.home() / ".chatsystem_history.json"

        names = [sessions.DEFAULT_SESSION] + sessions.list_sessions()
        for name in names:
            path = default_path if name == sessions.DEFAULT_SESSION else sessions.session_path(name)
            modified = "—"
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                modified = mtime.strftime("%Y-%m-%d %H:%M")
            marker = "* " if name == self.session_name else "  "
            table.add_row(f"{marker}{name}", modified)

        self.console.print(table)
        self.console.print("[dim]Usage: /session list | new <name> | switch <name> | delete <name>[/dim]")

    def handle_session_command(self, arg: Optional[str]):
        """Handle /session subcommands: list (default), new, switch, delete"""
        parts = arg.split(maxsplit=1) if arg else []
        sub = parts[0].lower() if parts else "list"
        name = parts[1].strip() if len(parts) > 1 else None

        if sub == "list":
            self.display_sessions()
            return
        if sub not in ("new", "switch", "delete"):
            self.console.print(f"[red]Unknown subcommand:[/red] {sub}")
            self.console.print("Usage: /session list | new <name> | switch <name> | delete <name>")
            return
        if not name:
            self.console.print(f"[red]Usage:[/red] /session {sub} <name>")
            return

        # Sessions ride ConversationManager's auto-save persistence; without it
        # nothing is loaded or written, so activation would silently no-op.
        if sub in ("new", "switch") and not self.conversation.auto_save:
            self.console.print(
                "[red]Sessions require auto-save.[/red] Enable conversation.auto_save_history in config.yaml"
            )
            return

        if name == sessions.DEFAULT_SESSION:
            if sub != "switch":
                self.console.print(
                    f"[red]'{sessions.DEFAULT_SESSION}' is reserved[/red] — it is the main history and cannot be created or deleted"
                )
                return
            path = None
        else:
            try:
                path = str(sessions.session_path(name))
            except ValueError as e:
                self.console.print(f"[red]Invalid session name:[/red] {e}")
                return
            # On case-insensitive filesystems (macOS default) "WORK" opens
            # work.json — canonicalize to the on-disk name so the active-session
            # guards compare like with like.
            existing = sessions.list_sessions()
            if name not in existing and Path(path).exists():
                match = next((s for s in existing if s.lower() == name.lower()), None)
                if match:
                    name = match
                    path = str(sessions.session_path(match))

        if sub == "delete":
            if name == self.session_name:
                self.console.print("[red]Cannot delete the active session.[/red] Switch away first.")
                return
            if not Path(path).exists():
                self.console.print(f"[red]No session named:[/red] {name}")
                return
            if Confirm.ask(f"Delete session '{name}'?"):
                sessions.delete_session(name)
                self.console.print(f"[green]✓[/green] Deleted session '{name}'")
            return

        if name == self.session_name:
            self.console.print(f"[yellow]Already in session:[/yellow] {name}")
            return

        if sub == "new" and Path(path).exists():
            self.console.print(
                f"[red]Session '{name}' already exists.[/red] Use /session switch {name}"
            )
            return
        if sub == "switch" and path is not None and not Path(path).exists():
            if not Confirm.ask(f"No session named '{name}'. Create it?"):
                return

        self._activate_session(name, path)

    def switch_agent(self, agent_name: Optional[str] = None):
        """Switch to a different agent"""
        if not agent_name:
            # Show current agent and prompt for selection
            current_info = self.agent_manager.get_agent_info(self.agent_manager.current_agent_type)
            self.console.print(f"\n[cyan]Current agent:[/cyan] {current_info['name']} ({current_info['short_name']})")
            agent_name = Prompt.ask("\nEnter agent name or short name")

        # Parse agent type
        agent_type = AgentManager.parse_agent_type(agent_name)

        if not agent_type:
            self.console.print(f"[red]Unknown agent:[/red] {agent_name}")
            self.console.print("Use [cyan]/agents[/cyan] to see available agents")
            return

        # Switch agent
        try:
            # Create a fresh chat engine (and its config-wired conversation) for
            # the new agent to avoid persona mixing. Stays on the active
            # session's history file.
            new_chat_engine = self._build_engine(self._session_history)
            new_conversation = new_chat_engine.conversation

            # Set new agent
            self.agent_manager.set_current_agent(agent_type, chat_engine=new_chat_engine)
            self.agent = self.agent_manager.get_current_agent()

            # Update chat engine and conversation
            self.chat_engine = new_chat_engine
            self.conversation = new_conversation

            agent_info = self.agent_manager.get_agent_info(agent_type)
            self.console.print(f"\n[green]✓ Switched to:[/green] {agent_info['name']}")
            self.console.print(f"[dim]{agent_info['description']}[/dim]\n")

        except Exception as e:
            self.console.print(f"[red]Error switching agent:[/red] {str(e)}")

    def handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if should continue, False to exit"""

        cmd = command.lower().strip()
        parts = command.strip().split(maxsplit=1)
        base_cmd = parts[0].lower()
        cmd_arg = parts[1] if len(parts) > 1 else None

        if cmd in ["/exit", "/quit", "/q"]:
            self.console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
            return False

        elif cmd == "/help":
            self.display_help()

        elif cmd == "/agents":
            self.display_agents()

        elif base_cmd == "/agent":
            self.switch_agent(cmd_arg)

        elif base_cmd == "/session":
            self.handle_session_command(cmd_arg)

        elif cmd == "/tools":
            self.display_tools()

        elif cmd == "/stats":
            self.display_stats()

        elif cmd == "/health":
            self.display_health()

        elif cmd == "/context":
            self.display_context_usage()

        elif cmd == "/show_reasoning":
            self.display_reasoning_trace()

        elif cmd == "/summarize":
            self.summarize_conversation()

        elif cmd == "/clear":
            if Confirm.ask("Clear conversation history?"):
                self.chat_engine.reset()
                self.console.print("[green]✓[/green] Conversation cleared!")

        elif cmd == "/export":
            filename = Prompt.ask("Export filename", default="conversation.json")
            self.conversation.export_conversation(filename)
            self.console.print(f"[green]✓[/green] Exported to {filename}")

        elif cmd == "/model":
            self.console.print(f"\n[cyan]Current model:[/cyan] {self.settings.model_name}")
            # Could add model switching here

        else:
            self.console.print(f"[red]Unknown command:[/red] {command}")
            self.console.print("Type [cyan]/help[/cyan] for available commands")

        return True

    def run(self) -> None:
        """Run the interactive chat loop"""

        # Display welcome
        self.display_welcome()

        while True:
            try:
                # Get user input
                self.console.print()
                user_input = Prompt.ask("[bold green]You[/bold green]")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    should_continue = self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Route the turn through the active agent's primary method
                # (e.g. the task_executor runs its full plan→reason→act loop).
                # Agent methods return a complete response string, so we show a
                # spinner while it works, then render the Markdown result.
                self.console.print()
                agent_info = self.agent_manager.get_agent_info(
                    self.agent_manager.current_agent_type
                )
                self.console.print(
                    f"[bold cyan]🤖 {agent_info.get('name', 'Assistant')}:[/bold cyan]"
                )

                with self.console.status("[cyan]Working...", spinner="dots"):
                    response = self.agent_manager.dispatch(user_input)

                self.console.print(
                    Markdown(response or "", code_theme=self.cli_config["theme"])
                )

                # Optional per-response context footer (cli.show_token_usage)
                if self.cli_config.get("show_token_usage"):
                    usage = self.conversation.get_context_window_usage()
                    self.console.print(
                        f"[dim]Context: {usage['total_tokens']:,}/{usage['max_tokens']:,} "
                        f"({usage['usage_percent']:.1f}%)[/dim]"
                    )

            except KeyboardInterrupt:
                self.console.print("\n\n[yellow]Interrupted. Use /exit to quit properly.[/yellow]\n")
                continue  # Continue the loop instead of exiting

            except EOFError:
                self.console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                break

            except Exception as e:
                self.console.print(f"\n[red]Error:[/red] {str(e)}\n")
                if self.settings.log_level == "DEBUG":
                    import traceback
                    self.console.print(traceback.format_exc())
                continue  # Continue after error


_MISSING_KEY_HELP = (
    "\n[red]Missing OpenAI API key.[/red] Set OPENAI_API_KEY before starting:\n\n"
    "  cp .env.example .env      # then edit .env and set OPENAI_API_KEY=sk-...\n"
    "  # or: export OPENAI_API_KEY=sk-...\n\n"
    "See CHATSYSTEM_SETUP.md for setup details.\n"
)


def main():
    """Main entry point"""
    console = Console()

    # An unset key surfaces as a pydantic ValidationError; an empty or
    # placeholder key passes validation but fails deep in the OpenAI SDK. Catch
    # both here and print actionable guidance instead of a raw SDK error.
    try:
        settings = get_settings()
    except ValidationError as e:
        # Only a missing/blank OPENAI_API_KEY should show the key help. Any other
        # invalid setting (e.g. a bad MODEL_NAME) must surface its real error
        # rather than misdirect the user to key setup.
        if any("openai_api_key" in str(loc)
               for err in e.errors() for loc in err.get("loc", ())):
            console.print(_MISSING_KEY_HELP)
        else:
            console.print(f"\n[red]Fatal Error:[/red] {e}\n")
        sys.exit(1)

    api_key = (settings.openai_api_key or "").strip()
    if not api_key or api_key == "your-api-key-here":
        console.print(_MISSING_KEY_HELP)
        sys.exit(1)

    try:
        # Wire log_file / log_level (previously unused config)
        logging.basicConfig(
            filename=settings.log_file,
            level=getattr(logging, settings.log_level, logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        cli = ChatCLI(settings=settings)
        cli.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal Error:[/red] {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
