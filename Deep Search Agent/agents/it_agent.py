"""
agents/it_agent.py
──────────────────
IT Sector Research Agent.
Specialized for Indian IT services, software, cloud, AI/ML companies.
"""

from agents.base_agent import BaseSectorAgent
from config.sector_config import IT_CONFIG
from utils.validators import ResearchSession
from utils.logger import get_logger

logger = get_logger(__name__)


class ITSectorAgent(BaseSectorAgent):
    """
    Deep Research Agent for Indian IT & Technology Sector.
    
    Specialized in:
    - IT services companies (TCS, Infosys, Wipro, HCL, etc.)
    - Software product companies
    - Cloud, AI/ML, SaaS trends
    - NASSCOM reports and IT export data
    - Deal wins, attrition, utilization analysis
    """

    def __init__(self):
        super().__init__()
        self._sector_config = IT_CONFIG

    # ── HOOKS ─────────────────────────────────────────────────────────────────

    def pre_research_hook(self, query: str):
        """Log sector-specific research start."""
        logger.info(
            f"🖥️  IT Agent activated | Companies tracked: {', '.join(self._sector_config.key_companies[:4])}..."
        )

    def post_research_hook(self, session: ResearchSession) -> ResearchSession:
        """
        Enhance the report with IT-specific insights:
        - Add sector context if not already present
        - Tag deal wins and attrition mentions
        """
        if session.final_report:
            # Append IT-specific data footnote
            it_note = (
                "\n\n---\n"
                "**IT Sector Research Notes:**\n"
                "- Revenue figures for Indian IT companies are typically reported in INR (crore) for domestic operations and USD for exports\n"
                "- Deal TCV (Total Contract Value) represents the total value of new contracts signed\n"
                "- Attrition rate is a critical metric for IT services companies; industry normal is 15-25% annualised\n"
                "- NASSCOM data is the gold standard for Indian IT export revenue\n"
            )
            session.final_report += it_note
        return session

    # ── IT-SPECIFIC METHODS ───────────────────────────────────────────────────

    def compare_it_companies(self, companies: list) -> dict:
        """Compare multiple IT companies' financial metrics."""
        return self.financial_analyzer.financial_api.get_sector_comparison(companies)

    def get_top_it_stocks(self) -> dict:
        """Get current market data for top IT stocks."""
        top_companies = self._sector_config.key_companies[:6]
        results = {}
        for company in top_companies:
            quote = self.financial_analyzer.financial_api.get_stock_quote(company)
            if "error" not in quote:
                results[company] = quote
        return results

    def search_deal_wins(self, company: str) -> dict:
        """Search for recent deal wins for an IT company."""
        from tools.tavily_search import TavilySearchTool
        searcher = TavilySearchTool()
        results = searcher.search(
            f"{company} large deal wins TCV 2024 2025",
            include_domains=["economictimes.com", "livemint.com", "moneycontrol.com"],
        )
        return results
