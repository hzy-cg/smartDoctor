"""
语义感知分块器（v2.2 增强）

替换原有的固定字符数按段落切分，实现：
1. 分隔符优先级：句号 → 换行 → 空格
2. 滑动窗口重叠（chunk_overlap）
3. 近似 token 计量（中文约 1.5 字符/token）
4. 文档上下文注入（v2.2 增强：支持解析元数据传递）
5. build_chunk_metadata() 桥接解析器与分块器
"""
from __future__ import annotations

import logging
import json

logger = logging.getLogger(__name__)

# 分隔符优先级：尽量在完整句子边界切分
_DEFAULT_SEPARATORS = ["。", ".", "！", "？", "?",
                         "\n\n", "\n", "；", ";", "，", ",", " ", ""]

# 中文 token 近似：1 token ≈ 1.5 字符
TOKEN_CHAR_RATIO = 1.5


def split_semantic_chunks(
    content: str,
    chunk_tokens: int = 512,
    chunk_overlap_tokens: int = 64,
    source_name: str = "",
    doc_context: dict | None = None,
) -> list[dict]:
    """
    语义感知分块，返回带元数据的 chunk 列表。

    每个 chunk 为 dict: {"content": str, "metadata": dict}

    Args:
        content: 原始文本
        chunk_tokens: 每块目标 token 数
        chunk_overlap_tokens: 相邻块重叠 token 数
        source_name: 文档来源名（如文件名）
        doc_context: 额外文档上下文（如页码、章节标题等）
    """
    if not content.strip():
        return []

    char_size = max(int(chunk_tokens * TOKEN_CHAR_RATIO), 100)
    overlap_chars = max(int(chunk_overlap_tokens * TOKEN_CHAR_RATIO), 20)

    raw_chunks = _recursive_split(content, _DEFAULT_SEPARATORS, char_size)

    # 滑动窗口拼接
    chunks_with_overlap = _apply_overlap(raw_chunks, char_size, overlap_chars)

    # 注入文档上下文 + 构建元数据
    base_meta = doc_context or {}
    base_meta["source"] = source_name

    enriched = []
    for i, (chunk_text, is_first_part) in enumerate(chunks_with_overlap):
        context_prefix = _build_context_line(source_name, base_meta, chunk_text)
        enriched_text = context_prefix + chunk_text if context_prefix else chunk_text

        meta = dict(base_meta)
        meta["chunk_index"] = i
        meta["total_chunks"] = len(chunks_with_overlap)
        meta["char_length"] = len(chunk_text)
        meta["approx_tokens"] = int(len(chunk_text) / TOKEN_CHAR_RATIO)

        enriched.append({
            "content": enriched_text.strip(),
            "metadata": meta,
        })

    return enriched


def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """递归分割：尝试用高优先级分隔符，不够则降级"""
    if len(text) <= chunk_size:
        return [text]

    for sep in separators:
        if sep == "":
            # 最后手段：强制按字符截断
            return _force_split(text, chunk_size)

        if sep not in text:
            continue

        parts = text.split(sep)
        chunks = []
        current = ""

        for part in parts:
            candidate = (current + sep + part).strip(sep) if current else part

            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # 如果单独一部分就超长，递归拆分
                if len(part) > chunk_size:
                    sub_chunks = _recursive_split(part, separators[separators.index(sep) + 1:], chunk_size)
                    chunks.extend(sub_chunks)
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current)

        return chunks

    return [text]


def _force_split(text: str, chunk_size: int) -> list[str]:
    """强制按字符截断"""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def _apply_overlap(chunks: list[str], target_size: int, overlap: int) -> list[tuple[str, bool]]:
    """
    滑动窗口重叠。
    返回 (chunk_text, is_first_part_of_original) 元组列表。
    """
    if len(chunks) <= 1:
        return [(c, True) for c in chunks]

    result: list[tuple[str, bool]] = []
    i = 0
    while i < len(chunks):
        current = chunks[i]

        # 检查是否需要和前一个 chunk 重叠
        if i > 0 and len(current) < target_size:
            # 从前一个 chunk 末尾取 overlap 字符拼接
            prev = chunks[i - 1]
            if len(prev) > overlap:
                tail = prev[-overlap:]
                current = tail + current
                result.append((current, False))

        # 检查是否需要和后一个 chunk 重叠
        elif i < len(chunks) - 1 and len(current) < target_size:
            next_chunk = chunks[i + 1]
            if len(next_chunk) > overlap:
                head = next_chunk[:overlap]
                current = current + head
                result.append((current, False))
        else:
            result.append((current, True))

        i += 1

    return result


def _build_context_line(source: str, meta: dict, chunk_text: str) -> str:
    """为 chunk 构建文档上下文行"""
    parts = [f"[文档: {source}"]
    if meta.get("page"):
        parts.append(f"第{meta['page']}页")
    if meta.get("slide") is not None:
        parts.append(f"幻灯片{meta['slide']}")
    if meta.get("heading"):
        parts.append(meta["heading"])
    if meta.get("timestamp_start") is not None:
        parts.append(f"[{_format_time(meta['timestamp_start'])}]")
    if meta.get("confidence", 1.0) < 0.8:
        parts.append("(低置信度)")
    parts.append("]")
    return " ".join(parts) + " "


def build_chunk_metadata(
    source_name: str = "",
    doc_type: str = "",
    parsed_meta: dict | None = None,
) -> dict:
    """
    构建分块上下文元数据（v2.2 新增）。

    桥接解析器输出与分块器，将解析阶段获取的文档元数据
    注入到每个分块的 metadata 中，供后续检索使用。

    Args:
        source_name: 文档名（如 高血压指南.pdf）
        doc_type: 文件类型（pdf, docx, txt 等）
        parsed_meta: 解析器返回的元数据，包含:
            - file_type, encoding, parse_method
            - page_count, parse_duration_ms, file_size
            - segments: list[dict] 解析片段

    Returns:
        dict: 注入到每个 chunk metadata 的文档上下文
    """
    meta: dict = {
        "source": source_name,
        "doc_type": doc_type,
    }

    # 上传时间戳（始终添加）
    from datetime import datetime, timezone
    meta["uploaded_at"] = datetime.now(timezone.utc).isoformat()

    if not parsed_meta:
        return meta

    # 解析器通用元数据
    for key in ("encoding", "parse_method", "page_count", "file_size"):
        if key in parsed_meta:
            meta[key] = parsed_meta[key]

    # 解析耗时（毫秒 → 秒，便于阅读）
    if "parse_duration_ms" in parsed_meta:
        meta["parse_duration_ms"] = parsed_meta["parse_duration_ms"]

    # 解析置信度均值
    segments = parsed_meta.get("segments", [])
    if segments:
        confidences = [s.get("confidence", 1.0) for s in segments if s.get("confidence")]
        if confidences:
            meta["avg_confidence"] = round(sum(confidences) / len(confidences), 3)

    # 上传时间戳
    from datetime import datetime, timezone
    meta["uploaded_at"] = datetime.now(timezone.utc).isoformat()

    return meta


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
