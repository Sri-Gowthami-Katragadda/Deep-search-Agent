"""
utils/logger.py
───────────────
Structured, colourful console logging using Rich.
"""

import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme
from config.settings import get_settings

console = Console(theme=Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "research": "bold magenta",
    "step": "blue",
}))


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            console=console,
            rich_tracebacks=True,
            markup=True,
        )],
    )
    return logging.getLogger(name)


def log_research_step(step: int, query: str, logger: logging.Logger):
    logger.info(f"[step]🔍 Step {step}:[/step] {query}")


def log_finding(finding: str, logger: logging.Logger):
    logger.info(f"[research]💡 Finding:[/research] {finding[:120]}...")


def log_success(message: str, logger: logging.Logger):
    logger.info(f"[success]✅ {message}[/success]")


def log_section(title: str):
    console.rule(f"[bold cyan]{title}[/bold cyan]")
