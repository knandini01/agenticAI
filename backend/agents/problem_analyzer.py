"""
Problem Analyzer Agent — understands what the user is actually asking.
Classifies problem type, complexity, data requirements, and needed capabilities.
"""
import json
import uuid
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.state import AgentState
from agents.llm_client import llm_call, make_trace_entry
from memory.experience_db import find_similar_cases


SYSTEM_PROMPT = """You are the Problem Analyzer for an Enterprise AI Problem-Solving System.
Your job is to analyze a user's problem and classify it precisely.

You must respond ONLY with valid JSON. No markdown, no explanation, just JSON.

Output format:
{
  "problem_type": "root_cause_analysis|prediction|optimization|recommendation|investigation",
  "complexity": "low|medium|high",
  "domain": "manufacturing|finance|healthcare|logistics|general",
  "required_data": ["production", "machine", "maintenance", "supplier", "financial", "hr"],
  "required_agents": ["research_agent", "data_agent", "analysis_agent"],
  "needs_tools": true,
  "needs_verification": true,
  "key_entities": ["Machine M17", "Supplier Y", "defect rate"],
  "time_dimension": "historical|current|predictive",
  "risk_level_hint": "low|medium|high|critical",
  "summary": "One sentence summary of what needs to be investigated"
}"""


def problem_analyzer_node(state: AgentState) -> AgentState:
    """LangGraph node: analyze the problem and classify it."""
    problem = state["problem"]
    trace = list(state.get("trace_log", []))

    trace.append(make_trace_entry("Problem Analyzer", "Analyzing problem", f'"{problem[:80]}..."'))

    # Call LLM to analyze
    prompt = f"""Analyze this enterprise problem and classify it:

PROBLEM: {problem}

Provide the JSON classification."""

    response = llm_call(prompt, SYSTEM_PROMPT)

    # Parse JSON response
    try:
        # Strip any accidental markdown
        clean = response.strip().strip("```json").strip("```").strip()
        analysis = json.loads(clean)
    except Exception as e:
        # Fallback classification
        analysis = {
            "problem_type": "root_cause_analysis",
            "complexity": "high",
            "domain": "manufacturing",
            "required_data": ["production", "machine", "maintenance", "supplier"],
            "required_agents": ["research_agent", "data_agent", "analysis_agent"],
            "needs_tools": True,
            "needs_verification": True,
            "key_entities": [],
            "time_dimension": "historical",
            "risk_level_hint": "medium",
            "summary": problem[:100],
            "parse_error": str(e)
        }

    trace.append(make_trace_entry(
        "Problem Analyzer", "Classification complete",
        f"Type: {analysis['problem_type']} | Complexity: {analysis['complexity']} | "
        f"Agents needed: {', '.join(analysis.get('required_agents', []))}",
        "SUCCESS"
    ))

    # Look up similar past cases from experience DB
    similar_cases = find_similar_cases(problem, analysis["problem_type"])
    if similar_cases:
        trace.append(make_trace_entry(
            "Problem Analyzer", "Experience lookup",
            f"Found {len(similar_cases)} similar past case(s). Strategy reuse possible.",
            "INFO"
        ))

    return {
        **state,
        "problem_id": f"CASE-{str(uuid.uuid4())[:8].upper()}",
        "problem_analysis": analysis,
        "similar_cases": similar_cases,
        "trace_log": trace
    }
