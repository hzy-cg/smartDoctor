import logging
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import get_settings
from app.infrastructure.vectorstore.base import VectorStore

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStore):
    _default_embedding = None
    _default_embedding_failed = False

    def __init__(self):
        settings = get_settings()
        persist_dir = settings.chroma_persist_dir or "./data/chroma"
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._load_embedding(settings)

    def _load_embedding(self, settings):
        if ChromaVectorStore._default_embedding is not None:
            return
        if ChromaVectorStore._default_embedding_failed:
            return

        model_name = settings.chroma_embedding_model
        if model_name in ("", "none", "chroma-default"):
            logger.info("Using ChromaDB default embedding (ONNX all-MiniLM-L6-v2)")
            ChromaVectorStore._default_embedding_failed = True
            return

        try:
            import socket
            socket.setdefaulttimeout(10)
            ChromaVectorStore._default_embedding = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name
                )
            )
            logger.info("ChromaDB embedding function loaded: %s", model_name)
        except Exception as e:
            ChromaVectorStore._default_embedding_failed = True
            logger.warning(
                "Failed to load embedding model '%s': %s. ChromaDB will use built-in ONNX default. "
                "To use a local model, set chroma_embedding_model to a local path or 'chroma-default'.",
                model_name, e,
            )

    async def search(self, collection: str, query: str, top_k: int = 5) -> list[dict]:
        try:
            col = self._client.get_collection(collection)
            if ChromaVectorStore._default_embedding:
                results = col.query(
                    query_texts=[query],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"],
                )
            else:
                results = col.query(query_texts=[query], n_results=top_k)
            items = []
            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    items.append({"content": doc, "source": meta.get("source", ""),
                                  "score": results["distances"][0][i] if results.get("distances") else 0.0})
            return items
        except Exception:
            return []

    async def add(self, collection: str, documents: list[str],
                  metadatas: list[dict], ids: list[str],
                  embeddings: list[list[float]] | None = None) -> None:
        try:
            col = self._client.get_collection(collection)
        except Exception:
            if ChromaVectorStore._default_embedding:
                col = self._client.create_collection(
                    collection,
                    embedding_function=ChromaVectorStore._default_embedding,
                )
            else:
                col = self._client.create_collection(collection)
        if embeddings:
            col.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
        else:
            col.add(documents=documents, metadatas=metadatas, ids=ids)

    async def delete(self, collection: str, ids: list[str]) -> None:
        try:
            col = self._client.get_collection(collection)
            col.delete(ids=ids)
        except Exception:
            pass

    async def delete_collection(self, collection: str) -> None:
        try:
            self._client.delete_collection(collection)
        except Exception:
            pass
