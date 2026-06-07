from uuid import UUID


class VectorStore:
    async def search(self, collection: str, query: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError

    async def add(self, collection: str, documents: list[str],
                  metadatas: list[dict], ids: list[str],
                  embeddings: list[list[float]] | None = None) -> None:
        raise NotImplementedError

    async def delete(self, collection: str, ids: list[str]) -> None:
        raise NotImplementedError

    async def delete_collection(self, collection: str) -> None:
        raise NotImplementedError
