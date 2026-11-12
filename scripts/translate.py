"""Dich song ngu Anh -> Viet (ngon ngu Y khoa) bang Gemini. Co cache de doan lap lai khong ton luot goi."""
import json, os, time, requests

KEY = os.environ.get("GEMINI_API_KEY", "")
# Co the doi bang bien moi truong GEMINI_MODEL; neu model loi se thu model ke tiep
MODELS = [m for m in (os.environ.get("GEMINI_MODEL"), "gemini-flash-latest",
                      "gemini-3.5-flash", "gemini-2.5-flash") if m]
CACHE = "state/translations.json"

SYSTEM = (
    "Bạn là dịch giả y khoa chuyên nghiệp. Với mỗi đoạn văn trong danh sách: "
    "(1) xác định đoạn đó có phải tiếng Anh không; "
    "(2) nếu là tiếng Anh, dịch sang tiếng Việt bằng ngôn ngữ Y khoa chuẩn, dùng thuật ngữ y khoa tiếng Việt "
    "thông dụng trong sách giáo khoa và lâm sàng; giữ nguyên số liệu, đơn vị, viết tắt, tên thuốc, tên gen; "
    "với thuật ngữ ít phổ biến có thể kèm thuật ngữ gốc trong ngoặc đơn; "
    "dịch đầy đủ, chính xác, không tóm tắt, không thêm ý, không giải thích; "
    "(3) nếu không phải tiếng Anh (ví dụ đã là tiếng Việt) thì đặt english=false và vi=\"\". "
    "Trả về đúng JSON theo schema, giữ nguyên chỉ số i."
)

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "i": {"type": "INTEGER"},
            "english": {"type": "BOOLEAN"},
            "vi": {"type": "STRING"},
        },
        "required": ["i", "english", "vi"],
    },
}


def _load():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        return {}


def _save(cache):
    os.makedirs("state", exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _call(model, texts):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(
            [{"i": i, "text": t} for i, t in enumerate(texts)], ensure_ascii=False)}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }
    r = requests.post(url, headers={"x-goog-api-key": KEY, "Content-Type": "application/json"},
                      json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    return {int(x["i"]): x for x in json.loads(raw)}


def translate(items):
    """items: {id: text}. Tra ve ({id: ban_dich_viet hoac ''}, loi hoac None).
    '' nghia la doan khong phai tieng Anh (khong can dich)."""
    cache = _load()
    out = {i: cache[i] for i in items if i in cache}
    todo = [i for i in items if i not in cache]
    if not todo:
        return out, None
    if not KEY:
        return out, "Chưa có GEMINI_API_KEY"

    texts = [items[i] for i in todo]
    err = None
    for model in MODELS:
        for attempt in range(2):
            try:
                res = _call(model, texts)
                for k, i in enumerate(todo):
                    x = res.get(k)
                    if x is None:
                        continue
                    vi = (x.get("vi") or "").strip() if x.get("english") else ""
                    out[i] = cache[i] = vi
                _save(cache)
                missing = [i for i in todo if i not in out]
                return out, (f"Thiếu bản dịch {len(missing)} đoạn" if missing else None)
            except Exception as e:
                err = f"{model}: {str(e)[:150]}"
                print("Gemini loi:", err, flush=True)
                time.sleep(3)
    return out, err
