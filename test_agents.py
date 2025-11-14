#!/usr/bin/env python3
"""
Test script for the three new AI agents.

This script demonstrates the capabilities of each agent:
1. Transcript Analyzer - Analyzes transcripts for business value, skills, frameworks
2. Trillionaire Futurist - Strategic advisor operating at trillionaire scale
3. Framework Teacher - Teaches through frameworks and mental models
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from ChatSystem.core.config import get_settings
from agents.agent_manager import AgentManager, AgentType


def test_transcript_analyzer():
    """Test the Transcript Analyzer agent."""
    console = Console()
    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]Testing Transcript Analyzer Agent[/bold cyan]"))
    console.print("="*80 + "\n")

    settings = get_settings()
    agent_manager = AgentManager(settings=settings)

    # Get the transcript analyzer
    agent = agent_manager.get_agent(AgentType.TRANSCRIPT_ANALYZER)

    # Sample transcript
    sample_transcript = """
    Naval Ravikant: The way I think about wealth creation is very simple.
    You're not going to get rich renting out your time. You must own equity -
    a piece of a business - to gain your financial freedom.

    The internet has massively broadened the possible space of careers.
    Most people haven't figured this out yet. You can now reach any niche audience
    if you're authentic and unique. Build a brand, build a following, and
    opportunities will come to you.

    Specific knowledge is found by pursuing your genuine curiosity and your innate
    talents. It's usually highly technical or creative. It cannot be trained but
    it can be learned. When specific knowledge is taught, it's through apprenticeships,
    not schools.

    Leverage is critical. You want to be using code and media as your leverage.
    Those have zero marginal cost of replication. That's where the big fortunes are made.
    """

    console.print("[yellow]Sample Transcript (Naval Ravikant):[/yellow]")
    console.print(Panel(sample_transcript, style="dim"))
    console.print()

    console.print("[yellow]Requesting quick summary...[/yellow]\n")

    try:
        # Get quick summary
        result = agent.quick_summary(sample_transcript)
        console.print(Markdown(result["summary"]))

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())

    console.print("\n[dim]Note: For full analysis, use agent.analyze(transcript)[/dim]\n")


def test_trillionaire_futurist():
    """Test the Trillionaire Futurist agent."""
    console = Console()
    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]Testing Trillionaire Futurist Agent[/bold cyan]"))
    console.print("="*80 + "\n")

    settings = get_settings()
    agent_manager = AgentManager(settings=settings)

    # Get the trillionaire futurist
    agent = agent_manager.get_agent(AgentType.TRILLIONAIRE_FUTURIST)

    # Sample strategic question
    question = """
    I'm 28, have $500K saved, working in tech at $300K/year.
    Should I start an AI company or stay at my current job?
    """

    console.print("[yellow]Strategic Question:[/yellow]")
    console.print(Panel(question, style="dim"))
    console.print()

    console.print("[yellow]Getting trillionaire-level strategic guidance...[/yellow]\n")

    try:
        response = agent.respond(question)
        console.print(Markdown(response))

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())

    console.print()


def test_framework_teacher():
    """Test the Framework Teacher agent."""
    console = Console()
    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]Testing Framework Teacher Agent[/bold cyan]"))
    console.print("="*80 + "\n")

    settings = get_settings()
    agent_manager = AgentManager(settings=settings)

    # Get the framework teacher
    agent = agent_manager.get_agent(AgentType.FRAMEWORK_TEACHER)

    # Sample learning request
    learning_request = """
    How should I respond when someone asks me a difficult question randomly
    in a meeting or conversation?
    """

    console.print("[yellow]Learning Request:[/yellow]")
    console.print(Panel(learning_request, style="dim"))
    console.print()

    console.print("[yellow]Getting framework-based teaching...[/yellow]\n")

    try:
        # Get quick framework
        response = agent.quick_framework("responding to difficult questions")
        console.print(Markdown(response))

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())

    console.print("\n[dim]Note: For full teaching, use agent.teach(request)[/dim]\n")


def test_agent_manager():
    """Test the Agent Manager functionality."""
    console = Console()
    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]Testing Agent Manager[/bold cyan]"))
    console.print("="*80 + "\n")

    settings = get_settings()
    agent_manager = AgentManager(settings=settings)

    # List all agents
    console.print("[yellow]Available Agents:[/yellow]\n")
    console.print(agent_manager.format_agent_list())

    # Test agent parsing
    console.print("\n[yellow]Testing Agent Name Parsing:[/yellow]\n")
    test_names = ["analyzer", "futurist", "teacher", "transcript", "framework"]

    for name in test_names:
        agent_type = AgentManager.parse_agent_type(name)
        if agent_type:
            info = agent_manager.get_agent_info(agent_type)
            console.print(f"✓ '{name}' → {info['name']}")
        else:
            console.print(f"✗ '{name}' → Not found")

    console.print()


def main():
    """Run all tests."""
    console = Console()

    console.print("\n")
    console.print(Panel(
        "[bold green]Three Agent System Test Suite[/bold green]\n\n"
        "This will test all three new agents:\n"
        "1. Transcript Analyzer\n"
        "2. Trillionaire Futurist\n"
        "3. Framework Teacher\n\n"
        "[dim]Press Ctrl+C to skip a test[/dim]",
        style="bold",
        border_style="green"
    ))
    console.print()

    tests = [
        ("Agent Manager", test_agent_manager),
        ("Transcript Analyzer", test_transcript_analyzer),
        ("Trillionaire Futurist", test_trillionaire_futurist),
        ("Framework Teacher", test_framework_teacher),
    ]

    for test_name, test_func in tests:
        try:
            console.print(f"\n[bold blue]Running: {test_name}[/bold blue]")
            test_func()
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Skipped: {test_name}[/yellow]\n")
            continue
        except Exception as e:
            console.print(f"\n[red]Failed: {test_name}[/red]")
            console.print(f"[red]Error:[/red] {str(e)}\n")
            import traceback
            console.print(traceback.format_exc())
            continue

    console.print("\n" + "="*80)
    console.print(Panel("[bold green]✓ Test Suite Complete[/bold green]"))
    console.print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n\n[yellow]Tests interrupted by user[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Fatal Error:[/red] {str(e)}\n")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
