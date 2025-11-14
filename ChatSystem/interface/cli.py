#!/usr/bin/env python3
"""
ChatCLI - Interactive CLI interface with Rich formatting
"""

import sys
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.prompt import Prompt, Confirm
from rich.progress import TextColumn

from ..core.config import Settings, get_settings
from ..core.chat_engine import ChatEngine
from ..core.conversation import ConversationManager
from ..tools.tool_registry import ToolRegistry
from agents.agent_manager import AgentManager, AgentType


class ChatCLI:
    """Interactive chat CLI with Rich formatting"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.console = Console()

        # Initialize components
        self.conversation = ConversationManager(
            model=self.settings.model_name,
            max_tokens=self.settings.max_tokens,
        )

        self.chat_engine = ChatEngine(
            settings=self.settings,
            conversation=self.conversation,
        )

        # Initialize tools
        enabled_tools = self.settings.get_enabled_tools()
        self.tool_registry = ToolRegistry(enabled_tools=enabled_tools)

        # Register tools with chat engine
        tools = self.tool_registry.get_tools()
        executor = self.tool_registry.get_tool_executor()
        self.chat_engine.register_tools(tools, executor)

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
# 🤖 ChatSystem v1.0

**Powered by:** {self.settings.model_name}
**Current Agent:** {current_agent_info.get('name', 'Unknown')}
**Tools Available:** {len(self.tool_registry.tools)}
**Context:** {self.settings.max_tokens:,} tokens

Type your message or try these commands:
- `/help` - Show available commands
- `/agents` - List available agents
- `/agent` - Switch agent
- `/tools` - List available tools
- `/stats` - Show usage statistics
- `/clear` - Clear conversation
- `/exit` - Exit the chat
        """

        self.console.print(Panel(Markdown(welcome_text), style="bold cyan", border_style="cyan"))

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
            ("/stats", "Show usage statistics"),
            ("/context", "Show context window usage"),
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
            # Create new chat engine for the new agent to avoid persona mixing
            new_conversation = ConversationManager(
                model=self.settings.model_name,
                max_tokens=self.settings.max_tokens,
            )

            new_chat_engine = ChatEngine(
                settings=self.settings,
                conversation=new_conversation,
            )

            # Register tools with new chat engine
            tools = self.tool_registry.get_tools()
            executor = self.tool_registry.get_tool_executor()
            new_chat_engine.register_tools(tools, executor)

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

        elif cmd == "/tools":
            self.display_tools()

        elif cmd == "/stats":
            self.display_stats()

        elif cmd == "/context":
            self.display_context_usage()

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

                # Display thinking indicator
                self.console.print()

                # Stream response
                self.console.print("[bold cyan]🤖 Assistant:[/bold cyan]")

                response_parts = []
                for chunk in self.chat_engine.chat(user_input):
                    self.console.print(chunk, end="")
                    response_parts.append(chunk)

                self.console.print()  # New line after response

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


def main():
    """Main entry point"""
    try:
        cli = ChatCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋\n")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Fatal Error:[/red] {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
