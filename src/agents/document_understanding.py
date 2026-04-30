from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from src.tools.document import ExtractionResult
import uuid

class DocumentUnderstandingAgent:
    def __init__(self, vector_store_url: str = ":memory:"):
        self.llm = ChatOpenAI(model="gpt-4o")
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize Qdrant client
        self.client = QdrantClient(vector_store_url)
        self.collection_name = "document_chunks"
        
        # Create collection if it doesn't exist
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embeddings=self.embeddings,
        )

    async def analyze_and_index(self, extraction: ExtractionResult, doc_id: str):
        # 1. Entity Extraction & Semantic Segmentation
        # For a production system, we'd use a specialized model. 
        # Here we use the LLM to identify key entities in the text for better indexing/metadata.
        
        prompt = f"""
        Extract key KYB entities (Company Names, UBOs, Registration Numbers, Addresses, Financial Figures) 
        from the following text:
        {extraction.text[:2000]} # Limit for demo
        
        Respond in JSON format: {{"entities": [{{"text": "...", "label": "..."}}]}}
        """
        response = await self.llm.ainvoke(prompt)
        # Parse and add to metadata if needed, but for now we'll just log or use for chunks
        
        # 2. Semantic Segmentation (Chunking)
        chunks = [c.strip() for c in extraction.text.split("\n\n") if c.strip()]
        
        indexed_chunks = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "doc_id": doc_id,
                "page": extraction.metadata.get("page", 1),
                "doc_type": extraction.metadata.get("engine", "unknown"),
                "chunk_index": i,
                "confidence": extraction.metadata.get("confidence", 1.0),
                "extracted_entities": response.content # simplified inclusion
            }
            
            indexed_chunks.append({
                "text": chunk,
                "metadata": metadata
            })
            
        # 3. Indexing into Qdrant
        if indexed_chunks:
            self.vector_store.add_texts(
                texts=[c["text"] for c in indexed_chunks],
                metadatas=[c["metadata"] for c in indexed_chunks]
            )
            
        return indexed_chunks

    async def query_facts(self, query: str) -> List[Dict[str, Any]]:
        # RAG loop to fetch facts
        results = self.vector_store.similarity_search(query, k=5)
        return [{"content": r.page_content, "metadata": r.metadata} for r in results]
