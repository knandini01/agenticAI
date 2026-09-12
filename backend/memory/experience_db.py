"""
Experience DB — stores past problem-solving cases and outcomes.
Enables strategy reuse for similar future problems.
"""
import sqlite3
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import EXPERIENCE_DB_URL


def _conn():
    os.makedirs(os.path.dirname(EXPERIENCE_DB_URL) if os.path.dirname(EXPERIENCE_DB_URL) else ".", exist_ok=True)
    return sqlite3.connect(EXPERIENCE_DB_URL)


def save_case(
    problem_description: str,
    problem_type: str,
    strategy: str,
    agents_used: list[str],
    tools_used: list[str],
    confidence: float,
    risk: float,
    recommendation: str,
    verification_result: str,
    human_required: bool,
    human_decision: Optional[str] = None,
    outcome: Optional[str] = None,
    success: Optional[bool] = None
) -> str:
    """Save a completed case to the experience database. Returns case_id."""
    case_id = f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

    conn = _conn()
    try:
        conn.execute("""
            INSERT INTO experience VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            case_id,
            problem_description,
            problem_type,
            strategy,
            json.dumps(agents_used),
            json.dumps(tools_used),
            confidence,
            risk,
            recommendation,
            verification_result,
            1 if human_required else 0,
            human_decision,
            outcome,
            1 if success else 0 if success is False else None,
            datetime.now().isoformat(),
            datetime.now().isoformat() if outcome else None
        ))
        conn.commit()
    finally:
        conn.close()

    return case_id


def find_similar_cases(problem_description: str, problem_type: str, limit: int = 3) -> list[dict]:
    """
    Find past cases similar to the current problem.
    Simple keyword matching on problem type and description.
    """
    conn = _conn()
    conn.row_factory = sqlite3.Row
    try:
        # Find cases with same type that succeeded
        results = conn.execute("""
            SELECT * FROM experience
            WHERE problem_type = ? AND (success = 1 OR success IS NULL)
            ORDER BY confidence DESC
            LIMIT ?
        """, (problem_type, limit)).fetchall()

        cases = [dict(r) for r in results]

        # Parse JSON fields
        for case in cases:
            if isinstance(case.get("agents_used"), str):
                case["agents_used"] = json.loads(case["agents_used"])
            if isinstance(case.get("tools_used"), str):
                case["tools_used"] = json.loads(case["tools_used"])

        return cases
    finally:
        conn.close()


def get_successful_strategies(problem_type: str) -> list[dict]:
    """Get winning strategies for a given problem type."""
    conn = _conn()
    conn.row_factory = sqlite3.Row
    try:
        results = conn.execute("""
            SELECT strategy, agents_used, tools_used, confidence, risk,
                   outcome, created_at,
                   COUNT(*) as usage_count,
                   AVG(confidence) as avg_confidence
            FROM experience
            WHERE problem_type = ? AND success = 1
            GROUP BY strategy
            ORDER BY avg_confidence DESC
        """, (problem_type,)).fetchall()

        strategies = [dict(r) for r in results]
        for s in strategies:
            if isinstance(s.get("agents_used"), str):
                s["agents_used"] = json.loads(s["agents_used"])
            if isinstance(s.get("tools_used"), str):
                s["tools_used"] = json.loads(s["tools_used"])
        return strategies
    finally:
        conn.close()


def get_all_cases(limit: int = 20) -> list[dict]:
    """Return recent cases for the Experience panel in the UI."""
    conn = _conn()
    conn.row_factory = sqlite3.Row
    try:
        results = conn.execute("""
            SELECT case_id, problem_description, problem_type, strategy,
                   confidence, risk, human_required, success, created_at, outcome
            FROM experience
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in results]
    finally:
        conn.close()


def update_case_outcome(case_id: str, outcome: str, success: bool):
    """Update a case with the real-world outcome after implementation."""
    conn = _conn()
    try:
        conn.execute("""
            UPDATE experience
            SET outcome = ?, success = ?, resolved_at = ?
            WHERE case_id = ?
        """, (outcome, 1 if success else 0, datetime.now().isoformat(), case_id))
        conn.commit()
    finally:
        conn.close()
