"""Quick test for semantic chunking."""
from app.application.utils.chunking import split_semantic_chunks

text = (
    "患者头痛3天。太阳穴双侧胀痛。伴有恶心呕吐。"
    "既往有高血压病史。血压控制不佳。近日血压160/100mmHg。"
    "无发热、无视觉异常。无肢体麻木。"
)
chunks = split_semantic_chunks(
    text, chunk_tokens=128, chunk_overlap_tokens=16,
    source_name="test.txt", doc_context={"doc_type": "txt"}
)
print(f"Chunks: {len(chunks)}")
for c in chunks:
    print(f"  [{c['metadata']['chunk_index']}] (tokens≈{c['metadata']['approx_tokens']}): {c['content'][:80]}...")
print("OK")
