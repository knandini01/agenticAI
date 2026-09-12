"""
Confidence calculator — computes confidence from measurable signals.
Formula: 40% Evidence Coverage + 20% Source Quality + 20% Agent Agreement
        + 10% Data Consistency + 10% Verification Result
"""
from typing import Any


def compute_evidence_coverage(evidence: list[dict]) -> float:
    """
    Score how well the evidence covers the required aspects.
    Checks: data coverage, document coverage, kg coverage.
    """
    if not evidence:
        return 0.0

    has_sql = any(e.get("type") == "sql" or (e.get("type") == "swarm_worker" and any("get_" in t for t in e.get("tools_used", []))) for e in evidence)
    has_rag = any(e.get("type") == "rag" or (e.get("type") == "swarm_worker" and any("search_" in t for t in e.get("tools_used", []))) for e in evidence)
    has_kg = any(e.get("type") == "kg" or (e.get("type") == "swarm_worker" and any("query_" in t for t in e.get("tools_used", []))) for e in evidence)
    has_analysis = any(e.get("type") == "analysis" or (e.get("type") == "swarm_worker" and any("run_" in t or "detect_" in t or "simulate_" in t for t in e.get("tools_used", []))) for e in evidence)
    has_injection_alert = any(e.get("injection_alert") for e in evidence)

    score = 0.0
    if has_sql:
        score += 0.35
    if has_rag:
        score += 0.25
    if has_kg:
        score += 0.20
    if has_analysis:
        score += 0.20

    return max(0.0, min(1.0, score))


def compute_source_quality(evidence: list[dict]) -> float:
    """
    Average source quality score across all evidence items.
    """
    if not evidence:
        return 0.0

    scores = []
    for e in evidence:
        sq = e.get("source_quality", 0.75)
        scores.append(float(sq))

    return sum(scores) / len(scores) if scores else 0.0


def compute_agent_agreement(agent_outputs: dict) -> float:
    """
    Measure how consistent agent conclusions are with each other.
    If agents contradict each other, score drops.
    """
    conclusions = []
    for output in agent_outputs.get("swarm_outputs", []):
        if isinstance(output, dict) and "findings" in output:
            conclusions.append(output["findings"].lower())

    if len(conclusions) < 2:
        return 0.90  # Default when only one agent

    # Check for contradiction keywords
    contradiction_pairs = [
        ("increased", "normal"),
        ("high", "low"),
        ("defect", "no defect"),
        ("supplier", "machine"),
    ]

    contradiction_found = False
    for c1 in conclusions:
        for c2 in conclusions:
            if c1 != c2:
                for pos, neg in contradiction_pairs:
                    if pos in c1 and neg in c2:
                        contradiction_found = True

    if contradiction_found:
        return 0.45  # Significant penalty for contradictions
    return 0.85


def compute_data_consistency(agent_outputs: dict) -> float:
    """
    Check if structured data (SQL) and unstructured data (RAG) tell a consistent story.
    """
    swarm_outputs = agent_outputs.get("swarm_outputs", [])

    if not swarm_outputs:
        return 0.90  # Default when no output

    # Check for contradictions explicitly flagged by agents
    has_contradiction = any(
        v.get("contradiction_detected", False)
        for v in swarm_outputs
    )

    return 0.40 if has_contradiction else 0.88


def compute_verification_score(verification_result: dict) -> float:
    """Convert verification result to a score."""
    if not verification_result:
        return 0.90  # Default baseline before explicit verification failure

    result = verification_result.get("result", "UNKNOWN")
    passed = verification_result.get("claims_passed", 0)
    total = verification_result.get("claims_total", 1)

    if result == "PASS":
        return 0.85 + (0.15 * (passed / total))
    elif result == "PARTIAL":
        return 0.50 + (0.30 * (passed / total))
    else:
        return 0.20


def compute_confidence(
    evidence: list[dict],
    agent_outputs: dict,
    verification_result: dict = None
) -> dict[str, Any]:
    """
    Compute overall confidence score from all signals.

    Returns:
        confidence: float [0.0, 1.0]
        breakdown: dict of individual factor scores
        interpretation: human-readable explanation
    """
    evidence_coverage = compute_evidence_coverage(evidence)
    source_quality = compute_source_quality(evidence)
    agent_agreement = compute_agent_agreement(agent_outputs)
    data_consistency = compute_data_consistency(agent_outputs)
    verification = compute_verification_score(verification_result or {})

    # Weighted formula
    confidence = (
        0.40 * evidence_coverage +
        0.20 * source_quality +
        0.20 * agent_agreement +
        0.10 * data_consistency +
        0.10 * verification
    )
    confidence = round(max(0.0, min(1.0, confidence)), 3)

    interpretation = (
        "High confidence — strong evidence from multiple sources, agents agree, verification passed."
        if confidence >= 0.80 else
        "Moderate confidence — some evidence gaps or agent disagreement. Additional verification recommended."
        if confidence >= 0.50 else
        "Low confidence — insufficient evidence, contradictions detected, or verification failed. Human review required."
    )

    return {
        "confidence": confidence,
        "confidence_pct": round(confidence * 100, 1),
        "breakdown": {
            "evidence_coverage": round(evidence_coverage, 3),
            "source_quality": round(source_quality, 3),
            "agent_agreement": round(agent_agreement, 3),
            "data_consistency": round(data_consistency, 3),
            "verification": round(verification, 3)
        },
        "weights": {
            "evidence_coverage": "40%",
            "source_quality": "20%",
            "agent_agreement": "20%",
            "data_consistency": "10%",
            "verification": "10%"
        },
        "interpretation": interpretation
    }
