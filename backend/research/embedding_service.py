"""Optional embedding service with a portable, SQLite-compatible fallback.

Uses a small pretrained sentence-transformer when ``sentence-transformers`` is
installed and the model can load. If it is unavailable, ``available()`` returns
False and callers fall back to the existing lexical retrieval — embeddings are
never fabricated. Vectors are stored as float32 blobs (portable across SQLite and
PostgreSQL); a pgvector column is created only on PostgreSQL by the migration.
"""

from __future__ import annotations

import math
import struct
import threading
from typing import List, Optional

from backend.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None
        self._loaded = False
        self._lock = threading.Lock()
        self.model_name = settings.embedding_model
        self.dim = settings.embedding_dim

    def available(self) -> bool:
        return self._ensure_loaded() is not None

    def _ensure_loaded(self):
        if self._loaded:
            return self._model
        with self._lock:
            if self._loaded:
                return self._model
            self._loaded = True
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._model = SentenceTransformer(self.model_name)
                # Trust the model's real dimension when available.
                dim = getattr(self._model, "get_sentence_embedding_dimension", lambda: None)()
                if isinstance(dim, int) and dim > 0:
                    self.dim = dim
            except Exception:
                self._model = None
            return self._model

    def embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        model = self._ensure_loaded()
        if model is None or not texts:
            return None
        try:
            vectors = model.encode(
                texts,
                batch_size=settings.embedding_batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return [list(map(float, row)) for row in vectors]
        except Exception:
            return None

    def embed_query(self, text: str) -> Optional[List[float]]:
        out = self.embed_texts([text])
        return out[0] if out else None

    def index_chunks(self, db) -> dict:
        """Embed stored chunks that are missing or stale. No-op without a model.

        Idempotent: a chunk is (re)embedded only when its content hash changed.
        Returns honest counts; never claims embeddings that were not produced.
        """
        if not self.available():
            return {"indexed": 0, "skipped": 0, "reason": "embeddings_unavailable"}

        import hashlib

        from backend.models.dataset import ChunkEmbedding
        from backend.models.pdf import PdfChunk

        chunks = db.query(PdfChunk).all()
        existing = {
            e.chunk_id: e
            for e in db.query(ChunkEmbedding)
            .filter(ChunkEmbedding.embedding_model == self.model_name)
            .all()
        }
        pending = []
        for c in chunks:
            chash = hashlib.sha256((c.content or "").encode("utf-8")).hexdigest()
            cur = existing.get(c.id)
            if cur and cur.content_hash == chash:
                continue
            pending.append((c, chash))

        indexed = 0
        batch = max(1, settings.embedding_batch_size)
        for i in range(0, len(pending), batch):
            group = pending[i : i + batch]
            vectors = self.embed_texts([c.content or "" for c, _ in group])
            if vectors is None:
                break
            for (c, chash), vec in zip(group, vectors):
                blob = self.pack(vec)
                row = existing.get(c.id)
                if row is None:
                    row = ChunkEmbedding(
                        chunk_id=c.id,
                        embedding_model=self.model_name,
                        embedding_dim=len(vec),
                        content_hash=chash,
                        vector=blob,
                    )
                    db.add(row)
                else:
                    row.embedding_dim = len(vec)
                    row.content_hash = chash
                    row.vector = blob
                indexed += 1
        db.commit()
        return {"indexed": indexed, "skipped": len(chunks) - indexed, "total_chunks": len(chunks)}

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return float(dot / (na * nb))

    @staticmethod
    def pack(vector: List[float]) -> bytes:
        return struct.pack(f"<{len(vector)}f", *vector)

    @staticmethod
    def unpack(blob: bytes) -> List[float]:
        n = len(blob) // 4
        return list(struct.unpack(f"<{n}f", blob[: n * 4]))


embedding_service = EmbeddingService()