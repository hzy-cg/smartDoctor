import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.vectorstore.base import VectorStore


class TestVectorStoreBase:
    @pytest.mark.asyncio
    async def test_search_not_implemented(self):
        store = VectorStore()
        with pytest.raises(NotImplementedError):
            await store.search("col", "query")

    @pytest.mark.asyncio
    async def test_add_not_implemented(self):
        store = VectorStore()
        with pytest.raises(NotImplementedError):
            await store.add("col", [], [], [], [])

    @pytest.mark.asyncio
    async def test_delete_collection_not_implemented(self):
        store = VectorStore()
        with pytest.raises(NotImplementedError):
            await store.delete_collection("col")