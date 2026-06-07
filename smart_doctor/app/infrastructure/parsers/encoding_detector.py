"""
编码检测器（v2.1）

检测顺序: BOM → chardet → 启发式逐尝试 → 回退 Latin-1
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# BOM (Byte Order Mark) 映射
BOM_MAP: dict[bytes, str] = {
    b"\xef\xbb\xbf": "utf-8-sig",
    b"\xff\xfe": "utf-16-le",
    b"\xfe\xff": "utf-16-be",
    b"\xff\xfe\x00\x00": "utf-32-le",
    b"\x00\x00\xfe\xff": "utf-32-be",
}

# 常见候选编码，按优先级排列
_CANDIDATE_ENCODINGS = [
    "utf-8", "gbk", "gb18030", "gb2312",
    "big5", "shift_jis", "euc-jp",
    "latin-1", "cp1252", "iso-8859-1",
]


class EncodingDetector:
    """自动编码检测器"""

    @staticmethod
    def detect(file_path: str) -> str:
        """
        检测文件编码。

        Returns:
            编码名称（如 utf-8, gbk）
        """
        # Step 1: 读取文件头检测 BOM
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
        except OSError:
            logger.warning("Cannot read file for encoding detection: %s", file_path)
            return "utf-8"

        for bom, enc in BOM_MAP.items():
            if header.startswith(bom):
                logger.debug("Encoding detected by BOM: %s", enc)
                return enc

        # Step 2: chardet 检测
        try:
            import chardet
            with open(file_path, "rb") as f:
                raw = f.read(100 * 1024)  # 前 100KB 足够
            result = chardet.detect(raw)
            enc = result.get("encoding", "")
            confidence = result.get("confidence", 0)
            if enc and confidence > 0.5:
                # 标准化编码名
                enc = _normalize_encoding(enc)
                logger.debug("chardet detected: %s (confidence=%.2f)", enc, confidence)
                return enc
        except ImportError:
            logger.debug("chardet not installed, using heuristic detection")
        except Exception:
            logger.debug("chardet failed, falling back to heuristics")

        # Step 3: 启发式逐尝试
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
        except OSError:
            return "utf-8"

        for enc in _CANDIDATE_ENCODINGS:
            try:
                raw.decode(enc)
                logger.debug("Heuristic encoding matched: %s", enc)
                return enc
            except (UnicodeDecodeError, LookupError):
                continue

        # Step 4: 回退
        logger.warning("Could not detect encoding, falling back to latin-1")
        return "latin-1"

    @staticmethod
    def read_text(file_path: str, encoding: str | None = None) -> tuple[str, str]:
        """
        读取文件文本内容，自动检测编码。

        Returns:
            (text_content, detected_encoding)
        """
        enc = encoding or EncodingDetector.detect(file_path)
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                return f.read(), enc
        except Exception:
            # 最终回退
            logger.warning("Read failed with %s, falling back to latin-1", enc)
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                return f.read(), "latin-1"


def _normalize_encoding(raw: str) -> str:
    """标准化编码名称"""
    raw = raw.lower().replace("-", "").replace("_", "")
    norm_map = {
        "gb2312": "gbk",
        "gbk": "gbk",
        "gb18030": "gb18030",
        "utf8": "utf-8",
        "utf16": "utf-16",
        "big5": "big5",
        "shiftjis": "shift_jis",
        "iso88591": "latin-1",
        "cp936": "gbk",
        "cp1252": "cp1252",
        "eucjp": "euc-jp",
    }
    return norm_map.get(raw, raw)
