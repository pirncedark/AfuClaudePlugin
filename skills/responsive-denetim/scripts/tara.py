#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
responsive-denetim / tara.py
Bir yerel HTML sayfasini bir dizi viewport genisliginde headless Chrome ile acar,
her viewport icin (1) ekran goruntusu alir, (2) OTOMATIK bozulma tespiti yapar:
  - yatay tasma (body/html scrollWidth > innerWidth)  -> en sik responsive bug
  - dev element (bir kartin/gorselin viewport'un buyuk kismini kaplamasi)
  - min-width:auto flex-item tuzagi (bu oturumdaki 769-900px bug'inin imzasi)

Kullanim:
  python tara.py <yerel_html_yolu> [--sel ".shop-card"] [--w 360,414,600,700,768,850,898,1024,1280]
                 [--out <klasor>] [--acik]   # --acik: tespit yoksa da tum ss'leri tut

Cikti: <out>/rapor.json + ss_<W>.png dosyalari. Konsola ozet + BOZUK viewport listesi.
Cikis kodu: bozulma bulunmazsa 0, bulunursa 1 (push oncesi CI-gibi kapi).

NOT: Chrome yolu otomatik bulunur; bulunamazsa CHROME env degiskeni ile ver.
"""
import json, os, subprocess, sys, tempfile, argparse, shutil

def chrome_bul():
    if os.environ.get("CHROME") and os.path.exists(os.environ["CHROME"]):
        return os.environ["CHROME"]
    adaylar = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome"),
    ]
    for a in adaylar:
        if a and os.path.exists(a):
            return a
    sys.exit("HATA: Chrome/Edge bulunamadi. CHROME=... ile yol ver.")

# Sayfada calisip bozulma metrikleri toplayan JS. Sonuc window.__RD_SONUC'a yazilir.
JS_OLC = r"""
(function(SEL){
  var de = document.documentElement, body = document.body;
  var vw = window.innerWidth;
  var yatayTasma = Math.max(de.scrollWidth, body.scrollWidth) - vw;
  var kartlar = SEL ? Array.prototype.slice.call(document.querySelectorAll(SEL)) : [];
  var enGenisKart = 0, devKartSayisi = 0, kartDetay = [];
  kartlar.forEach(function(el){
    var r = el.getBoundingClientRect();
    if (r.width > enGenisKart) enGenisKart = Math.round(r.width);
    // Dev kart: tek kart viewport'un %70'inden genis (grid/flex cokmesi imzasi)
    if (r.width > vw * 0.70) devKartSayisi++;
    kartDetay.push({w: Math.round(r.width), h: Math.round(r.height)});
  });
  // Herhangi bir elementin viewport'tan tasip tasmadigini kabaca yakala
  var tasanEleman = 0, hepsi = document.querySelectorAll('body *');
  for (var i=0;i<hepsi.length;i++){
    var rr = hepsi[i].getBoundingClientRect();
    if (rr.right - vw > 2 && rr.width > 0 && getComputedStyle(hepsi[i]).position !== 'fixed') { tasanEleman++; if (tasanEleman>50) break; }
  }
  return {
    vw: vw,
    yatayTasma: yatayTasma,          // >2px ise sayfa yatay kayiyor (BUG)
    enGenisKart: enGenisKart,
    devKartSayisi: devKartSayisi,    // >0 ise kart cokmesi (BUG)
    tasanEleman: tasanEleman,
    kartSayisi: kartlar.length
  };
})
"""

import re, base64, glob

def olc(chrome, url, w, out, sel, yol):
    """Tek viewport: ekran goruntusu + metrik. Metrigi hedef HTML'in bir kopyasina
    olcum scripti enjekte ederek (ayni klasor → rel yollar korunur) toplar."""
    ss = os.path.join(out, f"ss_{w}.png")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size={w},900",
                    f"--screenshot={ss}", url],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    metrik = _metrik_al(chrome, w, sel, yol)
    metrik["ss"] = ss if os.path.exists(ss) else None
    return metrik

def _metrik_al(chrome, w, sel, yol):
    """Hedef HTML icerigini oku, </body> oncesine JS_OLC enjekte et, ayni klasore
    gecici kopya yaz (rel css/img yollari calissin), --dump-dom ile RD::<json> oku.
    Base64 kullanilir → HTML-encode/quote sorunu olmaz."""
    sel_js = json.dumps(sel or "")
    src = open(yol, encoding="utf-8", errors="replace").read()
    enjekte = f"""
<script>window.addEventListener('load',function(){{setTimeout(function(){{
  try{{ var r=({JS_OLC})({sel_js});
    var el=document.createElement('div'); el.id='__RD__';
    el.textContent='RD::'+btoa(unescape(encodeURIComponent(JSON.stringify(r))));
    document.body.appendChild(el);
  }}catch(e){{ var el=document.createElement('div'); el.id='__RD__';
    el.textContent='RD_HATA::'+String(e); document.body.appendChild(el); }}
}},400);}});</script>
"""
    kopya = src.replace("</body>", enjekte + "</body>", 1) if "</body>" in src else src + enjekte
    kdosya = os.path.join(os.path.dirname(yol), f"__rd_{w}.html")
    open(kdosya, "w", encoding="utf-8").write(kopya)
    kurl = "file:///" + kdosya.replace("\\", "/")
    try:
        p = subprocess.run([chrome, "--headless=new", "--disable-gpu",
                            f"--window-size={w},900",
                            "--virtual-time-budget=3000", "--dump-dom", kurl],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=90)
        dom = p.stdout or ""
        m = re.search(r"RD::([A-Za-z0-9+/=]+)", dom)
        if m:
            return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
        mh = re.search(r"RD_HATA::([^<]+)", dom)
        if mh:
            return {"vw": w, "hata": mh.group(1)}
        return {"vw": w, "hata": "metrik okunamadi"}
    finally:
        try: os.unlink(kdosya)
        except OSError: pass

def bozuk_mu(m):
    """Bir viewport metrigini degerlendir; bozulma sebeplerini dondurur (bos = temiz)."""
    if "hata" in m:
        return [f"olcum hatasi: {m['hata']}"]
    sebep = []
    if m.get("yatayTasma", 0) > 2:
        sebep.append(f"yatay tasma {m['yatayTasma']}px (sayfa saga kayiyor)")
    if m.get("devKartSayisi", 0) > 0:
        sebep.append(f"{m['devKartSayisi']} dev kart (viewport %70+; grid/flex cokmesi)")
    return sebep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--sel", default=".shop-card", help="kart/kutu CSS secici(dev-kart tespiti icin)")
    ap.add_argument("--w", default="360,414,600,700,768,850,898,1024,1280",
                    help="virgullu viewport genislikleri")
    ap.add_argument("--out", default=None)
    ap.add_argument("--acik", action="store_true", help="temiz viewport ss'lerini de tut")
    a = ap.parse_args()

    yol = os.path.abspath(a.html)
    if not os.path.exists(yol):
        sys.exit(f"HATA: dosya yok: {yol}")
    url = "file:///" + yol.replace("\\", "/")
    chrome = chrome_bul()
    out = a.out or os.path.join(tempfile.gettempdir(), "responsive_denetim")
    os.makedirs(out, exist_ok=True)
    genislikler = [int(x) for x in a.w.split(",") if x.strip()]

    rapor, bozuklar = [], []
    for w in genislikler:
        m = olc(chrome, url, w, out, a.sel, yol)
        sebep = bozuk_mu(m)
        m["bozuk"] = bool(sebep); m["sebep"] = sebep
        rapor.append(m)
        durum = "BOZUK" if sebep else "ok"
        print(f"  {w:>5}px  {durum:<5}  kart:{m.get('kartSayisi','?')} "
              f"enGenis:{m.get('enGenisKart','?')} tasma:{m.get('yatayTasma','?')}"
              + (("  -> " + "; ".join(sebep)) if sebep else ""))
        if sebep:
            bozuklar.append(w)
        elif not a.acik and m.get("ss") and os.path.exists(m["ss"]):
            os.unlink(m["ss"])  # temizse ss tutma (bozuklarin ss'i incelensin)

    json.dump({"html": yol, "sel": a.sel, "rapor": rapor},
              open(os.path.join(out, "rapor.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\nRAPOR: {os.path.join(out, 'rapor.json')}")
    if bozuklar:
        print(f"BOZUK VIEWPORT'LAR: {bozuklar}")
        print(f"Ekran goruntuleri: {out}\\ss_<W>.png  (Read tool ile incele)")
        sys.exit(1)
    print("TUM VIEWPORT'LAR TEMIZ.")
    sys.exit(0)

if __name__ == "__main__":
    main()
