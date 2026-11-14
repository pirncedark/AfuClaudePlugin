# Koprü: opencode (SQLite) + codex (jsonl) canli etkinlik goruntuleyici
import sqlite3, os, json, time, sys, glob
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12

def opencode(n):
    p = os.path.expanduser("~/.local/share/opencode/opencode.db")
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    cols = {r[1] for r in c.execute("PRAGMA table_info(part)")}
    tcol = "time_created" if "time_created" in cols else ("created_at" if "created_at" in cols else "id")
    rows = list(c.execute(f"select * from part order by {tcol} desc limit ?", (n*3,)))
    out = []
    for r in rows:
        d = dict(r)
        blob = d.get("data") or d.get("content") or ""
        try: j = json.loads(blob) if isinstance(blob, str) and blob.startswith("{") else {}
        except Exception: j = {}
        t = j.get("type") or d.get("type") or "?"
        if t == "text":
            s = (j.get("text") or "")[:160].replace("\n", " ")
        elif t == "tool":
            st = j.get("state") or {}
            s = f"{j.get('tool')} {json.dumps(st.get('input', {}), ensure_ascii=False)[:130]}"
        elif t == "reasoning":
            s = "[dusunuyor] " + (j.get("text") or "")[:110].replace("\n", " ")
        else:
            continue
        out.append(f"  {t:9s} | {s}")
        if len(out) >= n: break
    return out

def codex(n):
    base = os.path.expanduser("~/.codex")
    files = sorted(glob.glob(base + "/**/*.jsonl", recursive=True), key=os.path.getmtime, reverse=True)
    if not files: return ["  (codex kaydi yok)"]
    f = files[0]
    lines = open(f, encoding="utf-8", errors="replace").read().splitlines()[-n*4:]
    out = []
    for ln in lines:
        try: j = json.loads(ln)
        except Exception: continue
        t = j.get("type") or j.get("role") or "?"
        s = json.dumps(j, ensure_ascii=False)[:170]
        out.append(f"  {str(t)[:9]:9s} | {s}")
    return [f"  kaynak: {os.path.basename(f)}"] + out[-n:]

print("=" * 72); print("OPENCODE — son etkinlik"); print("=" * 72)
for l in opencode(N): print(l)
print(); print("=" * 72); print("CODEX — son etkinlik"); print("=" * 72)
for l in codex(N): print(l)
