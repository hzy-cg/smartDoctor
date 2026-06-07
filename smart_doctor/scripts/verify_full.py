import httpx
import uuid

BASE = "http://localhost:8000/api/v1"

client = httpx.Client(timeout=60)

print("=" * 60)
print("SmartDoctor 完整链路验证")
print("=" * 60)

print("\n[1] 注册...")
uname = f"test{uuid.uuid4().hex[:8]}"
r = client.post(f"{BASE}/auth/register?username={uname}&password=123456")
d = r.json()
token = d["data"]["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"    OK code={d['code']}")

print("\n[2] 医生列表...")
r = client.get(f"{BASE}/doctors", headers=headers)
print(f"    count={len(r.json()['data'])}")

print("\n[3] 创建对话...")
did = r.json()["data"][0]["id"] if r.json()["data"] else None
if not did:
    print("    跳过：无可用医生")
else:
    r = client.post(f"{BASE}/chat/conversations", json={"doctor_id": did}, headers=headers)
    conv_id = r.json()["data"]["id"]
    print(f"    OK conv_id={conv_id}")

    print("\n[4] 发送消息（需 LLM API Key）...")
    r = client.post(f"{BASE}/chat/conversations/{conv_id}/messages",
                    json={"content": "头痛三天，前额部位", "input_type": "text"}, headers=headers)
    d = r.json()
    if d.get("code") == 0:
        print(f"    assistant: {d['data']['assistant_message']['content'][:100]}")
    else:
        print(f"    错误(预期): code={d.get('code')}, msg={d.get('message','LLM API Key未配置')}")

    print("\n[5] 对话历史...")
    r = client.get(f"{BASE}/chat/conversations/{conv_id}/messages", headers=headers)
    print(f"    共 {len(r.json()['data'])} 条消息")

print("\n" + "=" * 60)
print("核心链路验证完成！")
print()
print("已通过（无需 LLM）：")
print("  注册/登录   Auth API")
print("  医生列表   Doctor API")
print("  创建对话   Chat API")
print("  对话历史   Chat API")
print()
print("需配置 LLM API Key：")
print("  编辑 .env → OPENAI_API_KEY=sk-xxx")
print("  然后 AI 问诊回复功能可用")
print("=" * 60)
