"""
Seed Neo4j Knowledge Graph with manufacturing relationships.
Creates the causal relationship graph for the demo scenario.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def seed_kg():
    from neo4j import GraphDatabase

    driver = None
    for attempt in range(15):
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            driver.verify_connectivity()
            print(f"  [OK] Connected to Neo4j at {NEO4J_URI}")
            break
        except Exception as e:
            print(f"  Waiting for Neo4j... attempt {attempt+1}/15 ({e})")
            time.sleep(4)

    if driver is None:
        print("ERROR: Could not connect to Neo4j. Knowledge Graph will be unavailable.")
        return

    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        print("  [OK] Cleared existing graph")

        # Create nodes and relationships
        cypher = """
        // Suppliers
        CREATE (supX:Supplier {id: 'SUP-X', name: 'Apex Materials Co.', approved: true, rating: 0.97})
        CREATE (supY:Supplier {id: 'SUP-Y', name: 'Titan Metals Ltd.', approved: false, rating: 0.71})

        // Materials
        CREATE (matA01:Material {id: 'MAT-A01', type: 'Aluminum Alloy 6061', hardness: 82, tensile_mpa: 276, in_spec: true})
        CREATE (matA02:Material {id: 'MAT-A02', type: 'Aluminum Alloy 6061', hardness: 83, tensile_mpa: 275, in_spec: true})
        CREATE (matX17:Material {id: 'MAT-X17', type: 'Aluminum Alloy 7075', hardness: 98, tensile_mpa: 503, in_spec: false, deviation: 'ALLOY-GRADE-MISMATCH'})
        CREATE (matA03:Material {id: 'MAT-A03', type: 'Aluminum Alloy 6061', hardness: 82, tensile_mpa: 276, in_spec: true})

        // Machines
        CREATE (m01:Machine {id: 'M01', model: 'ProCut-17', calibrated_for: 'Alloy 6061', temp_threshold: 80})
        CREATE (m02:Machine {id: 'M02', model: 'ProCut-17', calibrated_for: 'Alloy 6061', temp_threshold: 80})
        CREATE (m17:Machine {id: 'M17', model: 'ProCut-17', calibrated_for: 'Alloy 6061', temp_threshold: 80})

        // Events
        CREATE (supChange:Event {id: 'EVT-001', type: 'SupplierChange', date: '2024-03-05', description: 'Switch from SUP-X to SUP-Y for material procurement'})
        CREATE (tempIncrease:Event {id: 'EVT-002', type: 'TemperatureIncrease', date: '2024-03-08', machine: 'M17', peak_temp: 84.3})
        CREATE (defectSpike:Event {id: 'EVT-003', type: 'DefectRateIncrease', date: '2024-03-08', from_rate: 0.020, to_rate: 0.070, machine: 'M17'})
        CREATE (maintenance:Event {id: 'EVT-004', type: 'EmergencyMaintenance', date: '2024-03-17', machine: 'M17', finding: 'Spindle bearing damage from thermal expansion'})
        CREATE (resolution:Event {id: 'EVT-005', type: 'ProblemResolved', date: '2024-04-01', machine: 'M17', action: 'Switched back to SUP-X alloy 6061'})

        // Historical incident
        CREATE (hist:HistoricalIncident {id: 'INC-2023-008', date: '2023-08-14', line: 'Line 3', pattern: 'Alloy 7075 vs 6061 mismatch causing defects', outcome: 'Defect rate returned to 2.1% after correction'})

        // Supplier → Material relationships
        CREATE (supX)-[:SUPPLIES {batch: 'MAT-A01', date: '2024-01-10'}]->(matA01)
        CREATE (supX)-[:SUPPLIES {batch: 'MAT-A02', date: '2024-02-08'}]->(matA02)
        CREATE (supY)-[:SUPPLIES {batch: 'MAT-X17', date: '2024-03-05', quality_hold: true, waiver: 'WVR-2024-031'}]->(matX17)
        CREATE (supX)-[:SUPPLIES {batch: 'MAT-A03', date: '2024-03-20'}]->(matA03)

        // Machine → Material usage
        CREATE (m17)-[:USES {from_date: '2024-01-01', to_date: '2024-03-04'}]->(matA01)
        CREATE (m17)-[:USES {from_date: '2024-03-05', to_date: '2024-03-19', caused_issues: true}]->(matX17)
        CREATE (m17)-[:USES {from_date: '2024-04-01'}]->(matA03)
        CREATE (m01)-[:USES {from_date: '2024-03-05', to_date: '2024-03-19', partial: true}]->(matX17)
        CREATE (m02)-[:USES]->(matA01)

        // Material incompatibility
        CREATE (matX17)-[:INCOMPATIBLE_WITH {reason: 'Hardness 98 HRB exceeds machine calibration range 78-88 HRB', risk: 'HIGH'}]->(m17)
        CREATE (matX17)-[:INCOMPATIBLE_WITH {reason: 'Hardness 98 HRB exceeds machine calibration range 78-88 HRB', risk: 'MEDIUM'}]->(m01)

        // Causal chain
        CREATE (supChange)-[:CAUSED]->(tempIncrease)
        CREATE (tempIncrease)-[:CAUSED]->(defectSpike)
        CREATE (defectSpike)-[:TRIGGERED]->(maintenance)
        CREATE (maintenance)-[:LED_TO]->(resolution)
        CREATE (matX17)-[:CONTRIBUTED_TO]->(tempIncrease)
        CREATE (matX17)-[:CONTRIBUTED_TO]->(defectSpike)

        // Historical pattern
        CREATE (defectSpike)-[:MATCHES_PATTERN]->(hist)
        CREATE (supChange)-[:MATCHES_PATTERN]->(hist)

        RETURN 'Knowledge Graph seeded' AS status
        """
        result = session.run(cypher)
        print(f"  [OK] {result.single()['status']}")

        # Count nodes
        count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        print(f"  [OK] Total nodes: {count}")

    driver.close()


if __name__ == "__main__":
    print("Seeding Neo4j Knowledge Graph...")
    seed_kg()
    print("[OK] Knowledge Graph seeded successfully.")
