"""
FastMCP server — exposes enterprise tools as MCP-compatible endpoints.
Agents call these via the MCP protocol; tools are registered with @mcp.tool().
"""
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP

# Import tool modules
from tools.sql_tools import (
    get_defect_trend, get_machine_stats, get_maintenance_records,
    get_supplier_data, get_machines_by_defect_rate,
    get_material_defect_correlation, get_supplier_change_timeline
)
from tools.rag_tools import query as rag_query, detect_prompt_injection
from tools.analysis_tools import (
    run_correlation_analysis, detect_trend_change,
    detect_anomalies, compute_defect_statistics, run_hypothesis_test
)
from tools.knowledge_graph import (
    query_causal_chain, query_supplier_material_machine,
    query_historical_patterns, query_machine_risk
)

mcp = FastMCP("Enterprise Problem-Solving AI Tools")


# ─── Structured Data Tools ────────────────────────────────────────────────────

@mcp.tool()
def get_machine_data(machine_id: Optional[str] = None) -> dict:
    """
    Retrieve sensor data (temperature, vibration, pressure) for machines.
    Filter by machine_id or get all machines.
    """
    return get_machine_stats(machine_id)


@mcp.tool()
def get_defect_history(
    machine_id: Optional[str] = None,
    start_date: str = "2024-02-01",
    end_date: str = "2024-04-30"
) -> dict:
    """
    Retrieve production defect rate history over a date range.
    Optionally filter by machine_id.
    """
    return get_defect_trend(machine_id, start_date, end_date)


@mcp.tool()
def get_maintenance_history(machine_id: Optional[str] = None) -> dict:
    """Retrieve maintenance records and events for machines."""
    return get_maintenance_records(machine_id)


@mcp.tool()
def get_supplier_history(supplier_id: Optional[str] = None) -> dict:
    """Retrieve supplier delivery records and quality scores."""
    return get_supplier_data(supplier_id)


@mcp.tool()
def get_material_correlation() -> dict:
    """
    Correlate material batches with defect rates across all production runs.
    Useful for identifying if a material change caused quality issues.
    """
    return get_material_defect_correlation()


@mcp.tool()
def get_supplier_timeline() -> dict:
    """
    Get a timeline showing when supplier changes occurred relative to defect rate changes.
    """
    return get_supplier_change_timeline()


@mcp.tool()
def get_high_defect_machines(threshold: float = 0.03) -> dict:
    """
    Find machines with average defect rate above a threshold.
    Default threshold is 3%.
    """
    return get_machines_by_defect_rate(threshold)


# ─── RAG / Document Search ────────────────────────────────────────────────────

@mcp.tool()
def search_engineering_docs(query: str, top_k: int = 5) -> dict:
    """
    Semantic search across enterprise documents including machine manuals,
    supplier reports, historical incident reports, and quality policies.
    Returns relevant text chunks with source attribution.
    Automatically detects and blocks prompt injection in retrieved content.
    """
    return rag_query(query, top_k=top_k)


@mcp.tool()
def check_prompt_injection(text: str) -> dict:
    """
    Security check: detect prompt injection patterns in a text string.
    Returns detection result and matched patterns.
    """
    return detect_prompt_injection(text)


# ─── Statistical Analysis Tools ───────────────────────────────────────────────

@mcp.tool()
def run_statistical_analysis(
    analysis_type: str,
    data: dict,
    params: Optional[dict] = None
) -> dict:
    """
    Run statistical analysis on provided data.
    analysis_type options:
      - 'correlation': Pearson correlation between two columns
      - 'trend_change': Detect statistically significant trend changes
      - 'anomaly': Z-score based anomaly detection
      - 'descriptive': Descriptive statistics for defect rates
      - 'hypothesis_test': Compare two groups with t-test
    params: dict with analysis-specific parameters
    """
    p = params or {}

    if analysis_type == "correlation":
        return run_correlation_analysis(data, p.get("x_col", ""), p.get("y_col", ""))

    elif analysis_type == "trend_change":
        rows = data.get("rows", [])
        dates = [r.get(p.get("date_col", "date"), "") for r in rows]
        values = [float(r.get(p.get("value_col", "avg_defect_rate"), 0)) for r in rows]
        return detect_trend_change(dates, values, p.get("change_date"))

    elif analysis_type == "anomaly":
        return detect_anomalies(data, p.get("column", "temperature_c"), p.get("threshold_std", 2.0))

    elif analysis_type == "descriptive":
        rows = data.get("rows", [])
        col = p.get("column", "defect_rate")
        values = [float(r.get(col, 0)) for r in rows if r.get(col) is not None]
        return compute_defect_statistics(values)

    elif analysis_type == "hypothesis_test":
        return run_hypothesis_test(
            p.get("group_a", []),
            p.get("group_b", []),
            p.get("hypothesis", "Groups are different")
        )

    return {"error": f"Unknown analysis_type: {analysis_type}"}


# ─── Knowledge Graph Tools ────────────────────────────────────────────────────

@mcp.tool()
def query_knowledge_graph(
    query_type: str,
    params: Optional[dict] = None
) -> dict:
    """
    Query the Neo4j knowledge graph for relationships.
    query_type options:
      - 'causal_chain': Get causal event chains
      - 'supplier_machine': Supplier → Material → Machine relationships
      - 'historical_patterns': Find matching historical incidents
      - 'machine_risk': Risk factors for a specific machine
    """
    p = params or {}

    if query_type == "causal_chain":
        return query_causal_chain(p.get("event_type"))
    elif query_type == "supplier_machine":
        return query_supplier_material_machine(p.get("supplier_id"))
    elif query_type == "historical_patterns":
        return query_historical_patterns(p.get("pattern_type", "defect_increase"))
    elif query_type == "machine_risk":
        return query_machine_risk(p.get("machine_id", "M17"))

    return {"error": f"Unknown query_type: {query_type}"}


if __name__ == "__main__":
    mcp.run(port=8001)
