"""
LangGraph Orchestrator — defines the agent graph and execution flow.
This is the core of the AEPSA system.
"""
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.problem_analyzer import problem_analyzer_node
from agents.planner import planner_node
from agents.supervisor import supervisor_node
from agents.swarm import swarm_node
from agents.critic import critic_node
from agents.verifier import verifier_node
from agents.llm_client import make_trace_entry
from safety.confidence import compute_confidence
from safety.risk import compute_risk
from safety.router import route
from memory.experience_db import save_case


# ─── Confidence + Risk Node ───────────────────────────────────────────────────

def confidence_risk_node(state: AgentState) -> AgentState:
    """Compute confidence and risk scores from all agent outputs."""
    trace = list(state.get("trace_log", []))
    trace.append(make_trace_entry("Safety System", "Computing confidence score", ""))

    agent_outputs = {
        "swarm_outputs": state.get("swarm_outputs", [])
    }

    confidence_result = compute_confidence(
        state.get("evidence", []),
        agent_outputs,
        state.get("verification_result")
    )

    trace.append(make_trace_entry(
        "Safety System", "Confidence computed",
        f"Confidence: {confidence_result['confidence_pct']}% "
        f"(Evidence: {confidence_result['breakdown']['evidence_coverage']:.2f}, "
        f"Sources: {confidence_result['breakdown']['source_quality']:.2f}, "
        f"Agreement: {confidence_result['breakdown']['agent_agreement']:.2f})",
        "INFO"
    ))

    trace.append(make_trace_entry("Safety System", "Computing risk score", ""))

    risk_result = compute_risk(
        state.get("draft_recommendation", ""),
        agent_outputs,
        state.get("evidence", []),
        state.get("critic_output", {}),
        confidence_result["breakdown"]
    )

    trace.append(make_trace_entry(
        "Safety System", "Risk computed",
        f"Risk: {risk_result['risk_pct']}% ({risk_result['level']}) "
        f"(Reversibility: {risk_result['breakdown']['action_reversibility']:.2f}, "
        f"Impact: {risk_result['breakdown']['impact_scope']:.2f})",
        "INFO"
    ))

    return {
        **state,
        "confidence_result": confidence_result,
        "risk_result": risk_result,
        "trace_log": trace
    }


# ─── Safety Router Node ────────────────────────────────────────────────────────

def safety_router_node(state: AgentState) -> AgentState:
    """Apply safety routing rules and determine APPROVE/RECHECK/HUMAN."""
    trace = list(state.get("trace_log", []))
    trace.append(make_trace_entry("Safety Router", "Evaluating routing rules", ""))

    confidence = state.get("confidence_result", {}).get("confidence", 0.5)
    risk = state.get("risk_result", {}).get("risk", 0.5)
    recheck_count = state.get("recheck_count", 0)
    contradiction = state.get("contradiction_detected", False)

    decision = route(
        confidence=confidence,
        risk=risk,
        evidence=state.get("evidence", []),
        critic_output=state.get("critic_output", {}),
        recheck_count=recheck_count,
        contradiction_detected=contradiction
    )

    level_map = {"APPROVE": "SUCCESS", "RECHECK": "WARNING", "HUMAN": "ERROR"}
    trace.append(make_trace_entry(
        "Safety Router", f"Decision: {decision['decision']}",
        f"Rule: {decision['rule']} | Confidence: {confidence:.2f} | Risk: {risk:.2f} | "
        f"Reason: {'; '.join(decision.get('reasons', [])[:2])}",
        level_map.get(decision["decision"], "INFO")
    ))

    awaiting_human = decision["decision"] == "HUMAN"

    return {
        **state,
        "router_decision": decision,
        "awaiting_human": awaiting_human,
        "trace_log": trace
    }


# ─── Record Outcome Node ───────────────────────────────────────────────────────

def record_outcome_node(state: AgentState) -> AgentState:
    """Save this case to the experience database."""
    trace = list(state.get("trace_log", []))
    trace.append(make_trace_entry("Experience DB", "Recording case", ""))

    try:
        case_id = save_case(
            problem_description=state["problem"],
            problem_type=state.get("problem_analysis", {}).get("problem_type", "unknown"),
            strategy=state.get("plan", {}).get("strategy_name", "unknown"),
            agents_used=state.get("selected_agents", {}).get("selected_agents", []),
            tools_used=["get_defect_history", "get_machine_data", "get_supplier_history",
                       "search_engineering_docs", "run_statistical_analysis"],
            confidence=state.get("confidence_result", {}).get("confidence", 0.0),
            risk=state.get("risk_result", {}).get("risk", 0.0),
            recommendation=state.get("final_recommendation", ""),
            verification_result=state.get("verification_result", {}).get("result", "UNKNOWN"),
            human_required=state.get("awaiting_human", False),
            human_decision=state.get("human_decision"),
            outcome=None,  # To be filled in when real outcome is known
            success=None
        )
        trace.append(make_trace_entry(
            "Experience DB", "Case recorded",
            f"Case ID: {case_id} | Strategy: {state.get('plan', {}).get('strategy_name', 'unknown')}",
            "SUCCESS"
        ))
    except Exception as e:
        trace.append(make_trace_entry("Experience DB", "Record failed", str(e), "WARNING"))
        raise RuntimeError("Could not persist the pending human-review case") from e

    return {**state, "case_id": case_id, "completed": True, "trace_log": trace}


# ─── Routing Conditions ────────────────────────────────────────────────────────

def router_condition(state: AgentState) -> str:
    """LangGraph conditional edge: route based on safety decision."""
    decision = state.get("router_decision", {}).get("decision", "HUMAN")

    if decision == "APPROVE":
        return "verify"
    elif decision == "RECHECK":
        recheck_count = state.get("recheck_count", 0)
        if recheck_count >= 2:
            return "human"
        return "recheck"
    else:
        return "human"


def recheck_node(state: AgentState) -> AgentState:
    """Re-run analysis with broader scope for RECHECK cases."""
    trace = list(state.get("trace_log", []))
    recheck_count = state.get("recheck_count", 0) + 1

    trace.append(make_trace_entry(
        "Supervisor", f"RECHECK iteration {recheck_count}",
        "Expanding evidence scope and re-analyzing...",
        "WARNING"
    ))

    return {**state, "recheck_count": recheck_count, "trace_log": trace}


def human_escalation_node(state: AgentState) -> AgentState:
    """Mark case as awaiting human review."""
    trace = list(state.get("trace_log", []))
    reasons = state.get("router_decision", {}).get("reasons", ["Insufficient confidence"])

    trace.append(make_trace_entry(
        "Human Escalation", "Escalating to human review",
        f"Reasons: {'; '.join(reasons)}",
        "ERROR"
    ))
    trace.append(make_trace_entry(
        "Human Escalation", "Awaiting human decision",
        "Available actions: APPROVE | MODIFY | REJECT",
        "WARNING"
    ))

    try:
        case_id = save_case(
            problem_description=state["problem"],
            problem_type=state.get("problem_analysis", {}).get("problem_type", "unknown"),
            strategy=state.get("plan", {}).get("strategy_name", "unknown"),
            agents_used=state.get("selected_agents", {}).get("selected_agents", []),
            tools_used=["get_defect_history", "get_machine_data", "get_supplier_history",
                       "search_engineering_docs", "run_statistical_analysis"],
            confidence=state.get("confidence_result", {}).get("confidence", 0.0),
            risk=state.get("risk_result", {}).get("risk", 0.0),
            recommendation=state.get("final_recommendation", ""),
            verification_result=state.get("verification_result", {}).get("result", "UNKNOWN"),
            human_required=True,
            human_decision=None,
            outcome=None,
            success=None
        )
        trace.append(make_trace_entry(
            "Experience DB", "Case recorded (Pending)",
            f"Case ID: {case_id} | Awaiting Human",
            "WARNING"
        ))
    except Exception as e:
        trace.append(make_trace_entry("Experience DB", "Record failed", str(e), "ERROR"))
        case_id = state.get("problem_id", "UNKNOWN")

    return {
        **state,
        "awaiting_human": True,
        "completed": False,
        "trace_log": trace,
        "case_id": case_id
    }


# ─── Build the Graph ──────────────────────────────────────────────────────────

def build_graph():
    """Construct and compile the LangGraph agent graph."""
    builder = StateGraph(AgentState)

    # Add all nodes
    builder.add_node("problem_analyzer", problem_analyzer_node)
    builder.add_node("planner", planner_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("swarm", swarm_node)
    builder.add_node("critic", critic_node)
    builder.add_node("confidence_risk", confidence_risk_node)
    builder.add_node("safety_router", safety_router_node)
    builder.add_node("verifier", verifier_node)
    builder.add_node("recheck", recheck_node)
    builder.add_node("human_escalation", human_escalation_node)
    builder.add_node("record_outcome", record_outcome_node)

    # Define edges (execution flow)
    builder.set_entry_point("problem_analyzer")
    builder.add_edge("problem_analyzer", "planner")
    builder.add_edge("planner", "supervisor")
    builder.add_edge("supervisor", "swarm")
    builder.add_edge("swarm", "critic")
    builder.add_edge("critic", "confidence_risk")
    builder.add_edge("confidence_risk", "safety_router")

    # Conditional routing after safety check
    builder.add_conditional_edges(
        "safety_router",
        router_condition,
        {
            "verify": "verifier",
            "recheck": "recheck",
            "human": "human_escalation"
        }
    )

    # After recheck: re-run from swarm
    builder.add_edge("recheck", "swarm")

    # After verification: record outcome
    builder.add_edge("verifier", "record_outcome")
    builder.add_edge("record_outcome", END)

    # Human escalation ends (awaits async human input)
    builder.add_edge("human_escalation", END)

    return builder.compile()


# Singleton graph instance
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_analysis(problem: str):
    """
    Run the full analysis pipeline for a problem.
    Returns the final state with all results.
    """
    graph = get_graph()

    initial_state: AgentState = {
        "problem": problem,
        "problem_id": "",
        "problem_analysis": {},
        "plan": {},
        "selected_agents": {},
        "similar_cases": [],
        "research_output": {},
        "data_output": {},
        "analysis_output": {},
        "evidence": [],
        "hypotheses": [],
        "contradiction_detected": False,
        "injection_alerts": [],
        "draft_recommendation": "",
        "final_recommendation": "",
        "supporting_evidence": [],
        "critic_output": {},
        "confidence_result": {},
        "risk_result": {},
        "router_decision": {},
        "verification_result": {},
        "recheck_count": 0,
        "trace_log": [],
        "case_id": "",
        "human_decision": None,
        "human_notes": None,
        "awaiting_human": False,
        "completed": False,
        "error": None
    }

    final_state = graph.invoke(initial_state)
    return final_state
