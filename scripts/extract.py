import os, re, json, traceback
import pymupdf as fitz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from zalo import send

SRC = os.environ["GDRIVE_UNPROCESSED_ID"]
DST = os.environ["GDRIVE_PROCESSED_ID"]
creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GDRIVE_SA_KEY"]),
    scopes=["https://www.googleapis.com/auth/drive"],
)
drive = build("drive", "v3", credentials=creds)

MIN_LEN = 15       # bo doan to ngan hon so ky tu nay
HEADER = 0.08      # bo 8% phia tren moi trang (header)
FOOTER = 0.08      # bo 8% phia duoi moi trang (footer)
ZONE = 0.25        # vung dau/cuoi trang de noi doan to tren 2 trang
CITE = re.compile(r"\s*\[\s*\d+(?:\s*[,\-\u2013]\s*\d+)*\s*\]")  # bo [1], [3-5]


def list_pdfs():
    res = drive.files().list(
        q=f"'{SRC}' in parents and mimeType='application/pdf' and trashed=false",
        fields="files(id,name)", pageSize=1000,
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    return res.get("files", [])


def download(fid, path):
    req = drive.files().get_media(fileId=fid)
    with open(path, "wb") as f:
        dl = MediaIoBaseDownload(f, req, chunksize=32 * 1024 * 1024)
        done = False
        while not done:
            _, done = dl.next_chunk()


def extract(path, name):
    raw, empty, n_annots = [], 0, 0
    doc = fitz.open(path)
    for page in doc:
        h = page.rect.height
        top = page.rect.y0 + HEADER * h
        bot = page.rect.y1 - FOOTER * h
        page_items = []
        for a in page.annots(types=[fitz.PDF_ANNOT_HIGHLIGHT]) or []:
            n_annots += 1
            v = a.vertices or []
            rects = []
            for i in range(0, len(v) - 3, 4):
                r = fitz.Quad(v[i:i + 4]).rect
                r = fitz.Rect(r.x0 + 0.5, max(r.y0 + 2, top), r.x1 - 0.5, min(r.y1 - 2, bot))
                if not r.is_empty and r.height >= 3:
                    rects.append(r)
            if not rects:
                continue  # vung to nam tron trong header/footer
            rects.sort(key=lambda r: (round(r.y0), r.x0))
            text = " ".join(page.get_textbox(r) for r in rects)
            text = re.sub(r"\s+", " ", text).strip()
            text = CITE.sub("", text).strip()
            if not text:
                empty += 1
                continue
            color = (a.colors or {}).get("stroke")
            page_items.append({
                "text": text, "source": name, "page": page.number + 1,
                "page_end": page.number + 1,
                "color": [round(c, 2) for c in color] if color else None,
                "_y0": rects[0].y0,
                "_top_ok": rects[0].y0 <= page.rect.y0 + ZONE * h,
                "_bot_ok": rects[-1].y1 >= page.rect.y1 - ZONE * h,
            })
        page_items.sort(key=lambda x: x["_y0"])
        raw.extend(page_items)

    # Doan to cuoi trang N + doan to dau trang N+1 (cung mau) -> coi la 1 doan
    merged = []
    for it in raw:
        prev = merged[-1] if merged else None
        if (prev and it["page"] == prev["page_end"] + 1
                and prev["_bot_ok"] and it["_top_ok"]
                and prev["color"] == it["color"]):
            prev["text"] += " " + it["text"]
            prev["page_end"] = it["page"]
            prev["_bot_ok"] = it["_bot_ok"]
        else:
            merged.append(it)

    items, seen = [], set()
    for it in merged:
        if len(it["text"]) < MIN_LEN or it["text"] in seen:
            continue
        seen.add(it["text"])
        for k in ("_y0", "_top_ok", "_bot_ok"):
            it.pop(k)
        if it["page_end"] == it["page"]:
            it.pop("page_end")
        items.append(it)
    return items, empty, n_annots


def move(fid):
    p = drive.files().get(fileId=fid, fields="parents", supportsAllDrives=True).execute()
    drive.files().update(
        fileId=fid, addParents=DST, removeParents=",".join(p["parents"]),
        supportsAllDrives=True, fields="id",
    ).execute()


def main():
    files = list_pdfs()
    if not files:
        print("Khong co file moi, bo qua.")
        return
    os.makedirs("highlights", exist_ok=True)
    lines, errs = [], []
    for f in files:
        name = re.sub(r"\.pdf$", "", f["name"], flags=re.I)
        try:
            download(f["id"], "/tmp/x.pdf")
            items, empty, n = extract("/tmp/x.pdf", name)
            safe = re.sub(r'[\\/:*?"<>|]', "_", name)
            with open(f"highlights/{safe}.json", "w", encoding="utf-8") as out:
                json.dump(items, out, ensure_ascii=False, indent=1)
            move(f["id"])
            note = f"✅ {name}: {len(items)} mục"
            if n == 0:
                note += " (⚠️ không thấy highlight nào, có thể file đã flatten)"
            elif empty:
                note += f" (⚠️ {empty} vùng tô không có chữ, có thể là bản scan)"
            lines.append(note)
        except Exception:
            traceback.print_exc()
            errs.append(f"❌ {name}: lỗi, file vẫn nằm ở Chưa xử lý")
        finally:
            if os.path.exists("/tmp/x.pdf"):
                os.remove("/tmp/x.pdf")
    send("Kết quả xử lý PDF mới:\n" + "\n".join(lines + errs))


main()
