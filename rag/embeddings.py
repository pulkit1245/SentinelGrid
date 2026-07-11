import os
from typing import List, Dict, Any
import uuid

# We will use sentence-transformers for local dense embeddings (MVP safe)
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class VectorDatabaseBuilder:
    """
    Handles automated document indexing into Qdrant.
    """
    def __init__(self, qdrant_url: str = "http://localhost:6333", collection_name: str = "sentinelgrid_knowledge"):
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        self.model = SentenceTransformer('all-MiniLM-L6-v2') # Fast, small model for hackathon
        
        self._init_collection()

    def _init_collection(self):
        # Create collection if it doesn't exist
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            print(f"Created Qdrant collection: {self.collection_name}")

    def embed_and_index(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return
            
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.model.encode(texts)
        
        points = []
        for i, chunk in enumerate(chunks):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["id"]))
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[i].tolist(),
                    payload={
                        "text": chunk["text"],
                        **chunk["metadata"]
                    }
                )
            )
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Indexed {len(points)} vectors into Qdrant.")

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.model.encode(query).tolist()
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        results = []
        for hit in hits:
            results.append({
                "score": hit.score,
                "payload": hit.payload
            })
        return results
