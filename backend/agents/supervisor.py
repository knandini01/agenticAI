"""
Supervisor Agent — decides which specialized agents to invoke and why.
Demonstrates "adaptive" selection — not every problem needs every agent.
"""
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.state import AgentState
from agents.llm_client import llm_call, make_trace_entry

AVAILABLE_TOOLS = {
    "search_engineering_docs": "RAG search through engineering documents and incidents.",
    "get_machine_data": "SQL query for machine sensor telemetry.",
    "get_defect_history": "SQL query for defect rates.",
    "get_supplier_timeline": "SQL query for supplier changes.",
    "run_statistical_analysis": "Trend change, anomaly detection, hypothesis testing.",
    "query_knowledge_graph": "Causal chains and hardware dependencies.",
    "simulate_thermal_stress": "Physics simulation of machine stress."
}

SYSTEM_PROMPT = """You are the Swarm Supervisor for an Enterprise AI System.
Your job is to review the Planner's tasks, validate the dynamic agent roles, and confirm the tools required for the Swarm execution.

Respond ONLY with valid JSON:
{
  "approved_swarm_agents": [
    {
      "agent_role": "Role Name",
      "task_id": "T1",
      "tools_assigned": ["tool_name"]
    }
  ],
  "supervisor_note": "Overall delegation strategy for the swarm"
}"""


def supervisor_node(state: AgentState) -> AgentState:
    """LangGraph node: dynamically dispatch temporary agents."""
    trace = list(state.get("trace_log", []))
    plan = state.get("plan", {})

    trace.append(make_trace_entry("Supervisor", "Validating swarm tasks", ""))

    prompt = f"""PROBLEM: {state['problem']}

Review the plan and approve the swarm agents to spawn:

PLAN TASKS:
{json.dumps(plan.get('tasks', []), indent=2)}"""

    response = llm_call(prompt, SYSTEM_PROMPT)

    try:
        clean = response.strip().strip("```json").strip("```").strip()
        selection = json.loads(clean)
    except Exception:
        # Fallback
        agents = []
        for t in plan.get('tasks', []):
            agents.append({
                "agent_role": t.get("agent_role", "Worker"),
                "task_id": t.get("task_id", ""),
                "tools_assigned": t.get("tools_to_use", [])
            })
        selection = {
            "approved_swarm_agents": agents,
            "supervisor_note": "Swarm dispatched as planned."
        }

    trace.append(make_trace_entry(
        "Supervisor", "Swarm dispatch complete",
        f"Spawning {len(selection.get('approved_swarm_agents', []))} temporary agents. Note: {selection.get('supervisor_note', '')}",
        "SUCCESS"
    ))

    return {**state, "selected_agents": selection, "trace_log": trace}
