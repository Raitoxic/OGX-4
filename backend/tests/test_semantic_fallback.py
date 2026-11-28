from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_semantic_test_")
_test_db_path = Path(_tmp_dir) / "test_semantic.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from backend.database.init_db import init_db  # noqa: E402

init_db()

from backend.research import providers  # noqa: E402
from backend.research.embedding_service import embedding_service  # noqa: E402


def _force_unavailable() -> None:
    embedding_service._loaded = True
    embedding_service._model = None


def test_embedding_pack_unpack_roundtrip() -> None:
    vec = [0.1, -0.2, 0.3, 0.0]
    blob = embedding_service.pack(vec)
    out = embedding_service.unpack(blob)
    assert len(out) == len(vec)
    for a, b in zip(vec, out):
        assert abs(a - b) < 1e-6


def test_cosine_basic() -> None:
    assert abs(embedding_service.cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6
    assert abs(embedding_service.cosine([1.0, 0.0], [0.0, 1.0])) < 1e-6
    assert embedding_service.cosine([], [1.0]) == 0.0


def test_semantic_provider_falls_back_when_unavailable() -> None:
    _force_unavailable()
    assert embedding_service.available() is False
    records = asyncio.run(providers.search_semantic("cloud security", 5))
    assert records == []


def test_semantic_registered_but_inert_without_model() -> None:
    _force_unavailable()
    assert "semantic" in providers.PROVIDERS
    records = asyncio.run(providers.run_providers("cloud", ["semantic"], 5))
    assert records == []


def test_lexical_provider_still_works() -> None:
    # Lexical retrieval must not depend on embeddings being available.
    _force_unavailable()
    records = asyncio.run(providers.search_local_pdf("cloud computing security", 5))
    # No corpus seeded in this DB; must simply not raise and return a list.
    assert isinstance(records, list)