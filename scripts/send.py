import glob, hashlib, json, os, random
from datetime import datetime
from zoneinfo import ZoneInfo
from zalo import send, send_blocks
from translate import translate

STATE = "state/history.json"
CONFIG = "config/config.json"

# --- Cau hinh: lay tu config/config.json (chinh bang trang GitHub Pages) ---
cfg = {"count": 3, "max_repeat": 1, "time": "07:00", "docs": [], "order": "random"}
if os.path.exists(CONFIG):
    try:
        cfg.update(json.load(open(CONFIG, encoding="utf-8")))
    except Exception as e:
        print("Doc config loi, dung mac dinh:", e)

# Gia tri nhap tay luc chay workflow (neu co) se de len config
COUNT = max(int(os.environ.get("COUNT") or cfg["count"] or 3), 1)
MAX_REPEAT = max(int(os.environ.get("MAX_REPEAT") or cfg["max_repeat"] or 0), 0)
FORCE = os.environ.get("FORCE") == "true"
TEST = os.environ.get("TEST") == "true"   # gui thu: khong tinh la da nhac, khong ghi lich su
SEQ = cfg.get("order") == "seq"             # nhac theo thu tu trong file

now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
today = now.date().isoformat()

# 1. Doc tat ca doan highlight
by_id = {}
for fi, p in enumerate(sorted(glob.glob("highlights/*.json"))):
    stem = os.path.basename(p)[:-5]
    for k, it in enumerate(json.load(open(p, encoding="utf-8"))):
        i = hashlib.sha1(it["text"].encode("utf-8")).hexdigest()[:12]
        if i not in by_id:
            it["id"] = i
            it["_file"] = stem
            it["_ord"] = (fi, k)   # vi tri trong file de nhac theo thu tu
            by_id[i] = it

if not by_id:
    send("Chưa có highlight nào để nhắc. Hãy thả PDF vào folder Chưa xử lý.")
    raise SystemExit(0)

# 2. Tai lieu duoc chon tren trang cai dat (rong = tat ca tai lieu)
chosen_docs = cfg.get("docs") or []
pool = [i for i, it in by_id.items() if it["_file"] in chosen_docs] if chosen_docs else []
candidates = pool or list(by_id)

# 3. Doc lich su
state = {"last_date": "", "last_ids": [], "sent": {}}
if os.path.exists(STATE):
    state.update(json.load(open(STATE, encoding="utf-8")))
sent = state["sent"]


def pick():
    rnd = random.Random()
    new_ids = [i for i in candidates if i not in sent]
    old_ids = [i for i in candidates if i in sent]
    if SEQ:  # theo thu tu trong file; doan cu: lau chua nhac nhat truoc, cung ngay thi theo thu tu
        new_ids.sort(key=lambda i: by_id[i]["_ord"])
        old_ids.sort(key=lambda i: (sent[i]["last"], sent[i]["n"], by_id[i]["_ord"]))
    else:
        rnd.shuffle(new_ids)
        # doan cu: uu tien doan lau chua nhac nhat
        old_ids.sort(key=lambda i: (sent[i]["last"], sent[i]["n"], rnd.random()))
    n = min(COUNT, len(candidates))
    n_old = min(MAX_REPEAT, len(old_ids), n)
    n_new = min(n - n_old, len(new_ids))
    chosen = new_ids[:n_new] + old_ids[:n_old]
    if len(chosen) < n:  # het doan moi: buoc phai lay them doan cu
        chosen += old_ids[n_old:][: n - len(chosen)]
    return chosen


# 4. Chon doan hom nay
reuse = False
chosen = []
if state["last_date"] == today and not TEST:
    if not FORCE:
        print("Hom nay da gui roi, bo qua.")
        raise SystemExit(0)
    chosen = [i for i in state["last_ids"] if i in by_id]
    reuse = bool(chosen)
if not chosen:
    chosen = pick()

# 5. Dich song ngu (Gemini) - loi dich khong lam hong viec nhac bai
vi_map, tr_err = translate({i: by_id[i]["text"] for i in chosen})

# 6. Gui (danh so #1 #2 de Zalo khong tu doi thanh 1. 1. 1.)
blocks = []
for k, i in enumerate(chosen, 1):
    it = by_id[i]
    pg = it["page"] if it.get("page_end", it["page"]) == it["page"] else f"{it['page']}–{it['page_end']}"
    src = f"📖 {it['source']}, trang {pg}"
    vi = vi_map.get(i, "")
    if vi:
        blocks.append(f"#{k} 🇬🇧 {it['text']}\n\n🇻🇳 {vi}\n{src}")
    else:
        blocks.append(f"#{k} {it['text']}\n{src}")
if tr_err:
    blocks.append(f"⚠️ Chưa dịch được một số đoạn ({tr_err})")

header = "🧪 Gửi thử (không tính là đã nhắc)" if TEST else "📌 Nhắc bài hôm nay"
if pool:
    header += " · " + ", ".join(dict.fromkeys(by_id[i]["source"] for i in chosen))
send_blocks(header, blocks)

# 7. Luu lich su (chi sau khi gui thanh cong; gui thu thi khong luu)
if not reuse and not TEST:
    for i in chosen:
        rec = sent.get(i, {"n": 0})
        sent[i] = {"last": today, "n": rec["n"] + 1}
    state["last_date"] = today
    state["last_ids"] = chosen
    os.makedirs("state", exist_ok=True)
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
