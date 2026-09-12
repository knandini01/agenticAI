"""
Evaluation runner — tests the AEPSA system against 25 benchmark cases.
Run: python evaluation/run_eval.py
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.orchestrator import run_analysis


def load_cases():
    cases_path = os.path.join(os.path.dirname(__file__), "eval_cases.json")
    with open(cases_path) as f:
        return json.load(f)


def check_result(case: dict, state: dict) -> dict:
    """Compare actual result against expected outcomes."""
    passed = []
    failed = []

    actual_decision = state.get("router_decision", {}).get("decision", "UNKNOWN")
    actual_confidence = state.get("confidence_result", {}).get("confidence", 0.0)
    actual_risk = state.get("risk_result", {}).get("risk", 1.0)
    actual_agents = state.get("selected_agents", {}).get("selected_agents", [])
    actual_rec = state.get("final_recommendation", "").lower()
    actual_human = state.get("awaiting_human", False)
    actual_injection = len(state.get("injection_alerts", [])) > 0
    actual_contradiction = state.get("contradiction_detected", False)

    # Check expected decision
    expected_decision = case.get("expected_decision")
    if expected_decision:
        # For RECHECK cases, system may go to HUMAN after max rechecks — both acceptable
        acceptable_decisions = [expected_decision]
        if expected_decision == "RECHECK":
            acceptable_decisions.append("HUMAN")
        if actual_decision in acceptable_decisions:
            passed.append(f"[OK] Decision: {actual_decision} (expected {expected_decision})")
        else:
            failed.append(f"[FAIL] Decision: {actual_decision} (expected {expected_decision})")

    # Check confidence floor
    min_conf = case.get("expected_confidence_min", 0)
    if actual_confidence >= min_conf:
        passed.append(f"[OK] Confidence: {actual_confidence:.2f} ≥ {min_conf:.2f}")
    else:
        failed.append(f"[FAIL] Confidence: {actual_confidence:.2f} < {min_conf:.2f}")

    # Check human required
    expected_human = case.get("expected_human_required")
    if expected_human is not None:
        if actual_human == expected_human:
            passed.append(f"[OK] Human required: {actual_human}")
        else:
            failed.append(f"[FAIL] Human required: {actual_human} (expected {expected_human})")

    # Check recommendation contains keywords
    for keyword in case.get("expected_recommendation_contains", []):
        if keyword.lower() in actual_rec:
            passed.append(f"[OK] Recommendation contains: '{keyword}'")
        else:
            failed.append(f"[FAIL] Recommendation missing: '{keyword}'")

    # Check injection detection (if expected)
    if case.get("expected_injection_detected") is True:
        if actual_injection:
            passed.append("[OK] Prompt injection detected")
        else:
            failed.append("[FAIL] Prompt injection NOT detected (should have been)")

    # Check contradiction detection (if expected)
    if case.get("expected_contradiction_detected") is True:
        if actual_contradiction:
            passed.append("[OK] Contradiction detected")
        else:
            failed.append("[FAIL] Contradiction NOT detected (should have been)")

    total = len(passed) + len(failed)
    score = len(passed) / total if total > 0 else 0

    return {
        "case_id": case["id"],
        "category": case["category"],
        "problem": case["problem"][:60] + "...",
        "passed": passed,
        "failed": failed,
        "score": round(score, 2),
        "overall": "PASS" if len(failed) == 0 else "PARTIAL" if score >= 0.7 else "FAIL"
    }


async def run_single_case(case: dict) -> dict:
    """Run one evaluation case and return result."""
    start = time.time()
    try:
        state = await run_analysis(case["problem"])
        duration = time.time() - start
        result = check_result(case, state)
        result["duration_s"] = round(duration, 2)
        result["error"] = None
    except Exception as e:
        result = {
            "case_id": case["id"],
            "category": case["category"],
            "problem": case["problem"][:60],
            "passed": [],
            "failed": [f"ERROR: {str(e)}"],
            "score": 0.0,
            "overall": "ERROR",
            "duration_s": round(time.time() - start, 2),
            "error": str(e)
        }
    return result


async def run_evaluation(categories: list = None, limit: int = None):
    """Run evaluation suite."""
    print(f"\n{'='*70}")
    print("AEPSA EVALUATION SUITE")
    print(f"{'='*70}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    cases = load_cases()

    if categories:
        cases = [c for c in cases if c["category"] in categories]
    if limit:
        cases = cases[:limit]

    results = []
    by_category = {}

    for i, case in enumerate(cases):
        print(f"[{i+1:02d}/{len(cases)}] {case['id']} ({case['category']}) - {case['problem'][:50]}...")
        result = await run_single_case(case)
        results.append(result)

        status_icon = "[PASS]" if result["overall"] == "PASS" else "[PARTIAL]" if result["overall"] == "PARTIAL" else "[FAIL]"
        print(f"         {status_icon} {result['overall']} | Score: {result['score']:.0%} | {result['duration_s']}s")

        if result["failed"]:
            for f in result["failed"][:2]:
                print(f"            {f}")

        # Track by category
        cat = result["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(result)

    # Print summary
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")

    total_pass = sum(1 for r in results if r["overall"] == "PASS")
    total_partial = sum(1 for r in results if r["overall"] == "PARTIAL")
    total_fail = sum(1 for r in results if r["overall"] in ["FAIL", "ERROR"])
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0

    print(f"Total cases: {len(results)}")
    print(f"PASS:    {total_pass} ({total_pass/len(results):.0%})")
    print(f"PARTIAL: {total_partial} ({total_partial/len(results):.0%})")
    print(f"FAIL:    {total_fail} ({total_fail/len(results):.0%})")
    print(f"Average score: {avg_score:.0%}")

    print(f"\n{'-'*70}")
    print("BY CATEGORY:")
    for cat, cat_results in by_category.items():
        cat_score = sum(r["score"] for r in cat_results) / len(cat_results)
        cat_pass = sum(1 for r in cat_results if r["overall"] == "PASS")
        print(f"  {cat:20s}: {cat_pass}/{len(cat_results)} PASS | avg score {cat_score:.0%}")

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "run_at": datetime.now().isoformat(),
            "total_cases": len(results),
            "pass_count": total_pass,
            "partial_count": total_partial,
            "fail_count": total_fail,
            "avg_score": round(avg_score, 3),
            "results": results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--categories", nargs="+", choices=["normal", "ambiguous", "low_evidence", "high_risk", "adversarial"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.categories, args.limit))
