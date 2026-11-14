#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO indeksleme denetimi — robots.txt / noindex / sitemap tutarlilik taramasi.

Yakaladigi ASIL tuzak:
  Bir uc hem robots.txt'te "Disallow" hem de 200 donuyorsa, Google sayfayi
  CEKEMEZ -> noindex'i GOREMEZ -> linklerden dizine ekler.
  Search Console: "Robots.txt tarafindan engelleniyor olsa da dizine eklendi".
  Dogru cozum: Disallow KALDIR + X-Robots-Tag/meta noindex ver.

Kullanim:
  python indeks_denetim.py https://site.com
  python indeks_denetim.py https://site.com --sitemap-ornek 40

Cikis kodu: 0 = temiz, 1 = sorun bulundu.
"""
import argparse, re, sys, gzip
import urllib.parse, urllib.request, urllib.error  # urllib.error SART:
# yoksa "except urllib.error.HTTPError" satiri AttributeError firlatir ve
# tum HTTP hatalari sessizce "baglanilamadi (0)" gorunur.

UA = {"User-Agent": "Mozilla/5.0 (compatible; SEO-Denetim/1.0)"}


def cek(url, timeout=15, sadece_baslik=False):
    try:
        r = urllib.request.Request(url, headers=UA,
                                   method="HEAD" if sadece_baslik else "GET")
        with urllib.request.urlopen(r, timeout=timeout) as y:
            ham = b"" if sadece_baslik else y.read()
            if y.headers.get("Content-Encoding") == "gzip":
                ham = gzip.decompress(ham)
            return y.status, dict(y.headers), ham.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), ""
    except Exception:
        return 0, {}, ""


def robots_coz(metin):
    """Sadece 'User-agent: *' blogundaki Disallow/Allow satirlarini alir."""
    dis, allow, sitemaps, genel = [], [], [], False
    for satir in metin.splitlines():
        s = satir.split("#")[0].strip()
        if not s:
            continue
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            genel = (v == "*")
        elif k == "sitemap":
            sitemaps.append(v)
        elif genel and k == "disallow" and v:
            dis.append(v)
        elif genel and k == "allow" and v:
            allow.append(v)
    return dis, allow, sitemaps


def eslesir(yol, kural):
    """robots.txt kalibi (* ve $ destekli) yola uyuyor mu?"""
    d = re.escape(kural).replace(r"\*", ".*")
    if d.endswith(r"\$"):
        d = d[:-2] + "$"
    return re.match(d, yol) is not None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("site")
    p.add_argument("--sitemap-ornek", type=int, default=25,
                   help="Sitemap'ten kac URL ornekleme yapilsin (0=kapali)")
    a = p.parse_args()
    kok = a.site.rstrip("/")
    sorun = []

    print(f"=== {kok} indeks denetimi ===\n")

    # 1) robots.txt
    st, _, rt = cek(f"{kok}/robots.txt")
    if st != 200:
        print(f"[HATA] robots.txt -> HTTP {st}")
        return 1
    dis, allow, sitemaps = robots_coz(rt)
    print(f"robots.txt: {len(dis)} Disallow, {len(allow)} Allow, {len(sitemaps)} sitemap")

    # 2) ASIL TUZAK: Disallow'lu ama 200 donen ve noindex TASIMAYAN uclar
    print("\n--- Disallow'lu uclarin gercek durumu ---")
    for k in dis:
        if "*" in k:
            continue  # kalip kurallarini tek tek test edemeyiz
        url = kok + k
        st, bas, govde = cek(url)
        xr = (bas.get("X-Robots-Tag") or bas.get("x-robots-tag") or "").lower()
        meta = bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', govde, re.I))
        if st == 200 and "noindex" not in xr and not meta:
            print(f"  [SORUN] {k} -> 200, Disallow'lu ama noindex YOK")
            print("          Google cekemez -> noindex goremez -> linklerden dizine ekler.")
            print("          COZUM: Disallow kaldir + X-Robots-Tag: noindex ver.")
            sorun.append(k)
        elif st == 200:
            kaynak = "X-Robots-Tag" if "noindex" in xr else "meta"
            print(f"  [!] {k} -> 200, noindex var ({kaynak}) ama Disallow da var")
            print("          Google noindex'i GOREMEZ (cekemiyor). Disallow'u kaldir.")
            sorun.append(k)
        elif st in (301, 302, 307, 308):
            print(f"  [!] {k} -> {st} yonlendirme, Disallow'lu")
            print("          Google yonlendirmeyi izleyemez -> 'Yonlendirmeli sayfa' uyarisi.")
            sorun.append(k)
        elif st == 0:
            print(f"  [?] {k} -> baglanilamadi")
        else:
            print(f"  [ok] {k} -> {st} (icerik yok, Disallow uygun)")

    # 3) noindex'li ama Disallow'lu sayfalar (ters yon kontrol)
    print("\n--- noindex sayfalar taranabiliyor mu? ---")
    for aday in ["admin.html", "bakim.html", "hesabim.html"]:
        url = f"{kok}/{aday}"
        st, bas, govde = cek(url)
        if st != 200:
            continue
        meta = bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', govde, re.I))
        if not meta:
            continue
        engelli = any(eslesir("/" + aday, k) for k in dis)
        if engelli:
            print(f"  [SORUN] {aday}: noindex VAR ama robots.txt engelliyor -> Google goremez")
            sorun.append(aday)
        else:
            print(f"  [ok] {aday}: noindex var, taranabiliyor (dogru)")

    # 4) Sitemap sagligi
    print("\n--- Sitemap ---")
    tum = []
    for sm in sitemaps:
        st, _, x = cek(sm)
        if st != 200:
            print(f"  [SORUN] {sm} -> HTTP {st}")
            sorun.append(sm)
            continue
        loclar = re.findall(r"<loc>([^<]+)</loc>", x)
        print(f"  {sm}: {len(loclar)} URL")
        tum += loclar
    tekil = sorted(set(tum))
    print(f"  TOPLAM benzersiz: {len(tekil)}")

    if a.sitemap_ornek and tekil:
        adim = max(1, len(tekil) // a.sitemap_ornek)
        ornek = tekil[::adim][: a.sitemap_ornek]
        print(f"\n--- Sitemap ornekleme ({len(ornek)} URL) ---")
        kotu = 0
        for u in ornek:
            st, _, _ = cek(u, sadece_baslik=True)
            if st != 200:
                print(f"  [SORUN] {st} <- {u}")
                sorun.append(u)
                kotu += 1
        if not kotu:
            print("  Hepsi 200 (olu link yok)")

    print("\n" + "=" * 50)
    if sorun:
        print(f"SORUN BULUNDU: {len(sorun)} adet (yukari bak)")
        return 1
    print("TEMIZ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
