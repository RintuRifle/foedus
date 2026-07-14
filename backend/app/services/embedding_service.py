"""
Foedus — Embedding Service
Two providers, switched by EMBEDDING_PROVIDER in .env:

  gemini (default) — Gemini Embedding API. Zero local RAM, free tier,
                     multilingual (Hindi + English). This is what lets the
                     whole backend fit in a 512MB free-tier container.
  local            — BGE-M3 via sentence-transformers (needs ~1GB+ RAM and
                     the optional heavy deps from requirements.txt).

Interface is identical either way: embed_text / embed_texts / embed_document.
"""

import math
from typing import List

from app.config import settings
from app.utils.helpers import chunk_text
from app.utils.logger import logger


class EmbeddingService:
    """Text → vector embeddings, provider-agnostic."""

    GEMINI_MODEL = "gemini-embedding-001"
    GEMINI_BATCH_SIZE = 100  # API max batch
    LOCAL_MODEL = "BAAI/bge-m3"

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        self.dim = settings.EMBEDDING_DIM
        self._local_model = None
        self._gemini_client = None

    # ── Providers ─────────────────────────────────────────────

    def _gemini(self):
        """Lazy Gemini client (shares API key with the LLM service)."""
        if self._gemini_client is None:
            from google import genai
            self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._gemini_client

    def _local(self):
        """Lazy-load BGE-M3 (heavy: only for EMBEDDING_PROVIDER=local)."""
        if self._local_model is None:
            logger.info(f"🔄 Loading local embedding model: {self.LOCAL_MODEL}")
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.LOCAL_MODEL)
            logger.info("   ✅ Model loaded")
        return self._local_model

    def _embed_gemini(self, texts: List[str]) -> List[List[float]]:
        from google.genai import types
        client = self._gemini()
        out: List[List[float]] = []
        for i in range(0, len(texts), self.GEMINI_BATCH_SIZE):
            batch = texts[i : i + self.GEMINI_BATCH_SIZE]
            resp = client.models.embed_content(
                model=self.GEMINI_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.dim,
                    task_type="RETRIEVAL_DOCUMENT",
                ),
            )
            for e in resp.embeddings:
                out.append(self._normalize(list(e.values)))
        return out

    def _embed_local(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        model = self._local()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        """L2-normalize (Gemini embeddings below 3072 dims aren't pre-normalized)."""
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    # ── Public interface (unchanged) ──────────────────────────

    def embed_text(self, text: str) -> List[float]:
        """Embedding for a single string."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embeddings for multiple strings."""
        if not texts:
            return []
        if self.provider == "local":
            return self._embed_local(texts, batch_size)
        return self._embed_gemini(texts)

    def embed_document(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> List[dict]:
        """Chunk a document and embed each chunk."""
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return []
        logger.info(f"   Document split into {len(chunks)} chunks [{self.provider}]")
        embeddings = self.embed_texts(chunks)
        return [
            {"text": chunk, "embedding": emb, "chunk_index": i}
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Cosine similarity between two vectors (pure python, no numpy)."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        na = math.sqrt(sum(a * a for a in vec_a)) or 1.0
        nb = math.sqrt(sum(b * b for b in vec_b)) or 1.0
        return dot / (na * nb)


# Singleton
embedding_service = EmbeddingService()
