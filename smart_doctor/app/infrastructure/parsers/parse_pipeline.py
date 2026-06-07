"""
解析流水线（v2.2 新增）

多级降级解析链路：
  Level 1: 标准解析（完整提取 + 编码检测）
  Level 2: 跳过 OCR 解析（仅提取原生文本，跳过 OCR 图像层）
  Level 3: 仅前 N 页（大文档截断，只解析前若干页）
  Level 4: 仅元数据（完全失败时返回文件基本信息）

集成 MemoryGuard 和 TimeoutParser，确保解析不会拖垮服务。
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from app.infrastructure.parsers.base import (
    DocumentParser, ParsedDocument, TextSegment, ParserRegistry,
)
from app.infrastructure.parsers.exceptions import (
    ParseError, CorruptedFileError, EncryptedFileError,
    FileTooLargeError, MemoryExceededError, TimeoutError,
)
from app.infrastructure.parsers.memory_guard import MemoryGuard
from app.infrastructure.parsers.timeout_parser import TimeoutParser
from app.infrastructure.parsers.validator import FileValidator, MAX_FILE_SIZE
from app.infrastructure.parsers.registry import get_parser_registry

logger = logging.getLogger(__name__)

# 降级配置
MAX_PAGES_FULL = 200        # 全量解析最大页数
MAX_PAGES_REDUCED = 50      # 降级模式最大页数
PARSE_TIMEOUT_FULL = 60.0   # 全量解析超时（秒）
PARSE_TIMEOUT_REDUCED = 15.0  # 降级解析超时（秒）
MEMORY_THRESHOLD_MB = 300.0

# 文件大小限制（阶段六暂定 100MB，设计文档值）
_VALIDATE_MAX_SIZE = MAX_FILE_SIZE


class ParsePipeline:
    """
    多级降级解析流水线。

    用法:
        pipeline = ParsePipeline()
        doc = await pipeline.parse(file_path, file_type="pdf")
        if doc.level < 4:
            # 解析成功（可能部分降级）
            print(doc.text)
        else:
            # 完全失败，仅元数据
            print(f"解析失败: {doc.error}")
    """

    def __init__(self,
                 max_full_pages: int = MAX_PAGES_FULL,
                 max_reduced_pages: int = MAX_PAGES_REDUCED,
                 timeout_full: float = PARSE_TIMEOUT_FULL,
                 timeout_reduced: float = PARSE_TIMEOUT_REDUCED,
                 memory_threshold_mb: float = MEMORY_THRESHOLD_MB):
        self._max_full_pages = max_full_pages
        self._max_reduced_pages = max_reduced_pages
        self._timeout_full = timeout_full
        self._timeout_reduced = timeout_reduced
        self._memory_threshold_mb = memory_threshold_mb

    async def parse(self,
                    file_path: str,
                    file_type: str | None = None,
                    **kwargs) -> ParsedDocument:
        """
        执行多级降级解析。

        Args:
            file_path: 文件路径
            file_type: 文件类型（如 pdf, docx），None 则从文件名推断

        Returns:
            ParsedDocument: 解析结果，level 字段标记降级程度
        """
        t_start = time.time()
        file_size = _safe_size(file_path)

        # 推断文件类型
        if not file_type:
            file_type = _infer_file_type(file_path)

        # Step 0: 大小校验
        if file_size > _VALIDATE_MAX_SIZE:
            elapsed = (time.time() - t_start) * 1000
            logger.warning(
                "File too large: %s %.1fMB > limit %.1fMB",
                file_path, file_size / 1024 / 1024, _VALIDATE_MAX_SIZE / 1024 / 1024,
            )
            return _make_error_doc(
                file_size=file_size, file_type=file_type,
                parse_method="rejected", elapsed_ms=elapsed,
                error=f"文件过大 ({file_size / 1024 / 1024:.1f}MB)，超过限制",
                level=4,
            )

        # Step 1: 格式校验
        valid, err_msg = FileValidator.validate(file_path, file_type)
        if not valid:
            elapsed = (time.time() - t_start) * 1000
            logger.warning("File validation failed: %s type=%s err=%s", file_path, file_type, err_msg)
            error = f"文件校验失败: {err_msg}"
            # 判断是否为损坏/加密文件
            if "损坏" in str(err_msg) or "不匹配" in str(err_msg):
                error = f"文件已损坏或格式与扩展名不匹配: {err_msg}"
            return _make_error_doc(
                file_size=file_size, file_type=file_type,
                parse_method="rejected", elapsed_ms=elapsed,
                error=error, level=4,
            )

        # Step 2: 获取解析器
        registry = get_parser_registry()
        parser = registry.get(file_type)

        if not parser:
            # 无解析器 → 纯文本降级
            doc = await self._text_fallback(file_path, file_size, file_type)
            setattr(doc, "level", 2)
            return doc

        # Level 1: 标准解析（带超时 + 内存监控）
        doc = await self._try_level1(parser, file_path, file_size, file_type)
        if doc.parse_method not in ("timeout", "failed", "memory_exceeded"):
            setattr(doc, "level", 1)
            return doc

        logger.warning(
            "Level 1 parse failed (%s), degrading to Level 2: file=%s",
            doc.parse_method, file_path,
        )

        # Level 2: 跳过 OCR，仅前 N 页
        doc = await self._try_level2(parser, file_path, file_size, file_type)
        if doc.parse_method not in ("timeout", "failed", "memory_exceeded"):
            setattr(doc, "level", 2)
            return doc

        logger.warning(
            "Level 2 parse failed (%s), degrading to Level 3: file=%s",
            doc.parse_method, file_path,
        )

        # Level 3: 仅前 N 页（更少页数）
        doc = await self._try_level3(parser, file_path, file_size, file_type)
        if doc.parse_method not in ("timeout", "failed", "memory_exceeded"):
            setattr(doc, "level", 3)
            return doc

        logger.warning(
            "Level 3 parse failed (%s), degrading to Level 4 (metadata only): file=%s",
            doc.parse_method, file_path,
        )

        # Level 4: 仅元数据
        elapsed = (time.time() - t_start) * 1000
        return _make_error_doc(
            file_size=file_size, file_type=file_type,
            parse_method="failed", elapsed_ms=elapsed,
            error=f"所有解析方式均失败，无法提取内容（{doc.error}）",
            level=4,
        )

    # ---------------------------------------------------------------
    # Level 1: 标准解析
    # ---------------------------------------------------------------
    async def _try_level1(self,
                          parser: DocumentParser,
                          file_path: str,
                          file_size: int,
                          file_type: str) -> ParsedDocument:
        """标准解析：完整提取，带超时 + 内存监控"""
        timeout_parser = TimeoutParser(parser, timeout=self._timeout_full)
        memory_guard = MemoryGuard(threshold_mb=self._memory_threshold_mb)

        memory_guard.start()
        try:
            doc = await timeout_parser.parse(
                file_path, max_pages=self._max_full_pages,
            )
        finally:
            memory_guard.stop()

        if memory_guard.exceeded:
            doc.parse_method = "memory_exceeded"
            doc.error = f"Level 1 内存超限 ({memory_guard.peak_mb:.0f}MB)"

        return doc

    # ---------------------------------------------------------------
    # Level 2: 跳过 OCR（仅原生文本）
    # ---------------------------------------------------------------
    async def _try_level2(self,
                          parser: DocumentParser,
                          file_path: str,
                          file_size: int,
                          file_type: str) -> ParsedDocument:
        """跳过 OCR 解析，仅提取原生文本，减少页数"""
        timeout_parser = TimeoutParser(parser, timeout=self._timeout_reduced)
        memory_guard = MemoryGuard(threshold_mb=self._memory_threshold_mb)

        memory_guard.start()
        try:
            doc = await timeout_parser.parse(
                file_path,
                max_pages=self._max_reduced_pages,
                skip_ocr=True,
            )
        finally:
            memory_guard.stop()

        if memory_guard.exceeded:
            doc.parse_method = "memory_exceeded"
            doc.error = f"Level 2 内存超限 ({memory_guard.peak_mb:.0f}MB)"

        return doc

    # ---------------------------------------------------------------
    # Level 3: 仅前 N 页（更少）
    # ---------------------------------------------------------------
    async def _try_level3(self,
                          parser: DocumentParser,
                          file_path: str,
                          file_size: int,
                          file_type: str) -> ParsedDocument:
        """仅解析前 10 页，快速返回"""
        timeout_parser = TimeoutParser(parser, timeout=self._timeout_reduced)
        memory_guard = MemoryGuard(threshold_mb=self._memory_threshold_mb)

        memory_guard.start()
        try:
            doc = await timeout_parser.parse(
                file_path,
                max_pages=10,
                skip_ocr=True,
            )
        finally:
            memory_guard.stop()

        if memory_guard.exceeded:
            doc.parse_method = "memory_exceeded"
            doc.error = f"Level 3 内存超限 ({memory_guard.peak_mb:.0f}MB)"

        return doc

    # ---------------------------------------------------------------
    # 纯文本回退
    # ---------------------------------------------------------------
    async def _text_fallback(self,
                             file_path: str,
                             file_size: int,
                             file_type: str) -> ParsedDocument:
        """无解析器时，以纯文本方式读取"""
        from app.infrastructure.parsers.encoding_detector import EncodingDetector
        t0 = time.time()
        try:
            text, encoding = EncodingDetector.read_text(file_path)
            elapsed = (time.time() - t0) * 1000
            return ParsedDocument(
                text=text,
                segments=[TextSegment(text=text[:500])],
                page_count=0,
                encoding=encoding,
                parse_method="txt-fallback",
                parse_duration_ms=elapsed,
                file_size=file_size,
                file_type=file_type,
            )
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            return _make_error_doc(
                file_size=file_size, file_type=file_type,
                parse_method="failed", elapsed_ms=elapsed,
                error=f"纯文本回退也失败: {e}", level=4,
            )


# ---------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------
def _safe_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _infer_file_type(file_path: str) -> str:
    if "." in file_path:
        return file_path.rsplit(".", 1)[-1].lower()
    return "txt"


def _make_error_doc(*,
                    file_size: int,
                    file_type: str,
                    parse_method: str,
                    elapsed_ms: float,
                    error: str,
                    level: int = 4) -> ParsedDocument:
    """构建错误文档对象"""
    doc = ParsedDocument(
        text="",
        segments=[],
        page_count=0,
        encoding="unknown",
        parse_method=parse_method,
        parse_duration_ms=elapsed_ms,
        file_size=file_size,
        file_type=file_type,
        error=error,
    )
    setattr(doc, "level", level)
    return doc