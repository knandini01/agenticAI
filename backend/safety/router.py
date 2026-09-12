"""
Safety Router — routes to APPROVE / RECHECK / HUMAN based on confidence + risk.
Implements the three-rule routing logic from the spec.
"""
from typing import Any
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    CONFIDENCE_APPROVE_THRESHOLD, CONFIDENCE_RECHECK_MIN,
    RISK_APPROVE_MAX, RISK_HUMAN_MIN, MAX_RECHECK_ITERATIONS
)


def route(
    confidence: float,
    risk: float,
    evidence: list,
    critic_output: dict,
    recheck_count: int = 0,
    contradiction_detected: bool = False
) -> dict[str, Any]:
    """
    Route the recommendation to one of three outcomes:
      - APPROVE: safe to present to user
      - RECHECK: retrieve more evidence and re-analyze
      - HUMAN: escalate to human review

    Rules:
      Rule A — APPROVE: confidence ≥ 0.80 AND risk ≤ 0.30 AND evidence sufficient
      Rule B — RECHECK: 0.50 ≤ confidence < 0.80 (up to MAX_RECHECK_ITERATIONS)
      Rule C — HUMAN: confidence < 0.50 OR risk > 0.70 OR contradictions OR tool failures
    """
    has_sufficient_evidence = len(evidence) >= 3

    # Rule C — Human escalation (highest priority check)
    human_reasons = []

    if confidence < CONFIDENCE_RECHECK_MIN:
        human_reasons.append(f"Confidence {confidence:.2f} below minimum threshold {CONFIDENCE_RECHECK_MIN}")

    if risk > RISK_HUMAN_MIN:
        human_reasons.append(f"Risk {risk:.2f} exceeds human escalation threshold {RISK_HUMAN_MIN}")

    if contradiction_detected:
        human_reasons.append("Contradictory evidence detected between sources")

    critic_risk = critic_output.get("risk_level", "LOW") if critic_output else "LOW"
    if critic_risk == "CRITICAL":
        human_reasons.append("Critic flagged CRITICAL risk level")

    if recheck_count >= MAX_RECHECK_ITERATIONS:
        human_reasons.append(f"Maximum recheck iterations ({MAX_RECHECK_ITERATIONS}) reached without sufficient confidence")

    if human_reasons:
        return {
            "decision": "HUMAN",
            "rule": "Rule C",
            "confidence": confidence,
            "risk": risk,
            "reasons": human_reasons,
            "message": "Human review required. This recommendation has insufficient confidence or carries unacceptable risk for autonomous approval.",
            "escalation_context": {
                "what_to_review": human_reasons,
                "available_actions": ["APPROVE", "MODIFY", "REJECT"],
                "urgency": "HIGH" if risk > 0.70 else "MEDIUM"
            }
        }

    # Rule A — Approve
    if (confidence >= CONFIDENCE_APPROVE_THRESHOLD and
            risk <= RISK_APPROVE_MAX and
            has_sufficient_evidence):
        return {
            "decision": "APPROVE",
            "rule": "Rule A",
            "confidence": confidence,
            "risk": risk,
            "reasons": [
                f"Confidence {confidence:.2f} >= threshold {CONFIDENCE_APPROVE_THRESHOLD}",
                f"Risk {risk:.2f} <= threshold {RISK_APPROVE_MAX}",
                f"Evidence count {len(evidence)} sufficient"
            ],
            "message": "Recommendation approved for presentation."
        }

    # Rule B — Recheck
    recheck_reasons = []
    if confidence < CONFIDENCE_APPROVE_THRESHOLD:
        recheck_reasons.append(f"Confidence {confidence:.2f} < threshold {CONFIDENCE_APPROVE_THRESHOLD}")
    if risk > RISK_APPROVE_MAX:
        recheck_reasons.append(f"Risk {risk:.2f} > threshold {RISK_APPROVE_MAX}")
    if not has_sufficient_evidence:
        recheck_reasons.append(f"Insufficient evidence items ({len(evidence)} < 3 required)")

    return {
        "decision": "RECHECK",
        "rule": "Rule B",
        "confidence": confidence,
        "risk": risk,
        "recheck_count": recheck_count + 1,
        "max_rechecks": MAX_RECHECK_ITERATIONS,
        "reasons": recheck_reasons,
        "message": f"Re-analyzing with additional evidence. Attempt {recheck_count + 1}/{MAX_RECHECK_ITERATIONS}.",
        "recheck_strategy": "Retrieve additional documents and re-run analysis with broader evidence scope."
    }
