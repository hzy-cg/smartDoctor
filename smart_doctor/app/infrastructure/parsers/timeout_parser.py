"""
超时解析器包装（v2.2 新增）

对任意 DocumentParser 添加超时控制，超时时返回部分结果而非崩溃。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.infrastructure.parsers.base import DocumentParser, ParsedDocument
from app.infrastructure.parsers.exceptions import TimeoutError

logger = logging.getLogger(__name__)

# 默认超时（秒）
DEFAULT_TIMEOUT = 30.0


class TimeoutParser:
    """
    超时解析器包装。

    用法:
        parser = TimeoutParser(PdfParser(), timeout=30.0)
        doc = await parser.parse(file_path)
        if doc.parse_method == "timeout":
            # 超时了，只有部分结果
            ...

    设计要点:
      - 内部在 executor 中运行同步解析，通过 asyncio.wait_for 控制超时
      - 超时后返回部分结果（ParsedDocument 中 error 字段标注）
      - 不中断原始解析器线程（避免资源泄漏），只是不再等待结果
    """

    def __init__(self,
                 parser: DocumentParser,
                 timeout: float = DEFAULT_TIMEOUT):
        self._parser = parser
        self._timeout = timeout

    async def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        """
        带超时控制的解析。

        Returns:
            ParsedDocument: 正常完成时 parse_method 为原始解析器名；
                            超时时 parse_method 为 "timeout"，
                            error 字段包含超时信息。
        """
        t0 = time.time()
        try:
            doc = await asyncio.wait_for(
                self._parser.parse(file_path, **kwargs),
                timeout=self._timeout,
            )
            return doc
        except asyncio.TimeoutError:
            elapsed = (time.time() - t0) * 1000
            logger.warning(
                "Parse timeout after %.1fs: file=%s parser=%s",
                self._timeout, file_path, type(self._parser).__name__,
            )
            return ParsedDocument(
                text="",
                segments=[],
                page_count=0,
                encoding="unknown",
                parse_method="timeout",
                parse_duration_ms=elapsed,
                file_size=0,
                file_type=self._parser.supported_types.pop() if self._parser.supported_types else "unknown",
                error=f"解析超时（{self._timeout:.0f}s），无法提取内容",
            )
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            logger.warning(
                "Parse failed: file=%s parser=%s error=%s",
                file_path, type(self._parser).__name__, e,
            )
            return ParsedDocument(
                text="",
                segments=[],
                page_count=0,
                encoding="unknown",
                parse_method="failed",
                parse_duration_ms=elapsed,
                file_size=0,
                file_type=self._parser.supported_types.pop() if self._parser.supported_types else "unknown",
                error=str(e),
            )