from typing import Dict, Any, Optional, List
from src.tools.graph_engine import GraphEngine
from src.schema import KYBProfile, RegistryData, OwnershipStructure
import datetime
import json

class GraphMemory:
    def __init__(self):
        self.engine = GraphEngine()

    def get_historical_profile(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest facts for an entity from the knowledge graph."""
        # This simulates fetching a consolidated view from Neo4j
        # In practice, it would traverse nodes and relationships to build the profile
        if not self.engine._driver:
            return None
            
        with self.engine._driver.session() as session:
            query = (
                "MATCH (c:Company {id: $id}) "
                "RETURN c"
            )
            result = session.run(query, id=company_id).single()
            if result:
                node = result["c"]
                # Convert back to a dict that looks like a KYBProfile
                return {
                    "registry": node.get("registry_snapshot"),
                    "ownership": node.get("ownership_snapshot"),
                    "last_updated": node.get("last_updated")
                }
        return None

    def detect_deltas(self, historical: Dict[str, Any], current: RegistryData) -> List[str]:
        """Detects changes between historical data and current registry data."""
        deltas = []
        hist_reg = historical.get("registry")
        if not hist_reg:
            return ["full_investigation_required"]

        # Simple field comparison
        if isinstance(hist_reg, str):
            hist_reg = json.loads(hist_reg)

        if hist_reg.get("status") != current.status:
            deltas.append(f"status_changed: {hist_reg.get('status')} -> {current.status}")
        
        # In a real system, we'd use embedding drift here too
        return deltas

    def update_knowledge_base(self, company_id: str, profile: KYBProfile):
        """Updates the graph with new facts after an investigation."""
        properties = {
            "name": profile.registry.company_name if profile.registry else company_id,
            "registry_snapshot": profile.registry.model_dump_json() if profile.registry else None,
            "ownership_snapshot": profile.ownership.model_dump_json() if profile.ownership else None,
            "risk_score": profile.risk_assessment.score if profile.risk_assessment else None,
            "last_investigated": datetime.datetime.utcnow().isoformat()
        }
        self.engine.upsert_entity("Company", company_id, properties)
        
        # If ownership is resolved, add individual nodes and relationships
        if profile.ownership and profile.ownership.resolved:
            for entity in profile.ownership.entities:
                label = "Person" if entity.type == "Individual" else "Company"
                self.engine.upsert_entity(label, entity.name, {"name": entity.name, "type": entity.type})
                self.engine.add_relationship(
                    entity.name, 
                    company_id, 
                    "OWNS", 
                    {"percentage": entity.percentage, "is_ubo": entity.is_ubo}
                )
