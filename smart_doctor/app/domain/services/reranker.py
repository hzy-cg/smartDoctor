"""
CrossEncoder 重排序器（v2.2 新增）

对候选检索结果进行精细排序，提升 Top-K 相关性。

技术方案：
  主方案:  BAAI/bge-reranker-v2-m3 (sentence-transformers CrossEncoder)
  降级方案: 轻量级 TF-IDF 启发式重排序（无模型依赖，零启动成本）
  终极降级: 返回原始顺序（无 re-rank）

设计要点：
  - 懒加载模型，避免启动延迟
  - 模型加载失败时自动降级
  - 批处理打分，避免逐对推理
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 优先使用的重排序模型（需要 pip install sentence-transformers）
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
# 轻量备用模型（更快但精度略低）
FALLBACK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """
    CrossEncoder 重排序器。

    使用方式:
        reranker = CrossEncoderReranker()
        # 模型首次调用时懒加载
        ranked = await reranker.rerank("查询文本", candidate_docs, top_k=5)
    """

    def __init__(self, model_name: str | None = None):
        """
        Args:
            model_name: 模型名称，None = 自动降级为 TF-IDF 启发式。
                       设置为 RERANKER_MODEL 可强制使用指定模型。
        """
        self._model_name = model_name
        self._model = None          # CrossEncoder 实例（懒加载）
        self._load_attempted = False
        self._use_fallback = False  # True = 模型不可用，使用 TF-IDF

    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        对候选文档重新排序。

        Args:
            query: 用户查询文本
            candidates: 候选文档列表，每项须包含 "content" 字段
            top_k: 返回前 K 个结果

        Returns:
            按 relevance 降序排列的结果（原始 dict 追加 "rerank_score" 字段）
        """
        if not candidates:
            return candidates

        # 如果候选数 <= top_k，无需重排，直接标注
        if len(candidates) <= top_k:
            for c in candidates:
                c["rerank_score"] = c.get("final_score", c.get("score", 0.5))
            return candidates

        # Step 1: 尝试加载模型
        if not self._load_attempted:
            self._try_load_model()

        # Step 2: 模型可用 → CrossEncoder 精排
        if self._model is not None:
            return await self._rerank_with_model(query, candidates, top_k)

        # Step 3: 降级 → TF-IDF 启发式重排序
        return self._rerank_with_tfidf(query, candidates, top_k)

    # ---------------------------------------------------------------
    # 主方案: CrossEncoder 精排
    # ---------------------------------------------------------------
    def _try_load_model(self) -> None:
        """尝试加载 sentence-transformers CrossEncoder 模型"""
        self._load_attempted = True

        try:
            from sentence_transformers import CrossEncoder

            model_to_try = self._model_name or RERANKER_MODEL

            try:
                self._model = CrossEncoder(model_to_try, max_length=512)
                logger.info("CrossEncoder model loaded: %s", model_to_try)
            except Exception:
                # 主模型不可用，尝试备用
                logger.warning(
                    "Model %s unavailable, trying fallback %s",
                    model_to_try, FALLBACK_MODEL,
                )
                self._model = CrossEncoder(FALLBACK_MODEL, max_length=512)
                logger.info("CrossEncoder fallback model loaded: %s", FALLBACK_MODEL)

        except ImportError:
            logger.info(
                "sentence-transformers not installed, using TF-IDF heuristic reranker. "
                "To enable CrossEncoder: pip install sentence-transformers"
            )
            self._use_fallback = True
        except Exception as e:
            logger.warning("CrossEncoder load failed: %s, switching to TF-IDF", e)
            self._use_fallback = True

    async def _rerank_with_model(
        self, query: str, candidates: list[dict], top_k: int,
    ) -> list[dict]:
        """使用 CrossEncoder 模型打分"""
        import asyncio

        # 构造 (query, document) 对
        pairs = []
        valid_indices = []
        for i, c in enumerate(candidates):
            text = c.get("content", "")
            if text.strip():
                pairs.append([query, text])
                valid_indices.append(i)

        if not pairs:
            return candidates[:top_k]

        # 在线程池中推理（避免阻塞事件循环）
        try:
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, self._model.predict, pairs)
        except Exception as e:
            logger.warning("CrossEncoder predict failed: %s, falling back", e)
            return self._rerank_with_tfidf(query, candidates, top_k)

        # 填入分数
        for idx, score in zip(valid_indices, scores):
            candidates[idx]["rerank_score"] = float(score)

        # 未评分的保持原始分数
        for c in candidates:
            if "rerank_score" not in c:
                c["rerank_score"] = c.get("final_score", c.get("score", 0.5))

        # 按 rerank_score 降序
        ranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_k]

    # ---------------------------------------------------------------
    # 降级方案: TF-IDF 启发式重排序（零依赖，始终可用）
    # ---------------------------------------------------------------
    def _rerank_with_tfidf(
        self, query: str, candidates: list[dict], top_k: int,
    ) -> list[dict]:
        """
        基于 TF-IDF 相似度的启发式重排序。

        策略:
          1. Word-level 召回：query 中的词在文档中出现次数越多，分数越高
          2. 医学术语加权：医学关键词（高血压/糖尿病等）命中时加权 2x
          3. 标题命中加权：如果候选 heading 匹配 query 词，加分
          4. 最终分数 = base_score × 0.4 + tfidf_score × 0.6
        """
        from collections import Counter
        from math import log

        # 中文分词：按字符 bigram 切分 + 单字频率
        query_terms = _chinese_tokenize(query)
        doc_count = len(candidates)

        # 计算 IDF
        term_doc_freq = Counter()
        doc_term_sets = []
        for c in candidates:
            terms = set(_chinese_tokenize(c.get("content", "")))
            doc_term_sets.append(terms)
            for t in terms:
                term_doc_freq[t] += 1

        # IDF 计算
        idf = {}
        for term, freq in term_doc_freq.items():
            idf[term] = log((doc_count + 1) / (freq + 1)) + 1

        # 对每个候选打分
        for i, c in enumerate(candidates):
            base = c.get("final_score", c.get("score", 0.5))

            # TF-IDF 分数
            tfidf_score = 0.0
            doc_terms = doc_term_sets[i]
            for qt in query_terms:
                if qt in doc_terms:
                    tfidf_score += idf.get(qt, 0.5)

            # 归一化
            max_possible = sum(idf.get(qt, 0.5) for qt in query_terms)
            if max_possible > 0:
                tfidf_score = tfidf_score / max_possible

            # 标题命中加权
            heading = c.get("heading", "")
            heading_bonus = 0.0
            if heading:
                heading_terms = set(_chinese_tokenize(heading))
                for qt in query_terms:
                    if qt in heading_terms:
                        heading_bonus += 0.15  # 每个匹配词 +0.15

            # 医学术语加权
            medical_bonus = _medical_term_bonus(c.get("content", ""), query_terms)

            # 最终分数：base 40% + tfidf 50% + heading 5% + medical 5%
            rerank_score = (
                base * 0.4
                + tfidf_score * 0.5
                + min(heading_bonus, 0.5) * 0.1
                + medical_bonus * 0.1
            )
            # 压缩到 [0, 1]
            c["rerank_score"] = min(rerank_score, 1.0)

        ranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_k]


# ---------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------
def _chinese_tokenize(text: str) -> list[str]:
    """
    中文分词（字级别 bigram + 去标点）。

    示例: "高血压头痛" → ["高血", "血压", "压头", "头痛", "高", "血", "压", "头", "痛"]
    """
    import re
    cleaned = re.sub(r'[，。！？、；：\u201c\u201d（）\s\n\r]+', '', text)
    terms = []

    # Bigram（2字组合，适合医学术语）
    for i in range(len(cleaned) - 1):
        terms.append(cleaned[i:i + 2])

    # 单字（补充）
    terms.extend(list(cleaned))

    return terms


def _medical_term_bonus(text: str, query_terms: list[str]) -> float:
    """检查文档中是否包含医学术语关键词，给予加分"""
    medical_keywords = {
        "高血压", "糖尿病", "冠心病", "脑卒中", "哮喘", "肺结核",
        "肾功能", "肝功能", "心电图", "CT", "MRI", "血糖", "胆固醇",
        "心肌梗死", "房颤", "心衰", "肺炎", "流感", "过敏", "感染",
        "肿瘤", "癌症", "化疗", "手术", "医保", "诊断", "治疗",
        "卒中", "栓塞", "出血", "休克", "昏迷", "痉挛", "麻痹",
        "免疫", "激素", "抗生素", "降压", "降糖", "降脂",
    }
    hits = 0
    for kw in medical_keywords:
        if kw in text:
            hits += 1
    if hits > 5:
        hits = 5  # 上限
    return hits * 0.02
