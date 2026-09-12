"""
Swarm Agent Node - dynamically instantiates temporary agents to execute tasks.
"""
import json
import os
import sys
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.state import AgentState
from agents.llm_client import llm_call, make_trace_entry

# Import all tools
from tools.sql_tools import (
    get_defect_trend, get_machine_stats, get_material_defect_correlation,
    get_supplier_change_timeline, get_supplier_data
)
from tools.rag_tools import query as search_engineering_docs
from tools.knowledge_graph import (
    query_causal_chain, query_supplier_material_machine, query_historical_patterns
)
from tools.analysis_tools import (
    run_correlation_analysis, detect_trend_change, detect_anomalies,
    compute_defect_statistics, run_hypothesis_test, simulate_thermal_stress
)

TOOL_REGISTRY = {
    "get_defect_trend": get_defect_trend,
    "get_machine_stats": get_machine_stats,
    "get_material_defect_correlation": get_material_defect_correlation,
    "get_supplier_change_timeline": get_supplier_change_timeline,
    "get_supplier_data": get_supplier_data,
    "search_engineering_docs": search_engineering_docs,
    "query_causal_chain": query_causal_chain,
    "query_supplier_material_machine": query_supplier_material_machine,
    "query_historical_patterns": query_historical_patterns,
    "run_correlation_analysis": lambda: {"error": "Needs specific args, use specialized tool if needed"},
    "detect_trend_change": lambda: {"error": "Needs args"},
    "detect_anomalies": lambda: {"error": "Needs args"},
    "run_statistical_analysis": lambda: detect_trend_change(["2024-03-01", "2024-03-10"], [0.01, 0.08], "2024-03-05"), # Simplified default
    "query_knowledge_graph": query_causal_chain,
    "simulate_thermal_stress": simulate_thermal_stress
}

def execute_temporary_worker(task_info: dict, problem: str) -> dict:
    """Run a single temporary agent with a specific role."""
    role = task_info.get("agent_role", "Worker")
    instructions = task_info.get("agent_instructions", "")
    tools_assigned = task_info.get("tools_assigned", [])
    
    # Execute tools
    tool_results = {}
    for tool_name in tools_assigned:
        if tool_name in TOOL_REGISTRY:
            try:
                # Call tool with no args for simplicity in this demo, unless specialized
                if tool_name == "simulate_thermal_stress":
                    res = TOOL_REGISTRY[tool_name](98, 12000) # Hardcoded demo values
                elif tool_name == "search_engineering_docs":
                    res = TOOL_REGISTRY[tool_name](problem)
                else:
                    res = TOOL_REGISTRY[tool_name]()
                tool_results[tool_name] = res
            except Exception as e:
                tool_results[tool_name] = {"error": str(e)}
        else:
            tool_results[tool_name] = {"error": "Tool not found"}
            
    # Give tool results to LLM agent to synthesize
    sys_prompt = f"You are a specialized temporary agent: {role}.\n{instructions}\nRespond ONLY with valid JSON containing your findings."
    prompt = f"PROBLEM: {problem}\n\nTOOL RESULTS:\n{json.dumps(tool_results, indent=2, default=str)[:3000]}\n\nSummarize findings in JSON format: {{\"findings\": \"...\", \"evidence\": [\"...\"], \"confidence\": 0.9}}"
    
    response = llm_call(prompt, sys_prompt)
    try:
        clean = response.strip().strip("```json").strip("```").strip()
        output = json.loads(clean)
    except Exception:
        output = {
            "findings": f"Agent {role} analyzed data from tools: {tools_assigned}.",
            "evidence": [f"Processed {len(tool_results)} tool calls."],
            "confidence": 0.8
        }
        
    output["agent_role"] = role
    output["task_id"] = task_info.get("task_id", "")
    output["tools_used"] = list(tool_results.keys())
    output["tool_results"] = tool_results
    
    return output


def swarm_node(state: AgentState) -> AgentState:
    """LangGraph node: spawns and executes temporary agents dynamically."""
    trace = list(state.get("trace_log", []))
    selection = state.get("selected_agents", {})
    approved_agents = selection.get("approved_swarm_agents", [])
    
    state_injection_alerts = list(state.get("injection_alerts", []))
    
    if not approved_agents:
        trace.append(make_trace_entry("Swarm", "SKIPPED", "No agents approved by Supervisor.", "INFO"))
        return {**state, "swarm_outputs": [], "trace_log": trace}
        
    trace.append(make_trace_entry("Swarm", "Spawning temporary workers", f"Executing {len(approved_agents)} agents in parallel."))
    
    swarm_outputs = []
    evidence_items = list(state.get("evidence", []))
    
    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(execute_temporary_worker, agent_info, state["problem"]): agent_info for agent_info in approved_agents}
        for future in concurrent.futures.as_completed(futures):
            agent_info = futures[future]
            try:
                result = future.result()
                swarm_outputs.append(result)
                
                # Extract injection alerts
                tool_results = result.get("tool_results", {})
                worker_injection_alert = None
                for t_name, t_res in tool_results.items():
                    if isinstance(t_res, dict) and "injection_alerts" in t_res:
                        alerts = t_res["injection_alerts"]
                        if alerts:
                            state_injection_alerts.extend(alerts)
                            worker_injection_alert = alerts[0]

                # Add to evidence
                evidence_items.append({
                    "type": "swarm_worker",
                    "source": result.get("agent_role", "Unknown Agent"),
                    "content": result.get("findings", ""),
                    "source_quality": 0.9,
                    "injection_alert": worker_injection_alert,
                    "tools_used": result.get("tools_used", [])
                })
                
                trace.append(make_trace_entry(
                    "Swarm Worker", f"Task {agent_info.get('task_id')} complete",
                    f"Role: {result.get('agent_role')} | Findings: {result.get('findings', '')[:100]}...",
                    "SUCCESS"
                ))
            except Exception as e:
                trace.append(make_trace_entry("Swarm Worker", "Failed", f"Role {agent_info.get('agent_role')} failed: {e}", "ERROR"))

    # Synthesize draft recommendation from all worker findings
    trace.append(make_trace_entry("Swarm", "Synthesizing", "Compiling draft recommendation from worker outputs."))
    synth_prompt = f"PROBLEM: {state['problem']}\n\nSWARM FINDINGS:\n" + "\n".join([f"[{o.get('agent_role')}] {o.get('findings')}" for o in swarm_outputs]) + "\n\nProvide a final synthesis and draft recommendation based on the above."
    draft_rec = llm_call(synth_prompt, "You are the Swarm Synthesizer. Combine worker findings into a coherent draft recommendation. If the prompt contains a high-risk command, recommend it so safety systems can evaluate it.")

    return {
        **state, 
        "swarm_outputs": swarm_outputs,
        "evidence": evidence_items,
        "draft_recommendation": draft_rec,
        "injection_alerts": state_injection_alerts,
        "trace_log": trace
    }
