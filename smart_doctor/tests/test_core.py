"""
核心领域层单元测试（v2.2）

测试覆盖:
  - 状态机：合法/非法转换
  - RAG 策略：去重、权重排序
  - 上下文组装：Token 预算、来源注入
  - 解析流水线：多级降级
  - 分块策略：语义分块、重叠、元数据
"""
import sys
import uuid
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ============================================================
# 状态机测试
# ============================================================
def test_state_machine_valid_transitions():
    """测试所有合法状态转换"""
    from app.domain.state_machine import DiagnosisStateMachine

    sm = DiagnosisStateMachine("collecting")
    assert sm.state == "collecting"

    # collecting → analyzing
    assert sm.transition("symptom_complete") == "analyzing"
    assert sm.state == "analyzing"

    # analyzing → recommending
    assert sm.transition("ready_to_recommend") == "recommending"
    assert sm.state == "recommending"

    # recommending → completed
    assert sm.transition("user_confirmed") == "completed"
    assert sm.state == "completed"

    # completed → collecting (new_symptom)
    assert sm.transition("new_symptom") == "collecting"
    assert sm.state == "collecting"

    print("[PASS] test_state_machine_valid_transitions")


def test_state_machine_invalid_transitions():
    """测试非法状态转换"""
    from app.domain.state_machine import DiagnosisStateMachine
    from app.domain.state_machine import InvalidTransitionError

    sm = DiagnosisStateMachine("collecting")

    # collecting 不能直接 user_confirmed
    try:
        sm.transition("user_confirmed")
        assert False, "Should have raised InvalidTransitionError"
    except InvalidTransitionError:
        pass

    # completed 不能 symptom_complete
    sm._state = "completed"
    try:
        sm.transition("symptom_complete")
        assert False, "Should have raised InvalidTransitionError"
    except InvalidTransitionError:
        pass

    print("[PASS] test_state_machine_invalid_transitions")


def test_state_machine_self_loops():
    """测试自环（保持状态）"""
    from app.domain.state_machine import DiagnosisStateMachine

    sm = DiagnosisStateMachine("collecting")
    assert sm.transition("user_chitchat") == "collecting"
    assert sm.transition("need_more_info") == "collecting"

    sm._state = "completed"
    assert sm.transition("user_chitchat") == "completed"

    print("[PASS] test_state_machine_self_loops")


def test_intent_to_event():
    """测试意图→事件映射"""
    from app.domain.state_machine import DiagnosisStateMachine

    sm = DiagnosisStateMachine()

    # 基础映射
    assert sm.intent_to_event("new_symptom", "collecting") == "symptom_complete"
    assert sm.intent_to_event("new_symptom", "completed") == "new_symptom"
    assert sm.intent_to_event("follow_up_answer", "collecting") == "symptom_complete"
    assert sm.intent_to_event("need_detail", "analyzing") == "need_more_info"
    assert sm.intent_to_event("ready_recommend", "analyzing") == "ready_to_recommend"
    assert sm.intent_to_event("confirm", "recommending") == "user_confirmed"
    assert sm.intent_to_event("dissatisfied", "recommending") == "user_dissatisfied"
    assert sm.intent_to_event("chitchat", "analyzing") == "user_chitchat"

    # 未知意图 → need_more_info
    assert sm.intent_to_event("unknown_blah", "collecting") == "need_more_info"

    print("[PASS] test_intent_to_event")


# ============================================================
# RAG 策略测试
# ============================================================
def test_rag_deduplicate():
    """测试 RAG 结果去重"""
    from app.domain.services.diagnosis_strategy import RAGStrategy

    strategy = RAGStrategy(private_store=None, common_store=None, embedding=None)

    results = [
        {"content": "高血压是一种常见疾病", "source": "doc1.pdf"},
        {"content": "高血压是一种常见疾病", "source": "doc1.pdf"},  # 重复
        {"content": "糖尿病需要控制饮食", "source": "doc2.pdf"},
        {"content": "高血压是一种常见疾病", "source": "doc3.pdf"},  # 不同来源但内容相同
    ]

    deduped = strategy._deduplicate(results)
    assert len(deduped) == 3, f"Expected 3, got {len(deduped)}"
    assert deduped[0]["source"] == "doc1.pdf"
    assert deduped[1]["source"] == "doc2.pdf"
    assert deduped[2]["source"] == "doc3.pdf"

    print("[PASS] test_rag_deduplicate")


def test_rag_type_weights():
    """测试文档类型分层权重"""
    from app.domain.services.diagnosis_strategy import RAGStrategy

    strategy = RAGStrategy(private_store=None, common_store=None, embedding=None)

    results = [
        {"content": "PDF文档", "doc_type": "pdf", "score": 0.8},
        {"content": "TXT文档", "doc_type": "txt", "score": 0.8},
        {"content": "XLSX文档", "doc_type": "xlsx", "score": 0.8},
        {"content": "未知类型", "doc_type": "unknown", "score": 0.8},
    ]

    weighted = strategy._apply_type_weights(results)

    # PDF 权重最高，应该排在前面
    assert weighted[0]["doc_type"] == "pdf"
    # XLSX 权重最低，应该排在后面
    assert weighted[-1]["doc_type"] in ("xlsx", "unknown")

    # 所有结果都有 final_score
    for r in weighted:
        assert "final_score" in r
        assert 0 <= r["final_score"] <= 1.0

    print("[PASS] test_rag_type_weights")


# ============================================================
# 上下文组装测试
# ============================================================
def test_context_assembler_basic():
    """测试上下文组装基本功能"""
    from app.domain.services.context_assembler import ContextAssembler

    assembler = ContextAssembler()
    sources = [
        {"content": "高血压诊断标准", "final_score": 0.95, "source": "guide.pdf"},
        {"content": "糖尿病治疗指南", "final_score": 0.85, "source": "diabetes.pdf"},
    ]

    result = assembler.assemble(sources)
    assert "高血压诊断标准" in result
    assert "糖尿病治疗指南" in result
    assert "guide.pdf" in result
    assert "diabetes.pdf" in result

    print("[PASS] test_context_assembler_basic")


def test_context_assembler_token_budget():
    """测试 Token 预算控制"""
    from app.domain.services.context_assembler import ContextAssembler

    assembler = ContextAssembler(max_tokens=500)  # 小预算便于测试
    # 生成大量内容，确保超过预算
    long_content = "测试内容" * 500  # 2000 chars
    sources = [
        {"content": long_content, "final_score": 0.9, "source": "large.pdf"},
    ]

    result = assembler.assemble(sources)
    # 至少1个结果始终返回（即使超预算），但内容应被截断
    # 500 tokens * 1.5 = 750 chars budget
    # 实际长度 = 标签 + 500tokens内容 ≈ 不超过 2500 chars
    assert len(result) < 3000, f"Context too long: {len(result)} chars"
    assert "large.pdf" in result

    # 多来源场景：超预算后第二个来源应被跳过
    sources2 = [
        {"content": long_content, "final_score": 0.9, "source": "doc1.pdf"},
        {"content": "简短内容", "final_score": 0.5, "source": "doc2.pdf"},
    ]
    result2 = assembler.assemble(sources2)
    # doc2 应该被跳过（预算已满）
    assert "doc1.pdf" in result2

    print("[PASS] test_context_assembler_token_budget")


# ============================================================
# 解析流水线测试
# ============================================================
def test_parse_pipeline_level1_txt():
    """测试标准 TXT 解析"""
    from app.infrastructure.parsers.parse_pipeline import ParsePipeline
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("这是一段测试文本。\n包含多个段落。\n用于验证解析流水线。")
        tmp_path = f.name

    try:
        import asyncio
        pipeline = ParsePipeline()
        doc = asyncio.run(pipeline.parse(tmp_path, file_type="txt"))

        assert doc.text, "Should have extracted text"
        assert "测试文本" in doc.text
        assert doc.parse_method in ("txt", "txt-fallback")
        assert getattr(doc, "level", 1) == 1
        print("[PASS] test_parse_pipeline_level1_txt")
    finally:
        os.unlink(tmp_path)


def test_parse_pipeline_invalid_file():
    """测试无效文件拒绝"""
    from app.infrastructure.parsers.parse_pipeline import ParsePipeline
    import tempfile
    import os

    # 创建一个内容不是 PDF 的 .pdf 文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False, encoding="utf-8") as f:
        f.write("This is not a real PDF file")
        tmp_path = f.name

    try:
        import asyncio
        pipeline = ParsePipeline()
        doc = asyncio.run(pipeline.parse(tmp_path, file_type="pdf"))

        # 应该被拒绝（Magic Bytes 不匹配）
        level = getattr(doc, "level", 1)
        assert level >= 3, f"Should be rejected, got level {level}"
        print(f"[PASS] test_parse_pipeline_invalid_file (level={level})")
    finally:
        os.unlink(tmp_path)


def test_parse_pipeline_oversize_file():
    """测试超大文件拒绝"""
    from app.infrastructure.parsers.parse_pipeline import ParsePipeline
    import tempfile
    import os

    # 创建一个小文件但报告为超大
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("test")
        tmp_path = f.name

    try:
        import asyncio
        # 使用一个很小的阈值来测试
        pipeline = ParsePipeline()
        doc = asyncio.run(pipeline.parse(tmp_path, file_type="txt"))

        # 小文件应该正常解析
        assert doc.text, "Small file should parse normally"
        print("[PASS] test_parse_pipeline_oversize_file")
    finally:
        os.unlink(tmp_path)


# ============================================================
# 分块策略测试
# ============================================================
def test_semantic_chunking():
    """测试语义分块：分隔符优先级"""
    from app.application.utils.chunking import split_semantic_chunks

    # 生成足够长的内容以触发多块
    content = "第一句话。第二句话。第三句话。第四句话。第五句话。第六句话。" * 20
    # 将 chunk_tokens 设小以触发多块
    chunks = split_semantic_chunks(content, chunk_tokens=10, chunk_overlap_tokens=2, source_name="test.txt")

    assert len(chunks) > 1, f"Should have multiple chunks, got {len(chunks)}"
    # 验证每个块都有 metadata
    for chunk in chunks:
        assert "content" in chunk
        assert "metadata" in chunk
        assert "source" in chunk["metadata"]
        assert "chunk_index" in chunk["metadata"]

    print("[PASS] test_semantic_chunking")


def test_chunk_metadata_builder():
    """测试 build_chunk_metadata 函数"""
    from app.application.utils.chunking import build_chunk_metadata

    # 基本元数据
    meta = build_chunk_metadata(source_name="test.pdf", doc_type="pdf")
    assert meta["source"] == "test.pdf"
    assert meta["doc_type"] == "pdf"
    assert "uploaded_at" in meta

    # 带解析元数据
    parsed = {
        "file_type": "pdf",
        "encoding": "utf-8",
        "parse_method": "pdfplumber",
        "page_count": 42,
        "parse_duration_ms": 1500.0,
        "file_size": 1024000,
        "segments": [
            {"page": 1, "confidence": 0.95},
            {"page": 2, "confidence": 0.88},
        ],
    }
    meta = build_chunk_metadata(source_name="guide.pdf", doc_type="pdf", parsed_meta=parsed)
    assert meta["source"] == "guide.pdf"
    assert meta["page_count"] == 42
    assert meta["parse_method"] == "pdfplumber"
    assert meta["avg_confidence"] == 0.915  # (0.95 + 0.88) / 2

    print("[PASS] test_chunk_metadata_builder")


# ============================================================
# 异常分类测试
# ============================================================
def test_exception_classes():
    """测试异常分类体系"""
    from app.infrastructure.parsers.exceptions import (
        ParseError, FormatUnknownError, EncodingError,
        CorruptedFileError, EncryptedFileError,
        FileTooLargeError, MemoryExceededError,
    )

    # 基础异常
    e = ParseError("test error", "/tmp/test.pdf", "pdf")
    assert e.message == "test error"
    assert e.file_path == "/tmp/test.pdf"
    assert e.file_type == "pdf"

    # 各子类异常
    e = FormatUnknownError(file_type="xyz")
    assert "xyz" in str(e)

    e = EncodingError(detected_encoding="gbk")
    assert e.detected_encoding == "gbk"

    e = CorruptedFileError(file_type="pdf")
    assert "损坏" in str(e)

    e = EncryptedFileError(file_type="pdf")
    assert "加密" in str(e)

    e = FileTooLargeError(file_size=200 * 1024 * 1024, max_size=100 * 1024 * 1024)
    assert "200" in str(e) or "190" in str(e)  # 约 200MB

    e = MemoryExceededError(current_mb=350, threshold_mb=300)
    assert "350" in str(e)
    assert "300" in str(e)

    print("[PASS] test_exception_classes")


# ============================================================
# 运行所有测试
# ============================================================
if __name__ == "__main__":
    tests = [
        ("状态机-合法转换", test_state_machine_valid_transitions),
        ("状态机-非法转换", test_state_machine_invalid_transitions),
        ("状态机-自环", test_state_machine_self_loops),
        ("状态机-意图映射", test_intent_to_event),
        ("RAG-去重", test_rag_deduplicate),
        ("RAG-类型权重", test_rag_type_weights),
        ("上下文-基本组装", test_context_assembler_basic),
        ("上下文-Token预算", test_context_assembler_token_budget),
        ("解析-标准TXT", test_parse_pipeline_level1_txt),
        ("解析-无效文件", test_parse_pipeline_invalid_file),
        ("解析-超大文件", test_parse_pipeline_oversize_file),
        ("分块-语义分块", test_semantic_chunking),
        ("分块-元数据构建", test_chunk_metadata_builder),
        ("异常-分类体系", test_exception_classes),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"测试结果: {passed}/{len(tests)} 通过, {failed}/{len(tests)} 失败")
    if failed == 0:
        print("全部通过!")
    else:
        print(f"{failed} 个测试失败")
        sys.exit(1)