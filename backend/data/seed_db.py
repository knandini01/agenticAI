"""
Seed SQLite databases with synthetic manufacturing data.
Run once on startup.
"""
import sqlite3
import csv
import os
import sys

# Ensure we can import config from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DATABASE_URL, EXPERIENCE_DB_URL, DATA_DIR


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_URL) if os.path.dirname(DATABASE_URL) else ".", exist_ok=True)
    return sqlite3.connect(DATABASE_URL)


def seed_production(conn):
    conn.execute("DROP TABLE IF EXISTS production")
    conn.execute("""
        CREATE TABLE production (
            date TEXT,
            batch_id TEXT PRIMARY KEY,
            machine_id TEXT,
            shift TEXT,
            operator_id TEXT,
            units_produced INTEGER,
            defective_units INTEGER,
            defect_rate REAL,
            material_batch TEXT,
            supplier_id TEXT
        )
    """)
    with open(os.path.join(DATA_DIR, "production.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT INTO production VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                row["date"], row["batch_id"], row["machine_id"], row["shift"],
                row["operator_id"], int(row["units_produced"]),
                int(row["defective_units"]), float(row["defect_rate"]),
                row["material_batch"], row["supplier_id"]
            ))
    print(f"  [OK] Production: {conn.execute('SELECT COUNT(*) FROM production').fetchone()[0]} rows")


def seed_machine_data(conn):
    conn.execute("DROP TABLE IF EXISTS machine_data")
    conn.execute("""
        CREATE TABLE machine_data (
            date TEXT,
            machine_id TEXT,
            temperature_c REAL,
            vibration_mm_s REAL,
            pressure_bar REAL,
            uptime_hours REAL,
            oil_level_pct REAL,
            error_codes TEXT,
            PRIMARY KEY (date, machine_id)
        )
    """)
    with open(os.path.join(DATA_DIR, "machine_data.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT INTO machine_data VALUES (?,?,?,?,?,?,?,?)
            """, (
                row["date"], row["machine_id"],
                float(row["temperature_c"]), float(row["vibration_mm_s"]),
                float(row["pressure_bar"]), float(row["uptime_hours"]),
                float(row["oil_level_pct"]), row.get("error_codes", "")
            ))
    print(f"  [OK] Machine data: {conn.execute('SELECT COUNT(*) FROM machine_data').fetchone()[0]} rows")


def seed_maintenance(conn):
    conn.execute("DROP TABLE IF EXISTS maintenance")
    conn.execute("""
        CREATE TABLE maintenance (
            date TEXT,
            machine_id TEXT,
            maintenance_type TEXT,
            technician TEXT,
            duration_hours REAL,
            parts_replaced TEXT,
            notes TEXT,
            next_scheduled TEXT
        )
    """)
    with open(os.path.join(DATA_DIR, "maintenance.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT INTO maintenance VALUES (?,?,?,?,?,?,?,?)
            """, (
                row["date"], row["machine_id"], row["maintenance_type"],
                row["technician"], float(row["duration_hours"]),
                row["parts_replaced"], row["notes"], row["next_scheduled"]
            ))
    print(f"  [OK] Maintenance: {conn.execute('SELECT COUNT(*) FROM maintenance').fetchone()[0]} rows")


def seed_supplier(conn):
    conn.execute("DROP TABLE IF EXISTS supplier")
    conn.execute("""
        CREATE TABLE supplier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_date TEXT,
            supplier_id TEXT,
            supplier_name TEXT,
            material_batch TEXT,
            material_type TEXT,
            quantity_kg INTEGER,
            hardness_rating REAL,
            tensile_strength_mpa REAL,
            quality_score REAL,
            deviation_flag TEXT,
            inspector TEXT,
            notes TEXT
        )
    """)
    with open(os.path.join(DATA_DIR, "supplier.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT INTO supplier (delivery_date, supplier_id, supplier_name, material_batch, material_type, quantity_kg, hardness_rating, tensile_strength_mpa, quality_score, deviation_flag, inspector, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row["delivery_date"], row["supplier_id"], row["supplier_name"],
                row["material_batch"], row["material_type"], int(row["quantity_kg"]),
                float(row["hardness_rating"]), float(row["tensile_strength_mpa"]),
                float(row["quality_score"]), row["deviation_flag"],
                row["inspector"], row["notes"]
            ))
    print(f"  [OK] Supplier: {conn.execute('SELECT COUNT(*) FROM supplier').fetchone()[0]} rows")


def seed_experience_db():
    """Create the experience database with a seeded past case."""
    import json
    from datetime import datetime

    exp_conn = sqlite3.connect(EXPERIENCE_DB_URL)
    exp_conn.execute("DROP TABLE IF EXISTS experience")
    exp_conn.execute("""
        CREATE TABLE experience (
            case_id TEXT PRIMARY KEY,
            problem_description TEXT,
            problem_type TEXT,
            strategy TEXT,
            agents_used TEXT,
            tools_used TEXT,
            confidence REAL,
            risk REAL,
            recommendation TEXT,
            verification_result TEXT,
            human_required INTEGER,
            human_decision TEXT,
            outcome TEXT,
            success INTEGER,
            created_at TEXT,
            resolved_at TEXT
        )
    """)

    # Seed one past successful case for experience learning demo
    exp_conn.execute("""
        INSERT INTO experience VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        "CASE-016",
        "Defect rate on Assembly Line 3 increased from 1.9% to 6.8% in August 2023",
        "root_cause_analysis",
        "supplier_machine_investigation",
        json.dumps(["data_agent", "research_agent", "analysis_agent"]),
        json.dumps(["get_machine_data", "get_supplier_history", "run_statistical_analysis"]),
        0.88,
        0.19,
        "Replace alloy 7075 batch with correct alloy 6061 from approved supplier. Perform machine M-L3-01 bearing inspection and recalibration.",
        "PASS",
        0,
        None,
        "Defect rate reduced from 6.8% to 2.1% within 2 weeks of corrective action.",
        1,
        "2023-08-08T09:15:00",
        "2023-09-01T14:30:00"
    ))
    exp_conn.commit()
    exp_conn.close()
    print(f"  [OK] Experience DB: seeded with 1 historical case (CASE-016)")


if __name__ == "__main__":
    print("Seeding enterprise database...")
    conn = get_connection()
    try:
        seed_production(conn)
        seed_machine_data(conn)
        seed_maintenance(conn)
        seed_supplier(conn)
        conn.commit()
    finally:
        conn.close()

    print("Seeding experience database...")
    seed_experience_db()
    print("[OK] All databases seeded successfully.")
