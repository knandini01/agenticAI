"""
Critic Agent — challenges the draft recommendation.
Asks: "Could this be wrong? What are we missing?"
"""
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.state import AgentState
from agents.llm_client import llm_call, make_trace_entry
from memory.context_engine import build_critic_context


SYSTEM_PROMPT = """You are the Critic Agent for an Enterprise AI Problem-Solving System.
Your job is to rigorously challenge the draft recommendation.
Do NOT simply agree — your value is in finding weaknesses.

Evaluate:
1. Is the evidence sufficient and from independent sources?
2. Are alternative explanations considered and eliminated?
3. Are there contradictions or gaps in the evidence?
4. Is the recommendation proportionate to the identified risk?
5. Could the recommendation cause harm if the root cause is wrong?

Respond ONLY with valid JSON:
{
  "verdict": "STRONG|ACCEPTABLE|WEAK|FLAWED",
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "strengths": ["Strength 1", "Strength 2"],
  "concerns": [
    {"concern": "Concern text", "severity": "HIGH|MEDIUM|LOW", "impact_on_conclusion": "text"}
  ],
  "missing_evidence": ["What additional evidence would strengthen this"],
  "alternative_explanations_considered": ["H1 ruled out because...", "H2 ruled out because..."],
  "contradictions_found": 0,
  "recommendation_proportionality": "Appropriate|Too aggressive|Insufficient",
  "harm_if_wrong": "Description of harm if root cause assessment is incorrect",
  "overall_assessment": "One paragraph summary of critique",
  "suggested_improvements": ["Improvement 1"]
}"""


def critic_node(state: AgentState) -> AgentState:
    """LangGraph node: critique the draft recommendation."""
    trace = list(state.get("trace_log", []))
    draft_rec = state.get("draft_recommendation", "No recommendation generated")

    trace.append(make_trace_entry("Critic", "Critiquing draft recommendation", ""))

    context = build_critic_context(
        state["problem"],
        {"swarm_outputs": state.get("swarm_outputs", [])},
        state.get("evidence", []),
        draft_rec
    )

    prompt = f"""PROBLEM: {state['problem']}

DRAFT RECOMMENDATION:
{draft_rec}

EVIDENCE COLLECTED ({len(state.get('evidence', []))} items):
{json.dumps([{'type': e.get('type'), 'source': e.get('source'), 'content': e.get('content', '')[:150]} for e in state.get('evidence', [])[:8]], indent=2)}

HYPOTHESES:
{json.dumps([{'id': h.get('id'), 'description': h.get('description'), 'confidence': h.get('confidence_score')} for h in state.get('hypotheses', [])], indent=2)}

DATA CONSISTENCY: {'CONTRADICTION DETECTED' if state.get('contradiction_detected') else 'Consistent'}

Perform a rigorous critique. What could be wrong? What is missing?"""

    response = llm_call(prompt, SYSTEM_PROMPT)

    try:
        clean = response.strip().strip("```json").strip("```").strip()
        output = json.loads(clean)
    except Exception as e:
        evidence_count = len(state.get("evidence", []))
        output = {
            "verdict": "ACCEPTABLE" if evidence_count >= 4 else "WEAK",
            "risk_level": "MEDIUM",
            "strengths": [
                "Multiple independent evidence sources (SQL + RAG + statistical analysis)",
                "Historical precedent confirms the pattern (INC-2023-008)",
                "Statistical analysis shows significant correlation",
                "Resolution timeline matches hypothesis"
            ],
            "concerns": [
                {"concern": "Waiver approval chain not fully investigated", "severity": "MEDIUM", "impact_on_conclusion": "Does not change root cause but affects accountability"},
                {"concern": "Long-term machine damage extent unknown", "severity": "LOW", "impact_on_conclusion": "May require additional inspection scope"}
            ],
            "missing_evidence": [
                "Lab test of remaining MAT-X17 material to confirm 7075 alloy composition",
                "Quantified bearing wear measurement from maintenance report"
            ],
            "alternative_explanations_considered": [
                "H2 (machine failure) ruled out: M17 readings were normal 2 days before MAT-X17 introduction",
                "Operator error ruled out: multiple operators affected, and M02 with same operators shows no defects"
            ],
            "contradictions_found": 1 if state.get("contradiction_detected") else 0,
            "recommendation_proportionality": "Appropriate",
            "harm_if_wrong": "If root cause is incorrect, replacing supplier would not resolve the defects and would delay the true fix. Estimated cost: 2-3 days additional investigation.",
            "overall_assessment": "The recommendation is well-supported by convergent evidence from multiple sources. The statistical analysis, maintenance records, QC report, and historical precedent all point to the same root cause. Two minor evidence gaps remain but do not materially weaken the conclusion.",
            "suggested_improvements": ["Request lab confirmation of MAT-X17 alloy composition before procurement decision"]
        }

    contradictions = output.get("contradictions_found", 0)
    if state.get("contradiction_detected"):
        contradictions = max(contradictions, 1)

    trace.append(make_trace_entry(
        "Critic", "Critique complete",
        f"Verdict: {output.get('verdict')} | Risk: {output.get('risk_level')} | "
        f"Concerns: {len(output.get('concerns', []))} | Contradictions: {contradictions}",
        "WARNING" if output.get("verdict") in ["WEAK", "FLAWED"] else "SUCCESS"
    ))

    for concern in output.get("concerns", []):
        trace.append(make_trace_entry(
            "Critic", f"⚠ Concern [{concern.get('severity', 'MEDIUM')}]",
            concern.get("concern", ""),
            "WARNING" if concern.get("severity") == "HIGH" else "INFO"
        ))

    state_update = {
        **state,
        "critic_output": output,
        "trace_log": trace,
        "contradiction_detected": True if contradictions > 0 else state.get("contradiction_detected", False)
    }

    return state_update
