import os, time, requests

API = f"https://bot-api.zaloplatforms.com/bot{os.environ['ZALO_BOT_TOKEN']}"
print("Hay nhan 1 tin cho bot tren Zalo NGAY BAY GIO (60 giay)...", flush=True)
end = time.time() + 60
while time.time() < end:
    try:
        r = requests.post(f"{API}/getUpdates", json={"timeout": 5}, timeout=20).json()
    except Exception:
        print("loi mang, thu lai", flush=True)
        time.sleep(2)
        continue
    if r.get("ok"):
        res = r["result"]
        for u in (res if isinstance(res, list) else [res]):
            msg = u.get("message", {})
            print("CHAT_ID =", msg.get("chat", {}).get("id"), flush=True)
        break
    time.sleep(2)
else:
    print("Het 60 giay, chua nhan duoc tin. Hay chay lai.")
