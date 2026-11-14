#!/usr/bin/env bash
# Local snapshot renderer. It never calls a provider or accesses the network.
#
# Kolon izgarasi (referans goruntuye satir satir ayni):
#   0-7 etiket | 8 bosluk | 9-18 deger/cizbik | 19 bosluk | 20-23 yuzde-$ |
#   24 bosluk | 25 ayirici | 26 bosluk | 27-31 seviye/token | 32 bosluk |
#   33 ayirici | 34 bosluk | 35+ kalan
#
# Satir listesi: MODEL, NOBET, AJANLAR (kayit varsa tek satir), CALISAN, CLAUDE,
# GEMINI, OPENCODE, CODEX, Baglam.
PIPE='│'; DOT='·'; FULL='█'; EMPTY='░'; UNKNOWN='▒'; ARROW='↻'; BAGLAM='Bağlam  '
input=$(cat)
parsed=$(printf '%s' "$input" | python -c '
import json, os, re, sys, time
from datetime import datetime

ARROW_RESET = "↻"
DOT = "·"
BILINMIYOR = "bilinmiyor"
ACTIVE = ("çalışıyor", "arka planda", "bekliyor")
def mapping(value): return value if isinstance(value, dict) else {}
def clean(value, limit=90):
    text = " ".join(str(value or "?").replace("\r", " ").replace("\n", " ").split())
    text = re.sub(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|token|secret|password)\s*[:=]\s*[^\s,;]+", "[hidden]", text)
    text = re.sub(r"(?i)\bbearer\s+[^\s,;]+", "[hidden]", text)
    return text[:limit - 1] + "…" if len(text) > limit else text
def pad(text, width):
    text = text[:width]
    while len(text) < width: text = text + " "
    return text
def bilinmiyor_de(value, limit=90):
    text = clean(value, limit)
    return BILINMIYOR if text == "?" else text
def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as stream: return stream.read()
    except (OSError, ValueError): return ""
def strip_jsonc(text):
    out = []
    index = 0
    size = len(text)
    while index < size:
        char = text[index]
        if char == chr(34):
            end = index + 1
            while end < size:
                if text[end] == chr(92):
                    end = end + 2
                    continue
                if text[end] == chr(34):
                    end = end + 1
                    break
                end = end + 1
            out.append(text[index:end])
            index = end
            continue
        if char == "/" and index + 1 < size and text[index + 1] in ("/", "*"):
            if text[index + 1] == "/":
                end = text.find(chr(10), index)
            else:
                end = text.find("*/", index + 2)
                end = size if end < 0 else end + 2
            index = size if end < 0 else end
            continue
        out.append(char)
        index = index + 1
    return "".join(out)
def load_jsonc(path):
    text = strip_jsonc(read_text(path))
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    try: return mapping(json.loads(text))
    except (ValueError, TypeError): return {}
def py_string(text, name):
    match = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*[\"\x27]([^\"\x27]+)", text)
    return match.group(1) if match else ""
def toml_string(text, key):
    match = re.search(r"(?m)^\s*" + re.escape(key) + r"\s*=\s*\"([^\"]+)\"", text)
    return match.group(1) if match else ""
def iso_epoch(value):
    try: return float(datetime.fromisoformat(str(value)).timestamp())
    except (TypeError, ValueError): return 0.0
def job_start(job):
    digits = re.sub(r"\D", "", str(job.get("id") or ""))
    try:
        if len(digits) >= 13: return float(digits) / 1000000.0
        if len(digits) >= 10: return float(digits)
    except ValueError: pass
    return iso_epoch(job.get("created_at")) or iso_epoch(job.get("updated_at"))
def ayar_model_effort(provider, repo_dir):
    """Saglayicinin kendi yerel yapilandirmasindan gercek model ve effort."""
    provider = str(provider or "").upper()
    home = os.path.expanduser("~")
    model = effort = ""
    if provider == "OPENCODE":
        config = load_jsonc(os.path.join(home, ".config", "opencode", "opencode.jsonc"))
        model = clean(config.get("model"), 40)
        agents = mapping(config.get("agent"))
        wanted = model.rsplit("/", 1)[-1]
        for item in agents.values():
            item = mapping(item)
            item_model = clean(item.get("model"), 40)
            if wanted and item_model.rsplit("/", 1)[-1] == wanted:
                effort = clean(item.get("variant") or item.get("effort"), 16)
                break
        if effort in ("?", ""):
            build = mapping(agents.get("build"))
            effort = clean(build.get("variant") or build.get("effort"), 16)
        if effort in ("?", ""): effort = clean(config.get("variant") or config.get("effort"), 16)
        text = read_text(os.path.join(repo_dir, "afu", "providers", "opencode.py"))
        if model == "?": model = clean(py_string(text, "OPENCODE_MODEL"), 40)
        if effort in ("?", ""): effort = clean(py_string(text, "OPENCODE_VARIANT"), 16)
    elif provider == "CODEX":
        text = read_text(os.path.join(home, ".codex", "config.toml"))
        model = clean(toml_string(text, "model"), 40)
        effort = clean(toml_string(text, "model_reasoning_effort"), 16)
    elif provider == "GEMINI":
        text = read_text(os.path.join(repo_dir, "afu", "providers", "gemini.py"))
        model = clean(py_string(text, "FLASH_MODEL"), 40)
        effort = clean(py_string(text, "GEMINI_VARIANT"), 16)
    elif provider == "CLAUDE":
        config = load_jsonc(os.path.join(home, ".claude", "settings.json"))
        model = clean(config.get("model"), 40)
        effort = clean(config.get("effortLevel"), 16)
    if model in ("?", BILINMIYOR): model = ""
    if effort in ("?", BILINMIYOR): effort = ""
    return (model.rsplit("/", 1)[-1] if model else "", effort)
# EK 10: geri donus - NOBET satiri yine AfuNobet nobet_satiri(provider)
# yontemini kullanir (onceki surum 89-117 ve 400-420). Bu yontem model, effort
# ve saglayici bilgisini adaptörlerin GERCEK cagri ayarlarindan okur; bu yuzden
# is kaydinda model yokken de dogru degeri verir.
SEP = chr(9474)
YON = chr(8594)
NOBET_CACHE = {}
def nobet_satiri_oku(saglayici):
    global NOBET_CACHE
    saglayici = clean(saglayici, 20)
    if saglayici in ("", "?", BILINMIYOR): return ""
    if saglayici in NOBET_CACHE: return NOBET_CACHE[saglayici]
    metin = ""
    try:
        if repo not in sys.path: sys.path.insert(0, repo)
        from afunobet import nobet_satiri
        metin = str(nobet_satiri(saglayici) or "")
    except Exception:
        metin = ""
    NOBET_CACHE[saglayici] = metin
    return metin
def nobet_ayikla(saglayici):
    """nobet_satiri ciktisini (saglayici, model, bolum listesi) olarak ayirir."""
    metin = nobet_satiri_oku(saglayici)
    if not metin: return ("", "", [])
    govde = metin.split(None, 1)
    govde = govde[1].strip() if len(govde) > 1 else metin.strip()
    parcalar = [parca.strip() for parca in govde.split(SEP)]
    bas = parcalar[0] if parcalar else ""
    bolumler = [bolum for bolum in parcalar[1:] if bolum]
    isim = bas.split(" " + YON + " ", 1)
    model = isim[1].strip() if len(isim) > 1 else ""
    return (bas.split(" ")[0], model, bolumler)
def pct(value):
    try:
        number = float(value)
        return str(int(round(number))) if 0 <= number <= 100 else "?"
    except (TypeError, ValueError, OverflowError): return "?"
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
def local_time(value, gun=False):
    try:
        dt = datetime.fromtimestamp(float(value))
        return (GUNLER[dt.weekday()] + " " if gun else "") + dt.strftime("%H:%M")
    except (TypeError, ValueError, OSError, OverflowError): return BILINMIYOR
def provider_reset_time(value):
    try:
        timestamp = float(value)
        dt = datetime.fromtimestamp(timestamp)
        if timestamp - time.time() > 24 * 60 * 60:
            months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
            return str(dt.day) + " " + months[dt.month - 1]
        return dt.strftime("%H:%M")
    except (TypeError, ValueError, OSError, OverflowError): return BILINMIYOR

def token_text(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool): return BILINMIYOR
    if value >= 1000000: return "{:.1f}M".format(value / 1000000.0)
    if value >= 1000: return "{}K".format(int(value // 1000))
    return str(int(value))
def m_kisa(value):
    if value < 10: return "$%.1f" % value
    if value < 1000: return "$%.0f" % value
    return "$%.0fK" % (value / 1000)
try: data = mapping(json.load(sys.stdin))
except (ValueError, TypeError): data = {}
ctx, cost, limits = mapping(data.get("context_window")), mapping(data.get("cost")), mapping(data.get("rate_limits"))
five, seven = mapping(limits.get("five_hour")), mapping(limits.get("seven_day"))
model = pad(bilinmiyor_de(mapping(data.get("model")).get("display_name"), 32) or "bilinmiyor", 10)
effort = data.get("effort") or mapping(data.get("output_config")).get("effort") or ""
if isinstance(effort, dict): effort = effort.get("level") or effort.get("effort") or ""
if not effort:
    try:
        with open(os.path.expanduser("~/.claude/settings.json"), encoding="utf-8") as stream: effort = mapping(json.load(stream)).get("effortLevel") or ""
    except (OSError, ValueError, TypeError): effort = ""
effort = clean(effort, 14)
fast = "on" if data.get("fast_mode") is True else ("off" if data.get("fast_mode") is False else "")
thinking = data.get("thinking")
if isinstance(thinking, dict): thinking = thinking.get("enabled", thinking.get("type"))
thinking = "on" if thinking is True else ("off" if thinking is False else "")
repo = os.environ.get("AFUNOBET_DIR") or os.path.join(os.path.expanduser("~"), "Desktop", "afuproject", "AfuNobet")
status_path = os.environ.get("AFUNOBET_MONITOR_STATUS") or os.path.join(repo, "logs", "local_status.json")
snapshot = {}
izleyici = "kapalı"
try:
    with open(status_path, encoding="utf-8") as stream: snapshot = mapping(json.load(stream))
    age = time.time() - float(snapshot.get("updated_at"))
    if age < -5 or age > 30: snapshot, izleyici = {}, "bayat ({} dk)".format(int(age // 60)) if age > 30 else "saat hatası"
    else: izleyici = ""
except (OSError, ValueError, TypeError): snapshot = {}
summary = mapping(snapshot.get("job_summary"))
jobs = snapshot.get("jobs") if isinstance(snapshot.get("jobs"), list) else []
job_lookup = {str(job.get("id")): job for job in jobs if isinstance(job, dict) and job.get("id")}

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < float("inf")

def agent_elapsed(item):
    elapsed = item.get("elapsed_seconds", item.get("elapsed"))
    if not number(elapsed):
        start = 0
        for key in ("basladi", "started_at", "start_time", "created_at"):
            value = item.get(key)
            start = value if number(value) else iso_epoch(value)
            if start: break
        if not start and str(item.get("id") or "").startswith("is_"): start = job_start(item)
        elapsed = max(0, time.time() - start) if start else None
    if not number(elapsed): return BILINMIYOR
    minutes, seconds = divmod(int(elapsed), 60)
    return "{}m {}s".format(minutes, seconds)

def agent_tokens(item):
    # Per-call usage only; provider totals would repeat unrelated session tokens.
    usage = mapping(item.get("usage"))
    tokens = item.get("tokens")
    values = (item.get("output_tokens"), usage.get("output_tokens"),
              item.get("total_tokens"), usage.get("total_tokens"),
              mapping(tokens).get("value"), tokens, item.get("token_count"))
    for value in values:
        if number(value): return token_text(value)
    return BILINMIYOR

agent_rows = []
seen_agents = set()
CALISAN_DURUM = ("çalışıyor", "arka planda")
active_jobs = [job for job in jobs if isinstance(job, dict) and job.get("status") in CALISAN_DURUM]
live_states = CALISAN_DURUM + ("running", "in_progress", "background", "calisiyor")
# Verified provider calls and native task input share the same list with jobs.
sources = []
for owner, key, live in ((snapshot, "calisan", True), (data, "tasks", False),
                         (data, "subagents", False), (snapshot, "subagents", False)):
    records = owner.get(key)
    if isinstance(records, list): sources.extend((item, live) for item in records if isinstance(item, dict))
sources.extend((job, False) for job in active_jobs)
for item, verified_live in sources:
    state = str(item.get("status") or item.get("durum") or "").casefold()
    if not verified_live and state not in live_states: continue
    linked_id = item.get("job_id") or item.get("id") or item.get("agent_id")
    identity = str(linked_id) if linked_id else ""
    if identity and identity in seen_agents: continue
    if identity: seen_agents.add(identity)
    linked = job_lookup.get(identity, {})
    record = dict(linked)
    record.update({key: value for key, value in item.items() if value not in (None, "", "?")})
    # Saglayici kodu (CODEX/GEMINI/OPENCODE/CLAUDE) alt-ajan adi olarak
    # gosterilmez; kucuk harfli ajan adi tercih edilir.
    name = record.get("ajan") or record.get("subagent") or record.get("name") or record.get("agent") or record.get("agent_type")
    name = bilinmiyor_de(name, 24)
    if name != BILINMIYOR and str(name).upper() in ("CODEX", "GEMINI", "OPENCODE", "CLAUDE"):
        name = str(name).lower()
    task = record.get("gorev") or record.get("task") or record.get("description") or record.get("title")
    agent_rows.append("◯ {}  {}   {} · ↓ {}".format(
        name, bilinmiyor_de(task, 64), agent_elapsed(record), agent_tokens(record)))

main_row = "● main" + (" · izleyici " + izleyici if izleyici else "")
# Summary.get() preserves the known active count when no detailed jobs exist.
summary_count = sum(value for key in CALISAN_DURUM for value in (summary.get(key, 0),)
                    if isinstance(value, int) and not isinstance(value, bool) and value > 0)
if not agent_rows and summary_count:
    agent_rows.append("+{} · görev ayrıntısı bilinmiyor".format(summary_count))
# Satir siniri: en fazla 3 ajan satiri; fazlasi tek "+N" satirinda.
# AJANLAR blogu "● main" satirindan sonra gelir; Claude kodunun kendi
# "← N agents" satiri bu blogun ALTINDA kalir, hicbir sartta kaymaz veya kesilmez.
visible_agents = agent_rows[:3] if len(agent_rows) <= 3 else agent_rows[:2] + ["+{}".format(len(agent_rows) - 2)]
# One transport field avoids shifting provider indexes in the Bash mapfile.
summary_text = chr(31).join([main_row] + visible_agents)
nobet_data = mapping(snapshot.get("nobet"))
# EK 8: NOBET satiri EN SON BASLAYAN ve HALA CALISAN isi gosterir.
# Bitis/hata/kayip isler aday degildir. Birincil olcut is BASLANGIC zamanidir
# (is kimligi zaman damgasidir, yoksa updated_at); "calisiyor" onceligi yalnizca
# baslangic zamani esit oldugunda gecerlidir, aksi halde yeni baslayan "arka
# planda" isi eski calisan isin onune gecer.
STATUS_ONCELIK = {"çalışıyor": 0, "arka planda": 1, "bekliyor": 2}
aday = []
for job in jobs:
    if not isinstance(job, dict): continue
    state = clean(job.get("status"), 24)
    if state not in STATUS_ONCELIK: continue
    aday.append((-job_start(job), STATUS_ONCELIK[state], str(job.get("id") or ""), job))
aday.sort(key=lambda item: (item[0], item[1], item[2]))
is_kaydi = mapping(aday[0][3]) if aday else {}
is_id = clean(is_kaydi.get("id"), 40)
if is_id == "?": is_id = ""
# EK 8 KESIN KURAL: alt ajan adi = isi fiilen yurten ALT-AJAN (subagent kaydi).
# Sirasi: is kaydindaki gercek subagent -> nobet satiri -> saglayici.
# Claude adi ya da router onerisi ASLA gosterilmez.
# Izleyici kapali/bayatsa HICBIR kayit dogrulanamaz; ayar okuma devre disi kalir
# (izleyici "kapali" derken alt-ajan/model uydurmak yaniltici olurdu).
alt_ajan = ""
for kaynak in (is_kaydi, nobet_data):
    for anahtar in ("subagent", "alt_ajan", "ajan"):
        denenen = bilinmiyor_de(kaynak.get(anahtar), 16)
        if denenen != BILINMIYOR:
            alt_ajan = denenen
            break
    if alt_ajan: break
if not alt_ajan:
    alt_ajan = bilinmiyor_de(is_kaydi.get("agent"), 16)
if alt_ajan == BILINMIYOR:
    alt_ajan = bilinmiyor_de(nobet_data.get("provider"), 12)
if izleyici: alt_ajan = BILINMIYOR
# Is listesi varsa ondan secilir; nobet satirindaki kimlik yalnizca liste
# hic yoksa kullanilir. Boylece bitmis is (isimiz listede degilse) gosterilmez.
if not is_id and not jobs and nobet_data.get("job_id"):
    is_id = clean(nobet_data.get("job_id"), 40)
# Model ve effort sirasi (EK 8 KESIN KURAL):
#   1) IS KAYDININ GERCEK CAGRi KAYDI (subagent_model / subagent_effort) -
#      adaptörün fiilen başlattığı süreç bilgisi.
#   2) nobet satırındaki aynı kayıt.
#   3) Yalnız 1 ve 2 yoksa sağlayıcının kendi etkin ayarı (EK 8 madde 1).
# Tahmin, router önerisi veya sabit varsayılan ASLA kullanılmaz.
is_model = bilinmiyor_de(is_kaydi.get("subagent_model"), 32)
if is_model == BILINMIYOR: is_model = bilinmiyor_de(is_kaydi.get("model"), 32)
if is_model == BILINMIYOR: is_model = bilinmiyor_de(is_kaydi.get("model_id"), 32)
is_effort = bilinmiyor_de(is_kaydi.get("subagent_effort"), 16)
if is_effort == BILINMIYOR: is_effort = bilinmiyor_de(is_kaydi.get("effort"), 16)
if is_effort == BILINMIYOR: is_effort = bilinmiyor_de(is_kaydi.get("variant"), 16)
if is_model == BILINMIYOR: is_model = bilinmiyor_de(nobet_data.get("model"), 32)
if is_effort == BILINMIYOR: is_effort = bilinmiyor_de(nobet_data.get("effort"), 16)
# Renk ve 3. kademe ayar okuma GERCEK saglayiciye gore yapilir; alt-ajan adi
# ("opencode", "codex", "flash") saglayiciyle ayni olmayabilir.
nobet_provider = bilinmiyor_de(nobet_data.get("provider"), 12)
if nobet_provider == BILINMIYOR:
    nobet_provider = bilinmiyor_de(is_kaydi.get("agent"), 16)
# EK 8 KESIN KURAL: izleyici kapali/bayatsa router onerisi ve saglayici ayari
# HIC kullanilmaz; hicbir dogrulanabilir kayit yoktur.
ns_saglayici, ns_model, ns_bolumler = ("", "", []) if izleyici else nobet_ayikla(nobet_provider)
if not izleyici:
    if alt_ajan == BILINMIYOR and ns_saglayici: alt_ajan = clean(ns_saglayici, 12)
    if is_model == BILINMIYOR and ns_model: is_model = bilinmiyor_de(ns_model, 32)
    for bolum in ns_bolumler:
        parcalar = bolum.split(None, 1)
        if parcalar[0] == "effort" and is_effort == BILINMIYOR and len(parcalar) > 1:
            is_effort = bilinmiyor_de(parcalar[1], 16)
    if is_model == BILINMIYOR or is_effort == BILINMIYOR:
        ayar_model, ayar_effort = ayar_model_effort(nobet_provider, repo)
        if is_model == BILINMIYOR: is_model = ayar_model or BILINMIYOR
        if is_effort == BILINMIYOR: is_effort = ayar_effort or BILINMIYOR
if izleyici:
    is_model = is_effort = nobet_provider = BILINMIYOR
    ns_bolumler = []
nobet_model = pad(is_model[6:] if len(is_model) > 10 and is_model.startswith("space-") else is_model, 10)
nobet_effort = is_effort if is_effort != BILINMIYOR else "?"
# Sag blok: alt ajan + fast + is kimligi (saglayici satirlariyla tekrar yok).
nobet_rest = [alt_ajan] if alt_ajan not in ("", BILINMIYOR) else [BILINMIYOR]
# fast once is kaydinin gercek cagri kaydindan, sonra nobet satirindan okunur.
# KISALTMA ONCESI denetlenir: "bilinmiyor" 4 harfe kisaltilip gecmemeli.
def bilinmiyor_mu(deger):
    return deger in (None, "", "?", BILINMIYOR)
nobet_fast = is_kaydi.get("subagent_fast")
if bilinmiyor_mu(nobet_fast): nobet_fast = nobet_data.get("fast")
if bilinmiyor_mu(nobet_fast):
    # EK 10: nobet_satiri gercek fast degerini de (CODEX_HIZLI) bildirir.
    nobet_fast = ""
    for bolum in ns_bolumler:
        parcalar = bolum.split(None, 1)
        if parcalar[0] == "fast" and len(parcalar) > 1: nobet_fast = parcalar[1]
    nobet_fast = clean(nobet_fast, 4) if nobet_fast else "?"
else:
    nobet_fast = clean(nobet_fast, 4)
if nobet_fast != "?": nobet_rest.append("fast " + nobet_fast)
# EK 10: nobet_satiri den ek bilgiler (orn. "OpenCode Zen", "derin: pro")
# sag blokta gosterilir; effort ve fast zaten kendi hucrelerinde var.
for bolum in ns_bolumler:
    parcalar = bolum.split(None, 1)
    if parcalar[0] in ("effort", "fast"): continue
    if bolum not in nobet_rest: nobet_rest.append(bolum)
if is_id: nobet_rest.append("#" + is_id[-10:])
nobet_rest_text = " · ".join(nobet_rest)
if len(nobet_rest) == 1 and nobet_rest[0] == BILINMIYOR and izleyici:
    nobet_rest_text = "izleyici " + izleyici
metrics = mapping(snapshot.get("agent_metrics"))
def provider_cells(name):
    row = mapping(metrics.get(name))
    quota, tokens = mapping(row.get("quota")), mapping(row.get("tokens"))
    stale = ""
    updated = quota.get("updated_at")
    try:
        if updated is not None and time.time() - float(updated) > 900: stale = " eski"
    except (TypeError, ValueError): pass
    reset = quota.get("reset_at")
    ending = ARROW_RESET + " " + (provider_reset_time(reset) if reset is not None else "—") + stale
    # OPENCODE kota durumu 0/100 yerine acik/dolu olarak gelir; acikken sifirlama
    # saati yoktur, doluyken yeniden dolma saati vardir.
    state = quota.get("state")
    state = state.strip().casefold() if isinstance(state, str) else ""
    if state == "acik":
        return [pct(None), token_text(tokens.get("value")), "acik" + stale]
    if state == "dolu":
        return ["100", token_text(tokens.get("value")), "dolu, yen. " + (provider_reset_time(reset) if reset is not None else BILINMIYOR) + stale]
    return [pct(quota.get("value")), token_text(tokens.get("value")), ending]
claude_tokens = (ctx.get("total_input_tokens") or 0) + (ctx.get("total_output_tokens") or 0)
try: cost_text = "%.2f" % float(cost.get("total_cost_usd")) if cost.get("total_cost_usd") is not None else "?"
except (TypeError, ValueError, OverflowError): cost_text = "?"
try:
    model_mtok = m_kisa(float(cost.get("total_cost_usd") or 0) * 1e6 / claude_tokens) if claude_tokens > 0 else "$?"
except (TypeError, ValueError, ZeroDivisionError, OverflowError): model_mtok = "$?"
fields = [pct(ctx.get("used_percentage")), pct(ctx.get("remaining_percentage")), cost_text,
          pct(five.get("used_percentage")), pct(seven.get("used_percentage")), model, effort,
          local_time(five.get("resets_at")), local_time(seven.get("resets_at"), gun=True), token_text(claude_tokens) if claude_tokens else BILINMIYOR,
          fast, thinking, model_mtok,
          nobet_provider, nobet_model, nobet_effort, nobet_rest_text, summary_text,
          pct(five.get("used_percentage")), token_text(claude_tokens) if claude_tokens else BILINMIYOR, ARROW_RESET + " " + (local_time(five.get("resets_at")) if five.get("resets_at") is not None else BILINMIYOR)]
for name in ("OPENCODE", "GEMINI", "CODEX"): fields += provider_cells(name)
nobet_cost = nobet_data.get("cost_mtok")
nobet_mtok = "$?"
if not izleyici and isinstance(nobet_cost, (int, float)) and not isinstance(nobet_cost, bool) and 0 <= nobet_cost < float("inf"):
    nobet_mtok = "$0" if nobet_cost == 0 else m_kisa(nobet_cost)
fields.append(nobet_mtok)
running = snapshot.get("calisan") if isinstance(snapshot.get("calisan"), list) else []
running = [item for item in running if isinstance(item, dict)]
running.sort(key=lambda item: -(item.get("basladi") or 0))
running_parts = []

def tam_gorev(value):
    # Gorev adini burada tekrar kesme; bos/kesik kayit tamamlanmalidir.
    text = clean(value, len(str(value or "")) + 1)
    if text.casefold() in ("", "?", BILINMIYOR, "gorev?") or text.endswith(("…", "...")): return ""
    return text

def gorev_adi(item):
    task = tam_gorev(item.get("gorev"))
    if not task:
        job = job_lookup.get(str(item.get("job_id") or item.get("id")), {})
        task = tam_gorev(job.get("task"))
    return task or "gorev?"

for item in running[:2]:
    name = bilinmiyor_de(item.get("ajan"), 24)
    actual_model = bilinmiyor_de(item.get("model"), 64)
    level = bilinmiyor_de(item.get("effort"), 16)
    elapsed = item.get("elapsed_seconds")
    duration = str(int(elapsed // 60)) + "dk" if isinstance(elapsed, (int, float)) and elapsed >= 60 else str(int(elapsed)) + "sn" if isinstance(elapsed, (int, float)) else BILINMIYOR
    first = (name + " " + actual_model)
    # Keep column 25/33 separators fixed; preserve the full model after them.
    row = name[:15].ljust(15) + " │ " + level[:5].rjust(5) + " │ " + actual_model + " · " + duration if not running_parts else first + " · " + level + " · " + duration
    if item.get("tur") and item.get("max"): row += " · tur {}/{}".format(item["tur"], item["max"])
    gorev_kisa = gorev_adi(item)
    row += " · " + (gorev_kisa if len(gorev_kisa) <= 28 else gorev_kisa[:27].rstrip() + "…")
    running_parts.append(row)
running_text = " · ".join(running_parts) if running_parts else "boşta".ljust(15) + " │ "
if len(running) > 2: running_text += " · +" + str(len(running) - 2)
fields.append(running_text)
local_agents = []
now = time.time()
agent_dir = os.path.expanduser("~/.claude/.calisan_ajanlar")
try:
    entries = sorted(os.listdir(agent_dir))
except OSError:
    entries = []
for entry in entries:
    if not entry.endswith(".json"): continue
    try:
        with open(os.path.join(agent_dir, entry), encoding="utf-8") as stream:
            record = json.load(stream)
        if not isinstance(record, dict): continue
        started = record.get("baslangic")
        if not number(started): continue
        elapsed = now - started
        if elapsed < 0 or elapsed > 3 * 3600: continue
        name = clean(record.get("ajan"), 24)
        if name == "?": continue
        seconds = int(elapsed)
        if seconds >= 660:
            color_code = "[38;2;255;80;80m"
            warning = "⚠ "
            if seconds >= 3600:
                duration = str(seconds // 3600) + "sa" + str(seconds % 3600 // 60) + "dk"
            else:
                duration = str(seconds // 60) + "dk"
        else:
            color_code = "[38;2;0;255;65m"
            warning = "◉ "
            if seconds >= 3600:
                duration = str(seconds // 3600) + "sa" + str(seconds % 3600 // 60) + "dk"
            elif seconds >= 60:
                duration = str(seconds // 60) + "dk"
            else:
                duration = str(seconds) + "sn"
        local_agents.append(color_code + warning + name + "[38;5;255m " + duration)
    except (OSError, ValueError, TypeError, OverflowError):
        continue
agent_parts = local_agents[:4]
if len(local_agents) > 4:
    agent_parts.append("\033[38;5;255m+" + str(len(local_agents) - 4))
fields.append("\033[38;5;240m · ".join(agent_parts))

sys.stdout.buffer.write("\n".join(str(value) for value in fields).encode("utf-8"))
')
mapfile -t fields <<< "$parsed"
used_pct="${fields[0]:-?}"; remaining_pct="${fields[1]:-?}"; cost_usd="${fields[2]:-?}"
five_pct="${fields[3]:-?}"; seven_pct="${fields[4]:-?}"; model="${fields[5]:-bilinmiyor }"
effort="${fields[6]:-}"; five_reset="${fields[7]:-?}"; week_reset="${fields[8]:-?}"
claude_tokens="${fields[9]:-?}"; fast_mode="${fields[10]:-}"; thinking="${fields[11]:-}"
model_mtok="${fields[12]:-bilinmiyor}"
nobet_provider="${fields[13]:-bilinmiyor}"; nobet_model="${fields[14]:-bilinmiyor}"; nobet_effort="${fields[15]:-?}"; nobet_rest="${fields[16]:-}"
summary="${fields[17]:-● main}"
claude_pct="${fields[18]:-?}"; claude_token="${fields[19]:-?}"; claude_reset="${fields[20]:-?}"
open_pct="${fields[21]:-?}"; open_token="${fields[22]:-?}"; open_reset="${fields[23]:-?}"
gem_pct="${fields[24]:-?}"; gem_token="${fields[25]:-?}"; gem_reset="${fields[26]:-?}"
cod_pct="${fields[27]:-?}"; cod_token="${fields[28]:-?}"; cod_reset="${fields[29]:-?}"

# EK 11 (ZORUNLU): cubuktaki TUM yardimci yazilar OBEK bazinda SIRAYLA
# renklendirilir. "│" veya "·" ile ayrilmis her ifade bir obektir; obekler
# matrix yesili (38;2;0;255;65) ile koyu gri (38;5;240) arasinda donusumlu
# (yesil, koyu gri, yesil, koyu gri...) siralanir; yan yana iki obek ASLA ayni
# renkte olmaz. Bir obegin kelimeleri kendi icinde tek renktedir. Ayiricilar
# (│ ve ·) koyu gri kalir. DegistirilMEYENler: MODEL/NOBET/AJANLAR/saglayici/
# Baglam-5H-7D baslik renkleri, model moru/beyazi, seviye renkleri
# (low/mid/high/xhigh), saglayici etiket-dolu cubuk-token renkleri, bos cubuk
# (koyu 237) ve NÖBET veri duzeltmesi.
DIM=$'\033[38;2;0;255;65m'; RESET=$'\033[0m'
# Obek yazilarinin ikinci rengi beyaz (30 Eyl: gri yerine); ayiricilar gri kalir
GRI=$'\033[38;5;255m'
SEP_C=$'\033[38;5;240m'
ORANGE=$'\033[38;5;209m'
LAVENDER=$'\033[1;38;5;141m'; SNOW=$'\033[1;38;5;255m'; TURKUAZ=$'\033[38;5;80m'; PEMBE=$'\033[38;5;212m'
CONTEXT=$'\033[38;5;141m'
# Baglam/5H/7D dolu cubuklari MODEL satirindaki model adiyla ayni renk (141)
BAR_C=$'\033[38;5;141m'
FIVE=$'\033[38;5;178m'; DIM_FIVE=$'\033[2;38;5;178m'
SEVEN=$'\033[38;5;160m'; DIM_SEVEN=$'\033[2;38;5;160m'
AJAN_GREEN=$'\033[38;5;41m'; ALERT=$'\033[1;38;5;196m'
NOBET_DEFAULT=$'\033[38;5;178m'
CLAUDE_C=$'\033[38;5;209m'
GEMINI_C=$'\033[38;5;69m'
OPENCODE_C=$'\033[38;5;179m'
CODEX_C=$'\033[38;5;41m'
# Bos cubuk kismi: koyu ve sakin (saglayici rengiyle karismaz)
EMPTY_C=$'\033[2;38;5;237m'

bar() {
  local value="$1" renk="$2" n=0 i
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    n=$(( value / 10 )); (( n > 10 )) && n=10
    printf '%b' "$renk"
    for ((i=0; i<n; i++)); do printf '%s' "$FULL"; done
    printf '%b' "$EMPTY_C"
    for ((i=n; i<10; i++)); do printf '%s' "$EMPTY"; done
  else
    printf '%b' "$EMPTY_C"
    for ((i=0; i<10; i++)); do printf '%s' "$UNKNOWN"; done
  fi
  printf '%b' "$RESET"
}

rate_bar() {
  local value="$1" renk="$2" n=0 i h=5
  [[ -n "${3:-}" ]] && h="$3"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    n=$(( value * h / 100 )); (( n > h )) && n=$h
    printf '%b' "$renk"
    for ((i=0; i<n; i++)); do printf '%s' "$FULL"; done
    printf '%b' "$EMPTY_C"
    for ((i=n; i<h; i++)); do printf '%s' "$EMPTY"; done
  else
    printf '%b' "$EMPTY_C"
    for ((i=0; i<h; i++)); do printf '%s' "$UNKNOWN"; done
  fi
  printf '%b' "$RESET"
}
# Yuzde hucresi: bilinen deger yuzde, bilinmeyen deger — (uydurma yok)
pct_cell() {
  if [[ "$1" =~ ^[0-9]+$ ]]; then printf '%3s%%' "$1"; else printf '   —'; fi
}
# EK 11: obek tabanli kademeli renklendirme.
# OBEK_SIRA = siradaki yardimci obegin sira numarasi (0 = matrix yesili,
# 1 = koyu gri, 2 = yesil, ...). Satir basinda 0 a dondurulur.
OBEK_SIRA=0
# obek <sabit_genislik|0> <metin>
# Metin icindeki her "·" ile ayrilmis ifade AYRI bir obektir; obekler sirayla
# yesil / koyu gri alir ve aralarina koyu gri "·" ayiricisi girer.
# Sonuc: OBEK_METIN (ANSI'li). OBEK_SIRA sonraki obek icin guncellenir.
# Tek obekli hucrelerde (yuzde, ucret, yenilenme saati) sira yine ilerler,
# boylece komsu obekle ayni renk dusebilmesi mumkun olmaz.
obek() {
  local w="$1" metin="$2" bolum s="" ilk=1
  OBEK_METIN=""
  while IFS= read -r bolum; do
    [[ -z "$bolum" ]] && continue
    s="$bolum"
    if [[ "$w" =~ ^[0-9]+$ ]] && (( w > 0 )); then printf -v s "%${w}s" "$bolum"; fi
    if (( ilk )); then ilk=0; else OBEK_METIN="${OBEK_METIN}${SEP_C}${DOT}${RESET}"; fi
    if (( OBEK_SIRA % 2 == 0 )); then OBEK_METIN="${OBEK_METIN}${DIM}${s}${RESET}"
    else OBEK_METIN="${OBEK_METIN}${GRI}${s}${RESET}"; fi
    OBEK_SIRA=$(( OBEK_SIRA + 1 ))
  done < <(printf '%s\n' "${metin//$DOT/$'\n'}")
}
# Baglam satiri yuzdeleri: obek sirasi ilerler ama renk mor (BAR_C)
# Verilen renkle mor_obek (5H sari, 7D kirmizi yuzdeleri icin)
ren_obek() {
  local saklanan="$BAR_C"
  BAR_C="$1"
  mor_obek "${@:2}"
  BAR_C="$saklanan"
}
mor_obek() {
  local w="$1" s="$2"
  obek "$w" "$s"
  if [[ "$w" =~ ^[0-9]+$ ]] && (( w > 0 )); then printf -v s "%${w}s" "$s"; fi
  OBEK_METIN="${BAR_C}${s}${RESET}"
}
effort_kisa() {
  case "$1" in
    medium|med) printf 'med' ;;
    '?'|bilinmiyor|'-'|'') printf '—' ;;
    *) printf '%.5s' "$1" ;;
  esac
}
# EK 8: NOBET seviyesi gercek effort degerini gosterir; hicbir kaynakta yoksa
# acikca "?" (uydurma yok).
nobet_effort_kisa() {
  case "$1" in
    medium|med) printf 'med' ;;
    '?'|bilinmiyor|'-'|'') printf '—' ;;
    *) printf '%.5s' "$1" ;;
  esac
}
# seviye_hucre <kisaltilmis_metin> <ham_deger>
# Bilinen seviye kendi rengini alir (low/mavi-mor, medium mavi, high sari,
# xhigh kirmizi - DEGISMEZ). Bilinmeyen seviye ("?" / "—") bir yardimci obektir:
# kademeli renk dizisine girer, boylece komsu obekle ayni renk olmaz.
seviye_hucre() {
  local metin="$1" deger="$2" renk=""
  case "$deger" in
    low) renk=$'\033[1;38;5;72m' ;;
    medium|med) renk=$'\033[1;38;5;111m' ;;
    high) renk=$'\033[1;38;5;220m' ;;
    xhigh|max) renk=$'\033[1;38;5;203m' ;;
    *) obek 5 "$metin"; SEVIYE_HUCRE="$OBEK_METIN"; return ;;
  esac
  printf -v SEVIYE_HUCRE '%b%5s%b' "$renk" "$metin" "$RESET"
}
# Ortak kolon izgarasi: etiket(8) bosluk deger(10) bosluk ilk hucre bosluk
# PIPE bosluk seviye/token bosluk PIPE bosluk kalan
#   $1 etiket rengi  $2 etiket  $3 deger  $4 deger rengi
#   $5 renkli ilk hucre (obek)  $6 renkli seviye/token  $7 renkli kalan (obek)
# Hucreler ANSI'li olarak ONCEDEN hazirlanir (genislik kirpmasi icin dolgu
# obek() icinde yapilir), bu yuzden burada %s kullanilir.
# Ayiricilar koyu gridir (EK 11).
hizali_satir() {
  printf '%b%-8s%b %b%-10s%b %s %b%b%b %s %b%b%b %s%b' \
    "$1" "$2" "$RESET" "$4" "$3" "$RESET" "$5" \
    "$SEP_C" "$PIPE" "$RESET" "$6" \
    "$SEP_C" "$PIPE" "$RESET" "$7" "$RESET"
}
satir() { hizali_satir "$@"; printf '\n'; }

# 1) MODEL — baslik turuncu, model mor, ucret ve hiz/dusunme durumu OBEG sirasi
model_more=""
[[ -n "$fast_mode" ]] && model_more="fast $fast_mode"
[[ -n "$thinking" ]] && model_more="${model_more:+$model_more $DOT }thinking $thinking"
OBEK_SIRA=0
# Maliyet, seviye ve kalan hucre model adiyla ayni renkte (LAVENDER)
printf -v m_mtok '%b%4s%b' "$TURKUAZ" "$model_mtok" "$RESET"
printf -v m_seviye '%b%5s%b' "$TURKUAZ" "$(effort_kisa "$effort")" "$RESET"
printf -v m_more '%b%s%b' "$TURKUAZ" "$model_more" "$RESET"
satir "$TURKUAZ" MODEL "$model" "$TURKUAZ" "$m_mtok" "$m_seviye" "$m_more"

# 2) NOBET — ajan/model adi beyaz, seviye sari, saglayici + job bilgisi gri
# Maliyet: taze yerel izleyiciden USD / 1M token; veri yoksa $?.
# ASCII maliyet hucresi 4 kolon, ucretsiz model $0 olarak gosterilir.
case "$(printf '%s' "$nobet_provider" | tr '[:lower:]' '[:upper:]')" in
  OPENCODE) ncolor="$OPENCODE_C" ;;
  GEMINI) ncolor="$GEMINI_C" ;;
  CODEX) ncolor="$CODEX_C" ;;
  CLAUDE) ncolor="$ORANGE" ;;
  *) ncolor="$NOBET_DEFAULT" ;;
esac
# EK 11 obek sirasi: 1) bilinmeyen maliyet  2) seviye (bilinmiyse obek olarak)
# 3+) alt ajan / fast / ek bilgi / job kimligi (her biri ayri obek)
OBEK_SIRA=0
# Maliyet, seviye ve kalan hucre model adiyla ayni renkte (SNOW)
printf -v n_ucret '%b%4s%b' "$PEMBE" "${fields[30]:-$?}" "$RESET"
printf -v n_seviye '%b%5s%b' "$PEMBE" "$(nobet_effort_kisa "$nobet_effort")" "$RESET"
printf -v n_rest '%b%s%b' "$PEMBE" "$nobet_rest" "$RESET"
satir "$PEMBE" NOBET "$nobet_model" "$PEMBE" "$n_ucret" "$n_seviye" "$n_rest"


# 3 Eki (kullanici kurali): CALISAN, AJANLAR ve gece kuyrugu satirlari ana cubukta BASILMAZ;
# calisan ajanlar Claude Code alt-ajan panelinde (subagentStatusLine) gorunur. Duzen KILITLI.
# 4-7) Saglayici satirlari — etiket, dolu cizbik ve token ayni renkte; yuzde ve
# yenilenme saati OBEK sirasi (yesil, koyu gri)
saglayici_satir() {
  local renk="$1" etiket="$2" yuzde="$3" token="$4" yenilenme="$5" p t
  OBEK_SIRA=0
  printf -v p '%b%s%b' "$renk" "$(pct_cell "$yuzde")" "$RESET"
  printf -v t '%b%5s%b' "$renk" "$token" "$RESET"
  local y
  printf -v y '%b%s%b' "$renk" "$yenilenme" "$RESET"
  satir "$renk" "$etiket" "$(bar "$yuzde" "$renk")" "" "$p" "$t" "$y"
}
saglayici_satir "$CLAUDE_C" CLAUDE "$five_pct" "$claude_token" "$claude_reset"
saglayici_satir "$GEMINI_C" GEMINI "$gem_pct" "$gem_token" "$gem_reset"
saglayici_satir "$OPENCODE_C" OPENCODE "$open_pct" "$open_token" "$open_reset"
saglayici_satir "$CODEX_C" CODEX "$cod_pct" "$cod_token" "$cod_reset"

# 8) Baglam + 5H + 7D — baslik ve cizbik yesil, 5H sari, 7D pembe
# Dar terminalde tasma: yuzde ve yenilenme saati HIC kesilmez; onceki bolumler kisalir.
GENISLIK="${COLUMNS:-0}"
[[ "$GENISLIK" =~ ^[0-9]+$ ]] || GENISLIK=0
if [[ -n "${AFUNOBET_DURUM_GENISLIK:-}" && "${AFUNOBET_DURUM_GENISLIK}" =~ ^[0-9]+$ ]]; then GENISLIK="$AFUNOBET_DURUM_GENISLIK"; fi
[[ "$GENISLIK" =~ ^[0-9]+$ ]] || GENISLIK=150
(( GENISLIK < 70 )) && GENISLIK=70
# ANSI renk kodlarini saymadan gorunur genislik olcer.
# Cok baytli karakterler once tek ASCII harfe indirgenir, sonra ${#s} ile olculur.
gizli_uzunluk() {
  local s="$1" on="" kalan i ch
  while [[ "$s" == *$'\033['* ]]; do
    kalan="${s#*$'\033['}"
    i=0
    while (( i < ${#kalan} )); do
      ch="${kalan:i:1}"
      [[ "$ch" == [0-9\;] ]] || break
      i=$(( i + 1 ))
    done
    [[ "${kalan:i:1}" == "m" ]] && i=$(( i + 1 ))
    on+="${s%%$'\033['*}"
    s="${kalan:i}"
  done
  s="${on}${s}"
  s="${s//█/H}"; s="${s//░/H}"; s="${s//▒/H}"; s="${s//│/|}"
  s="${s//↻/>}"; s="${s//·/.}"; s="${s//—/-}"
  s="${s//Bağlam/Baglam}"
  s="${s//ç/c}"; s="${s//ğ/g}"; s="${s//ı/i}"; s="${s//ö/o}"; s="${s//ş/s}"; s="${s//ü/u}"
  s="${s//Ç/C}"; s="${s//Ğ/G}"; s="${s//İ/I}"; s="${s//Ö/O}"; s="${s//Ş/S}"; s="${s//Ü/U}"
  printf '%s' "${#s}"
}
# Kisaltma sirasi: gun adi -> ucret -> kalan yuzde -> cubuk boyu.
# Yuzde ve yenilenme saati HICbir seviyede atlanmaz ve hicbir seviyede kesilmez.
baglam_satir() {
  local seviye="$1" gun=1 kalan=1 ucret=1 bes_bar=5 yedi_bar=5 bag_bar=10
  (( seviye >= 1 )) && gun=0
  (( seviye >= 2 )) && ucret=0
  (( seviye >= 3 )) && kalan=0
  (( seviye >= 4 )) && { bes_bar=4; yedi_bar=4; bag_bar=8; }
  (( seviye >= 5 )) && { bes_bar=3; yedi_bar=3; bag_bar=6; }
  (( seviye >= 6 )) && { bes_bar=2; yedi_bar=2; bag_bar=4; }
  local yedi_saat
  yedi_saat="${week_reset##* }"
  (( gun )) && yedi_saat="$week_reset"
  # EK 11: yardimci yazilar OBEK sirasiyla kademelendirilir (yesil, koyu gri,
  # yesil, koyu gri...): 1 Baglam yuzde, 2 ucret, 3 5H yuzde, 4 5H yenilenme,
  # 5 7D yuzde, 6 7D yenilenme. Baslik/bolum renkleri ve bos cubuk degismez.
  OBEK_SIRA=0
  if (( seviye >= 7 )); then
    # Son kademe: yalnizca zorunlu alanlar. Yuzde ve yenilenme saati yine tam.
    mor_obek 0 "$(pct_cell "$used_pct")"; o_bag="$OBEK_METIN"
    ren_obek "$FIVE" 0 "$(pct_cell "$five_pct")"; o_bes="$OBEK_METIN"
    mor_obek 0 "$ARROW $five_reset"; o_bes_yen="$OBEK_METIN"
    ren_obek "$SEVEN" 0 "$(pct_cell "$seven_pct")"; o_yedi="$OBEK_METIN"
    mor_obek 0 "$ARROW $yedi_saat"; o_yedi_yen="$OBEK_METIN"
    printf '%b%-8s%b ' "$CONTEXT" "$BAGLAM" "$RESET"
    printf '%b%s%b %s ' "$BAR_C" "$(rate_bar "$used_pct" "$BAR_C" 1)" "$RESET" "$o_bag"
    printf '%b%s%b ' "$SEP_C" "$PIPE" "$RESET"
    printf '%b5H%b %b%s%b %s ' "$DIM_FIVE" "$RESET" "$FIVE" \
      "$(rate_bar "$five_pct" "$FIVE" 1)" "$RESET" "$o_bes"
    printf '%s ' "$o_bes_yen"
    printf '%b%s%b ' "$SEP_C" "$PIPE" "$RESET"
    printf '%b7D%b %b%s%b %s ' "$DIM_SEVEN" "$RESET" "$SEVEN" \
      "$(rate_bar "$seven_pct" "$SEVEN" 1)" "$RESET" "$o_yedi"
    printf '%s\n' "$o_yedi_yen"
    return 0
  fi
  OBEK_SIRA=0
  mor_obek 0 "$(pct_cell "$used_pct")"; b_yuzde="$OBEK_METIN"
  # Kalan yuzde hucre 5 karakterlik kolona sigdirilir (kolon izgarasi degismez).
  if (( kalan )); then mor_obek 5 "$(pct_cell "$remaining_pct")"
  else obek 5 "   -"; fi
  b_kalan="$OBEK_METIN"
  if (( ucret )); then mor_obek 0 "$(printf '%s %s' '$' "$cost_usd")"
  else mor_obek 0 "—"; fi
  b_ucret="$OBEK_METIN"
  hizali_satir "$CONTEXT" "$BAGLAM" "$(rate_bar "$used_pct" "$BAR_C" "$bag_bar")" "" \
    "$b_yuzde" "$b_kalan" "$b_ucret"
  # EK 11: 5H ve 7D bloklarinin yuzde + yenilenme ogeleri de ayni kademe
  # dizisine devam eder (yesil, koyu gri, yesil, koyu gri...).
  ren_obek "$FIVE" 0 "$(pct_cell "$five_pct")"; b_bes="$OBEK_METIN"
  mor_obek 0 "$ARROW $five_reset"; b_bes_yen="$OBEK_METIN"
  ren_obek "$SEVEN" 0 "$(pct_cell "$seven_pct")"; b_yedi="$OBEK_METIN"
  mor_obek 0 "$ARROW $yedi_saat"; b_yedi_yen="$OBEK_METIN"
  printf ' %b%b%b %b%b%b %b%s%b %s %s' "$SEP_C" "$PIPE" "$RESET" "$DIM_FIVE" 5H "$RESET" \
    "$FIVE" "$(rate_bar "$five_pct" "$FIVE" "$bes_bar")" "$RESET" "$b_bes" "$b_bes_yen"
  printf ' %b%b%b %b%b%b %b%s%b %s %s\n' "$SEP_C" "$PIPE" "$RESET" "$DIM_SEVEN" 7D "$RESET" \
    "$SEVEN" "$(rate_bar "$seven_pct" "$SEVEN" "$yedi_bar")" "$RESET" "$b_yedi" "$b_yedi_yen"
}
satir_kisa=""
for seviye in 0 1 2 3 4 5 6 7; do
  satir_kisa="$(baglam_satir "$seviye")"
  (( $(gizli_uzunluk "$satir_kisa") <= GENISLIK )) && break
done
printf '%s\n' "$satir_kisa"
