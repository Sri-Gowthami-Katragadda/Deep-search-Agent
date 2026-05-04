"""
tools/financial_api.py
──────────────────────
Financial data retrieval using yfinance (free) and Alpha Vantage (optional).
Handles stock prices, financial ratios, income statements, balance sheets.

IMPORTANT: All calculations done programmatically (no LLM math).
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings
from utils.logger import get_logger
from utils.helpers import format_currency

logger = get_logger(__name__)

# NSE ticker mapping for common Indian companies
NSE_TICKER_MAP = {
    # IT Sector
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "Wipro": "WIPRO.NS",
    "HCL Technologies": "HCLTECH.NS",
    "Tech Mahindra": "TECHM.NS",
    "LTIMindtree": "LTIM.NS",
    "Mphasis": "MPHASIS.NS",
    "Persistent Systems": "PERSISTENT.NS",
    "Coforge": "COFORGE.NS",
    "Tata Elxsi": "TATAELXSI.NS",
    "KPIT Technologies": "KPITTECH.NS",
    # Pharma Sector
    "Sun Pharmaceutical": "SUNPHARMA.NS",
    "Dr. Reddy's Laboratories": "DRREDDY.NS",
    "Cipla": "CIPLA.NS",
    "Lupin": "LUPIN.NS",
    "Aurobindo Pharma": "AUROPHARMA.NS",
    "Divi's Laboratories": "DIVISLAB.NS",
    "Biocon": "BIOCON.NS",
    "Alkem Laboratories": "ALKEM.NS",
    "Torrent Pharmaceuticals": "TORNTPHARM.NS",
    "Glenmark Pharmaceuticals": "GLENMARK.NS",
}


class FinancialDataAPI:
    """
    Retrieves real financial data from yfinance and Alpha Vantage.
    All financial calculations are done programmatically.
    """

    def __init__(self):
        self.settings = get_settings()
        self._yf = None  # Lazy import

    def _get_yf(self):
        """Lazy import yfinance to avoid cold-start delay."""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                logger.error("yfinance not installed. Run: pip install yfinance")
                raise
        return self._yf

    def get_ticker_symbol(self, company_name: str) -> Optional[str]:
        """Resolve company name to NSE ticker symbol."""
        # Direct lookup
        if company_name in NSE_TICKER_MAP:
            return NSE_TICKER_MAP[company_name]
        # Partial match
        for name, ticker in NSE_TICKER_MAP.items():
            if company_name.lower() in name.lower() or name.lower() in company_name.lower():
                return ticker
        # If looks like a ticker already
        if company_name.endswith(".NS") or company_name.endswith(".BO"):
            return company_name
        return None

    def get_stock_quote(self, company_name: str) -> Dict[str, Any]:
        """Get current stock price and basic metrics."""
        yf = self._get_yf()
        ticker_symbol = self.get_ticker_symbol(company_name)

        if not ticker_symbol:
            return {"error": f"Could not find ticker for '{company_name}'"}

        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE")
            pb_ratio = info.get("priceToBook")
            dividend_yield = info.get("dividendYield", 0)
            fifty_two_week_high = info.get("fiftyTwoWeekHigh")
            fifty_two_week_low = info.get("fiftyTwoWeekLow")

            return {
                "company": company_name,
                "ticker": ticker_symbol,
                "current_price": round(price, 2) if price else None,
                "market_cap": market_cap,
                "market_cap_formatted": format_currency(market_cap, "INR") if market_cap else "N/A",
                "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
                "pb_ratio": round(pb_ratio, 2) if pb_ratio else None,
                "dividend_yield_pct": round(dividend_yield * 100, 2) if dividend_yield else None,
                "52w_high": fifty_two_week_high,
                "52w_low": fifty_two_week_low,
                "currency": info.get("currency", "INR"),
                "exchange": info.get("exchange", "NSE"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
            }
        except Exception as e:
            logger.warning(f"Stock quote failed for {company_name}: {e}")
            return {"error": str(e), "company": company_name}

    def get_income_statement(self, company_name: str) -> Dict[str, Any]:
        """Get annual income statement data."""
        yf = self._get_yf()
        ticker_symbol = self.get_ticker_symbol(company_name)
        if not ticker_symbol:
            return {"error": f"No ticker for '{company_name}'"}

        try:
            ticker = yf.Ticker(ticker_symbol)
            income_stmt = ticker.financials  # Annual by default

            if income_stmt is None or income_stmt.empty:
                return {"error": "No income statement data available"}

            # Convert to readable format
            data = {}
            for col in income_stmt.columns[:4]:  # Last 4 years
                year = str(col.year) if hasattr(col, 'year') else str(col)
                data[year] = {}
                for row in income_stmt.index:
                    val = income_stmt.loc[row, col]
                    if pd.notna(val):
                        data[year][str(row)] = float(val)

            # Calculate key ratios programmatically
            years = list(data.keys())
            ratios = {}
            for year in years:
                y_data = data[year]
                total_revenue = y_data.get("Total Revenue", 0)
                gross_profit = y_data.get("Gross Profit", 0)
                operating_income = y_data.get("Operating Income", 0)
                net_income = y_data.get("Net Income", 0)

                ratios[year] = {
                    "gross_margin_pct": round((gross_profit / total_revenue) * 100, 2) if total_revenue else None,
                    "operating_margin_pct": round((operating_income / total_revenue) * 100, 2) if total_revenue else None,
                    "net_margin_pct": round((net_income / total_revenue) * 100, 2) if total_revenue else None,
                }

            return {
                "company": company_name,
                "ticker": ticker_symbol,
                "income_statement": data,
                "calculated_ratios": ratios,
                "years_available": years,
            }
        except Exception as e:
            logger.warning(f"Income statement failed for {company_name}: {e}")
            return {"error": str(e)}

    def get_balance_sheet(self, company_name: str) -> Dict[str, Any]:
        """Get balance sheet data with computed ratios."""
        yf = self._get_yf()
        ticker_symbol = self.get_ticker_symbol(company_name)
        if not ticker_symbol:
            return {"error": f"No ticker for '{company_name}'"}

        try:
            ticker = yf.Ticker(ticker_symbol)
            bs = ticker.balance_sheet

            if bs is None or bs.empty:
                return {"error": "No balance sheet data"}

            data = {}
            for col in bs.columns[:4]:
                year = str(col.year) if hasattr(col, 'year') else str(col)
                data[year] = {
                    str(row): float(bs.loc[row, col])
                    for row in bs.index if pd.notna(bs.loc[row, col])
                }

            # Compute D/E ratio programmatically
            computed = {}
            for year, vals in data.items():
                total_debt = vals.get("Total Debt", 0)
                equity = vals.get("Stockholders Equity", vals.get("Total Stockholders Equity", 0))
                de_ratio = round(total_debt / equity, 2) if equity and equity != 0 else None
                computed[year] = {"debt_to_equity": de_ratio}

            return {
                "company": company_name,
                "ticker": ticker_symbol,
                "balance_sheet": data,
                "computed_ratios": computed,
            }
        except Exception as e:
            logger.warning(f"Balance sheet failed for {company_name}: {e}")
            return {"error": str(e)}

    def get_cash_flow(self, company_name: str) -> Dict[str, Any]:
        """Get cash flow statement."""
        yf = self._get_yf()
        ticker_symbol = self.get_ticker_symbol(company_name)
        if not ticker_symbol:
            return {"error": f"No ticker for '{company_name}'"}

        try:
            ticker = yf.Ticker(ticker_symbol)
            cf = ticker.cashflow

            if cf is None or cf.empty:
                return {"error": "No cash flow data"}

            data = {}
            for col in cf.columns[:4]:
                year = str(col.year) if hasattr(col, 'year') else str(col)
                data[year] = {
                    str(row): float(cf.loc[row, col])
                    for row in cf.index if pd.notna(cf.loc[row, col])
                }

            # Compute Free Cash Flow programmatically
            fcf_by_year = {}
            for year, vals in data.items():
                operating_cf = vals.get("Operating Cash Flow", vals.get("Total Cash From Operating Activities", 0))
                capex = abs(vals.get("Capital Expenditure", vals.get("Capital Expenditures", 0)))
                fcf = operating_cf - capex
                fcf_by_year[year] = {"free_cash_flow": fcf, "operating_cf": operating_cf, "capex": capex}

            return {
                "company": company_name,
                "ticker": ticker_symbol,
                "cash_flow": data,
                "free_cash_flow": fcf_by_year,
            }
        except Exception as e:
            logger.warning(f"Cash flow failed for {company_name}: {e}")
            return {"error": str(e)}

    def get_price_history(self, company_name: str, period: str = "1y") -> Dict[str, Any]:
        """Get historical stock price data."""
        yf = self._get_yf()
        ticker_symbol = self.get_ticker_symbol(company_name)
        if not ticker_symbol:
            return {"error": f"No ticker for '{company_name}'"}

        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return {"error": "No price history"}

            start_price = float(hist["Close"].iloc[0])
            end_price = float(hist["Close"].iloc[-1])
            price_change_pct = round(((end_price - start_price) / start_price) * 100, 2)

            return {
                "company": company_name,
                "ticker": ticker_symbol,
                "period": period,
                "start_price": round(start_price, 2),
                "end_price": round(end_price, 2),
                "price_change_pct": price_change_pct,
                "high": round(float(hist["High"].max()), 2),
                "low": round(float(hist["Low"].min()), 2),
                "avg_volume": int(hist["Volume"].mean()),
            }
        except Exception as e:
            logger.warning(f"Price history failed for {company_name}: {e}")
            return {"error": str(e)}

    def get_sector_comparison(self, companies: List[str]) -> Dict[str, Any]:
        """Compare multiple companies' key metrics."""
        comparison = {}
        for company in companies:
            quote = self.get_stock_quote(company)
            if "error" not in quote:
                comparison[company] = {
                    "price": quote.get("current_price"),
                    "market_cap": quote.get("market_cap"),
                    "pe_ratio": quote.get("pe_ratio"),
                    "pb_ratio": quote.get("pb_ratio"),
                }
        return {
            "companies_compared": companies,
            "comparison_data": comparison,
            "generated_at": datetime.now().isoformat(),
        }

    def format_for_report(self, financial_data: Dict[str, Any]) -> str:
        """Convert financial data dict into markdown table for reports."""
        if "error" in financial_data:
            return f"_Financial data unavailable: {financial_data['error']}_"

        lines = []
        company = financial_data.get("company", "Company")

        if "current_price" in financial_data:
            lines.append(f"**{company} Stock Data**")
            lines.append(f"- Current Price: ₹{financial_data.get('current_price', 'N/A')}")
            lines.append(f"- Market Cap: {financial_data.get('market_cap_formatted', 'N/A')}")
            lines.append(f"- P/E Ratio: {financial_data.get('pe_ratio', 'N/A')}")
            lines.append(f"- 52W High/Low: ₹{financial_data.get('52w_high', 'N/A')} / ₹{financial_data.get('52w_low', 'N/A')}")

        return "\n".join(lines)
