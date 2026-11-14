#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INP / etkilesim gecikmesi olcumu — ALMASIK ve TEKRARLI.

Neden bu arac var:
  Tek olcum YALAN SOYLER. Ilk cagri derleme + ilk layout maliyeti tasir
  (soguk baslangic), ve arka arkaya olculen iki yontemde ONCE calisan
  dezavantajli/avantajli cikar (sira yanliligi).
  Bu arac ikisini de kirar: A,B,A,B... almasik + medyan.

Kullanim:
  python inp_olc.py <url> --tik ".hero-chip[data-cat=esans]" [--tekrar 10]
  python inp_olc.py <url> --js "renderProducts()" --tekrar 12
  python inp_olc.py <url> --js "renderProducts()" --karsilastir ".kategori-satir{content-visibility:visible}"

Cikti: medyan/min/maks ms + mobil tahmini (4x/6x) + karsilastirma varsa kazanc %.
Cikis kodu: 0 = olculdu, 1 = hata.
"""
import argparse, json, os, statistics, subprocess, sys, tempfile

JS_OLC = r"""
async (args) => {
  const bekle = ms => new Promise(r => setTimeout(r, ms));
  // TUZAK: eval/new Function KULLANMA — sitede CSP 'unsafe-eval' kapali olabilir
  // (bazi sitelerde kapali, bilincli guvenlik karari). Bunun yerine
  // "fnAdi" veya "fnAdi(arg1,arg2)" bicimini elle cozup window[fnAdi] cagiririz.
  const cagir = (kod) => {
    const m = kod.match(/^\s*([A-Za-z_$][\w$]*)\s*\((.*)\)\s*;?\s*$/);
    if (!m) {
      const f = window[kod.trim()];
      if (typeof f === 'function') return f();
      throw new Error('Cozulemedi (CSP nedeniyle eval yok): ' + kod);
    }
    const fn = window[m[1]];
    if (typeof fn !== 'function') throw new Error('Fonksiyon yok: ' + m[1]);
    const ham = m[2].trim();
    const argl = ham ? JSON.parse('[' + ham.replace(/'/g, '"') + ']') : [];
    return fn.apply(window, argl);
  };
  const olcBir = async (kod) => {
    // Layout'u zorla ki paint maliyeti de olcume girsin
    const t0 = performance.now();
    cagir(kod);
    document.body.offsetHeight;
    return performance.now() - t0;
  };
  const isinma = 2, N = args.tekrar;
  const A = [], B = [];
  for (let i = 0; i < isinma; i++) { await olcBir(args.js); await bekle(50); }
  for (let i = 0; i < N; i++) {
    A.push(await olcBir(args.js)); await bekle(args.ara);
    if (args.karsilastirCss) {
      const st = document.createElement('style'); st.id = '__karsi';
      st.textContent = args.karsilastirCss;
      document.head.appendChild(st); await bekle(80);
      B.push(await olcBir(args.js)); await bekle(args.ara);
      st.remove(); await bekle(80);
    }
  }
  return { A, B };
}
"""


def med(v):
    return round(statistics.median(v), 1) if v else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--js", help="Olculecek JS ifadesi (or: renderProducts())")
    p.add_argument("--tik", help="Tiklanacak CSS secici (gercek INP olcumu)")
    p.add_argument("--tekrar", type=int, default=10)
    p.add_argument("--ara", type=int, default=60, help="Olcumler arasi bekleme ms")
    p.add_argument("--bekle", type=int, default=2500,
                   help="Sayfa acildiktan sonra veri/render icin bekleme ms")
    p.add_argument(
        "--karsilastir",
        help="Karsilastirma icin gecici CSS (ozelligi KAPATIR, kazanci olcer)",
    )
    p.add_argument("--mobil-carpan", default="4,6", help="Mobil CPU tahmin carpanlari")
    a = p.parse_args()

    if not a.js and not a.tik:
        print("HATA: --js veya --tik ver.", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: playwright yok. Kur: pip install playwright && playwright install chromium",
              file=sys.stderr)
        return 1

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 844})  # mobil varsayilan
        # TUZAK: networkidle kullanma — analytics (GA/Clarity/Yandex) surekli
        # istek attigi icin bu sitelerde ASLA gerceklesmez, 60sn timeout yer.
        pg.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(a.bekle)  # JS'in veri cekmesi + ilk render bitsin

        sonuc = {}
        if a.tik:
            # GERCEK INP: tarayicinin kendi olcumu (interactionId sadece gercek girdide gelir)
            pg.evaluate("""() => {
              window.__inp = [];
              new PerformanceObserver(l => { for (const e of l.getEntries())
                if (e.interactionId) window.__inp.push({ad:e.name, sure:+e.duration.toFixed(1),
                  islem:+(e.processingEnd-e.processingStart).toFixed(1)});
              }).observe({type:'event', buffered:true, durationThreshold:0});
            }""")
            try:
                pg.click(a.tik, timeout=10000)
            except Exception as e:
                print(f"HATA: tiklanamadi ({a.tik}): {e}", file=sys.stderr)
                b.close()
                return 1
            pg.wait_for_timeout(700)
            olaylar = pg.evaluate("() => window.__inp || []")
            if olaylar:
                sonuc["INP_ms"] = max(o["sure"] for o in olaylar)
                sonuc["islem_ms"] = max(o["islem"] for o in olaylar)
                sonuc["olaylar"] = olaylar
            else:
                sonuc["uyari"] = "interactionId gelmedi (headless sinirlamasi olabilir)"

        if a.js:
            r = pg.evaluate(
                JS_OLC,
                {"js": a.js, "tekrar": a.tekrar, "ara": a.ara,
                 "karsilastirCss": a.karsilastir or ""},
            )
            A, B = r["A"], r["B"]
            sonuc["olculen_ms"] = {"medyan": med(A), "min": round(min(A), 1),
                                   "maks": round(max(A), 1), "orneklem": len(A)}
            if B:
                mA, mB = med(A), med(B)
                sonuc["karsilastirma"] = {
                    "ozellik_ACIK_ms": mA, "ozellik_KAPALI_ms": mB,
                    "kazanc_yuzde": round((mB - mA) / mB * 100) if mB else None,
                }
        b.close()

    # Mobil tahmini
    temel = (sonuc.get("INP_ms")
             or (sonuc.get("olculen_ms") or {}).get("medyan"))
    if temel:
        sonuc["mobil_tahmin_ms"] = {
            f"{c}x": round(temel * float(c))
            for c in a.mobil_carpan.split(",")
        }
        sonuc["esik"] = "INP: <200ms iyi, 200-500 iyilestirme, >500 kotu"

    print(json.dumps(sonuc, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
