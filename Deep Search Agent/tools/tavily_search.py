"""
tools/tavily_search.py
──────────────────────
Tavily API integration for intelligent web search.
Supports single searches, multi-query batches, and domain-filtered searches.
"""

from tavily import TavilyClient
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import get_settings
from utils.logger import get_logger
from utils.helpers import truncate_text

logger = get_logger(__name__)


class TavilySearchTool:
    """
    Wraps the Tavily Search API with retry logic and result processing.
    
    Features:
    - Advanced search with full page content extraction
    - Domain filtering for sector-specific sources
    - Automatic result summarization
    - Rate-limit resilient via exponential backoff
    """

    def __init__(self):
        settings = get_settings()
        self.client = TavilyClient(api_key=settings.tavily_api_key)
        self.search_depth = settings.tavily_search_depth
        self.max_results = settings.tavily_max_results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        search_depth: Optional[str] = None,
        include_answer: bool = True,
        include_raw_content: bool = False,
    ) -> dict:
        """
        Perform a web search with Tavily.
        
        Returns:
            {
                "query": str,
                "answer": str,          # Tavily's synthesised answer
                "results": [...],       # Individual source results
                "combined_text": str,   # All content merged for LLM ingestion
                "sources": [str]        # List of URLs
            }
        """
        logger.debug(f"Tavily search: '{query}'")

        response = self.client.search(
            query=query,
            search_depth=search_depth or self.search_depth,
            max_results=max_results or self.max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
        )

        results = response.get("results", [])
        answer = response.get("answer", "")

        # Build a combined text blob for LLM consumption
        parts = []
        if answer:
            parts.append(f"SUMMARY: {answer}\n")

        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            url = r.get("url", "")
            content = r.get("content", "")
            parts.append(
                f"SOURCE {i}: {title}\nURL: {url}\n{truncate_text(content, 1500)}\n"
            )

        return {
            "query": query,
            "answer": answer,
            "results": results,
            "combined_text": "\n---\n".join(parts),
            "sources": [r.get("url", "") for r in results],
            "result_count": len(results),
        }

    def financial_news_search(self, query: str) -> dict:
        """Search for financial news with domain focus."""
        financial_domains = [
            "economictimes.com", "livemint.com", "moneycontrol.com",
            "bseindia.com", "nseindia.com", "businessstandard.com",
            "reuters.com", "bloomberg.com", "financialexpress.com",
        ]
        return self.search(query, include_domains=financial_domains)

    def regulatory_search(self, query: str, sector: str) -> dict:
        """Search for regulatory/government information."""
        if sector == "pharma":
            domains = ["fda.gov", "cdsco.gov.in", "ema.europa.eu", "who.int"]
        else:
            domains = ["meity.gov.in", "nasscom.in", "sebi.gov.in", "cert-in.org.in"]
        return self.search(query, include_domains=domains)

    def company_filing_search(self, company: str, filing_type: str = "annual report") -> dict:
        """Search for company filings and financial documents."""
        query = f"{company} {filing_type} 2024 financial statements"
        return self.search(
            query,
            include_domains=["bseindia.com", "nseindia.com", "moneycontrol.com"],
        )

    def multi_search(self, queries: List[str]) -> List[dict]:
        """Run multiple searches sequentially."""
        results = []
        for q in queries:
            try:
                results.append(self.search(q))
            except Exception as e:
                logger.warning(f"Search failed for '{q}': {e}")
                results.append({"query": q, "error": str(e), "combined_text": ""})
        return results
