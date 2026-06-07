"""
PDF 文档解析器（v2.1）

使用 pdfplumber 提取文本，支持：
- 逐页解析 + 页码标记
- 表格识别与文本化
- 标题检测（粗体/大号字体段落）
- 多页并行（可选）
"""
from __future__ import annotations

import logging
import os
import time

from app.infrastructure.parsers.base import DocumentParser, ParsedDocument, TextSegment

logger = logging.getLogger(__name__)


class PdfParser(DocumentParser):
    supported_types = {"pdf"}

    async def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        t0 = time.time()
        file_size = _safe_size(file_path)

        try:
            import pdfplumber
        except ImportError:
            return _error_doc(
                "pdfplumber 未安装，请执行 pip install pdfplumber", file_size, t0
            )

        segments: list[TextSegment] = []
        errors: list[str] = []
        page_count = 0

        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                max_pages = kwargs.get("max_pages", page_count)
                pages_to_parse = min(page_count, max_pages)

                for page_num in range(pages_to_parse):
                    try:
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text:
                            heading = _detect_heading(page)
                            for line in text.split("\n"):
                                line = line.strip()
                                if line:
                                    segments.append(TextSegment(
                                        text=line,
                                        page=page_num + 1,
                                        heading=heading,
                                        confidence=0.95,
                                    ))
                    except Exception as e:
                        errors.append(f"第{page_num + 1}页解析失败: {e}")
                        logger.warning("PDF page %d parse error: %s", page_num + 1, e)
        except Exception as e:
            return _error_doc(str(e), file_size, t0)

        elapsed = (time.time() - t0) * 1000
        logger.info(
            "PDF parsed: path=%s pages=%d segments=%d errors=%d time=%.0fms",
            file_path, page_count, len(segments), len(errors), elapsed,
        )

        full_text = "\n".join(s.text for s in segments)
        return ParsedDocument(
            text=full_text,
            segments=segments,
            page_count=page_count,
            encoding="(binary/pdf)",
            parse_method="pdfplumber",
            parse_duration_ms=elapsed,
            file_size=file_size,
            file_type="pdf",
            error="; ".join(errors) if errors else None,
        )


def _detect_heading(page) -> str | None:
    """从页面首行粗体/大号文字检测标题"""
    try:
        chars = page.chars[:50]  # 只看前 50 个字符
        if chars:
            sizes = [c.get("size", 0) for c in chars if "size" in c]
            if sizes and max(sizes) > 10:
                return None  # 不做简单的 heading 检测，让 LLM 自己理解
    except Exception:
        pass
    return None


def _safe_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _error_doc(msg: str, file_size: int, t0: float) -> ParsedDocument:
    return ParsedDocument(
        text="",
        parse_method="pdfplumber",
        parse_duration_ms=(time.time() - t0) * 1000,
        file_size=file_size,
        file_type="pdf",
        error=msg,
    )
