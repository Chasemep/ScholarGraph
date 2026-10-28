"""ChromaDB persistent vector store and 384-d dense embedding wrapper."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import settings
from backend.models.paper import BoundingBox, TextChunk

COLLECTION_NAME = "scholar_chunks"
BI_ENCODER_MODEL_NAME = "all-MiniLM-L6-v2"

_shared_bi_encoder: Any = None


def get_bi_encoder():
    """Lazy-load and cache the singleton SentenceTransformer Bi-Encoder model."""
    global _shared_bi_encoder
    if _shared_bi_encoder is None:
        from sentence_transformers import SentenceTransformer

        _shared_bi_encoder = SentenceTransformer(BI_ENCODER_MODEL_NAME)
    return _shared_bi_encoder


def default_embedding_fn(texts: List[str]) -> List[List[float]]:
    """Compute 384-d normalized dense vectors using all-MiniLM-L6-v2."""
    model = get_bi_encoder()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


class VectorStoreManager:
    """Manages ChromaDB persistent collection (`scholar_chunks`) and dense vector search."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: str = COLLECTION_NAME,
        embedding_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
    ) -> None:
        self.persist_dir = Path(persist_dir) if persist_dir else Path(settings.chroma_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._embedding_fn = embedding_fn or default_embedding_fn

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of strings into 384-dimensional dense vectors."""
        if not texts:
            return []
        vecs = self._embedding_fn(texts)
        for v in vecs:
            if len(v) != 384:
                raise ValueError(f"Expected 384-dimensional vector, got {len(v)}")
        return vecs

    def index_chunks(self, chunks: List[TextChunk]) -> int:
        """Embed and upsert a batch of TextChunk objects with spatial bounding-box metadata."""
        if not chunks:
            return 0

        ids = [c.id for c in chunks]
        documents = [c.text for c in chunks]
        embeddings = self.embed_texts(documents)
        metadatas = [
            {
                "paper_id": c.paper_id,
                "paper_title": c.paper_title or "",
                "chunk_id": c.id,
                "section": c.section,
                "page": int(c.page_number),
                "bbox_x": float(c.bbox.x),
                "bbox_y": float(c.bbox.y),
                "bbox_w": float(c.bbox.width),
                "bbox_h": float(c.bbox.height),
                "token_count": int(c.token_count),
            }
            for c in chunks
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 20,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query the vector collection for top-K semantically similar chunks."""
        if not query or not query.strip():
            return []

        total_count = self.collection.count()
        if total_count == 0:
            return []

        where_filter: Optional[Dict[str, Any]] = None
        if paper_ids:
            if len(paper_ids) == 1:
                where_filter = {"paper_id": paper_ids[0]}
            else:
                where_filter = {"paper_id": {"$in": paper_ids}}

        query_embedding = self.embed_texts([query])[0]
        n_results = min(top_k, total_count)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        dists_list = results.get("distances", [[]])[0]

        hits: List[Dict[str, Any]] = []
        for chunk_id, doc_text, meta, dist in zip(ids_list, docs_list, metas_list, dists_list):
            # Cosine similarity from cosine distance in [0, 2]
            similarity = max(0.0, 1.0 - float(dist))
            chunk = TextChunk(
                id=chunk_id,
                paper_id=str(meta.get("paper_id", "")),
                paper_title=str(meta.get("paper_title", "")) or None,
                section=str(meta.get("section", "Body")),
                page_number=int(meta.get("page", 1)),
                bbox=BoundingBox(
                    page=int(meta.get("page", 1)),
                    x=float(meta.get("bbox_x", 0.0)),
                    y=float(meta.get("bbox_y", 0.0)),
                    width=float(meta.get("bbox_w", 1.0)),
                    height=float(meta.get("bbox_h", 0.1)),
                ),
                text=doc_text,
                token_count=int(meta.get("token_count", max(1, len(doc_text.split())))),
            )
            hits.append(
                {
                    "chunk": chunk,
                    "score": similarity,
                    "rank": len(hits) + 1,
                }
            )
        return hits

    def delete_paper_chunks(self, paper_id: str) -> None:
        """Remove all vectors associated with a paper_id."""
        self.collection.delete(where={"paper_id": paper_id})

    def count(self) -> int:
        """Return total number of indexed chunks in the collection."""
        return self.collection.count()

    def check_health(self) -> bool:
        """Verify ChromaDB client and collection readiness."""
        try:
            _ = self.collection.count()
            return True
        except Exception:
            return False


vector_store = VectorStoreManager()

