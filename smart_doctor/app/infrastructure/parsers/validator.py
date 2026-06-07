"""
文件格式校验器（v2.1）

- Magic Bytes 校验（防伪造扩展名）
- 文件大小限制（最大 100MB）
- 扩展名白名单
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Magic Bytes 签名映射
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04"],  # Office Open XML
    "pptx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
    "doc": [b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"],  # OLE2
    "xls": [b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"],
    "txt": [],   # 无固定签名
    "md": [],
}

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    "txt", "md", "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class FileValidator:
    """文件格式校验器"""

    @staticmethod
    def validate(file_path: str, file_type: str) -> tuple[bool, str | None]:
        """
        校验文件。

        Returns:
            (is_valid, error_message)
        """
        # 1. 扩展名白名单
        ft = file_type.lower().lstrip(".")
        if ft not in ALLOWED_EXTENSIONS:
            return False, f"不支持的文件类型: {ft}"

        # 2. 文件大小检查
        import os
        try:
            size = os.path.getsize(file_path)
        except OSError:
            return False, "无法读取文件"

        if size > MAX_FILE_SIZE:
            return False, f"文件大小 {size / 1024 / 1024:.1f}MB 超过限制 (100MB)"

        if size == 0:
            return False, "文件为空"

        # 3. Magic Bytes 校验（文本文件跳过）
        signatures = MAGIC_SIGNATURES.get(ft)
        if signatures:  # 有定义的才校验
            try:
                with open(file_path, "rb") as f:
                    header = f.read(8)
            except OSError:
                return False, "无法读取文件头"

            matched = any(header.startswith(sig) for sig in signatures)
            if not matched:
                logger.warning(
                    "Magic bytes mismatch: type=%s expected=%s got=%s",
                    ft, signatures, header[:8].hex(),
                )
                return False, f"文件头与扩展名 {ft} 不匹配，文件可能已损坏"

        return True, None

    @staticmethod
    def is_text_type(file_type: str) -> bool:
        """判断是否为纯文本类型"""
        return file_type.lower() in ("txt", "md", "csv")
