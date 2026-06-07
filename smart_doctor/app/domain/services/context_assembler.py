"""
上下文组装器（v2.2 新增）

负责将检索结果组装为 LLM 可消费的上下文：
1. Token 预算管理（MAX_CONTEXT_TOKENS=2000）
2. 按 final_score 降序排列
3. 同文档连续片段合并
4. 来源标签注入（文档名、页码、置信度）
5. 预算内截断
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 中文近似：1 token ≈ 1.5 字符
TOKEN_CHAR_RATIO = 1.5
MAX_CONTEXT_TOKENS = 2000
MAX_CONTEXT_CHARS = int(MAX_CONTEXT_TOKENS * TOKEN_CHAR_RATIO)


class ContextAssembler:
    """将检索结果组装为格式化的 LLM 上下文"""

    def __init__(self, max_tokens: int = MAX_CONTEXT_TOKENS):
        self._max_chars = int(max_tokens * TOKEN_CHAR_RATIO)

    def assemble(self, sources: list[dict]) -> str:
        """
        组装上下文文本。

        Args:
            sources: 检索结果列表，每项含 content/score/source/doc_type/page 等

        Returns:
            格式化的上下文文本，在 token 预算内
        """
        if not sources:
            return ""

        # Step 1: 按 final_score 降序排列
        sorted_sources = sorted(
            sources, key=lambda x: x.get("final_score", x.get("score", 0)), reverse=True
        )

        # Step 2: 同文档连续片段合并
        merged = self._merge_consecutive(sorted_sources)

        # Step 3: 按 token 预算截断 + 注入来源标签
        return self._build_context(merged)

    def _merge_consecutive(self, sources: list[dict]) -> list[dict]:
        """合并同一文档的连续片段，减少重复标题"""
        if not sources:
            return []

        merged = []
        current = dict(sources[0])
        current["content"] = sources[0].get("content", "")

        for next_src in sources[1:]:
            same_doc = (
                next_src.get("source") == current.get("source")
                and next_src.get("page") == current.get("page")
            )
            if same_doc:
                current["content"] += "\n" + next_src.get("content", "")
                # 保留更高置信度
                current["confidence"] = max(
                    current.get("confidence", 0), next_src.get("confidence", 0)
                )
                current["final_score"] = max(
                    current.get("final_score", 0), next_src.get("final_score", 0)
                )
            else:
                merged.append(current)
                current = dict(next_src)
                current["content"] = next_src.get("content", "")

        merged.append(current)
        return merged

    def _build_context(self, sources: list[dict]) -> str:
        """组装最终上下文文本"""
        parts = []
        char_count = 0

        for src in sources:
            label = self._format_label(src)
            chunk_text = src.get("content", "")

            # 估算该 chunk 的总字符数（含标签和分隔符）
            estimated = len(label) + len(chunk_text) + 10  # 分隔符开销

            if char_count + estimated > self._max_chars and parts:
                # 超出预算，截断当前 chunk 或跳过
                remaining = self._max_chars - char_count - len(label) - 10
                if remaining > 50:
                    chunk_text = chunk_text[:remaining] + "..."
                else:
                    break

            parts.append(f"{label}\n{chunk_text}")
            char_count += estimated

        return "\n\n---\n\n".join(parts)

    def _format_label(self, meta: dict) -> str:
        """格式化来源标签"""
        source = meta.get("source", "未知文档")
        parts = [f"[来源: {source}"]

        if meta.get("page"):
            parts.append(f"第{meta['page']}页")

        if meta.get("heading"):
            parts.append(meta["heading"])

        if meta.get("doc_type"):
            parts.append(meta["doc_type"].upper())

        if meta.get("timestamp_start") is not None:
            parts.append(f"[{self._format_time(meta['timestamp_start'])}]")

        confidence = meta.get("confidence", 1.0)
        if isinstance(confidence, (int, float)) and confidence < 0.8:
            parts.append("低置信度")

        parts.append("]")
        return " | ".join(parts)

    def _format_time(self, seconds: float) -> str:
        """格式化音频时间戳"""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


class SearchQualityMonitor:
    """检索质量监控（v2.2 新增）"""

    def __init__(self):
        self._metrics: list[dict] = []

    def record(self, search_latency_ms: float, hit_count: int,
               avg_score: float, context_chars: int,
               query: str = "", rewritten_queries: int = 0):
        """记录一次检索指标"""
        self._metrics.append({
            "latency_ms": search_latency_ms,
            "hit_count": hit_count,
            "avg_score": avg_score,
            "context_chars": context_chars,
            "rewritten_queries": rewritten_queries,
            "query_preview": query[:40] if query else "",
        })

        # 告警阈值
        if search_latency_ms > 500:
            logger.warning("Search latency exceeds 500ms: %.0fms", search_latency_ms)
        if hit_count == 0 and query:
            logger.warning("Search returned zero results for: '%s'", query[:80])

    def summary(self) -> dict:
        """返回最近检索质量摘要"""
        if not self._metrics:
            return {"samples": 0}
        recent = self._metrics[-100:]
        latencies = [m["latency_ms"] for m in recent]
        hits = [m["hit_count"] for m in recent]
        scores = [m["avg_score"] for m in recent]
        return {
            "samples": len(recent),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "median_latency_ms": sorted(latencies)[len(latencies) // 2],
            "hit_rate": sum(1 for h in hits if h > 0) / len(hits),
            "avg_similarity": sum(scores) / len(scores) if scores else 0.0,
            "avg_context_chars": sum(m["context_chars"] for m in recent) / len(recent),
        }
