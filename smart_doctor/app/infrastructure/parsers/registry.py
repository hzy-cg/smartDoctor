"""
解析器注册表工厂（v2.1）

统一注册所有解析器，提供唯一的 get_parser() 入口。
"""
from __future__ import annotations

from app.infrastructure.parsers.base import ParserRegistry
from app.infrastructure.parsers.txt_parser import TxtParser
from app.infrastructure.parsers.pdf_parser import PdfParser
from app.infrastructure.parsers.docx_parser import DocxParser
from app.infrastructure.parsers.pptx_parser import PptxParser
from app.infrastructure.parsers.xlsx_parser import XlsxParser

_registry: ParserRegistry | None = None


def get_parser_registry() -> ParserRegistry:
    """懒加载单例 ParserRegistry"""
    global _registry
    if _registry is None:
        _registry = ParserRegistry()
        _registry.register(TxtParser())
        _registry.register(PdfParser())
        _registry.register(DocxParser())
        _registry.register(PptxParser())
        _registry.register(XlsxParser())
    return _registry
