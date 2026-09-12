"""
Knowledge Graph tools — query Neo4j for relationships and causal chains.
Includes in-memory fallback representation when Neo4j database is offline.
"""
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

_driver = None
_driver_failed = False


def _get_driver():
    global _driver, _driver_failed
    if _driver_failed:
        return None
    if _driver is None:
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            driver.verify_connectivity()
            _driver = driver
            print(f"[KG] Connected to Neo4j at {NEO4J_URI}")
        except Exception as e:
            print(f"[KG] Neo4j unavailable ({e}). Using in-memory Knowledge Graph fallback.")
            _driver_failed = True
            return None
    return _driver


def query_causal_chain(event_type: str = None) -> dict[str, Any]:
    """Retrieve causal chain relationships from the knowledge graph."""
    driver = _get_driver()
    if driver is not None:
        try:
            with driver.session() as session:
                cypher = """
                    MATCH path = (a:Event)-[:CAUSED|LED_TO|TRIGGERED*1..3]->(b:Event)
                    RETURN 
                        a.type as from_event, a.date as from_date,
                        b.type as to_event, b.date as to_date,
                        [r IN relationships(path) | type(r)] as relationship_types,
                        length(path) as chain_length
                    ORDER BY a.date
                """
                results = session.run(cypher)
                chains = [dict(r) for r in results]

            return {
                "causal_chains": chains,
                "chain_count": len(chains),
                "query_type": "causal_chain"
            }
        except Exception as e:
            print(f"[KG] Cypher query error ({e}), falling back to in-memory KG.")

    # In-memory Causal Chain Fallback
    fallback_chains = [
        {
            "from_event": "Supplier Substitution (SUP-Y)",
            "from_date": "2024-03-01",
            "to_event": "Material Incompatibility (MAT-X17)",
            "to_date": "2024-03-05",
            "relationship_types": ["SUPPLIES_INCOMPATIBLE"],
            "chain_length": 1
        },
        {
            "from_event": "Material Incompatibility (MAT-X17)",
            "from_date": "2024-03-05",
            "to_event": "High Friction & Thermal Spike (84C)",
            "to_date": "2024-03-06",
            "relationship_types": ["CAUSES_FRICTION"],
            "chain_length": 1
        },
        {
            "from_event": "High Friction & Thermal Spike (84C)",
            "from_date": "2024-03-06",
            "to_event": "Defect Rate Spike (2% -> 7.4%)",
            "to_date": "2024-03-07",
            "relationship_types": ["TRIGGERS_DEFECTS"],
            "chain_length": 1
        }
    ]
    return {
        "causal_chains": fallback_chains,
        "chain_count": len(fallback_chains),
        "query_type": "causal_chain",
        "mode": "in_memory_fallback"
    }


def query_supplier_material_machine(supplier_id: str = None) -> dict[str, Any]:
    """Query the supplier → material → machine relationship chain."""
    driver = _get_driver()
    if driver is not None:
        try:
            with driver.session() as session:
                if supplier_id:
                    cypher = """
                        MATCH (s:Supplier {id: $supplier_id})-[r1:SUPPLIES]->(m:Material)
                        OPTIONAL MATCH (machine:Machine)-[r2:USES]->(m)
                        OPTIONAL MATCH (m)-[r3:INCOMPATIBLE_WITH]->(machine)
                        RETURN s.name as supplier, s.approved as approved,
                               m.id as material_batch, m.type as material_type,
                               m.hardness as hardness, m.in_spec as in_spec,
                               m.deviation as deviation,
                               machine.id as machine_id,
                               r3.reason as incompatibility_reason,
                               r3.risk as risk_level
                    """
                    results = session.run(cypher, supplier_id=supplier_id)
                else:
                    cypher = """
                        MATCH (s:Supplier)-[r1:SUPPLIES]->(m:Material)
                        OPTIONAL MATCH (machine:Machine)-[r2:USES]->(m)
                        OPTIONAL MATCH (m)-[r3:INCOMPATIBLE_WITH]->(machine)
                        RETURN s.id as supplier_id, s.name as supplier, s.approved as approved,
                               m.id as material_batch, m.type as material_type,
                               m.hardness as hardness, m.in_spec as in_spec,
                               m.deviation as deviation,
                               machine.id as machine_id,
                               r3.reason as incompatibility_reason
                    """
                    results = session.run(cypher)

                rows = [dict(r) for r in results]

            return {
                "relationships": rows,
                "relationship_count": len(rows),
                "query_type": "supplier_material_machine"
            }
        except Exception as e:
            print(f"[KG] Cypher query error ({e}), falling back to in-memory KG.")

    # In-memory Supplier → Material → Machine Fallback
    fallback_rows = [
        {
            "supplier_id": "SUP-Y",
            "supplier": "Titan Metals Ltd.",
            "approved": "WAIVER_ONLY",
            "material_batch": "MAT-X17",
            "material_type": "Aluminum Alloy 7075",
            "hardness": 98.0,
            "in_spec": False,
            "deviation": "Hardness 98 vs 82-86 spec for 6061",
            "machine_id": "M17",
            "incompatibility_reason": "Machine M17 tooling calibrated for 6061 alloy (hardness ~82). 7075 alloy (hardness 98) causes high friction, chatter, and dimensional defects.",
            "risk_level": "HIGH"
        },
        {
            "supplier_id": "SUP-X",
            "supplier": "Apex Materials Co.",
            "approved": "YES",
            "material_batch": "MAT-A01",
            "material_type": "Aluminum Alloy 6061",
            "hardness": 82.0,
            "in_spec": True,
            "deviation": "None",
            "machine_id": "M17",
            "incompatibility_reason": None,
            "risk_level": "LOW"
        }
    ]
    if supplier_id:
        fallback_rows = [r for r in fallback_rows if r["supplier_id"] == supplier_id]

    return {
        "relationships": fallback_rows,
        "relationship_count": len(fallback_rows),
        "query_type": "supplier_material_machine",
        "mode": "in_memory_fallback"
    }


def query_historical_patterns(pattern_type: str = "defect_increase") -> dict[str, Any]:
    """Find historical incidents that match current patterns."""
    driver = _get_driver()
    if driver is not None:
        try:
            with driver.session() as session:
                cypher = """
                    MATCH (e:Event)-[:MATCHES_PATTERN]->(h:HistoricalIncident)
                    RETURN e.type as current_event, e.date as event_date,
                           h.id as incident_id, h.date as incident_date,
                           h.pattern as pattern, h.outcome as outcome
                    ORDER BY h.date
                """
                results = session.run(cypher)
                patterns = [dict(r) for r in results]

            return {
                "historical_patterns": patterns,
                "pattern_count": len(patterns),
                "query_type": "historical_patterns"
            }
        except Exception as e:
            print(f"[KG] Cypher query error ({e}), falling back to in-memory KG.")

    # Fallback historical patterns
    fallback_patterns = [
        {
            "current_event": "Defect Spike on Machine M17",
            "event_date": "2024-03-07",
            "incident_id": "INC-2023-04",
            "incident_date": "2023-11-12",
            "pattern": "Unapproved hard alloy substitution under cost waiver",
            "outcome": "Machine tool head damage ($45k repair), 12% scrap rate until batch replaced with standard 6061 stock."
        }
    ]
    return {
        "historical_patterns": fallback_patterns,
        "pattern_count": len(fallback_patterns),
        "query_type": "historical_patterns",
        "mode": "in_memory_fallback"
    }


def query_machine_risk(machine_id: str) -> dict[str, Any]:
    """Get all risk factors associated with a machine."""
    driver = _get_driver()
    if driver is not None:
        try:
            with driver.session() as session:
                cypher = """
                    MATCH (m:Machine {id: $machine_id})
                    OPTIONAL MATCH (mat:Material)-[r:INCOMPATIBLE_WITH]->(m)
                    OPTIONAL MATCH (s:Supplier)-[:SUPPLIES]->(mat)
                    OPTIONAL MATCH (e:Event {machine: $machine_id})
                    RETURN m.id as machine_id, m.calibrated_for as calibrated_for,
                           m.temp_threshold as temp_threshold,
                           collect(DISTINCT mat.id) as incompatible_materials,
                           collect(DISTINCT r.reason) as risk_reasons,
                           collect(DISTINCT e.type) as events
                """
                results = session.run(cypher, machine_id=machine_id)
                row = results.single()

            return {
                "machine": dict(row) if row else {},
                "query_type": "machine_risk"
            }
        except Exception as e:
            print(f"[KG] Cypher query error ({e}), falling back to in-memory KG.")

    # Fallback machine risk
    return {
        "machine": {
            "machine_id": machine_id,
            "calibrated_for": "Aluminum Alloy 6061 (Hardness 80-86)",
            "temp_threshold": 75.0,
            "incompatible_materials": ["MAT-X17"],
            "risk_reasons": ["Hardness 98 causes high tool friction and thermal spikes (84C vs 75C max threshold)"],
            "events": ["Overheating warning", "Defect spike 2.1% -> 7.4%"]
        },
        "query_type": "machine_risk",
        "mode": "in_memory_fallback"
    }
