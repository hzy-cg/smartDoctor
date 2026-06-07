"""
查询优化器（v2.2 新增）

功能：
1. 医学术语映射：口语 → 医学标准术语
2. 多角度查询生成：单次查询拆分为 2-3 个检索语句
3. 查询缓存：相同查询 5 分钟内复用结果
"""
from __future__ import annotations

import logging
import time
from typing import Sequence

logger = logging.getLogger(__name__)

# ============================================================
# 医学术语映射表（静默扩展，无需 LLM 调用）
# 格式：口语表达 → [标准术语列表]
# ============================================================
MEDICAL_TERM_MAP: dict[str, list[str]] = {
    # 疼痛类
    "头疼": ["头痛", "偏头痛", "紧张性头痛", "丛集性头痛"],
    "头晕": ["眩晕", "头晕", "体位性低血压", "前庭性眩晕"],
    "牙疼": ["牙痛", "龋齿疼痛", "牙髓炎", "根尖周炎"],
    "胸口疼": ["胸痛", "心绞痛", "胸部不适", "肋间神经痛"],
    "肚子疼": ["腹痛", "急性胃肠炎", "消化道痉挛", "腹膜炎"],
    "腰疼": ["腰痛", "腰椎间盘突出", "腰肌劳损", "肾脏病变"],
    "腿疼": ["下肢疼痛", "坐骨神经痛", "关节炎", "深静脉血栓"],
    "嗓子疼": ["咽喉痛", "扁桃体炎", "咽炎", "喉炎"],

    # 血压/心血管
    "血压高": ["高血压", "血压升高", "高血压病", "原发性高血压"],
    "血压低": ["低血压", "血压偏低", "体位性低血压"],
    "心跳快": ["心动过速", "心悸", "心率增快"],
    "心慌": ["心悸", "心跳不规律", "心律失常", "心前区不适"],

    # 呼吸系统
    "喘不上气": ["呼吸困难", "气促", "呼吸窘迫", "支气管痉挛"],
    "咳嗽": ["咳嗽", "干咳", "湿咳", "咳痰"],
    "打喷嚏": ["喷嚏", "过敏性鼻炎", "上呼吸道感染"],
    "鼻塞": ["鼻塞", "鼻窦炎", "过敏性鼻炎", "鼻息肉"],

    # 消化系统
    "拉肚子": ["腹泻", "急性胃肠炎", "肠道感染", "消化不良"],
    "便秘": ["便秘", "排便困难", "肠蠕动减慢", "功能性便秘"],
    "烧心": ["胃灼热", "胃食管反流", "反酸"],
    "胃疼": ["胃痛", "胃痉挛", "胃炎", "胃溃疡"],
    "吃不下": ["食欲不振", "厌食", "胃纳差"],
    "想吐": ["恶心", "呕吐感", "胃肠不适"],

    # 体温/发热
    "发烧": ["发热", "体温升高", "高热", "低热"],
    "发冷": ["寒战", "畏寒", "体温调节异常"],
    "出汗多": ["多汗", "盗汗", "自主神经功能紊乱"],

    # 皮肤
    "起疹子": ["皮疹", "荨麻疹", "皮炎", "药疹"],
    "痒": ["瘙痒", "皮肤瘙痒", "过敏性皮炎", "湿疹"],
    "长痘": ["痤疮", "毛囊炎", "粉刺"],

    # 泌尿系统
    "尿频": ["尿频", "膀胱过度活动症", "泌尿系感染"],
    "尿痛": ["排尿困难", "尿路感染", "膀胱炎"],
    "尿血": ["血尿", "泌尿系统出血", "肾结石", "膀胱肿瘤"],

    # 神经系统
    "睡不着": ["失眠", "入睡困难", "睡眠障碍"],
    "手脚麻": ["肢体麻木", "周围神经病变", "颈椎病", "脑血管病变"],
    "抽筋": ["肌肉痉挛", "抽搐", "电解质紊乱", "低钙血症"],

    # 骨骼肌肉
    "关节疼": ["关节痛", "关节炎", "类风湿性关节炎", "骨关节炎"],
    "脖子疼": ["颈椎病", "颈部肌肉劳损", "落枕"],
    "肩膀疼": ["肩周炎", "肩袖损伤", "冻结肩"],

    # 五官
    "眼睛干": ["干眼症", "泪液分泌不足", "视疲劳"],
    "眼睛红": ["结膜炎", "角膜炎", "红眼病"],
    "耳鸣": ["耳鸣", "听力下降", "神经性耳鸣", "血管性耳鸣"],
    "流鼻血": ["鼻出血", "鼻衄", "鼻腔黏膜破裂"],

    # 妇科
    "痛经": ["痛经", "月经期疼痛", "原发性痛经"],
    "月经不调": ["月经周期紊乱", "闭经", "多囊卵巢综合征"],

    # 全身症状
    "没力气": ["乏力", "疲劳", "倦怠", "体能下降"],
    "瘦了": ["体重下降", "消瘦", "消耗性疾病"],
    "胖了": ["体重增加", "肥胖", "代谢综合征"],

    # 血常规相关
    "贫血": ["贫血", "血红蛋白降低", "缺铁性贫血", "巨幼细胞性贫血"],
    "血糖高": ["高血糖", "糖尿病", "糖耐量异常"],
    "血脂高": ["高脂血症", "胆固醇升高", "甘油三酯升高"],

    # 急症（仅做识别，不扩展术语）
    "胸痛": ["急性胸痛", "心绞痛", "心肌梗死", "肺栓塞"],
    "呼吸困难": ["急性呼吸困难", "呼吸衰竭", "哮喘急性发作", "气胸"],
}


class MedicalTermExpander:
    """
    医学术语扩展器 — 静默扩展，无需 LLM 调用。

    将用户口语化描述映射为标准医学术语集合。
    """

    def __init__(self, term_map: dict[str, list[str]] | None = None):
        self._term_map = term_map or MEDICAL_TERM_MAP

    def expand(self, query: str) -> str:
        """
        扩展查询中的口语词汇为医学术语。

        示例:
            "我头疼血压高" → "头痛 偏头痛 紧张性头痛 高血压 血压升高 高血压病"
        """
        expanded = [query]
        for oral, terms in self._term_map.items():
            if oral in query:
                for t in terms:
                    if t != oral and t not in query:
                        expanded.append(t)
        result = " ".join(expanded)
        if result != query:
            logger.debug("Term expansion: '%s' → '%s'", query[:60], result[:120])
        return result

    def hit_rate(self, query: str) -> float:
        """计算术语映射命中率"""
        hits = sum(1 for oral in self._term_map if oral in query)
        return hits / max(len(self._term_map), 1)


class QueryRewriter:
    """
    查询改写器 — 生成多角度检索查询。

    策略：
    1. 静默术语扩展（MedicalTermExpander）
    2. 分解生成长查询为短查询
    3. LLM 驱动的多角度查询（可选，需要 inject_llm）
    """

    CACHE_TTL = 300  # 5 分钟

    def __init__(self, term_expander: MedicalTermExpander | None = None):
        self._term_expander = term_expander or MedicalTermExpander()
        self._llm = None  # 可选 LLM 用于高级查询生成
        self._cache: dict[str, tuple[float, list[str]]] = {}

    def inject_llm(self, llm) -> None:
        """注入 LLM 用于高级多角度查询生成"""
        self._llm = llm

    async def rewrite(self, query: str, history: list[dict] | None = None) -> list[str]:
        """
        改写查询为多个检索语句。

        Args:
            query: 用户原始查询
            history: 对话历史（可选，用于上下文查询）

        Returns:
            改写后的查询列表（至少包含原始查询）
        """
        now = time.time()
        if query in self._cache:
            ts, results = self._cache[query]
            if now - ts < self.CACHE_TTL:
                return results

        queries = [query]

        # Step 1: 术语扩展查询
        expanded = self._term_expander.expand(query)
        if expanded != query:
            queries.append(expanded)

        # Step 2: 生成诊断类查询
        diagnostic = self._make_diagnostic_query(query)
        if diagnostic and diagnostic != query:
            queries.append(diagnostic)

        # Step 3: 生成病因类查询
        etiology = self._make_etiology_query(query)
        if etiology and etiology != query:
            queries.append(etiology)

        # Step 4: LLM 高级查询（如果可用）
        if self._llm:
            try:
                llm_queries = await self._llm_rewrite(query)
                for q in llm_queries:
                    if q not in queries:
                        queries.append(q)
            except Exception:
                logger.debug("LLM query rewriting failed, using static methods only")

        # 去重保持顺序
        seen = set()
        unique = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique.append(q)

        self._cache[query] = (now, unique)
        logger.debug("Query rewritten: '%s' → %d queries", query[:40], len(unique))
        return unique

    def _make_diagnostic_query(self, query: str) -> str:
        """生成诊断类查询"""
        patterns = ["发烧", "疼", "痛", "肿", "红", "疹", "血", "咳", "晕", "吐", "拉"]
        if any(p in query for p in patterns):
            return f"{query}的诊断标准和鉴别诊断"
        return f"{query}的常见病因"

    def _make_etiology_query(self, query: str) -> str:
        """生成病因类查询"""
        return f"{query}的可能原因和危险因素"

    async def _llm_rewrite(self, query: str) -> Sequence[str]:
        """使用 LLM 生成多角度查询"""
        if not self._llm:
            return []

        prompt = (
            "你是一个医学查询改写助手。将用户的症状描述改写为2-3个不同角度的"
            "医学检索查询，每个查询用换行分隔。只输出查询，不要解释。\n\n"
            f"用户描述：{query}\n查询："
        )
        messages = [
            {"role": "system", "content": "你是医学查询改写助手。只输出改写后的查询。"},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.chat(messages, max_tokens=200)
        lines = [line.strip() for line in response.strip().split("\n") if line.strip()]
        return lines[:3]
