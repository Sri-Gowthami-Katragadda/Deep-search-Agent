"""
api/app.py
──────────
FastAPI REST interface for the Financial Research Agent.
Provides HTTP endpoints for query submission, status checking, and report retrieval.
"""

import asyncio
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from agents.router_agent import RouterAgent
from core.report_generator import ReportGenerator
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Financial Deep Research Agent API",
    description="Multi-agent financial research system for IT and Pharma sectors",
    version="1.0.0",
)

# In-memory session store (use Redis for production)
research_sessions: dict = {}

router_agent = RouterAgent()
report_gen = ReportGenerator()


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=5, description="Financial research query")
    max_steps: Optional[int] = Field(None, ge=1, le=30, description="Max research iterations")
    sector_hint: Optional[str] = Field(None, description="Optional: 'it' or 'pharma'")


class ResearchResponse(BaseModel):
    session_id: str
    status: str
    message: str
    sector: Optional[str] = None
    query_type: Optional[str] = None


class SessionStatus(BaseModel):
    session_id: str
    status: str
    steps_completed: int
    current_step: Optional[str] = None
    sector: Optional[str] = None
    report_available: bool
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── BACKGROUND RESEARCH ───────────────────────────────────────────────────────

def run_research_task(session_id: str, query: str, max_steps: Optional[int]):
    """Background task that runs the full research pipeline."""
    research_sessions[session_id]["status"] = "researching"

    def progress_callback(step: int, query: str):
        research_sessions[session_id]["current_step"] = f"Step {step}: {query}"
        research_sessions[session_id]["steps_completed"] = step

    try:
        session, decision = router_agent.dispatch(
            query=query,
            max_steps=max_steps,
            progress_callback=progress_callback,
        )

        if session:
            research_sessions[session_id].update({
                "status": "complete",
                "session": session,
                "report_path": session.report_path,
                "steps_completed": len(session.steps),
                "completed_at": datetime.now().isoformat(),
            })
        else:
            reason = "out_of_scope" if decision.sector == "out_of_scope" else "clarification_needed"
            research_sessions[session_id].update({
                "status": reason,
                "message": decision.clarification_question or decision.reasoning,
            })
    except Exception as e:
        logger.error(f"Research task failed: {e}")
        research_sessions[session_id].update({
            "status": "error",
            "error": str(e),
        })


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Financial Deep Research Agent",
        "version": "1.0.0",
        "sectors": ["IT", "Pharma"],
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/research", response_model=ResearchResponse, tags=["Research"])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Start a new research session.
    Research runs in background — poll /research/{session_id}/status for updates.
    """
    import uuid
    session_id = str(uuid.uuid4())

    # Quick routing check
    decision = router_agent.route_query(request.query)

    if decision.sector == "out_of_scope":
        raise HTTPException(
            status_code=400,
            detail="Query is outside the financial research domain. Please ask about IT or Pharma sectors.",
        )

    if decision.sector == "clarification_needed":
        return ResearchResponse(
            session_id=session_id,
            status="clarification_needed",
            message=decision.clarification_question or "Please provide more details.",
            sector=None,
            query_type=decision.query_type,
        )

    # Initialize session record
    research_sessions[session_id] = {
        "session_id": session_id,
        "query": request.query,
        "sector": decision.sector,
        "status": "queued",
        "steps_completed": 0,
        "current_step": None,
        "report_path": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    # Launch background research
    background_tasks.add_task(
        run_research_task, session_id, request.query, request.max_steps
    )

    return ResearchResponse(
        session_id=session_id,
        status="started",
        message=f"Research started for {decision.sector.upper()} sector. Poll /research/{session_id}/status",
        sector=decision.sector,
        query_type=decision.query_type,
    )


@app.get("/research/{session_id}/status", response_model=SessionStatus, tags=["Research"])
def get_research_status(session_id: str):
    """Get the status of an ongoing or completed research session."""
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = research_sessions[session_id]
    return SessionStatus(
        session_id=session_id,
        status=s["status"],
        steps_completed=s.get("steps_completed", 0),
        current_step=s.get("current_step"),
        sector=s.get("sector"),
        report_available=s.get("report_path") is not None,
        started_at=s.get("started_at"),
        completed_at=s.get("completed_at"),
    )


@app.get("/research/{session_id}/report", tags=["Research"])
def get_research_report(session_id: str, format: str = "json"):
    """
    Get the final research report.
    format: 'json' (default) | 'file' (download markdown file)
    """
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = research_sessions[session_id]

    if s["status"] != "complete":
        raise HTTPException(
            status_code=202,
            detail=f"Report not ready yet. Status: {s['status']}",
        )

    if format == "file" and s.get("report_path"):
        return FileResponse(
            s["report_path"],
            media_type="text/markdown",
            filename=f"research_report_{session_id[:8]}.md",
        )

    session_obj = s.get("session")
    if session_obj and session_obj.final_report:
        return JSONResponse({
            "session_id": session_id,
            "query": s["query"],
            "sector": s["sector"],
            "steps_completed": s["steps_completed"],
            "report": session_obj.final_report,
            "report_path": s.get("report_path"),
        })

    raise HTTPException(status_code=500, detail="Report content not available")


@app.get("/reports", tags=["Reports"])
def list_reports():
    """List all generated research reports."""
    reports = report_gen.get_all_reports()
    return {
        "count": len(reports),
        "reports": [
            {"filename": r.name, "size_kb": round(r.stat().st_size / 1024, 1)}
            for r in reports
        ],
    }


@app.get("/sectors", tags=["Info"])
def list_sectors():
    """List available research sectors and their key companies."""
    return {
        "it": router_agent.it_agent.get_sector_info(),
        "pharma": router_agent.pharma_agent.get_sector_info(),
    }


@app.post("/ingest", tags=["Documents"])
async def ingest_document(filepath: str, sector: str):
    """Ingest a PDF document into the RAG knowledge base for a sector."""
    if sector not in ("it", "pharma"):
        raise HTTPException(status_code=400, detail="sector must be 'it' or 'pharma'")

    agent = router_agent.get_agent(sector)
    if not agent:
        raise HTTPException(status_code=400, detail=f"No agent for sector '{sector}'")

    chunks = agent.ingest_document(filepath)
    return {"status": "success", "chunks_indexed": chunks, "sector": sector}
