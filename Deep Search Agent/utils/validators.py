"""
utils/validators.py
───────────────────
Pydantic models for validating inputs and outputs throughout the pipeline.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class ResearchQuery(BaseModel):
    query: str = Field(..., min_length=5, max_length=1000)
    sector_hint: Optional[str] = None   # Optional: "it" | "pharma"
    max_steps: Optional[int] = Field(None, ge=1, le=30)
    output_format: Literal["markdown", "json", "both"] = "markdown"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class RouterDecision(BaseModel):
    sector: Literal["it", "pharma", "both", "out_of_scope", "clarification_needed"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    query_type: str
    companies_mentioned: List[str] = []
    clarification_question: Optional[str] = None


class ResearchPhase(BaseModel):
    phase_number: int
    phase_name: str
    objective: str
    search_queries: List[str]
    expected_outputs: List[str]


class ResearchPlan(BaseModel):
    research_title: str
    query_type: str
    estimated_steps: int
    research_phases: List[ResearchPhase]
    key_questions_to_answer: List[str]
    expected_report_sections: List[str]
    data_sources_to_use: List[str]


class ResearchStep(BaseModel):
    step_number: int
    query: str
    results_summary: str
    key_insights: List[str]
    data_points: Dict[str, Any] = {}
    next_query: Optional[str] = None
    completeness_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class ResearchSession(BaseModel):
    session_id: str
    original_query: str
    sector: str
    router_decision: Optional[RouterDecision] = None
    research_plan: Optional[ResearchPlan] = None
    steps: List[ResearchStep] = []
    final_report: Optional[str] = None
    report_path: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: Literal["planning", "researching", "synthesizing", "complete", "error"] = "planning"


class FinancialMetrics(BaseModel):
    company: str
    period: Optional[str] = None
    revenue: Optional[Dict[str, Any]] = None
    ebitda: Optional[Dict[str, Any]] = None
    net_profit: Optional[Dict[str, Any]] = None
    eps: Optional[Dict[str, Any]] = None
    deal_wins: Optional[Dict[str, Any]] = None
    headcount: Optional[Dict[str, Any]] = None
    guidance: Optional[Dict[str, Any]] = None
    other_metrics: Dict[str, Any] = {}
    notable_mentions: List[str] = []
