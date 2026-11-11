import os, requests

TOKEN = os.environ["ZALO_BOT_TOKEN"]
CHAT_ID = os.environ["ZALO_CHAT_ID"]
API = f"https://bot-api.zaloplatforms.com/bot{TOKEN}"
LIMIT = 1900  # Zalo cho toi da 2000 ky tu/tin


def _post(text):
    r = requests.post(
        f"{API}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=15,
    ).json()
    if not r.get("ok"):
        raise RuntimeError(f"Zalo loi: {r}")


def send(text):
    for i in range(0, len(text), LIMIT):
        _post(text[i:i + LIMIT])


def send_blocks(header, blocks):
    """Gop cac khoi vao tin nhan, khong cat doi 1 khoi neu con vua 1 tin."""
    if not blocks:
        return
    blocks = [header + "\n\n" + blocks[0]] + blocks[1:]
    msgs, cur = [], ""
    for b in blocks:
        if cur and len(cur) + 2 + len(b) > LIMIT:
            msgs.append(cur)
            cur = b
        else:
            cur = (cur + "\n\n" + b) if cur else b
    if cur:
        msgs.append(cur)
    for m in msgs:
        send(m)
