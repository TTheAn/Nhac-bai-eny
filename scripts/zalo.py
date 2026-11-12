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


def _split(text, limit=LIMIT):
    """Cat text dai thanh nhieu phan <= limit, uu tien cat o xuong dong / het cau / khoang trang."""
    parts = []
    while len(text) > limit:
        window = text[:limit]
        cut = -1
        for sep, keep in (("\n\n", 0), ("\n", 0), (". ", 1), ("; ", 1), (" ", 0)):
            k = window.rfind(sep)
            if k > limit * 0.5:
                cut = k + keep
                break
        if cut <= 0:
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


def send(text):
    for part in _split(text):
        _post(part)


def send_blocks(header, blocks):
    """Gop cac khoi vao 1 tin neu vua; qua gioi han thi tach tin, khong cat doi 1 khoi neu no con vua 1 tin."""
    if not blocks:
        return
    blocks = [header + "\n\n" + blocks[0]] + blocks[1:]
    msgs, cur = [], ""
    for b in blocks:
        if len(b) > LIMIT:  # 1 khoi tu no da qua dai: gui rieng, cat o cho hop ly
            if cur:
                msgs.append(cur)
                cur = ""
            msgs.extend(_split(b))
        elif cur and len(cur) + 2 + len(b) > LIMIT:
            msgs.append(cur)
            cur = b
        else:
            cur = (cur + "\n\n" + b) if cur else b
    if cur:
        msgs.append(cur)
    for m in msgs:
        _post(m)
