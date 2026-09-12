"""
Planner Agent — converts problem analysis into an ordered investigation plan.
Checks experience DB for successful past strategies to reuse.
"""
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.state import AgentState
from agents.llm_client import llm_call, make_trace_entry
from memory.experience_db import get_successful_strategies


SYSTEM_PROMPT = """You are the Planner for an Enterprise AI Problem-Solving System.
Your job is to create an ordered investigation plan given a problem analysis.
Instead of using fixed agents, you MUST dynamically invent temporary agent roles (e.g., "Thermal Dynamics Specialist", "Historical Records Investigator", "Sensor Data Analyst") to execute specific tasks.

You must respond ONLY with valid JSON. No markdown, no explanation.

Output format:
{
  "strategy_name": "short_snake_case_strategy_name",
  "strategy_description": "One sentence description of the overall investigation approach",
  "tasks": [
    {
      "task_id": "T1",
      "description": "Task description",
      "agent_role": "Dynamic Role Name (e.g. Sensor Data Analyst)",
      "agent_instructions": "Specific prompt for the agent",
      "tools_to_use": ["tool_name_1", "tool_name_2"],
      "depends_on": [],
      "priority": "high|medium|low"
    }
  ],
  "estimated_duration": "short|medium|long",
  "reusing_past_strategy": false,
  "past_strategy_reference": null
}"""


def planner_node(state: AgentState) -> AgentState:
    """LangGraph node: generate investigation plan from problem analysis."""
    trace = list(state.get("trace_log", []))
    analysis = state.get("problem_analysis", {})
    similar_cases = state.get("similar_cases", [])

    trace.append(make_trace_entry("Planner", "Generating investigation plan", ""))

    # Check if we have a past successful strategy to reuse
    past_strategies = get_successful_strategies(analysis.get("problem_type", "root_cause_analysis"))
    strategy_hint = ""
    reusing = False

    if past_strategies:
        best = past_strategies[0]
        strategy_hint = f"""
IMPORTANT: A similar problem was successfully solved before using this strategy:
Strategy: {best['strategy']}
Agents used: {best.get('agents_used', [])}
Tools used: {best.get('tools_used', [])}
Result confidence: {best.get('avg_confidence', 0.0):.2f}
Consider reusing this strategy adapted to the current problem.
"""
        reusing = True
        trace.append(make_trace_entry(
            "Planner", "Experience reuse",
            f"Found successful past strategy: '{best['strategy']}' (confidence: {best.get('avg_confidence', 0):.2f}). Adapting for current problem.",
            "INFO"
        ))

    prompt = f"""Create an investigation plan for this problem:

PROBLEM: {state['problem']}

PROBLEM ANALYSIS:
{json.dumps(analysis, indent=2)}

{strategy_hint}

Create a detailed task plan with 6-10 tasks. Remember to invent dynamic agent_roles."""

    response = llm_call(prompt, SYSTEM_PROMPT)

    try:
        clean = response.strip().strip("```json").strip("```").strip()
        plan = json.loads(clean)
    except Exception as e:
        # Fallback plan
        plan = {
            "strategy_name": "supplier_machine_investigation",
            "strategy_description": "Investigate supplier changes and machine data to identify root cause of quality issue",
            "tasks": [
                {"task_id": "T1", "description": "Retrieve defect rate trend data", "agent_role": "Production Data Analyst", "agent_instructions": "Get defect history and analyze trend.", "tools_to_use": ["get_defect_trend"], "depends_on": [], "priority": "high"},
                {"task_id": "T2", "description": "Retrieve machine sensor data", "agent_role": "Machine Telemetry Expert", "agent_instructions": "Analyze machine stats for anomalies.", "tools_to_use": ["get_machine_stats"], "depends_on": [], "priority": "high"},
                {"task_id": "T3", "description": "Check supplier change timeline", "agent_role": "Supply Chain Investigator", "agent_instructions": "Check for supplier changes matching the anomaly timeline.", "tools_to_use": ["get_supplier_change_timeline", "get_supplier_data"], "depends_on": [], "priority": "high"},
                {"task_id": "T4", "description": "Search engineering documents and historical incidents", "agent_role": "Historical Records Researcher", "agent_instructions": "Search documentation for related incidents.", "tools_to_use": ["search_engineering_docs"], "depends_on": [], "priority": "high"},
                {"task_id": "T5", "description": "Run statistical correlation and trend analysis", "agent_role": "Statistical Modeler", "agent_instructions": "Run statistical tests to correlate variables.", "tools_to_use": ["run_statistical_analysis"], "depends_on": ["T1", "T2", "T3"], "priority": "high"},
                {"task_id": "T6", "description": "Query knowledge graph for causal relationships", "agent_role": "Causal Graph Analyst", "agent_instructions": "Query KG for causal chains related to the issue.", "tools_to_use": ["query_knowledge_graph"], "depends_on": ["T3"], "priority": "medium"},
            ],
            "estimated_duration": "medium",
            "reusing_past_strategy": reusing,
            "past_strategy_reference": past_strategies[0]["strategy"] if past_strategies else None
        }

    plan["reusing_past_strategy"] = reusing

    trace.append(make_trace_entry(
        "Planner", "Plan generated",
        f"Strategy: '{plan.get('strategy_name')}' | {len(plan.get('tasks', []))} tasks planned",
        "SUCCESS"
    ))

    return {**state, "plan": plan, "trace_log": trace}
