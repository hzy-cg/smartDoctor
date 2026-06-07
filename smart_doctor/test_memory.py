import httpx, json, time

base = "http://localhost:8000/api/v1"

r = httpx.post(f"{base}/auth/login", params={"username": "hzy", "password": "123456"}, timeout=10)
token = r.json()["data"]["token"]
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

r = httpx.get(f"{base}/doctors", headers=h, timeout=10)
doctor_id = r.json()["data"][0]["id"]

r = httpx.post(f"{base}/chat/conversations", headers=h, content=json.dumps({"doctor_id": doctor_id}), timeout=15)
cid = r.json()["data"]["id"]
print(f"Conversation: {cid}")

messages = ["我头痛3天了", "太阳穴两侧胀痛", "还有点恶心"]

for i, msg in enumerate(messages):
    print(f"\n--- Round {i+1}: {msg} ---")
    r = httpx.post(f"{base}/chat/conversations/{cid}/messages", headers=h, content=json.dumps({"content": msg}), timeout=120)
    if r.status_code != 200:
        print(f"ERROR: {r.status_code} {r.text[:300]}")
        continue
    ai_msg = r.json()["data"]["assistant_message"]["content"]
    print(f"AI: {ai_msg[:300]}")
    time.sleep(1)

print("\n=== Done ===")
