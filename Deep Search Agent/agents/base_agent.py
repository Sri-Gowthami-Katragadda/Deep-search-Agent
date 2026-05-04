"""
agents/base_agent.py
────────────────────
Abstract base class for all sector research agents.
All sector agents inherit from this and override sector-specific behaviour.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable

from groq import Groq

from config.settings import get_settings
from config.sector_config import SectorConfig
from core.research_engine import ResearchEngine
from core.rag_engine import RAGEngine
from core.financial_analyzer import FinancialAnalyzer
from core.report_generator import ReportGenerator
from utils.logger import get_logger
from utils.validators import ResearchSession, RouterDecision


class BaseSectorAgent(ABC):
    """
    Abstract base class for sector-specific research agents.
    Concrete agents (ITAgent, PharmaAgent) override:
    - sector_config: The sector's configuration
    - pre_research_hook(): Optional sector-specific setup
    - post_research_hook(): Optional report enhancement
    """

    def __init__(self):
        self.settings = get_settings()
        self.groq = Groq(api_key=self.settings.groq_api_key)
        self.logger = get_logger(self.__class__.__name__)
        self.rag_engine = RAGEngine()
        self.report_generator = ReportGenerator()

        # These must be set by child class
        self._sector_config: Optional[SectorConfig] = None
        self._research_engine: Optional[ResearchEngine] = None
        self._financial_analyzer: Optional[FinancialAnalyzer] = None
# @property turns a method into something that looks like an attribute but runs code when accessed
    @property
    def sector_config(self) -> SectorConfig:
        if self._sector_config is None:
            raise NotImplementedError("Child class must set _sector_config")
        return self._sector_config

    @property
    def research_engine(self) -> ResearchEngine:
        if self._research_engine is None:
            rag_processor = self.rag_engine.get_processor(self.sector_config.name)
            self._research_engine = ResearchEngine(self.sector_config, rag_processor)
        return self._research_engine

    @property
    def financial_analyzer(self) -> FinancialAnalyzer:
        if self._financial_analyzer is None:
            self._financial_analyzer = FinancialAnalyzer(self.sector_config)
        return self._financial_analyzer

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def create_research_plan(self, query: str):
        """Generate a research plan (shown to user for approval)."""
        return self.research_engine.create_research_plan(query)

    def run_research(
        self,
        query: str,
        max_steps: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
        plan=None,                          # ← accept pre-created plan
    ) -> ResearchSession:
        """
        Full research pipeline for this sector.
        If plan is provided (already shown to user), it is reused — no duplicate LLM call.
        Returns a completed ResearchSession with final report.
        """
        self.logger.info(f"[{self.sector_config.display_name}] Starting research: {query}")
        self.pre_research_hook(query)

        session = self.research_engine.run_full_research(
            query=query,
            max_steps=max_steps or self.settings.max_research_steps,
            progress_callback=progress_callback,
            existing_plan=plan,             # ← pass it through
        )

        if session:
            session = self.post_research_hook(session)
            report_path = self.report_generator.save(session)
            session.report_path = report_path

        return session

    def ingest_document(self, filepath: str, metadata: Optional[dict] = None) -> int:
        """Add a PDF document to this sector's RAG knowledge base."""
        return self.rag_engine.ingest_document(filepath, self.sector_config.name, metadata)

    def get_company_financials(self, company_name: str) -> dict:
        """Get live financial data for a specific company."""
        return self.financial_analyzer.get_full_company_analysis(company_name)

    # ── HOOKS ─────────────────────────────────────────────────────────────────

    def pre_research_hook(self, query: str):
        """Optional: Called before research loop. Override for custom setup."""
        pass

    def post_research_hook(self, session: ResearchSession) -> ResearchSession:
        """Optional: Called after research completes. Override to enhance report."""
        return session

    # ── INFO ──────────────────────────────────────────────────────────────────

    def get_sector_info(self) -> dict:
        """Return sector metadata."""
        return {
            "name": self.sector_config.name,
            "display_name": self.sector_config.display_name,
            "key_companies": self.sector_config.key_companies,
            "key_metrics": self.sector_config.key_metrics,
            "sub_sectors": self.sector_config.sub_sectors,
        }