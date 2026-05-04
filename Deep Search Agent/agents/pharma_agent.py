"""
agents/pharma_agent.py
──────────────────────
Pharma Sector Research Agent.
Specialized for Indian pharmaceutical, biotech, and healthcare companies.
"""

from agents.base_agent import BaseSectorAgent
from config.sector_config import PHARMA_CONFIG
from utils.validators import ResearchSession
from utils.logger import get_logger

logger = get_logger(__name__)


class PharmaSectorAgent(BaseSectorAgent):
    """
    Deep Research Agent for Indian Pharmaceutical & Healthcare Sector.
    
    Specialized in:
    - Indian pharma companies (Sun Pharma, Dr Reddy's, Cipla, etc.)
    - Biosimilars and generics pipeline
    - USFDA approvals, Form 483 observations, Warning Letters
    - API manufacturing and CDMO business
    - Clinical trials and drug approvals
    """

    def __init__(self):
        super().__init__()
        self._sector_config = PHARMA_CONFIG

    # ── HOOKS ─────────────────────────────────────────────────────────────────

    def pre_research_hook(self, query: str):
        """Log sector-specific research start."""
        logger.info(
            f"💊 Pharma Agent activated | Companies tracked: {', '.join(self._sector_config.key_companies[:4])}..."
        )

    def post_research_hook(self, session: ResearchSession) -> ResearchSession:
        """
        Enhance the report with pharma-specific insights:
        - Add regulatory context
        - Note data interpretation caveats
        """
        if session.final_report:
            pharma_note = (
                "\n\n---\n"
                "**Pharma Sector Research Notes:**\n"
                "- USFDA approvals are critical catalysts for Indian pharma companies' US revenue\n"
                "- Form 483 observations are non-binding; Warning Letters and Import Alerts are more serious\n"
                "- Domestic formulation revenue is relatively stable; export generics is more volatile\n"
                "- R&D spend as % of revenue (typically 5-12%) indicates innovation pipeline strength\n"
                "- CDMO (Contract Development & Manufacturing) is a high-growth emerging revenue stream\n"
            )
            session.final_report += pharma_note
        return session

    # ── PHARMA-SPECIFIC METHODS ───────────────────────────────────────────────

    def search_fda_approvals(self, company: str) -> dict:
        """Search for recent USFDA approvals for a pharma company."""
        from tools.tavily_search import TavilySearchTool
        searcher = TavilySearchTool()
        return searcher.search(
            f"{company} USFDA ANDA approval 2024 2025",
            include_domains=["fda.gov", "pharmabiz.com", "fiercepharma.com", "economictimes.com"],
        )

    def search_drug_pipeline(self, company: str) -> dict:
        """Search for drug pipeline and clinical trial info."""
        from tools.tavily_search import TavilySearchTool
        searcher = TavilySearchTool()
        return searcher.search(
            f"{company} drug pipeline biosimilar clinical trials 2024",
            include_domains=["clinicaltrials.gov", "pharmabiz.com", "fiercepharma.com"],
        )

    def get_top_pharma_stocks(self) -> dict:
        """Get current market data for top pharma stocks."""
        top_companies = self._sector_config.key_companies[:6]
        results = {}
        for company in top_companies:
            quote = self.financial_analyzer.financial_api.get_stock_quote(company)
            if "error" not in quote:
                results[company] = quote
        return results

    def search_regulatory_updates(self) -> dict:
        """Search for recent USFDA and CDSCO regulatory news."""
        from tools.tavily_search import TavilySearchTool
        searcher = TavilySearchTool()
        return searcher.search(
            "USFDA India pharma warning letter import alert 2025",
            include_domains=["fda.gov", "cdsco.gov.in", "pharmabiz.com"],
        )
