"""
TXT/MD 文本解析器（v2.1）

特点：
- 编码自动检测（BOM → chardet → 启发式）
- 多编码回退（UTF-8 → GBK → GB18030 → latin-1）
- 按段落分页（每 60 行视为一页）
"""
from __future__ import annotations

import logging
import os
import time

from app.infrastructure.parsers.base import DocumentParser, ParsedDocument, TextSegment
from app.infrastructure.parsers.encoding_detector import EncodingDetector

logger = logging.getLogger(__name__)


class TxtParser(DocumentParser):
    supported_types = {"txt", "md"}

    async def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        t0 = time.time()
        file_size = _safe_size(file_path)

        # 编码检测
        encoding = kwargs.get("encoding")
        text, encoding = EncodingDetector.read_text(file_path, encoding)

        # 分页（60 行/页）
        lines = text.split("\n")
        page_size = 60
        segments = []
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            page = i // page_size + 1
            segments.append(TextSegment(
                text=line.strip(),
                page=page,
                confidence=1.0,
            ))

        elapsed = (time.time() - t0) * 1000
        logger.info(
            "TXT parsed: path=%s encoding=%s size=%d lines=%d segments=%d time=%.0fms",
            file_path, encoding, file_size, len(lines), len(segments), elapsed,
        )

        return ParsedDocument(
            text=text,
            segments=segments,
            page_count=(len(lines) // page_size) + 1,
            encoding=encoding,
            parse_method="txt",
            parse_duration_ms=elapsed,
            file_size=file_size,
            file_type=_ext_type(file_path),
        )


def _ext_type(path: str) -> str:
    _, ext = os.path.splitext(path)
    return ext.lstrip(".").lower() or "txt"


def _safe_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
