"""
FastAPI application — main entry point for the AEPSA backend.
Endpoints:
  POST /analyze          — run analysis (returns full result)
  GET  /analyze/stream   — SSE streaming trace (for live UI updates)
  GET  /experience       — get past cases from experience DB
  POST /human-decision   — submit human review decision
  PUT  /case/{id}/outcome — update real-world outcome
  GET  /health           — health check
"""
import asyncio
import json
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from agents.orchestrator import run_analysis
from memory.experience_db import get_all_cases, update_case_outcome, save_case
from config import DATABASE_URL

app = FastAPI(
    title="Adaptive Enterprise Problem-Solving AI",
    description="Multi-agent AI for complex enterprise problem investigation",
    version="1.0.0"
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    problem: str


class HumanDecisionRequest(BaseModel):
    case_id: str
    decision: str   # APPROVE | MODIFY | REJECT
    notes: Optional[str] = None
    modified_recommendation: Optional[str] = None


class OutcomeRequest(BaseModel):
    outcome: str
    success: bool


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "AEPSA Backend",
        "version": "1.0.0"
    }


# ─── Main Analysis Endpoint ────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Run the full multi-agent analysis pipeline.
    Returns the complete state including recommendation, evidence, confidence, risk.
    """
    if not request.problem or len(request.problem.strip()) < 10:
        raise HTTPException(400, "Problem description too short (minimum 10 characters)")

    try:
        state = await run_analysis(request.problem.strip())

        # Build clean response
        return {
            "problem_id": state.get("problem_id"),
            "case_id": state.get("case_id"),
            "problem": state.get("problem"),

            # Analysis
            "problem_analysis": state.get("problem_analysis", {}),
            "plan": {
                "strategy_name": state.get("plan", {}).get("strategy_name"),
                "strategy_description": state.get("plan", {}).get("strategy_description"),
                "task_count": len(state.get("plan", {}).get("tasks", [])),
                "reusing_past_strategy": state.get("plan", {}).get("reusing_past_strategy", False),
                "past_strategy_reference": state.get("plan", {}).get("past_strategy_reference")
            },
            "selected_agents": state.get("selected_agents", {}),
            "similar_cases": state.get("similar_cases", []),

            # Agent outputs summary
            "research_summary": state.get("research_output", {}).get("primary_finding"),
            "data_summary": state.get("data_output", {}).get("primary_finding"),
            "analysis_summary": state.get("analysis_output", {}).get("primary_finding"),

            # Recommendation
            "final_recommendation": state.get("final_recommendation"),
            "draft_recommendation": state.get("draft_recommendation"),
            "hypotheses": state.get("hypotheses", []),

            # Evidence
            "evidence": state.get("evidence", [])[:10],  # Cap for response size
            "supporting_evidence": [
                {"type": e.get("type"), "source": e.get("source"),
                 "content": e.get("content", "")[:300], "source_quality": e.get("source_quality")}
                for e in state.get("evidence", [])[:8]
            ],
            "injection_alerts": state.get("injection_alerts", []),

            # Critic
            "critic": {
                "verdict": state.get("critic_output", {}).get("verdict"),
                "risk_level": state.get("critic_output", {}).get("risk_level"),
                "concerns": state.get("critic_output", {}).get("concerns", []),
                "strengths": state.get("critic_output", {}).get("strengths", []),
                "overall_assessment": state.get("critic_output", {}).get("overall_assessment")
            },

            # Safety
            "confidence": state.get("confidence_result", {}),
            "risk": state.get("risk_result", {}),
            "router_decision": state.get("router_decision", {}),

            # Verification
            "verification": state.get("verification_result", {}),

            # Flags
            "contradiction_detected": state.get("contradiction_detected", False),
            "awaiting_human": state.get("awaiting_human", False),
            "completed": state.get("completed", False),

            # Full trace
            "trace_log": state.get("trace_log", [])
        }

    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


# ─── SSE Streaming Endpoint ────────────────────────────────────────────────────

@app.post("/analyze/stream")
async def analyze_stream(request: AnalyzeRequest):
    """
    Server-Sent Events streaming endpoint.
    Streams trace entries as the analysis runs.
    """
    async def event_generator():
        try:
            # Run analysis (non-streaming — LangGraph runs synchronously)
            # We simulate streaming by running and then replaying trace
            state = await run_analysis(request.problem.strip())
            trace = state.get("trace_log", [])

            # Send trace entries with small delay for UI effect
            for entry in trace:
                data = json.dumps({"type": "trace", "entry": entry})
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.05)

            # Send final result
            result_data = json.dumps({
                "type": "result",
                "confidence": state.get("confidence_result", {}).get("confidence_pct"),
                "risk": state.get("risk_result", {}).get("risk_pct"),
                "decision": state.get("router_decision", {}).get("decision"),
                "awaiting_human": state.get("awaiting_human", False),
                "case_id": state.get("case_id"),
                "recommendation": state.get("final_recommendation", "")[:500]
            })
            yield f"data: {result_data}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ─── Experience DB Endpoints ───────────────────────────────────────────────────

@app.get("/experience")
async def get_experience():
    """Return past cases from the experience database."""
    cases = get_all_cases(limit=20)
    return {"cases": cases, "count": len(cases)}


@app.put("/case/{case_id}/outcome")
async def update_outcome(case_id: str, request: OutcomeRequest):
    """Update a case with its real-world outcome."""
    try:
        update_case_outcome(case_id, request.outcome, request.success)
        return {"status": "updated", "case_id": case_id}
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── Human Decision Endpoint ───────────────────────────────────────────────────

@app.post("/human-decision")
async def human_decision(request: HumanDecisionRequest):
    """Accept human review decision for an escalated case."""
    valid_decisions = ["APPROVE", "MODIFY", "REJECT"]
    if request.decision not in valid_decisions:
        raise HTTPException(400, f"Decision must be one of: {valid_decisions}")

    try:
        # Record the human decision as an outcome
        outcome = (
            f"Human decision: {request.decision}. "
            f"Notes: {request.notes or 'None'}. "
            f"Modified recommendation: {request.modified_recommendation or 'N/A'}"
        )
        success = request.decision in ["APPROVE", "MODIFY"]
        update_case_outcome(request.case_id, outcome, success)

        return {
            "status": "recorded",
            "case_id": request.case_id,
            "decision": request.decision,
            "message": f"Human decision '{request.decision}' recorded for case {request.case_id}"
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── OS & Laptop Automation Endpoints ──────────────────────────────────────────

class OSAutomateRequest(BaseModel):
    goal: str


@app.get("/os/diagnostics")
async def get_os_diagnostics():
    """Returns live CPU, Memory, Disk, and Battery diagnostics."""
    from tools.shell_tools import get_system_resources
    return get_system_resources()


@app.get("/os/windows")
async def get_os_windows():
    """List all open desktop windows and the currently active foreground window."""
    from tools.desktop_tools import list_open_windows, get_active_window_info
    return {
        "active_window": get_active_window_info(),
        "open_windows": list_open_windows()
    }


@app.post("/os/screenshot")
async def capture_os_screenshot():
    """Captures a screenshot of the laptop display and generates a coordinate grid."""
    import base64
    from tools.desktop_tools import take_screenshot, annotate_grid_on_image
    shot = take_screenshot()
    if shot["status"] == "success":
        grid_path = annotate_grid_on_image(shot["file_path"])
        shot["grid_path"] = grid_path
        try:
            with open(grid_path, "rb") as f:
                shot["grid_base64"] = base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    return shot


@app.post("/os/automate")
async def automate_os_task(request: OSAutomateRequest):
    """
    Executes a high-level laptop automation task using dynamic multi-agent orchestration.
    Coordinates Shell, File, Vision/GUI agents with closed-loop verification.
    """
    from agents.os_supervisor import OSSupervisor
    supervisor = OSSupervisor()
    result = supervisor.execute_custom_plan(request.goal)
    return result


# ─── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize databases on startup if not already seeded."""
    import subprocess
    import os

    # Seed databases if not present
    if not os.path.exists(DATABASE_URL):
        print("Seeding databases...")
        subprocess.run(["python", "data/seed_db.py"], cwd=os.path.dirname(__file__))
        subprocess.run(["python", "data/seed_rag.py"], cwd=os.path.dirname(__file__))
        subprocess.run(["python", "data/seed_kg.py"], cwd=os.path.dirname(__file__))

