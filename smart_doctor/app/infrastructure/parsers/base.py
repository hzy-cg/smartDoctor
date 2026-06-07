"""
文档解析器抽象基类与统一输出结构（v2.1）
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class TextSegment:
    """文本片段，带置信度标注"""
    text: str
    page: int | None = None        # 页码（PDF/PPT）
    slide: int | None = None       # 幻灯片编号（PPT）
    row: int | None = None         # 表格行号（Excel）
    sheet: str | None = None       # 工作表名（Excel）
    heading: str | None = None     # 最近的标题
    confidence: float = 1.0        # 提取置信度 0.0-1.0
    timestamp_start: float | None = None  # 音频起始秒数（预留）
    timestamp_end: float | None = None


@dataclass
class ParsedDocument:
    """统一解析输出结构"""
    text: str                                      # 提取的纯文本
    segments: list[TextSegment] = field(default_factory=list)
    page_count: int = 0                            # 总页数（PDF/PPT）
    sheet_count: int = 0                           # 工作表数（Excel）
    encoding: str = "utf-8"                        # 检测到的编码
    parse_method: str = "unknown"                  # 解析方法名
    parse_duration_ms: float = 0.0                 # 解析耗时（毫秒）
    file_size: int = 0                             # 原始文件大小（字节）
    file_type: str = "unknown"                     # 文件类型
    error: str | None = None                       # 部分失败时的错误信息


class DocumentParser(ABC):
    """文档解析器抽象基类"""

    # 子类需设置的类属性
    supported_types: ClassVar[set[str]] = set()

    @abstractmethod
    async def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        """解析文档，返回统一结构"""
        ...

    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() in self.supported_types


class ParserRegistry:
    """解析器注册表 — 按文件类型分发"""

    def __init__(self):
        self._parsers: dict[str, DocumentParser] = {}

    def register(self, parser: DocumentParser) -> None:
        for ft in parser.supported_types:
            self._parsers[ft.lower()] = parser
            logger.debug("Registered parser for '%s': %s", ft, type(parser).__name__)

    def get(self, file_type: str) -> DocumentParser | None:
        return self._parsers.get(file_type.lower())

    def has(self, file_type: str) -> bool:
        return file_type.lower() in self._parsers

    @property
    def supported_types(self) -> set[str]:
        return set(self._parsers.keys())
