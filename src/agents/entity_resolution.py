from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer
import numpy as np
from src.tools.graph_engine import GraphEngine
from src.schema import OwnershipEntity
import logging

logger = logging.getLogger(__name__)

class EntityResolutionAgent:
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.graph_engine = GraphEngine()
        self.model = SentenceTransformer(embedding_model_name)
        self.threshold = 0.85

    async def resolve_entities(self, entities: List[OwnershipEntity], source_metadata: Dict[str, Any], parent_id: str) -> List[Dict[str, Any]]:
        """
        Processes a list of entities found in a source and links them to the knowledge graph.
        """
        results = []
        for entity in entities:
            # 1. Search for potential matches in Graph
            potential_matches = self.graph_engine.search_similar_entities(entity.name)
            
            best_match = None
            max_score = 0.0
            
            for match in potential_matches:
                match_node = match['n']
                match_name = match_node.get('name', '')
                
                # 2. Fuzzy Matching
                fuzzy_score = fuzz.token_sort_ratio(entity.name.lower(), match_name.lower()) / 100.0
                
                # 3. Embedding Similarity
                embeddings = self.model.encode([entity.name, match_name])
                emb_score = np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]))
                
                # Weighted Score
                combined_score = (fuzzy_score * 0.4) + (emb_score * 0.6)
                
                if combined_score > max_score:
                    max_score = combined_score
                    best_match = match_node

            if best_match and max_score > self.threshold:
                logger.info(f"Linked {entity.name} to existing node {best_match['id']} (confidence: {max_score})")
                # Update existing node with new provenance
                self.graph_engine.upsert_entity(
                    label=entity.type,
                    entity_id=best_match['id'],
                    properties={
                        **entity.model_dump(),
                        "last_source": source_metadata.get("url"),
                        "confidence": max_score
                    }
                )
                results.append({"entity": entity.name, "status": "linked", "match_id": best_match['id'], "confidence": max_score})
                target_id = best_match['id']
            else:
                # 4. Create New Node if no match
                new_id = f"{entity.type}_{entity.name.replace(' ', '_').lower()}"
                self.graph_engine.upsert_entity(
                    label=entity.type,
                    entity_id=new_id,
                    properties={
                        **entity.model_dump(),
                        "source": source_metadata.get("url"),
                        "timestamp": source_metadata.get("timestamp"),
                        "confidence": 1.0 # Initial creation
                    }
                )
                results.append({"entity": entity.name, "status": "created", "id": new_id})
                target_id = new_id

            # 5. Add Ownership Relationship
            self.graph_engine.add_relationship(
                start_id=target_id,
                end_id=parent_id,
                rel_type="OWNS",
                properties={
                    "percentage": entity.percentage,
                    "is_ubo": entity.is_ubo,
                    "source": source_metadata.get("url"),
                    "confidence": max_score if best_match else 1.0
                }
            )

            # 6. Check for missing data / recursive tasks
            if entity.type == "Corporate" and entity.percentage > 25.0:
                # Flag for recursive investigation
                results[-1]["subtask"] = f"investigate linked entity {entity.name} in jurisdiction Unknown"

        return results

    def close(self):
        self.graph_engine.close()
