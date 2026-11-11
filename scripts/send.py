import glob, hashlib, json, os, random
from datetime import datetime
from zoneinfo import ZoneInfo
from zalo import send, send_blocks

COUNT = max(int(os.environ.get("COUNT") or 3), 1)            # so doan nhac moi ngay
MAX_REPEAT = max(int(os.environ.get("MAX_REPEAT") or 1), 0)  # so doan cu toi da moi ngay
FORCE = os.environ.get("FORCE") == "true"
STATE = "state/history.json"

today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()

# 1. Doc tat ca doan highlight
by_id = {}
for p in sorted(glob.glob("highlights/*.json")):
    for it in json.load(open(p, encoding="utf-8")):
        i = hashlib.sha1(it["text"].encode("utf-8")).hexdigest()[:12]
        if i not in by_id:
            it["id"] = i
            by_id[i] = it

if not by_id:
    send("Chưa có highlight nào để nhắc. Hãy thả PDF vào folder Chưa xử lý.")
    raise SystemExit(0)

# 2. Doc lich su
state = {"last_date": "", "last_ids": [], "sent": {}}
if os.path.exists(STATE):
    state.update(json.load(open(STATE, encoding="utf-8")))
sent = state["sent"]


def pick():
    rnd = random.Random()
    new_ids = [i for i in by_id if i not in sent]
    old_ids = [i for i in by_id if i in sent]
    rnd.shuffle(new_ids)
    # doan cu: uu tien doan lau chua nhac nhat
    old_ids.sort(key=lambda i: (sent[i]["last"], sent[i]["n"], rnd.random()))
    n = min(COUNT, len(by_id))
    n_old = min(MAX_REPEAT, len(old_ids), n)
    n_new = min(n - n_old, len(new_ids))
    chosen = new_ids[:n_new] + old_ids[:n_old]
    if len(chosen) < n:  # het doan moi: buoc phai lay them doan cu
        chosen += old_ids[n_old:][: n - len(chosen)]
    return chosen


# 3. Chon doan hom nay
reuse = False
chosen = []
if state["last_date"] == today:
    if not FORCE:
        print("Hom nay da gui roi, bo qua.")
        raise SystemExit(0)
    chosen = [i for i in state["last_ids"] if i in by_id]
    reuse = bool(chosen)
if not chosen:
    chosen = pick()

# 4. Gui (danh so #1 #2 de Zalo khong tu doi thanh 1. 1. 1.)
blocks = []
for k, i in enumerate(chosen, 1):
    it = by_id[i]
    pg = it["page"] if it.get("page_end", it["page"]) == it["page"] else f"{it['page']}–{it['page_end']}"
    blocks.append(f"#{k} {it['text']}\n📖 {it['source']}, trang {pg}")
send_blocks("📌 Nhắc bài hôm nay", blocks)

# 5. Luu lich su (chi sau khi gui thanh cong)
if not reuse:
    for i in chosen:
        rec = sent.get(i, {"n": 0})
        sent[i] = {"last": today, "n": rec["n"] + 1}
    state["last_date"] = today
    state["last_ids"] = chosen
    os.makedirs("state", exist_ok=True)
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
