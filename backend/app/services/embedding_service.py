"""
TenderAI — Embedding Service
Generates vector embeddings from text using BGE-M3 (free, multilingual Hindi+English).
"""

from typing import List

import numpy as np

from app.utils.helpers import chunk_text
from app.utils.logger import logger

class EmbeddingService:
    """
    Text → Vector embeddings using BGE-M3 from HuggingFace.
    - Free, no API key needed
    - Multilingual: works with Hindi + English mixed text (critical for Indian tenders)
    - 1024-dim embeddings
    """

    MODEL_NAME = "BAAI/bge-m3"
    EMBEDDING_DIM = 1024
    MAX_SEQUENCE_LENGTH = 8192

    def __init__(self):
        self._model = None

    def _load_model(self):
        """Lazy-load the model on first use to avoid slow startup."""
        if self._model is None:
            logger.info(f"🔄 Loading embedding model: {self.MODEL_NAME}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"   ✅ Model loaded successfully")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        If text is too long, it will be truncated.
        """
        self._load_model()
        embedding = self._model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding.tolist()

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        Returns list of embedding vectors.
        """
        self._load_model()
        if not texts:
            return []

        logger.info(f"   Embedding {len(texts)} texts in batches of {batch_size}")
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return embeddings.tolist()

    def embed_document(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> List[dict]:
        """
        Chunk a document and embed each chunk.
        Returns list of {text, embedding, chunk_index} dicts.
        """
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return []

        logger.info(f"   Document split into {len(chunks)} chunks")
        embeddings = self.embed_texts(chunks)

        return [
            {
                "text": chunk,
                "embedding": emb,
                "chunk_index": i,
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Cosine similarity between two embedding vectors."""
        a = np.array(vec_a)
        b = np.array(vec_b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# Singleton
embedding_service = EmbeddingService()
