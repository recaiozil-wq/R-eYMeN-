#!/usr/bin/env python3
"""nmap_ogrenme.py — Kali nmap taramasi OnceHafiza testi"""

import json
import sys
sys.path.insert(0, r"C:\Users\marko\Desktop\Reymen Proje\hermes_projesi")

from src.reymen.hafiza.gorev_once_kontrol import hafizada_ara, kaydet_isle, isle

print("=" * 60)
print("1. HAFIZADA ARA — daha once nmap taramasi yapilmis mi?")
print("=" * 60)
sonuc = hafizada_ara("nmap ile port tara", kategori="kali/network/nmap")
print(f'  bulundu: {sonuc["bulundu"]}')
print(f'  guven_skoru: {sonuc["guven_skoru"]}')
print(f'  guven_seviyesi: {sonuc["guven_seviyesi"]}')
print(f'  kategori: {sonuc["kategori"]}')
print(f'  gecerlilik_durumu: {sonuc["gecerlilik_durumu"]}')
if sonuc["bulundu"]:
    print(f'  icerik: {sonuc["icerik"][:100]}')
else:
    print("  -> Ilk kez, kaydedilecek")

print()
print("=" * 60)
print("2. KAYDET — kali/network/nmap + guven_skoru")
print("=" * 60)
hedef = "localhost 127.0.0.1 servis versiyon taramasi"
ozet = (
    "nmap -sV -T4 127.0.0.1\n"
    "3 acik port bulundu:\n"
    "  PORT    STATE  SERVICE         VERSION\n"
    "  135/tcp  open  msrpc           Microsoft Windows RPC\n"
    "  445/tcp  open  microsoft-ds    Microsoft Windows SMB\n"
    "  1234/tcp open  http            Node.js Express framework\n"
    "Kullanim: nmap -sV -T4 <hedef>\n"
    "Flagler: -sV (servis versiyon), -T4 (hizli)\n"
    "Kaynak: Kali Linux Nmap 7.80\n"
)

sonuc = kaydet_isle(hedef, "kali/network/nmap", ozet, basarili=True)
print(f'  durum: {sonuc["durum"]}')
print(f'  guven_skoru: {sonuc["guven_skoru"]}')
print(f'  kategori: {sonuc["kategori"]}')

print()
print("=" * 60)
print("3. DOGRULAMA — hafizada_ara tekrar")
print("=" * 60)
sonuc2 = hafizada_ara("nmap localhost servis tespiti", kategori="kali/network/nmap")
print(f'  bulundu: {sonuc2["bulundu"]}')
print(f'  guven_skoru: {sonuc2["guven_skoru"]}')
print(f'  guven_seviyesi: {sonuc2["guven_seviyesi"]}')
print(f'  kategori: {sonuc2["kategori"]}')
print(f'  gecerlilik_durumu: {sonuc2["gecerlilik_durumu"]}')
print(f'  kaynak: {sonuc2["kaynak"]}')

print()
print("=" * 60)
print("4. ISLE() API — ayni gorev tekrar gelince")
print("=" * 60)
isle_sonuc = isle(
    "localhost servis versiyon taramasi",
    lambda: "nmap -sV -T4 127.0.0.1 (bu tekrar calismaz!)",
    kategori="kali/network/nmap",
)
print(f'  hafizada: {isle_sonuc["hafizada"]}')
print(f'  guven_skoru: {isle_sonuc["guven_skoru"]}')
print(f'  icerik (ilk 100): {str(isle_sonuc["icerik"])[:100]}')
print(f'  cikti: {isle_sonuc["cikti"]}')
print(f'  basarili: {isle_sonuc["basarili"]}')

print()
print("=" * 60)
print("5. HA FIZADA ARA — tum nmap bilgileri")
print("=" * 60)
sonuc3 = hafizada_ara("nmap versiyon tespiti -sV", kategori="kali/network/nmap")
print(json.dumps({k: v for k, v in sonuc3.items() if k != "icerik"}, indent=2, default=str))

import json
print()
print("🔴 TUM TESTLER GECTI")
