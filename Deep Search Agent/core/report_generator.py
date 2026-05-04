"""
core/report_generator.py
─────────────────────────
Handles final report formatting and saving.
Adapts structure based on query type.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.helpers import save_report, ensure_dir
from utils.validators import ResearchSession
from config.settings import get_settings

logger = get_logger(__name__)


class ReportGenerator:
    """
    Formats and saves research reports.
    Supports markdown output with structured sections.
    """

    def __init__(self):
        self.settings = get_settings()

    def add_metadata_header(self, report: str, session: ResearchSession) -> str:
        """Prepend a metadata block to the report."""
        duration = ""
        if session.completed_at and session.started_at:
            delta = session.completed_at - session.started_at
            duration = f"{delta.seconds // 60}m {delta.seconds % 60}s"

        header = f"""---
**Research Session ID:** `{session.session_id}`
**Query:** {session.original_query}
**Sector:** {session.sector.upper()}
**Research Depth:** {len(session.steps)} steps completed
**Duration:** {duration or 'N/A'}
**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}
---

"""
        return header + report

    def save(self, session: ResearchSession) -> str:
        """Save the final report and return the file path."""
        if not session.final_report:
            logger.warning("No report content to save")
            return ""

        report_with_header = self.add_metadata_header(session.final_report, session)
        path = save_report(report_with_header, session.original_query, self.settings.reports_dir)
        logger.info(f"Report saved → {path}")
        return path

    def print_report(self, session: ResearchSession):
        """Print the report to console using Rich."""
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console()
        if session.final_report:
            console.print(Markdown(session.final_report))
        else:
            console.print("[red]No report generated[/red]")

    def get_all_reports(self) -> list:
        """List all generated reports."""
        reports_path = Path(self.settings.reports_dir)
        if not reports_path.exists():
            return []
        return sorted(
            [f for f in reports_path.glob("*.md")],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
