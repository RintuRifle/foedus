"""
Foedus — Vector Store Service (Qdrant)
Manages tender document embeddings for semantic search (RAG engine).
"""

import uuid
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.utils.logger import logger

class VectorStoreService:
    """
    Qdrant vector database operations.
    Used for:
    1. Storing tender document chunks with embeddings
    2. Semantic search for RAG (find relevant tender clauses)
    3. Company-tender similarity matching
    """

    EMBEDDING_DIM = 1024  # BGE-M3 dimension

    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION

    def ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            logger.info(f"📦 Creating Qdrant collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            # Create payload indexes for filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="tender_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            logger.info("   ✅ Collection created with indexes")
        else:
            logger.debug(f"   Collection '{self.collection_name}' already exists")

    def upsert_chunks(
        self,
        tender_id: str,
        chunks: List[Dict],
        source: str = "unknown",
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Store document chunks with embeddings in Qdrant.
        Each chunk has: text, embedding, chunk_index.
        Returns number of points upserted.
        """
        self.ensure_collection()

        if not chunks:
            return 0

        points = []
        for chunk in chunks:
            point_id = str(uuid.uuid4())
            payload = {
                "tender_id": tender_id,
                "text": chunk["text"],
                "chunk_index": chunk["chunk_index"],
                "source": source,
            }
            if metadata:
                payload.update(metadata)

            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=chunk["embedding"],
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.info(f"   📥 Upserted {len(points)} chunks for tender {tender_id}")
        return len(points)

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        tender_id: Optional[str] = None,
        score_threshold: float = 0.5,
    ) -> List[Dict]:
        """
        Semantic search: find the most relevant tender chunks.
        Optionally filter by tender_id for within-document search.
        """
        self.ensure_collection()

        query_filter = None
        if tender_id:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="tender_id",
                        match=qmodels.MatchValue(value=tender_id),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )

        return [
            {
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "tender_id": hit.payload.get("tender_id"),
                "chunk_index": hit.payload.get("chunk_index"),
                "source": hit.payload.get("source"),
            }
            for hit in results
        ]

    def delete_tender(self, tender_id: str) -> None:
        """Delete all chunks for a specific tender."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="tender_id",
                            match=qmodels.MatchValue(value=tender_id),
                        )
                    ]
                )
            ),
        )
        logger.info(f"   🗑️ Deleted chunks for tender {tender_id}")

    def get_collection_info(self) -> Dict:
        """Get collection stats (point count, etc.)."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value,
            }
        except Exception:
            return {"name": self.collection_name, "status": "not_found"}

# Singleton
vectorstore_service = VectorStoreService()
