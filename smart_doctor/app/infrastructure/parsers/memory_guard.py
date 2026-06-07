"""
内存守卫（v2.2 新增）

解析过程中监控内存使用，超阈值时自动触发降级。
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

# 默认内存阈值：300MB
DEFAULT_MEMORY_THRESHOLD_MB = 300

# 监控间隔（秒）
_MONITOR_INTERVAL = 0.5


class MemoryGuard:
    """
    解析过程内存监控器。

    用法:
        guard = MemoryGuard(threshold_mb=300)
        with guard:
            result = heavy_parsing()
        if guard.exceeded:
            # 降级处理
            ...

    或手动模式:
        guard = MemoryGuard(threshold_mb=300)
        guard.start()
        try:
            result = heavy_parsing()
        finally:
            guard.stop()
    """

    def __init__(self, threshold_mb: float = DEFAULT_MEMORY_THRESHOLD_MB):
        self._threshold_mb = threshold_mb
        self._exceeded = False
        self._peak_mb = 0.0
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pid = os.getpid()

    @property
    def exceeded(self) -> bool:
        return self._exceeded

    @property
    def peak_mb(self) -> float:
        return self._peak_mb

    def start(self) -> None:
        """启动后台内存监控"""
        self._exceeded = False
        self._peak_mb = 0.0
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """停止监控"""
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                current_mb = self._get_current_memory_mb()
                if current_mb > self._peak_mb:
                    self._peak_mb = current_mb
                if current_mb > self._threshold_mb:
                    self._exceeded = True
                    logger.warning(
                        "Memory guard triggered: %.0fMB > %.0fMB threshold",
                        current_mb, self._threshold_mb,
                    )
            except Exception:
                pass
            self._stop_event.wait(_MONITOR_INTERVAL)

    def _get_current_memory_mb(self) -> float:
        """获取当前进程内存使用量（MB），平台无关"""
        try:
            import psutil
            proc = psutil.Process(self._pid)
            mem_info = proc.memory_info()
            return mem_info.rss / (1024 * 1024)
        except ImportError:
            # psutil 不可用，使用 /proc 或回退
            pass
        except Exception:
            pass

        # Windows: 使用 GetProcessMemoryInfo 回退方案
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400 | 0x0010, False, self._pid)
            if handle:
                counters = PROCESS_MEMORY_COUNTERS()
                if kernel32.GetProcessMemoryInfo(
                    handle, ctypes.byref(counters), ctypes.sizeof(counters),
                ):
                    kernel32.CloseHandle(handle)
                    return counters.WorkingSetSize / (1024 * 1024)
                kernel32.CloseHandle(handle)
        except Exception:
            pass

        # 最终回退：返回 0
        return 0.0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        return False  # 不吞异常