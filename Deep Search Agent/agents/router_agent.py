"""
agents/router_agent.py
──────────────────────
Intelligent query routing agent.
Classifies queries → assigns to appropriate sector agent(s).
"""

from groq import Groq
from typing import Optional, Tuple

from config.settings import get_settings
from config.sector_config import get_all_keywords
from agents.it_agent import ITSectorAgent
from agents.pharma_agent import PharmaSectorAgent
from agents.base_agent import BaseSectorAgent
from utils.logger import get_logger
from utils.helpers import safe_json_parse
from utils.validators import RouterDecision, ResearchSession
from prompts.system_prompts import ROUTER_SYSTEM_PROMPT, QUERY_CLARIFIER_PROMPT

logger = get_logger(__name__)


class RouterAgent:
    """
    Intelligent query router that:
    1. Classifies financial queries by sector
    2. Rejects non-financial queries politely
    3. Routes to appropriate sector agent(s)
    4. Handles cross-sector queries
    5. Requests clarification when needed
    """

    # Out-of-scope topics (non-exhaustive)
    OUT_OF_SCOPE_KEYWORDS = [
        "recipe", "cook", "food", "sport", "cricket", "football",
        "movie", "music", "travel", "weather", "joke", "poem",
        "celebrity", "fashion", "health tips", "fitness",
    ]

    def __init__(self):
        self.settings = get_settings()
        self.groq = Groq(api_key=self.settings.groq_api_key)
        self._it_agent: Optional[ITSectorAgent] = None
        self._pharma_agent: Optional[PharmaSectorAgent] = None

    @property
    def it_agent(self) -> ITSectorAgent:
        if not self._it_agent:
            self._it_agent = ITSectorAgent()
        return self._it_agent

    @property
    def pharma_agent(self) -> PharmaSectorAgent:
        if not self._pharma_agent:
            self._pharma_agent = PharmaSectorAgent()
        return self._pharma_agent

    # ── ROUTING LOGIC ─────────────────────────────────────────────────────────

    def fast_keyword_check(self, query: str) -> Optional[str]:
        """
        Quick keyword-based pre-filter before LLM routing.
        Returns sector name or None if inconclusive.
        """
        q_lower = query.lower()

        # Quick out-of-scope check
        for kw in self.OUT_OF_SCOPE_KEYWORDS:
            if kw in q_lower:
                return "out_of_scope"

        # Keyword matching
        all_keywords = get_all_keywords()
        scores = {sector: 0 for sector in all_keywords}
        for sector, keywords in all_keywords.items():
            for kw in keywords:
                if kw.lower() in q_lower:
                    scores[sector] += 1

        best_sector = max(scores, key=scores.get)
        if scores[best_sector] >= 2:  # Threshold: 2+ keyword matches
            return best_sector

        return None  # Inconclusive — use LLM routing

    def route_query(self, query: str) -> RouterDecision:
        """
        Full routing decision using LLM analysis.
        Falls back to keyword check for speed on obvious queries.
        """
        # Fast path
        fast_result = self.fast_keyword_check(query)
        if fast_result in ("out_of_scope",):
            return RouterDecision(
                sector="out_of_scope",
                confidence=0.95,
                reasoning="Query contains non-financial keywords",
                query_type="out_of_scope",
            )

        # LLM routing
        try:
            response = self.groq.chat.completions.create(
                model=self.settings.groq_fast_model,  # Use fast model for routing
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Route this query: {query}"},
                ],
                max_tokens=500,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            data = safe_json_parse(raw)

            if data:
                return RouterDecision(**data)
        except Exception as e:
            logger.warning(f"LLM routing failed: {e}. Using keyword fallback.")

        # Fallback to keyword result
        sector = fast_result or "it"  # Default to IT if ambiguous
        return RouterDecision(
            sector=sector,
            confidence=0.6,
            reasoning="Keyword-based routing fallback",
            query_type="sector_analysis",
        )

    def get_clarification_message(self, decision: RouterDecision) -> str:
        """Generate a clarification question for ambiguous queries."""
        try:
            response = self.groq.chat.completions.create(
                model=self.settings.groq_fast_model,
                messages=[
                    {
                        "role": "system",
                        "content": QUERY_CLARIFIER_PROMPT.format(
                            original_query="",
                            clarification_reason=decision.reasoning,
                        ),
                    },
                    {
                        "role": "user",
                        "content": decision.clarification_question or "Need more information",
                    },
                ],
                max_tokens=200,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return decision.clarification_question or "Could you clarify which sector you're interested in?"

    # ── AGENT SELECTION ───────────────────────────────────────────────────────

    def get_agent(self, sector: str) -> Optional[BaseSectorAgent]:
        """Get the appropriate sector agent."""
        if sector == "it":
            return self.it_agent
        elif sector == "pharma":
            return self.pharma_agent
        return None

    def get_agents_for_sector(self, sector: str) -> list:
        """Get list of agents for a routing decision (handles 'both')."""
        if sector == "both":
            return [self.it_agent, self.pharma_agent]
        agent = self.get_agent(sector)
        return [agent] if agent else []

    # ── MAIN DISPATCH ─────────────────────────────────────────────────────────

    def dispatch(
        self,
        query: str,
        max_steps: Optional[int] = None,
        progress_callback=None,
    ) -> Tuple[Optional[ResearchSession], RouterDecision]:
        """
        Full dispatch pipeline:
        1. Route query
        2. Handle out-of-scope or clarification needed
        3. Execute research with appropriate agent(s)
        4. Return session + routing decision
        """
        decision = self.route_query(query)
        logger.info(
            f"Routing decision: sector={decision.sector}, "
            f"confidence={decision.confidence:.0%}, type={decision.query_type}"
        )

        if decision.sector == "out_of_scope":
            return None, decision

        if decision.sector == "clarification_needed":
            return None, decision

        agents = self.get_agents_for_sector(decision.sector)
        if not agents:
            logger.error(f"No agent found for sector: {decision.sector}")
            return None, decision

        if len(agents) == 1:
            session = agents[0].run_research(query, max_steps, progress_callback)
            return session, decision

        # Multi-sector: run primary agent, mention secondary
        logger.info(f"Cross-sector query — routing to both IT and Pharma agents")
        primary_session = agents[0].run_research(query, max_steps, progress_callback)
        return primary_session, decision
