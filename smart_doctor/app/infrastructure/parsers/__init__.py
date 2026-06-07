"""
文档解析器模块（v2.2）

支持格式: TXT, MD, PDF, DOCX, PPTX, XLSX
解析流程: 编码检测 → 内容提取 → 统一输出 ParsedDocument

v2.2 新增:
  - ParsePipeline: 多级降级解析链路
  - MemoryGuard: 解析过程内存监控
  - TimeoutParser: 解析超时控制
  - 异常分类: FormatUnknownError / EncodingError / CorruptedFileError / EncryptedFileError
"""
from app.infrastructure.parsers.base import DocumentParser, ParsedDocument, TextSegment, ParserRegistry
from app.infrastructure.parsers.validator import FileValidator
from app.infrastructure.parsers.encoding_detector import EncodingDetector
from app.infrastructure.parsers.parse_pipeline import ParsePipeline
from app.infrastructure.parsers.memory_guard import MemoryGuard
from app.infrastructure.parsers.timeout_parser import TimeoutParser
from app.infrastructure.parsers.exceptions import (
    ParseError, FormatUnknownError, EncodingError,
    CorruptedFileError, EncryptedFileError,
    FileTooLargeError, TimeoutError as ParseTimeoutError,
    MemoryExceededError,
)

__all__ = [
    "DocumentParser", "ParsedDocument", "TextSegment", "ParserRegistry",
    "FileValidator", "EncodingDetector",
    "ParsePipeline", "MemoryGuard", "TimeoutParser",
    "ParseError", "FormatUnknownError", "EncodingError",
    "CorruptedFileError", "EncryptedFileError",
    "FileTooLargeError", "ParseTimeoutError", "MemoryExceededError",
]
