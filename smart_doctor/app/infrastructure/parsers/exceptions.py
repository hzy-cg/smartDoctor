"""
解析异常分类（v2.2 新增）

定义统一的解析异常体系，便于上层统一处理降级逻辑。
"""
from __future__ import annotations


class ParseError(Exception):
    """解析异常基类"""

    def __init__(self, message: str, file_path: str = "", file_type: str = ""):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.file_type = file_type


class FormatUnknownError(ParseError):
    """无法识别的文件格式"""

    def __init__(self, file_path: str = "", file_type: str = ""):
        super().__init__(
            f"无法识别的文件格式: {file_type}" if file_type else "无法识别的文件格式",
            file_path, file_type,
        )


class EncodingError(ParseError):
    """编码检测失败 / 解码异常"""

    def __init__(self,
                 message: str = "编码检测失败，无法解码文件内容",
                 file_path: str = "",
                 detected_encoding: str = ""):
        super().__init__(message, file_path)
        self.detected_encoding = detected_encoding


class CorruptedFileError(ParseError):
    """文件损坏（Magic Bytes 不匹配 / 结构异常）"""

    def __init__(self,
                 message: str = "文件已损坏或格式与扩展名不匹配",
                 file_path: str = "",
                 file_type: str = ""):
        super().__init__(message, file_path, file_type)


class EncryptedFileError(ParseError):
    """加密文件（如加密 PDF / 密码保护的 Office 文档）"""

    def __init__(self,
                 message: str = "文件已加密，无法解析",
                 file_path: str = "",
                 file_type: str = ""):
        super().__init__(message, file_path, file_type)


class FileTooLargeError(ParseError):
    """文件超过大小限制"""

    def __init__(self,
                 file_size: int = 0,
                 max_size: int = 0,
                 file_path: str = ""):
        msg = f"文件过大 ({file_size / 1024 / 1024:.1f}MB)"
        if max_size:
            msg += f"，超过限制 {max_size / 1024 / 1024:.1f}MB"
        super().__init__(msg, file_path)


class TimeoutError(ParseError):
    """解析超时"""

    def __init__(self,
                 timeout_seconds: float = 0,
                 partial_text: str = "",
                 file_path: str = ""):
        super().__init__(
            f"解析超时 ({timeout_seconds:.0f}s)，已返回部分结果", file_path,
        )
        self.timeout_seconds = timeout_seconds
        self.partial_text = partial_text  # 超时前的部分结果


class MemoryExceededError(ParseError):
    """内存超限"""

    def __init__(self,
                 current_mb: float = 0,
                 threshold_mb: float = 0,
                 file_path: str = ""):
        super().__init__(
            f"解析占用内存过高 ({current_mb:.0f}MB / {threshold_mb:.0f}MB)，已降级处理",
            file_path,
        )
        self.current_mb = current_mb
        self.threshold_mb = threshold_mb