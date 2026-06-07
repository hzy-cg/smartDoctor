import uuid
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

from app.domain.state_machine import DiagnosisStateMachine
from app.domain.value_objects import ClinicalState
from app.infrastructure.llm import LLMProvider
from app.domain.services.context_assembler import ContextAssembler, SearchQualityMonitor

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    content: str
    sources: list[dict] = field(default_factory=list)


class RAGStrategy:
    COMMON_COLLECTION = "common_knowledge"

    def __init__(self, private_store, common_store, embedding,
                 query_rewriter=None, reranker=None):
        self._private_store = private_store
        self._common_store = common_store
        self._embedding = embedding
        self._query_rewriter = query_rewriter  # QueryRewriter (v2.2)
        self._reranker = reranker              # CrossEncoderReranker (v2.2)

    def _doctor_collection(self, doctor_id: str) -> str:
        return f"doctor_{doctor_id}"

    async def search(self, doctor_id: str, query: str, top_k: int = 5) -> RAGResult:
        # v2.2: 查询改写 — 生成多个检索查询
        queries = [query]
        if self._query_rewriter:
            try:
                queries = await self._query_rewriter.rewrite(query)
            except Exception:
                logger.debug("Query rewriting failed, using original query")

        # 多查询并行检索
        all_results = []
        for q in queries:
            if self._private_store:
                collection = self._doctor_collection(doctor_id)
                try:
                    results = await self._private_store.search(collection, q, top_k)
                    all_results.extend(results)
                except Exception:
                    pass
            if self._common_store:
                try:
                    results = await self._common_store.search(self.COMMON_COLLECTION, q, top_k)
                    all_results.extend(results)
                except Exception:
                    pass

        merged = self._deduplicate(all_results)

        # v2.2: 分层权重排序 — 按文档类型和可信度加权
        merged = self._apply_type_weights(merged)

        # v2.2: CrossEncoder 重排序（在分层权重后二次精排）
        if self._reranker and merged:
            try:
                merged = await self._reranker.rerank(query, merged, top_k=top_k)
            except Exception:
                logger.debug("Reranker failed, using type-weight sorted results")

        return RAGResult(
            content="\n".join(r.get("content", "") for r in merged[:top_k]),
            sources=merged[:top_k],
        )

    def _deduplicate(self, results: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for r in results:
            key = r.get("source", "") + r.get("content", "")[:80]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique[:10]

    # === v2.2: 分层权重 ===
    DOC_TYPE_WEIGHTS = {
        "pdf": 1.0, "docx": 0.9, "doc": 0.9,
        "pptx": 0.8, "ppt": 0.8,
        "xlsx": 0.6, "xls": 0.6,
        "txt": 0.7, "md": 0.7,
    }
    DEFAULT_DOC_WEIGHT = 0.7

    def _apply_type_weights(self, results: list[dict]) -> list[dict]:
        """按文档类型分层权重排序"""
        for r in results:
            score = r.get("score", 0.5)
            doc_type = r.get("doc_type", "txt")
            confidence = r.get("confidence", 1.0)

            type_weight = self.DOC_TYPE_WEIGHTS.get(doc_type, self.DEFAULT_DOC_WEIGHT)
            r["final_score"] = score * type_weight * confidence
        return sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)


class DiagnosisEngine:
    MAX_HISTORY_ROUNDS = 10

    def __init__(self, llm: LLMProvider, system_prompt: str,
                 rag_strategy: RAGStrategy | None = None):
        self._llm = llm
        self._system_prompt = system_prompt
        self._rag = rag_strategy
        self._context_assembler = ContextAssembler()  # v2.2
        self._quality_monitor = SearchQualityMonitor()  # v2.2

    def build_messages(self, state: ClinicalState,
                       history: list[dict] | None = None) -> list[dict]:
        messages = [{"role": "system", "content": self._system_prompt}]

        if state.symptoms:
            symptoms_text = "、".join(state.symptoms)
            messages.append({
                "role": "system",
                "content": f"[已收集症状：{symptoms_text}，请勿重复询问以上症状相关信息]"
            })

        if state.rag_context:
            messages.append({
                "role": "system",
                "content": f"参考以下医学资料：\n{state.rag_context}"
            })

        if history:
            trimmed = history[-(self.MAX_HISTORY_ROUNDS * 2):]
            for msg in trimmed:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
            last = trimmed[-1]
            if last["role"] == "user" and last["content"] == state._last_user_message:
                stage_hint = f"[当前阶段: {state.diagnosis_stage}]"
                messages[-1]["content"] = f"{stage_hint}\n{last['content']}"
                return messages

        current = {
            "role": "user",
            "content": f"[当前阶段: {state.diagnosis_stage}]\n{state._last_user_message}",
        }
        messages.append(current)
        return messages

    async def generate_intent(self, user_message: str,
                              history: list[dict] | None = None) -> str:
        context = ""
        if history:
            recent = history[-4:]
            context = "\n".join(f"{'患者' if m['role']=='user' else '医生'}：{m['content']}" for m in recent)
            context = f"\n最近对话：\n{context}\n"

        prompt = (
            f"分析以下用户消息的意图，仅输出意图标签（new_symptom/follow_up_answer/"
            f"need_detail/ready_recommend/confirm/dissatisfied/chitchat）：\n"
            f"{context}"
            f"用户：{user_message}\n意图："
        )
        messages = [
            {"role": "system", "content": "你是意图分类器，仅输出意图标签。"},
            {"role": "user", "content": prompt},
        ]
        return (await self._llm.chat(messages, max_tokens=20)).strip()

    async def _do_rag_search(self, state: ClinicalState, doctor_id: str) -> None:
        """执行 RAG 检索并组装上下文（v2.2 增强）"""
        if not self._rag or not doctor_id or not state._last_user_message:
            return

        import time
        t0 = time.time()
        top_k = 5
        try:
            rag_result = await self._rag.search(
                doctor_id, state._last_user_message, top_k=top_k
            )
            latency_ms = (time.time() - t0) * 1000

            if rag_result.sources:
                # v2.2: 使用 ContextAssembler 组装上下文
                context = self._context_assembler.assemble(rag_result.sources)
                state.rag_context = context
                state.rag_sources = rag_result.sources

                # 质量监控
                avg_score = sum(s.get("score", 0) for s in rag_result.sources) / len(rag_result.sources)
                self._quality_monitor.record(
                    search_latency_ms=latency_ms,
                    hit_count=len(rag_result.sources),
                    avg_score=avg_score,
                    context_chars=len(context),
                    query=state._last_user_message,
                )
            else:
                self._quality_monitor.record(
                    search_latency_ms=latency_ms,
                    hit_count=0,
                    avg_score=0.0,
                    context_chars=0,
                    query=state._last_user_message,
                )
        except Exception:
            pass

    async def generate_response(self, state: ClinicalState,
                                history: list[dict] | None = None,
                                doctor_id: str | None = None) -> str:
        await self._do_rag_search(state, doctor_id)
        messages = self.build_messages(state, history)
        return await self._llm.chat(messages, temperature=0.7, max_tokens=1024)

    async def generate_response_stream(self, state: ClinicalState,
                                       history: list[dict] | None = None,
                                       doctor_id: str | None = None) -> AsyncIterator[str]:
        await self._do_rag_search(state, doctor_id)

        messages = self.build_messages(state, history)
        async for chunk in self._llm.chat_stream(messages, temperature=0.7, max_tokens=1024):
            yield chunk


class AgentFactory:
    def __init__(self, llm: LLMProvider, rag_strategy: RAGStrategy | None = None):
        self._llm = llm
        self._rag = rag_strategy
        self._cache: dict[str, DiagnosisEngine] = {}

    def get_or_create(self, doctor_id: str, doctor_name: str, doctor_title: str,
                      doctor_specialty: str, doctor_expertise: str = "",
                      tone: str = "professional") -> DiagnosisEngine:
        if doctor_id in self._cache:
            return self._cache[doctor_id]

        prompt = ROLE_PROMPT.format(
            name=doctor_name,
            title=doctor_title,
            specialty=doctor_specialty,
            expertise=doctor_expertise or "暂无",
            tone=tone,
        )
        engine = DiagnosisEngine(llm=self._llm, system_prompt=prompt,
                                 rag_strategy=self._rag)
        if len(self._cache) >= 50:
            del self._cache[next(iter(self._cache))]
        self._cache[doctor_id] = engine
        return engine

    def invalidate(self, doctor_id: str) -> None:
        self._cache.pop(doctor_id, None)


ROLE_PROMPT = """你是 {name}，{title}，主攻 {specialty}。

擅长领域：{expertise}

你的问诊风格是 "{tone}"。请严格遵循以下规则：
1. 仅基于医学知识进行分析，不做超出能力范围的诊断
2. 逐步追问，每次问 1-2 个问题，不一次性问太多
3. 收集到充分症状后，给出初步分析并推荐就诊科室
4. 每条分析后必须附加免责声明："以上分析仅供参考，不能替代专业医生诊断，请及时就医"
5. 语气平和专业，用患者能理解的语言沟通
6. 不要给出任何具体药物或剂量建议
7. 用户描述紧急症状（胸痛、呼吸困难、剧烈腹痛等）时，立即建议拨打 120 前往急诊
8. 仔细阅读对话历史，绝对不要重复询问患者已经回答过的问题
9. 如果患者已提供某症状信息，直接基于已有信息继续分析，不要再追问同一症状
"""
