import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_openai import OpenAIEmbeddings
import uuid

class VectorMemory:
    def __init__(self, collection_name: str = "kyb_cases"):
        self.collection_name = collection_name
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        if os.getenv("OPENAI_API_KEY") == "ollama":
            from langchain_community.embeddings import OllamaEmbeddings
            self.embeddings = OllamaEmbeddings(
                model="phi3",
                base_url=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1").replace("/v1", "")
            )
        else:
            try:
                self.embeddings = OpenAIEmbeddings()
            except Exception:
                print("Warning: Could not initialize OpenAIEmbeddings. Vector memory will be restricted.")
                self.embeddings = None
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            if not self.embeddings:
                self.client = None
                return

            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            # Determine correct size
            if hasattr(self.embeddings, "model") and "3-large" in self.embeddings.model:
                size = 3072
            else:
                size = 1536

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=size,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                # Check for dimension mismatch by trying to get collection info
                info = self.client.get_collection(self.collection_name)
                current_size = info.config.params.vectors.size
                if current_size != size:
                    print(f"Warning: Dimension mismatch in Qdrant ({current_size} != {size}). Recreating collection.")
                    self.client.delete_collection(self.collection_name)
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(
                            size=size,
                            distance=models.Distance.COSINE
                        )
                    )
        except Exception as e:
            print(f"Warning: Could not connect to or configure Qdrant: {e}. Vector memory will be disabled.")
            self.client = None

    def add_case(self, profile_data: Dict[str, Any], metadata: Dict[str, Any]):
        """Adds a KYB case to the vector memory for future few-shot learning."""
        if not self.client:
            return

        text_to_embed = f"Company: {profile_data.get('company_name')}\n" \
                        f"Status: {profile_data.get('status')}\n" \
                        f"Ownership Pattern: {str(profile_data.get('ownership'))}"
        
        vector = self.embeddings.embed_query(text_to_embed)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "profile": profile_data,
                        "metadata": metadata
                    }
                )
            ]
        )

    def search_similar_cases(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Searches for similar past cases to provide context/few-shot examples."""
        if not self.client:
            return []

        vector = self.embeddings.embed_query(query_text)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit
        )
        
        return [res.payload for res in results]
