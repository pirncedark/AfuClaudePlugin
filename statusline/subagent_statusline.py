import json, sys, time
sys.stdout.reconfigure(newline="\n")
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tasks = [t for t in data.get("tasks", []) if isinstance(t, dict)]

def tok(n):
    if not isinstance(n, (int, float)) or n <= 0: return "—"
    return ("{:.1f}k".format(n / 1000).replace(".0k", "k")) if n >= 1000 else str(int(n))

def dur(t):
    if not isinstance(t, (int, float)) or t <= 0: return "—"
    if t > 1e12: t /= 1000
    s = max(0, int(time.time() - t))
    return "{}sn".format(s) if s < 60 else "{}dk".format(s // 60)

def first(t, keys):
    for k in keys:
        v = t.get(k)
        if isinstance(v, str) and v.strip(): return " ".join(v.split())
    return ""

# Oncelik: gorev basligi -> su anki eylem -> son arac -> gorev dosyasi adi
def is_adi(t):
    text = first(t, ("title", "description", "label", "currentAction", "current_action", "lastTool", "last_tool", "summary"))
    return text or first(t, ("file", "taskFile")) or "—"

def kisa(text, n=42):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"

CALISAN = ("running", "in_progress", "active", "working", "calisiyor", "çalışıyor", "arka planda", "background")
rows = []
for t in tasks:
    ad = first(t, ("name", "type")) or "ajan"
    model = first(t, ("model",)) or "?"
    if model.startswith("claude-"): model = model[7:]
    if len(model) > 9 and model[-9:-8] == "-" and model[-8:].isdigit(): model = model[:-9]
    live = str(t.get("status") or "").casefold() in CALISAN
    rows.append((t.get("id"), "◉" if live else "◯", ad, model, kisa(is_adi(t)), dur(t.get("startTime")), tok(t.get("tokenCount"))))

w_ad = max([len(r[2]) for r in rows] or [0])
w_model = max([len(r[3]) for r in rows] or [0])
w_is = max([len(r[4]) for r in rows] or [0])
W, R = "\033[1;38;5;255m", "\033[0m"
for i, mark, ad, model, is_, sure, token in rows:
    row = "{} {}  {}  {}  {} · ↓ {}".format(mark, ad.ljust(w_ad), model.ljust(w_model), is_.ljust(w_is), sure.rjust(4), token)
    print(json.dumps({"id": i, "content": W + row + R}, ensure_ascii=False))
