"""
Shared LangGraph state definition for the AEPSA orchestrator.
All agents read from and write to this typed state dict.
"""
from typing import TypedDict, Annotated, Any, Optional
import operator


class TraceEntry(TypedDict):
    timestamp: str
    agent: str
    action: str
    detail: str
    level: str  # INFO | WARNING | ERROR | SUCCESS


class AgentState(TypedDict):
    # Input
    problem: str
    problem_id: str

    # Analysis
    problem_analysis: dict          # From ProblemAnalyzer
    plan: dict                      # From Planner
    selected_agents: dict           # From Supervisor
    similar_cases: list             # From ExperienceDB lookup

    # Dynamic Swarm outputs
    swarm_outputs: list[dict]       # From temporary swarm worker agents

    # Compiled evidence
    evidence: list[dict]
    hypotheses: list[dict]
    contradiction_detected: bool
    injection_alerts: list[dict]

    # Recommendation
    draft_recommendation: str
    final_recommendation: str
    supporting_evidence: list[dict]

    # Critic
    critic_output: dict

    # Safety
    confidence_result: dict
    risk_result: dict
    router_decision: dict

    # Verifier
    verification_result: dict

    # Tracking
    recheck_count: int
    trace_log: list[TraceEntry]     # Append-only
    case_id: str

    # Human escalation
    human_decision: Optional[str]
    human_notes: Optional[str]
    awaiting_human: bool

    # Final output
    completed: bool
    error: Optional[str]
