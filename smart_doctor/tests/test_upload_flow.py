"""分片上传全流程自测脚本 — 使用 requests 库"""
import json
import os
import sys
import uuid

# 禁用代理
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["NO_PROXY"] = "*"

import requests

BASE = "http://localhost:8000/api/v1"
CHUNK_SIZE = 2 * 1024 * 1024
session = requests.Session()
session.trust_env = False  # 忽略系统代理


def test():
    issues = []

    # 准备测试文件
    test_file = os.path.join(os.path.dirname(__file__), "test_upload_sample.txt")
    content = "SmartDoctor上传测试内容。" * 5000  # ~150KB, 1 chunk
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)
    file_size = os.path.getsize(test_file)
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"[准备] 文件: {file_size} bytes, {total_chunks} chunks")

    # 1. 注册
    uname = f"uptest_{uuid.uuid4().hex[:6]}"
    r = session.post(f"{BASE}/auth/register", json={"username": uname, "password": "Test123456"})
    body = r.json()
    print(f"[注册] {r.status_code}: code={body.get('code')}")
    if r.status_code != 200 or body.get("code") != 0:
        issues.append(f"注册失败: {body}")
        return issues
    token = body["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 签署知情同意
    r = session.post(f"{BASE}/auth/consent", headers=headers)
    print(f"[同意] {r.status_code}")

    # 3. 获取医生
    r = session.get(f"{BASE}/doctors", headers=headers)
    body = r.json()
    doctor_id = None
    if body.get("code") == 0 and body.get("data"):
        doctor_id = body["data"][0]["id"]
        print(f"[医生] {doctor_id}")
    if not doctor_id:
        r = session.post(f"{BASE}/doctors", headers=headers, json={
            "name": "测试医生", "specialty": "全科", "description": "测试"
        })
        if r.json().get("code") == 0:
            doctor_id = r.json()["data"]["id"]
        else:
            issues.append(f"创建医生失败: {r.text[:200]}")
            return issues

    # 4. 初始化上传
    r = session.post(f"{BASE}/knowledge/upload/init", headers=headers, json={
        "doctor_id": doctor_id,
        "filename": "test_upload_sample.txt",
        "file_size": file_size,
        "file_type": "txt",
        "chunk_size": CHUNK_SIZE,
    })
    body = r.json()
    print(f"[INIT] {r.status_code}: {json.dumps(body, ensure_ascii=False)[:300]}")
    if body.get("code") != 0:
        issues.append(f"init 失败: {body}")
        return issues
    upload_id = body["data"]["upload_id"]
    server_total = body["data"]["total_chunks"]
    if server_total != total_chunks:
        issues.append(f"total_chunks 不匹配: client={total_chunks} server={server_total}")

    # 5. 逐片上传
    with open(test_file, "rb") as f:
        for i in range(total_chunks):
            chunk_data = f.read(CHUNK_SIZE)
            r = session.post(
                f"{BASE}/knowledge/upload/{upload_id}/chunk/{i}",
                headers=headers,
                files={"file": (str(i), chunk_data, "application/octet-stream")},
            )
            body = r.json()
            data = body.get("data", {})
            print(f"[CHUNK {i}] status={r.status_code} received={data.get('received_chunks')}/{data.get('total_chunks')} progress={data.get('progress_percent')}%")
            if r.status_code != 200 or body.get("code") != 0:
                issues.append(f"chunk {i} 失败: {body}")

    # 6. 重复上传 chunk 0（幂等性测试）
    with open(test_file, "rb") as f:
        chunk0 = f.read(CHUNK_SIZE)
    r = session.post(
        f"{BASE}/knowledge/upload/{upload_id}/chunk/0",
        headers=headers,
        files={"file": ("0", chunk0, "application/octet-stream")},
    )
    body = r.json()
    recv = body.get("data", {}).get("received_chunks")
    print(f"[DUP CHUNK 0] status={r.status_code} received={recv}/{total_chunks}")
    if recv != total_chunks:
        issues.append(f"重复上传后 received_chunks 错误: expected={total_chunks} got={recv}")
    else:
        print("[OK] 幂等性验证通过")

    # 7. 完成上传
    r = session.post(f"{BASE}/knowledge/upload/{upload_id}/complete", headers=headers)
    body = r.json()
    print(f"[COMPLETE] {r.status_code}: {json.dumps(body, ensure_ascii=False)[:500]}")
    if r.status_code != 200:
        issues.append(f"complete 失败 (HTTP {r.status_code}): {body}")
    elif body.get("code") != 0:
        issues.append(f"complete 返回非0: {body}")
    else:
        print("[OK] 上传完成!")

    # 8. 查询知识库
    r = session.get(f"{BASE}/knowledge", headers=headers, params={"doctor_id": doctor_id})
    body = r.json()
    if body.get("code") == 0:
        docs = body.get("data", [])
        print(f"[知识库] 文档数: {len(docs)}")
        for d in docs:
            print(f"  - {d.get('filename')} status={d.get('status')} chunks={d.get('chunk_count')}")
    else:
        issues.append(f"知识库查询失败: {body}")

    # 清理
    try: os.remove(test_file)
    except: pass

    return issues


if __name__ == "__main__":
    issues = test()
    print("\n" + "=" * 60)
    if issues:
        print(f"发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("所有测试通过!")
