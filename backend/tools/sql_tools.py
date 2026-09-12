"""
SQL tools — query structured manufacturing data from SQLite.
Returns typed results with the SQL query used (for evidence display).
"""
import sqlite3
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DATABASE_URL


def _conn():
    return sqlite3.connect(DATABASE_URL)


def _query(sql: str, params: tuple = ()) -> dict[str, Any]:
    """Execute SQL and return rows + metadata."""
    conn = _conn()
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]
        return {
            "rows": rows,
            "row_count": len(rows),
            "query": sql.strip(),
            "params": list(params)
        }
    finally:
        conn.close()


def get_defect_trend(machine_id: str = None, start_date: str = "2024-02-01", end_date: str = "2024-04-30") -> dict:
    """Get daily average defect rates over time, optionally filtered by machine."""
    if machine_id:
        sql = """
            SELECT date, machine_id, 
                   AVG(defect_rate) as avg_defect_rate,
                   SUM(defective_units) as total_defects,
                   SUM(units_produced) as total_units,
                   material_batch, supplier_id
            FROM production
            WHERE machine_id = ? AND date BETWEEN ? AND ?
            GROUP BY date, machine_id, material_batch, supplier_id
            ORDER BY date
        """
        return _query(sql, (machine_id, start_date, end_date))
    else:
        sql = """
            SELECT date, machine_id,
                   AVG(defect_rate) as avg_defect_rate,
                   SUM(defective_units) as total_defects,
                   SUM(units_produced) as total_units,
                   material_batch, supplier_id
            FROM production
            WHERE date BETWEEN ? AND ?
            GROUP BY date, machine_id, material_batch, supplier_id
            ORDER BY date, machine_id
        """
        return _query(sql, (start_date, end_date))


def get_machine_stats(machine_id: str = None) -> dict:
    """Get machine sensor statistics, optionally filtered by machine."""
    if machine_id:
        sql = """
            SELECT date, machine_id, temperature_c, vibration_mm_s,
                   pressure_bar, uptime_hours, oil_level_pct, error_codes
            FROM machine_data
            WHERE machine_id = ?
            ORDER BY date
        """
        return _query(sql, (machine_id,))
    else:
        sql = """
            SELECT date, machine_id, temperature_c, vibration_mm_s,
                   pressure_bar, uptime_hours, oil_level_pct, error_codes
            FROM machine_data ORDER BY date, machine_id
        """
        return _query(sql)


def get_maintenance_records(machine_id: str = None) -> dict:
    """Get maintenance history, optionally filtered by machine."""
    if machine_id:
        sql = "SELECT * FROM maintenance WHERE machine_id = ? ORDER BY date"
        return _query(sql, (machine_id,))
    else:
        sql = "SELECT * FROM maintenance ORDER BY date, machine_id"
        return _query(sql)


def get_supplier_data(supplier_id: str = None) -> dict:
    """Get supplier and material batch data."""
    if supplier_id:
        sql = "SELECT * FROM supplier WHERE supplier_id = ? ORDER BY delivery_date"
        return _query(sql, (supplier_id,))
    else:
        sql = "SELECT * FROM supplier ORDER BY delivery_date"
        return _query(sql)


def get_machines_by_defect_rate(threshold: float = 0.03) -> dict:
    """Find machines with average defect rate above threshold."""
    sql = """
        SELECT machine_id,
               AVG(defect_rate) as avg_defect_rate,
               MAX(defect_rate) as max_defect_rate,
               MIN(defect_rate) as min_defect_rate,
               COUNT(*) as batch_count
        FROM production
        WHERE date >= '2024-03-01'
        GROUP BY machine_id
        HAVING avg_defect_rate > ?
        ORDER BY avg_defect_rate DESC
    """
    return _query(sql, (threshold,))


def get_material_defect_correlation() -> dict:
    """Correlate material batches with defect rates."""
    sql = """
        SELECT p.material_batch, p.supplier_id,
               AVG(p.defect_rate) as avg_defect_rate,
               MAX(p.defect_rate) as max_defect_rate,
               COUNT(*) as batch_count,
               s.hardness_rating, s.tensile_strength_mpa,
               s.quality_score, s.deviation_flag
        FROM production p
        LEFT JOIN supplier s ON p.material_batch = s.material_batch
        GROUP BY p.material_batch, p.supplier_id
        ORDER BY avg_defect_rate DESC
    """
    return _query(sql)


def get_defect_by_date_machine() -> dict:
    """Cross-tabulation of defect rates by date and machine for heatmap."""
    sql = """
        SELECT date, machine_id, AVG(defect_rate) as avg_defect_rate
        FROM production
        GROUP BY date, machine_id
        ORDER BY date, machine_id
    """
    return _query(sql)


def get_supplier_change_timeline() -> dict:
    """Show when supplier changes occurred relative to defect changes."""
    sql = """
        SELECT p.date, p.machine_id, p.supplier_id, p.material_batch,
               AVG(p.defect_rate) as avg_defect_rate,
               s.deviation_flag, s.quality_score
        FROM production p
        LEFT JOIN supplier s ON p.material_batch = s.material_batch
        GROUP BY p.date, p.machine_id, p.supplier_id, p.material_batch
        ORDER BY p.date, p.machine_id
    """
    return _query(sql)
