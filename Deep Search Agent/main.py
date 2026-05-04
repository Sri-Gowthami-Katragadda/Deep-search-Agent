"""
main.py
───────
CLI Entry Point for the Financial Deep Research Agent.

Usage:
    python main.py                          # Interactive mode
    python main.py --query "Analyze TCS"   # Single query mode
    python main.py --ingest path.pdf --sector it  # Ingest documents
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.markdown import Markdown
from rich import print as rprint

# ── Bootstrap: ensure project root is on the path ────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from agents.router_agent import RouterAgent
from core.report_generator import ReportGenerator
from utils.logger import log_section
from config.settings import get_settings

console = Console()
router = RouterAgent()
report_gen = ReportGenerator()
settings = get_settings()


# ── BANNER ────────────────────────────────────────────────────────────────────

def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║         💹  FINANCIAL DEEP RESEARCH AGENT  💹                   ║
║                                                                  ║
║   Sector Coverage: IT Services  |  Pharmaceuticals              ║
║   Powered by: Groq (LLaMA 3.3 70B) + Tavily Search             ║
║   Research Depth: 5–20 iterative steps per query                ║
╚══════════════════════════════════════════════════════════════════╝
"""
    console.print(Panel(banner, style="bold cyan", border_style="cyan"))


# ── PLAN DISPLAY ──────────────────────────────────────────────────────────────
# takes the plan object and hows the tables and asks proceed yes or no
def display_research_plan(plan) -> bool:
    """Show the research plan to the user and get approval."""
    console.print("\n")
    console.print(Panel(
        f"[bold yellow]📋 RESEARCH PLAN[/bold yellow]\n"
        f"[white]Title:[/white] {plan.research_title}\n"
        f"[white]Type:[/white] {plan.query_type}\n"
        f"[white]Estimated Steps:[/white] {plan.estimated_steps}",
        border_style="yellow",
    ))

    # Research phases table
    table = Table(title="Research Phases", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Phase", style="cyan")
    table.add_column("Objective", style="white")
    table.add_column("Initial Queries", style="green")

    for phase in plan.research_phases:
        queries_preview = " | ".join(phase.search_queries[:2])
        table.add_row(
            str(phase.phase_number),
            phase.phase_name,
            phase.objective[:60] + ("..." if len(phase.objective) > 60 else ""),
            queries_preview[:80] + ("..." if len(queries_preview) > 80 else ""),
        )
    console.print(table)

    # Key questions
    if plan.key_questions_to_answer:
        console.print("\n[bold]🎯 Key Questions to Answer:[/bold]")
        for i, q in enumerate(plan.key_questions_to_answer, 1):
            console.print(f"  {i}. {q}")

    # Expected sections
    if plan.expected_report_sections:
        console.print("\n[bold]📄 Report Will Cover:[/bold]")
        console.print("  " + "  •  ".join(plan.expected_report_sections))

    console.print()
    return Confirm.ask("[bold green]Proceed with this research plan?[/bold green]", default=True)


# ── PROGRESS DISPLAY ──────────────────────────────────────────────────────────

class ResearchProgressTracker:
    """Tracks and displays research progress."""

    def __init__(self, max_steps: int):
        self.max_steps = max_steps
        self.current = 0

    def update(self, step: int, query: str):
        self.current = step
        console.print(
            f"  [dim cyan]Step {step}/{self.max_steps}[/dim cyan] "
            f"[white]→[/white] [yellow]{query[:90]}[/yellow]"
        )


# ── INTERACTIVE MODE ──────────────────────────────────────────────────────────
# main loop. keeps asking queries until you type quit 
def interactive_mode():
    """Full interactive CLI research session."""
    print_banner()

    console.print(
        "\n[dim]Type your financial research query below. "
        "Examples:[/dim]\n"
        "  • Analyze the Indian IT sector outlook for 2025\n"
        "  • Compare TCS vs Infosys financial performance\n"
        "  • Emerging trends in Indian pharmaceutical biosimilars\n"
        "  • Impact of rupee depreciation on IT exports\n"
    )

    while True:
        console.print()
        query = Prompt.ask("[bold green]🔍 Enter your research query[/bold green] (or 'quit' to exit)")

        if query.lower() in ("quit", "exit", "q"):
            console.print("[yellow]Goodbye! 👋[/yellow]")
            break

        if not query.strip():
            continue

        # ── Route the query ────────────────────────────────────────────────
        log_section("Query Analysis")
        decision = router.route_query(query)

        console.print(
            f"[bold]Routing Decision:[/bold] "
            f"Sector=[cyan]{decision.sector.upper()}[/cyan]  "
            f"Type=[magenta]{decision.query_type}[/magenta]  "
            f"Confidence=[green]{decision.confidence:.0%}[/green]"
        )

        if decision.sector == "out_of_scope":
            console.print(Panel(
                "❌ This query is outside the financial research domain.\n"
                "I can research IT services and Pharma sectors.\n"
                f"[dim]{decision.reasoning}[/dim]",
                style="red",
            ))
            continue

        if decision.sector == "clarification_needed":
            clarification = router.get_clarification_message(decision)
            console.print(Panel(f"❓ {clarification}", style="yellow", title="Clarification Needed"))
            continue

        # ── Create and display research plan ──────────────────────────────
        log_section("Research Planning")
        agent = router.get_agents_for_sector(decision.sector)[0]

        with console.status("[bold cyan]Creating research plan...[/bold cyan]"):
            plan = agent.create_research_plan(query)

        if not plan:
            console.print("[red]Failed to create research plan. Please try again.[/red]")
            continue

        # ── User approval ──────────────────────────────────────────────────
        approved = display_research_plan(plan)
        if not approved:
            console.print("[yellow]Research cancelled. Enter a new query.[/yellow]")
            continue

        # Custom step limit?
        custom_steps = Prompt.ask(
            f"[dim]Max research steps (default: {plan.estimated_steps}, max: {settings.max_research_steps})[/dim]",
            default=str(plan.estimated_steps),
        )
        try:
            max_steps = min(int(custom_steps), settings.max_research_steps)
        except ValueError:
            max_steps = plan.estimated_steps

        # ── Execute research ───────────────────────────────────────────────
        log_section(f"Deep Research — {max_steps} Steps")
        tracker = ResearchProgressTracker(max_steps)

        console.print("[bold cyan]Research in progress...[/bold cyan]\n")
        session = agent.run_research(
            query=query,
            plan=plan,                      # ← pass approved plan, no duplicate LLM call
            max_steps=max_steps,
            progress_callback=tracker.update,
        )

        if not session:
            console.print("[red]Research failed. Please try again.[/red]")
            continue

        # ── Display results ────────────────────────────────────────────────
        log_section("Research Complete")
        console.print(
            f"✅ [bold green]Research completed![/bold green] "
            f"Steps: {len(session.steps)}  |  "
            f"Report: [cyan]{session.report_path}[/cyan]"
        )

        # Show report?
        if Confirm.ask("\n[bold]Display the research report?[/bold]", default=True):
            console.print()
            console.print(Markdown(session.final_report))

        console.print(f"\n[dim]📁 Report saved to: {session.report_path}[/dim]")


# ── SINGLE QUERY MODE ─────────────────────────────────────────────────────────

def single_query_mode(query: str, max_steps: int, no_plan: bool):
    """Run a single query and exit."""
    console.print(f"\n[bold cyan]Query:[/bold cyan] {query}")

    decision = router.route_query(query)

    if decision.sector in ("out_of_scope", "clarification_needed"):
        console.print(f"[red]Cannot process: {decision.reasoning}[/red]")
        sys.exit(1)

    agents = router.get_agents_for_sector(decision.sector)
    if not agents:
        console.print(f"[red]No agent for sector: {decision.sector}[/red]")
        sys.exit(1)

    agent = agents[0]

    plan = None
    if not no_plan:
        with console.status("[cyan]Creating research plan...[/cyan]"):
            plan = agent.create_research_plan(query)
        if plan:
            display_research_plan(plan)

    console.print(f"\n[cyan]Running research ({max_steps} max steps)...[/cyan]")
    tracker = ResearchProgressTracker(max_steps)

    session = agent.run_research(
        query=query,
        max_steps=max_steps,
        progress_callback=tracker.update,
        plan=plan,                          # ← pass plan, no duplicate LLM call
    )

    if session:
        console.print(f"\n[green]✅ Report saved: {session.report_path}[/green]")
        console.print(Markdown(session.final_report))
    else:
        console.print("[red]Research failed[/red]")
        sys.exit(1)


# ── INGEST MODE ───────────────────────────────────────────────────────────────

def ingest_mode(filepath: str, sector: str):
    """Ingest a document into the RAG knowledge base."""
    agent = router.get_agent(sector)
    if not agent:
        console.print(f"[red]Unknown sector: {sector}[/red]")
        sys.exit(1)

    console.print(f"[cyan]Ingesting {filepath} into {sector.upper()} knowledge base...[/cyan]")
    chunks = agent.ingest_document(filepath)
    console.print(f"[green]✅ Indexed {chunks} chunks[/green]")


# ── ARGPARSE ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Financial Deep Research Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                        # Interactive mode
  python main.py --query "Analyze TCS financials"      # Single query
  python main.py --query "..." --steps 15              # Custom depth
  python main.py --ingest report.pdf --sector pharma   # Ingest document
        """,
    )
    parser.add_argument("--query", "-q", help="Financial research query")
    parser.add_argument("--steps", "-s", type=int, default=10, help="Max research steps (default: 10)")
    parser.add_argument("--no-plan", action="store_true", help="Skip plan display")
    parser.add_argument("--ingest", help="Path to PDF to ingest into RAG")
    parser.add_argument("--sector", choices=["it", "pharma"], help="Sector for --ingest")

    args = parser.parse_args()

    if args.ingest:
        if not args.sector:
            console.print("[red]--sector required with --ingest[/red]")
            sys.exit(1)
        ingest_mode(args.ingest, args.sector)
    elif args.query:
        single_query_mode(args.query, args.steps, args.no_plan)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()