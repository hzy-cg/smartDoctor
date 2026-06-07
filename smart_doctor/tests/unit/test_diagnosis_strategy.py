import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.services.diagnosis_strategy import (
    RAGResult, RAGStrategy, DiagnosisEngine, AgentFactory, ROLE_PROMPT,
)
from app.domain.value_objects import ClinicalState
from app.domain.state_machine import DiagnosisStateMachine


class TestRAGResult:
    def test_creation(self):
        r = RAGResult(content="test", sources=[{"a": 1}])
        assert r.content == "test"
        assert len(r.sources) == 1

    def test_default_sources(self):
        r = RAGResult(content="test")
        assert r.sources == []


class TestRAGStrategy:
    @pytest.mark.asyncio
    async def test_search_both_stores(self):
        private = AsyncMock()
        private.search.return_value = [{"content": "p1", "source": "a"}]
        common = AsyncMock()
        common.search.return_value = [{"content": "c1", "source": "b"}]
        strategy = RAGStrategy(private_store=private, common_store=common, embedding=None)
        result = await strategy.search("doc1", "头痛")
        assert "p1" in result.content
        assert "c1" in result.content
        assert len(result.sources) == 2

    @pytest.mark.asyncio
    async def test_search_private_only(self):
        private = AsyncMock()
        private.search.return_value = [{"content": "p1", "source": "a"}]
        strategy = RAGStrategy(private_store=private, common_store=None, embedding=None)
        result = await strategy.search("doc1", "头痛")
        assert "p1" in result.content

    @pytest.mark.asyncio
    async def test_search_common_only(self):
        common = AsyncMock()
        common.search.return_value = [{"content": "c1", "source": "b"}]
        strategy = RAGStrategy(private_store=None, common_store=common, embedding=None)
        result = await strategy.search("doc1", "头痛")
        assert "c1" in result.content

    @pytest.mark.asyncio
    async def test_search_no_stores(self):
        strategy = RAGStrategy(private_store=None, common_store=None, embedding=None)
        result = await strategy.search("doc1", "头痛")
        assert result.content == ""
        assert result.sources == []

    def test_deduplicate(self):
        strategy = RAGStrategy(private_store=None, common_store=None, embedding=None)
        items = [
            {"source": "a", "content": "hello world this is unique"},
            {"source": "a", "content": "hello world this is unique"},
            {"source": "b", "content": "different content here"},
        ]
        result = strategy._deduplicate(items)
        assert len(result) == 2

    def test_deduplicate_limit(self):
        strategy = RAGStrategy(private_store=None, common_store=None, embedding=None)
        items = [{"source": f"s{i}", "content": f"content {i} unique text"} for i in range(10)]
        result = strategy._deduplicate(items)
        assert len(result) == 5


class TestDiagnosisEngine:
    def test_build_messages_basic(self):
        llm = AsyncMock()
        engine = DiagnosisEngine(llm=llm, system_prompt="你是医生")
        state = ClinicalState(conversation_id=uuid.uuid4())
        state._last_user_message = "我头痛"
        messages = engine.build_messages(state)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "我头痛" in messages[1]["content"]

    def test_build_messages_with_rag_context(self):
        llm = AsyncMock()
        engine = DiagnosisEngine(llm=llm, system_prompt="你是医生")
        state = ClinicalState(conversation_id=uuid.uuid4(), rag_context="参考资料")
        state._last_user_message = "我头痛"
        messages = engine.build_messages(state)
        assert len(messages) == 3
        assert any("参考资料" in m["content"] for m in messages)

    @pytest.mark.asyncio
    async def test_generate_intent(self):
        llm = AsyncMock()
        llm.chat.return_value = "new_symptom"
        engine = DiagnosisEngine(llm=llm, system_prompt="你是医生")
        intent = await engine.generate_intent("我头痛")
        assert intent == "new_symptom"
        llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response(self):
        llm = AsyncMock()
        llm.chat.return_value = "请问持续多久了？"
        engine = DiagnosisEngine(llm=llm, system_prompt="你是医生")
        state = ClinicalState(conversation_id=uuid.uuid4())
        state._last_user_message = "我头痛"
        response = await engine.generate_response(state)
        assert response == "请问持续多久了？"


class TestAgentFactory:
    def test_get_or_create(self):
        llm = AsyncMock()
        factory = AgentFactory(llm=llm, rag_strategy=None)
        engine = factory.get_or_create(
            doctor_id="doc1",
            doctor_name="张医生",
            doctor_title="主任医师",
            doctor_specialty="神经内科",
            doctor_expertise="头痛",
        )
        assert isinstance(engine, DiagnosisEngine)
        assert "张医生" in engine._system_prompt

    def test_get_or_create_cached(self):
        llm = AsyncMock()
        factory = AgentFactory(llm=llm, rag_strategy=None)
        e1 = factory.get_or_create("doc1", "张医生", "主任医师", "神经内科")
        e2 = factory.get_or_create("doc1", "张医生", "主任医师", "神经内科")
        assert e1 is e2

    def test_invalidate(self):
        llm = AsyncMock()
        factory = AgentFactory(llm=llm, rag_strategy=None)
        factory.get_or_create("doc1", "张医生", "主任医师", "神经内科")
        factory.invalidate("doc1")
        assert "doc1" not in factory._cache

    def test_cache_eviction(self):
        llm = AsyncMock()
        factory = AgentFactory(llm=llm, rag_strategy=None)
        for i in range(51):
            factory.get_or_create(f"doc{i}", f"医生{i}", "医师", "内科")
        assert len(factory._cache) <= 51