"""
阶段六性能压测脚本（v2.2）

测试场景:
  1. 大文件上传（50MB 模拟）
  2. 多文件并发上传
  3. 大文档解析（PDF 100+ 页）
  4. 临时文件清理

使用方式:
  python tests/perf_test_upload.py
"""
import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.infrastructure.parsers.parse_pipeline import ParsePipeline
from app.infrastructure.parsers.memory_guard import MemoryGuard
from app.infrastructure.parsers.validator import FileValidator


def generate_large_text(mb: int) -> str:
    """生成指定大小的测试文本"""
    paragraph = "这是一段测试文本，用于模拟文档内容。" * 100
    target_bytes = mb * 1024 * 1024
    result = ""
    while len(result.encode("utf-8")) < target_bytes:
        result += paragraph
    return result


def create_test_file(content: str, name: str = "test.txt") -> str:
    """创建测试文件，返回路径"""
    tmp_dir = Path(__file__).resolve().parent.parent.parent / "data" / "test_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / name
    path.write_text(content, encoding="utf-8")
    return str(path)


async def test_large_file_upload():
    """测试 1: 50MB 文件上传性能"""
    print("=" * 60)
    print("测试 1: 大文件上传（50MB 模拟）")
    print("=" * 60)

    content = generate_large_text(50)
    file_path = create_test_file(content, f"perf_50mb_{uuid.uuid4().hex[:8]}.txt")

    # 验证文件大小
    actual_size = os.path.getsize(file_path)
    print(f"  文件大小: {actual_size / 1024 / 1024:.1f}MB")
    print(f"  文件路径: {file_path}")

    # 校验
    valid, err = FileValidator.validate(file_path, "txt")
    print(f"  格式校验: {'通过' if valid else f'失败: {err}'}")

    if not valid:
        return

    # 解析
    pipeline = ParsePipeline()
    t0 = time.time()
    doc = await pipeline.parse(file_path, file_type="txt")
    elapsed = time.time() - t0

    level = getattr(doc, "level", 1)
    text_len = len(doc.text)

    print(f"  解析耗时: {elapsed:.2f}s")
    print(f"  解析方法: {doc.parse_method}")
    print(f"  降级级别: {level}")
    print(f"  提取文本: {text_len} 字符")
    print(f"  解析错误: {doc.error or '无'}")
    print(f"  吞吐量: {(actual_size / 1024 / 1024) / elapsed:.1f} MB/s")

    # 清理
    os.remove(file_path)
    return elapsed, text_len, level


async def test_large_pdf_parse():
    """测试 2: 尝试解析大 PDF（如果存在）"""
    print("\n" + "=" * 60)
    print("测试 2: 大 PDF 解析（100+ 页）")
    print("=" * 60)

    # 尝试查找测试 PDF
    test_pdfs = list(Path(__file__).resolve().parent.parent.parent.glob("data/**/*.pdf"))
    if not test_pdfs:
        test_pdfs = list(Path(__file__).resolve().parent.parent.parent.glob("**/*.pdf"))

    if not test_pdfs:
        print("  未找到 PDF 测试文件，跳过")
        return

    pdf_path = str(test_pdfs[0])
    print(f"  测试文件: {pdf_path}")
    file_size = os.path.getsize(pdf_path)
    print(f"  文件大小: {file_size / 1024 / 1024:.1f}MB")

    pipeline = ParsePipeline()
    t0 = time.time()
    doc = await pipeline.parse(pdf_path, file_type="pdf")
    elapsed = time.time() - t0

    level = getattr(doc, "level", 1)
    print(f"  解析耗时: {elapsed:.2f}s")
    print(f"  解析方法: {doc.parse_method}")
    print(f"  降级级别: {level}")
    print(f"  页数: {doc.page_count}")
    print(f"  提取文本: {len(doc.text)} 字符")
    print(f"  解析错误: {doc.error or '无'}")
    return elapsed, doc.page_count, level


async def test_concurrent_uploads():
    """测试 3: 多文件并发上传"""
    print("\n" + "=" * 60)
    print("测试 3: 多文件并发上传（3 个文件）")
    print("=" * 60)

    files = [
        ("perf_concurrent_a.txt", generate_large_text(5)),
        ("perf_concurrent_b.txt", generate_large_text(5)),
        ("perf_concurrent_c.txt", generate_large_text(5)),
    ]

    paths = []
    for name, content in files:
        path = create_test_file(content, name)
        paths.append(path)
        print(f"  创建文件: {name} ({os.path.getsize(path) / 1024 / 1024:.1f}MB)")

    pipeline = ParsePipeline()
    t0 = time.time()
    tasks = [pipeline.parse(p, file_type="txt") for p in paths]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t0

    for i, doc in enumerate(results):
        level = getattr(doc, "level", 1)
        print(f"  文件 {i + 1}: 耗时 {doc.parse_duration_ms:.0f}ms, "
              f"级别 {level}, 字符 {len(doc.text)}, "
              f"错误: {doc.error or '无'}")

    print(f"  总耗时: {elapsed:.2f}s")
    print(f"  平均耗时: {elapsed / len(files):.2f}s/文件")

    for p in paths:
        os.remove(p)
    return elapsed, len(files)


async def test_memory_usage():
    """测试 4: 内存监控"""
    print("\n" + "=" * 60)
    print("测试 4: 内存监控（MemoryGuard）")
    print("=" * 60)

    content = generate_large_text(10)
    file_path = create_test_file(content, f"perf_mem_{uuid.uuid4().hex[:8]}.txt")

    pipeline = ParsePipeline()
    guard = MemoryGuard(threshold_mb=100)

    guard.start()
    t0 = time.time()
    doc = await pipeline.parse(file_path, file_type="txt")
    elapsed = time.time() - t0
    guard.stop()

    print(f"  解析耗时: {elapsed:.2f}s")
    print(f"  内存峰值: {guard.peak_mb:.0f}MB")
    print(f"  内存超限: {'是' if guard.exceeded else '否'}")
    print(f"  阈值: {100}MB")

    os.remove(file_path)
    return guard.peak_mb, guard.exceeded


async def main():
    print("SmartDoctor 知识库系统性能压测")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print()

    results = {}

    # 测试 1: 大文件上传
    r = await test_large_file_upload()
    if r:
        results["50MB上传"] = {
            "耗时(s)": round(r[0], 2),
            "提取字符": r[1],
            "降级级别": r[2],
        }

    # 测试 2: PDF 解析
    r = await test_large_pdf_parse()
    if r:
        results["PDF解析"] = {
            "耗时(s)": round(r[0], 2),
            "页数": r[1],
            "降级级别": r[2],
        }

    # 测试 3: 并发上传
    r = await test_concurrent_uploads()
    if r:
        results["并发上传"] = {
            "总耗时(s)": round(r[0], 2),
            "文件数": r[1],
            "平均耗时(s)": round(r[0] / r[1], 2),
        }

    # 测试 4: 内存监控
    r = await test_memory_usage()
    if r:
        results["内存监控"] = {
            "峰值(MB)": round(r[0], 0),
            "超限": r[1],
        }

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, metrics in results.items():
        print(f"  {name}:")
        for k, v in metrics.items():
            print(f"    {k}: {v}")

    # 验收标准检查
    print("\n验收标准检查:")
    if "50MB上传" in results:
        t = results["50MB上传"]["耗时(s)"]
        ok = t < 30
        print(f"  {('通过' if ok else '失败')} - 50MB 上传耗时 {t:.1f}s {'< 30s' if ok else '>= 30s'}")

    if "并发上传" in results:
        t = results["并发上传"]["总耗时(s)"]
        print(f"  并发上传总耗时: {t:.1f}s")

    if "内存监控" in results:
        peak = results["内存监控"]["峰值(MB)"]
        exceeded = results["内存监控"]["超限"]
        print(f"  内存峰值: {peak:.0f}MB {'(超限)' if exceeded else '(正常)'}")

    print("\n压测完成!")


if __name__ == "__main__":
    asyncio.run(main())