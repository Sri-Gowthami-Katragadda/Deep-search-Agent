"""
core/financial_analyzer.py
──────────────────────────
Financial metrics extraction and analysis module.
All calculations are done programmatically (not by LLM).
"""

import re
from typing import Optional, List
from groq import Groq

from config.settings import get_settings
from config.sector_config import SectorConfig
from tools.financial_api import FinancialDataAPI
from utils.logger import get_logger
from utils.helpers import safe_json_parse
from utils.validators import FinancialMetrics
from prompts.system_prompts import FINANCIAL_EXTRACTOR_PROMPT

logger = get_logger(__name__)


class FinancialAnalyzer:
    """
    Extracts and analyses financial metrics from text and live APIs.
    
    Design principle: LLM is used only for text extraction/understanding.
    All mathematical operations are done in Python.
    """

    def __init__(self, sector_config: SectorConfig):
        self.sector_config = sector_config
        self.settings = get_settings()
        self.groq = Groq(api_key=self.settings.groq_api_key)
        self.financial_api = FinancialDataAPI()

    def extract_metrics_from_text(self, text: str, company_name: str = "") -> Optional[FinancialMetrics]:
        """Use LLM to extract structured financial data from unstructured text."""
        if not text.strip():
            return None

        system = FINANCIAL_EXTRACTOR_PROMPT.format(
            text=text[:3000],
            company_name=company_name or "Unknown",
            sector=self.sector_config.display_name,
        )

        response = self.groq.chat.completions.create(
            model=self.settings.groq_fast_model,  # Use fast model for extraction
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "Extract all financial data from the provided text."},
            ],
            max_tokens=1000,
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()
        data = safe_json_parse(raw)

        if data:
            try:
                return FinancialMetrics(**data)
            except Exception as e:
                logger.debug(f"FinancialMetrics validation issue: {e}")
                return FinancialMetrics(company=company_name or "Unknown", **data)
        return None

    def compute_growth_rate(self, current: float, previous: float) -> Optional[float]:
        """Programmatic YoY growth rate calculation."""
        if previous and previous != 0:
            return round(((current - previous) / abs(previous)) * 100, 2)
        return None

    def compute_cagr(self, start_value: float, end_value: float, years: int) -> Optional[float]:
        """Compound Annual Growth Rate."""
        if start_value <= 0 or years <= 0:
            return None
        return round(((end_value / start_value) ** (1 / years) - 1) * 100, 2)

    def compute_margin(self, profit: float, revenue: float) -> Optional[float]:
        """Profit margin calculation."""
        if revenue and revenue != 0:
            return round((profit / revenue) * 100, 2)
        return None

    def get_full_company_analysis(self, company_name: str) -> dict:
        """
        Fetch comprehensive financial data for a company.
        Combines stock quote, income statement, balance sheet, and cash flows.
        """
        logger.info(f"Fetching full financial data for {company_name}")

        quote = self.financial_api.get_stock_quote(company_name)
        income = self.financial_api.get_income_statement(company_name)
        balance = self.financial_api.get_balance_sheet(company_name)
        cashflow = self.financial_api.get_cash_flow(company_name)
        price_hist = self.financial_api.get_price_history(company_name, "1y")

        # Compute supplementary ratios programmatically
        computed_ratios = {}
        if "calculated_ratios" in income:
            for year, ratios in income["calculated_ratios"].items():
                computed_ratios[year] = ratios

        return {
            "company": company_name,
            "stock_quote": quote,
            "income_statement": income,
            "balance_sheet": balance,
            "cash_flow": cashflow,
            "price_history_1y": price_hist,
            "computed_ratios": computed_ratios,
        }

    def format_financial_summary(self, analysis: dict) -> str:
        """Format full analysis as a concise markdown summary."""
        company = analysis.get("company", "Company")
        quote = analysis.get("stock_quote", {})
        ratios = analysis.get("computed_ratios", {})
        price_hist = analysis.get("price_history_1y", {})

        lines = [f"### {company} — Financial Summary\n"]

        if "error" not in quote:
            lines.append(f"**Market Data**")
            lines.append(f"- Price: ₹{quote.get('current_price', 'N/A')}")
            lines.append(f"- Market Cap: {quote.get('market_cap_formatted', 'N/A')}")
            lines.append(f"- P/E: {quote.get('pe_ratio', 'N/A')} | P/B: {quote.get('pb_ratio', 'N/A')}")

        if "error" not in price_hist:
            lines.append(f"\n**1-Year Price Performance**")
            lines.append(f"- Return: {price_hist.get('price_change_pct', 'N/A')}%")
            lines.append(f"- 52W Range: ₹{price_hist.get('low', 'N/A')} – ₹{price_hist.get('high', 'N/A')}")

        if ratios:
            latest_year = sorted(ratios.keys())[-1] if ratios else None
            if latest_year:
                r = ratios[latest_year]
                lines.append(f"\n**Profitability ({latest_year})**")
                lines.append(f"- Gross Margin: {r.get('gross_margin_pct', 'N/A')}%")
                lines.append(f"- Operating Margin: {r.get('operating_margin_pct', 'N/A')}%")
                lines.append(f"- Net Margin: {r.get('net_margin_pct', 'N/A')}%")

        return "\n".join(lines)
