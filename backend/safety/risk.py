"""
Risk scorer — separate from confidence.
High confidence + high risk = still requires careful handling.
"""
from typing import Any


# Risk factors and their base weights
RISK_FACTORS = {
    "action_reversibility": 0.30,   # Is the recommended action reversible?
    "impact_scope": 0.25,           # How many people/machines/revenue affected?
    "data_uncertainty": 0.20,       # How uncertain is the underlying data?
    "critic_flags": 0.15,           # Did the critic flag serious concerns?
    "policy_violation_risk": 0.10,  # Does action risk violating policy?
}


def assess_action_reversibility(recommendation: str) -> float:
    """Score action reversibility. Irreversible actions score higher risk."""
    high_risk_keywords = [
        "stop production", "halt", "shut down", "terminate", "fire", "replace all",
        "immediate", "emergency", "recall", "discard", "destroy"
    ]
    medium_risk_keywords = [
        "replace", "remove", "recalibrate", "retrain", "change supplier",
        "inspect all", "suspend"
    ]

    rec_lower = recommendation.lower() if recommendation else ""

    if any(k in rec_lower for k in high_risk_keywords):
        return 0.80
    elif any(k in rec_lower for k in medium_risk_keywords):
        return 0.35
    return 0.20


def assess_impact_scope(agent_outputs: dict, evidence: list) -> float:
    """Score potential impact scope of the recommended action."""
    # Count affected machines from evidence
    machines = set()
    for e in evidence:
        content = str(e.get("content", ""))
        for m in ["M01", "M02", "M17", "M03", "M04", "M05"]:
            if m in content:
                machines.add(m)

    if len(machines) >= 3:
        return 0.70
    elif len(machines) == 2:
        return 0.50
    elif len(machines) == 1:
        return 0.30
    return 0.25


def assess_data_uncertainty(confidence_breakdown: dict) -> float:
    """Derive uncertainty from confidence breakdown."""
    evidence_coverage = confidence_breakdown.get("evidence_coverage", 0.5)
    # Uncertainty is inverse of evidence coverage
    return round(1.0 - evidence_coverage, 3)


def assess_critic_flags(critic_output: dict) -> float:
    """Score risk from critic's concerns."""
    if not critic_output:
        return 0.20

    severity = critic_output.get("risk_level", "LOW")
    missing_evidence = critic_output.get("missing_evidence_count", 0)
    contradictions = critic_output.get("contradictions_found", 0)

    base = {
        "CRITICAL": 0.90,
        "HIGH": 0.70,
        "MEDIUM": 0.45,
        "LOW": 0.20
    }.get(severity, 0.30)

    # Increase for each missing evidence item or contradiction
    adjustment = (missing_evidence * 0.05) + (contradictions * 0.10)
    return min(1.0, base + adjustment)


def assess_policy_risk(evidence: list) -> float:
    """Check if evidence mentions policy violations or constraints."""
    policy_risk_keywords = [
        "waiver", "violation", "override", "quality hold",
        "mandatory review", "human required"
    ]

    for e in evidence:
        content = str(e.get("content", "")).lower()
        if any(k in content for k in policy_risk_keywords):
            return 0.65

    return 0.15


def compute_risk(
    recommendation: str,
    agent_outputs: dict,
    evidence: list,
    critic_output: dict,
    confidence_breakdown: dict
) -> dict[str, Any]:
    """
    Compute risk score independent of confidence.

    Returns:
        risk: float [0.0, 1.0]
        breakdown: individual factor scores
        level: LOW / MEDIUM / HIGH / CRITICAL
    """
    action_rev = assess_action_reversibility(recommendation)
    impact = assess_impact_scope(agent_outputs, evidence)
    uncertainty = assess_data_uncertainty(confidence_breakdown)
    critic = assess_critic_flags(critic_output)
    policy = assess_policy_risk(evidence)

    risk = (
        RISK_FACTORS["action_reversibility"] * action_rev +
        RISK_FACTORS["impact_scope"] * impact +
        RISK_FACTORS["data_uncertainty"] * uncertainty +
        RISK_FACTORS["critic_flags"] * critic +
        RISK_FACTORS["policy_violation_risk"] * policy
    )
    risk = round(max(0.0, min(1.0, risk)), 3)

    level = (
        "CRITICAL" if risk > 0.80 else
        "HIGH" if risk > 0.60 else
        "MEDIUM" if risk > 0.35 else
        "LOW"
    )

    return {
        "risk": risk,
        "risk_pct": round(risk * 100, 1),
        "level": level,
        "breakdown": {
            "action_reversibility": round(action_rev, 3),
            "impact_scope": round(impact, 3),
            "data_uncertainty": round(uncertainty, 3),
            "critic_flags": round(critic, 3),
            "policy_risk": round(policy, 3)
        },
        "weights": {
            "action_reversibility": "30%",
            "impact_scope": "25%",
            "data_uncertainty": "20%",
            "critic_flags": "15%",
            "policy_risk": "10%"
        }
    }
