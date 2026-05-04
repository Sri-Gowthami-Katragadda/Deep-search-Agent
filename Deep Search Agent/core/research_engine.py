"""
core/research_engine.py
───────────────────────
The Deep Research Loop Engine.

This is the "brain" — it orchestrates iterative, adaptive research
where each finding informs the next query. Implements the multi-step
research loop similar to Claude's Deep Research mode.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Callable

from groq import Groq

from config.settings import get_settings
from config.sector_config import SectorConfig
from tools.tavily_search import TavilySearchTool
from tools.financial_api import FinancialDataAPI
from tools.document_processor import DocumentProcessor
from utils.logger import get_logger, log_research_step, log_finding
from utils.helpers import safe_json_parse, build_research_summary, save_report
from utils.validators import ResearchSession, ResearchStep, ResearchPlan
from prompts.system_prompts import (
    RESEARCH_PLANNER_PROMPT,
    RESEARCH_ANALYST_PROMPT,
    REPORT_SYNTHESIZER_PROMPT,
    FINANCIAL_EXTRACTOR_PROMPT,
)

logger = get_logger(__name__)


class ResearchEngine:
    """
    Deep Research Loop Engine.
    
    Research flow:
    1. Plan → Generate detailed multi-phase research plan
    2. Execute Loop → Iteratively search, analyse, and adapt
    3. Synthesise → Compile all findings into structured report
    """

    def __init__(self, sector_config: SectorConfig, rag_processor: Optional[DocumentProcessor] = None):
        self.settings = get_settings()
        self.sector_config = sector_config
        self.groq = Groq(api_key=self.settings.groq_api_key)
        self.search_tool = TavilySearchTool()
        self.financial_api = FinancialDataAPI()
        self.rag = rag_processor  # Optional RAG processor

    # ── LLM CALLS ─────────────────────────────────────────────────────────────

    def _llm_call(self, system: str, user: str, model: Optional[str] = None, max_tokens: int = 2048) -> str:
        """Make a Groq LLM API call."""
        model = model or self.settings.groq_model
        response = self.groq.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    def _llm_json_call(self, system: str, user: str) -> Optional[dict]:
        """LLM call that returns parsed JSON."""
        raw = self._llm_call(system, user, max_tokens=2000)
        return safe_json_parse(raw)

    # ── PHASE 1: RESEARCH PLANNING ────────────────────────────────────────────

    def create_research_plan(self, query: str) -> Optional[ResearchPlan]:
        """Generate a detailed research plan for the query."""
        logger.info(f"Creating research plan for: {query}")

        system = RESEARCH_PLANNER_PROMPT.format(
            sector_display_name=self.sector_config.display_name,
            key_companies=", ".join(self.sector_config.key_companies[:8]),
            key_metrics=", ".join(self.sector_config.key_metrics[:6]),
            sub_sectors=", ".join(self.sector_config.sub_sectors),
        )

        data = self._llm_json_call(system, f"Create a comprehensive research plan for: {query}")

        if not data:
            logger.warning("Failed to parse research plan JSON")
            return None

        try:
            return ResearchPlan(**data)
        except Exception as e:
            logger.warning(f"Research plan validation error: {e}")
            # Build minimal plan from raw data
            return ResearchPlan(
                research_title=data.get("research_title", f"Research: {query}"),
                query_type=data.get("query_type", "sector_analysis"),
                estimated_steps=data.get("estimated_steps", 8),
                research_phases=data.get("research_phases", []),
                key_questions_to_answer=data.get("key_questions_to_answer", []),
                expected_report_sections=data.get("expected_report_sections", []),
                data_sources_to_use=data.get("data_sources_to_use", ["web_search"]),
            )

    # ── PHASE 2: DEEP RESEARCH LOOP ──────────────────────────────────────────

    def run_research_loop(
        self,
        query: str,
        research_plan: ResearchPlan,
        max_steps: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> ResearchSession:
        """
        Execute the deep iterative research loop.
        
        Each iteration:
        1. Execute search query
        2. Query RAG for internal docs
        3. Fetch financial data if companies mentioned
        4. Analyse findings & decide next query
        5. Repeat until comprehensive (or max_steps reached)
        """
        max_steps = max_steps or self.settings.max_research_steps
        min_steps = self.settings.min_research_steps

        session = ResearchSession(
            session_id=str(uuid.uuid4()),
            original_query=query,
            sector=self.sector_config.name,
            research_plan=research_plan,
            status="researching",
        )

        # Collect initial queries from the plan
        initial_queries = []
        for phase in research_plan.research_phases[:2]:  # First 2 phases
            initial_queries.extend(phase.search_queries[:2])

        if not initial_queries:
            initial_queries = self.sector_config.base_search_terms + [query]

        current_query = initial_queries[0] if initial_queries else query
        all_findings = []
        financial_data_collected = {}

        logger.info(f"Starting research loop: max {max_steps} steps")

        for step_num in range(1, max_steps + 1):
            log_research_step(step_num, current_query, logger)

            if progress_callback:
                progress_callback(step_num, current_query)

            # ── Web Search ────────────────────────────────────────────────────
            try:
                search_results = self.search_tool.search(current_query)
                search_text = search_results.get("combined_text", "")
            except Exception as e:
                logger.warning(f"Search failed at step {step_num}: {e}")
                search_text = ""

            # ── RAG Retrieval ─────────────────────────────────────────────────
            rag_text = ""
            if self.rag:
                rag_results = self.rag.query(current_query, n_results=3)
                if rag_results:
                    rag_text = self.rag.format_rag_results(rag_results)

            # ── Financial Data ────────────────────────────────────────────────
            # Check if any known companies were mentioned in search results
            mentioned_companies = self._extract_mentioned_companies(search_text)
            for company in mentioned_companies:
                if company not in financial_data_collected:
                    try:
                        fin_data = self.financial_api.get_stock_quote(company)
                        if "error" not in fin_data:
                            financial_data_collected[company] = fin_data
                            logger.debug(f"Fetched financial data for {company}")
                    except Exception:
                        pass

            # ── Combine Context ───────────────────────────────────────────────
            combined_context = search_text
            if rag_text:
                combined_context += f"\n\n{rag_text}"

            # ── Analyse Findings & Plan Next Step ─────────────────────────────
            research_history = build_research_summary(
                [{"query": s.query, "summary": s.results_summary} for s in session.steps]
            )

            analysis_system = RESEARCH_ANALYST_PROMPT.format(
                sector_display_name=self.sector_config.display_name,
                research_history=research_history or "This is the first step.",
                current_findings=combined_context[:3000],
                original_query=query,
                step_number=step_num,
                max_steps=max_steps,
            )

            analysis_result = self._llm_json_call(
                analysis_system,
                f"Analyze findings and determine next research action for: '{current_query}'",
            )

            if not analysis_result:
                analysis_result = {
                    "key_insights_found": ["Search completed"],
                    "data_points": {},
                    "next_search_query": f"{query} detailed analysis",
                    "next_search_rationale": "Continue research",
                    "research_gaps": [],
                    "completeness_score": step_num / max_steps,
                    "should_stop": False,
                }

            # Record step
            step = ResearchStep(
                step_number=step_num,
                query=current_query,
                results_summary=combined_context[:1000],
                key_insights=analysis_result.get("key_insights_found", []),
                data_points=analysis_result.get("data_points", {}),
                next_query=analysis_result.get("next_search_query"),
                completeness_score=analysis_result.get("completeness_score", 0),
            )
            session.steps.append(step)
            all_findings.append({
                "step": step_num,
                "query": current_query,
                "findings": combined_context[:2000],
                "insights": analysis_result.get("key_insights_found", []),
            })

            log_finding(
                str(analysis_result.get("key_insights_found", ["..."])[:2]),
                logger,
            )

            # ── Stopping Criteria ─────────────────────────────────────────────
            should_stop = analysis_result.get("should_stop", False)
            completeness = analysis_result.get("completeness_score", 0)

            if step_num >= min_steps and (should_stop or completeness >= 0.85):
                logger.info(f"Research complete at step {step_num} (completeness: {completeness:.0%})")
                break

            # ── Set Next Query ─────────────────────────────────────────────────
            next_q = analysis_result.get("next_search_query")

            # Use plan queries in early steps if available
            if step_num < len(initial_queries):
                current_query = initial_queries[step_num]
            elif next_q:
                current_query = next_q
            else:
                current_query = f"{query} comprehensive analysis {step_num}"

        # Attach collected financial data
        session.status = "synthesizing"
        return session, all_findings, financial_data_collected

    # ── PHASE 3: REPORT SYNTHESIS ─────────────────────────────────────────────

    def synthesize_report(
        self,
        session: ResearchSession,
        all_findings: list,
        financial_data: dict,
    ) -> str:
        """Compile all research findings into a comprehensive report."""
        logger.info(f"Synthesizing report from {len(all_findings)} research steps...")

        # Prepare financial data section
        fin_section = ""
        for company, data in financial_data.items():
            fin_section += f"\n{self.financial_api.format_for_report(data)}\n"

        # Compress findings for the prompt (token limit)
        findings_text = ""
        for f in all_findings:
            findings_text += f"\n## Step {f['step']}: {f['query']}\n"
            findings_text += f"**Key Insights:** {', '.join(f['insights'][:3])}\n"
            findings_text += f"{f['findings'][:800]}\n"

        if fin_section:
            findings_text += f"\n## Live Financial Data\n{fin_section}"

        system = REPORT_SYNTHESIZER_PROMPT.format(
            original_query=session.original_query,
            sector_display_name=self.sector_config.display_name,
            total_steps=len(session.steps),
            key_metrics=", ".join(self.sector_config.key_metrics[:6]),
            all_findings=findings_text[:8000],
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        report = self._llm_call(
            system,
            f"Generate a comprehensive research report for: {session.original_query}",
            max_tokens=4096,
        )

        return report

    # ── ORCHESTRATOR ──────────────────────────────────────────────────────────

    def run_full_research(
        self,
        query: str,
        max_steps: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
        existing_plan=None,                 # ← reuse plan if already created
    ) -> ResearchSession:
        """
        Full research pipeline:
        Plan → Research Loop → Synthesize → Save Report
        """
        # Step 1: Plan — reuse if already generated, otherwise create fresh
        if existing_plan is not None:
            plan = existing_plan
            logger.info("Reusing existing research plan (skipping duplicate LLM call)")
        else:
            plan = self.create_research_plan(query)

        # Fallback: if plan creation failed, build a minimal default plan
        if not plan:
            logger.warning("Plan creation failed — using minimal fallback plan")
            from utils.validators import ResearchPlan
            plan = ResearchPlan(
                research_title=f"Research: {query}",
                query_type="sector_analysis",
                estimated_steps=max_steps or 8,
                research_phases=[],
                key_questions_to_answer=[query],
                expected_report_sections=["Overview", "Analysis", "Outlook"],
                data_sources_to_use=["web_search"],
            )

        # Step 2: Execute research loop
        session, all_findings, financial_data = self.run_research_loop(
            query, plan, max_steps, progress_callback
        )

        # Step 3: Synthesize report
        report = self.synthesize_report(session, all_findings, financial_data)
        session.final_report = report
        session.status = "complete"
        session.completed_at = datetime.now()

        # Step 4: Save report
        report_path = save_report(report, query, self.settings.reports_dir)
        session.report_path = report_path
        logger.info(f"Report saved: {report_path}")

        return session

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _extract_mentioned_companies(self, text: str) -> list:
        """Find known sector companies mentioned in a text."""
        found = []
        text_lower = text.lower()
        for company in self.sector_config.key_companies:
            if company.lower() in text_lower:
                found.append(company)
        return found[:3]  # Limit to 3 to avoid too many API calls per step

