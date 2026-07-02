"""ReYMeN toplu test — 30 soru, cevap kalitesi raporu"""
import os, sys, json, time
from dotenv import load_dotenv
load_dotenv(".env", override=True)

from src.reymen.cereyan.conversation_loop import ConversationLoop

cl = ConversationLoop(motor=None, beyin=None, max_tur=3)

sorular = [
    # SELAMLASMA (cache testi)
    "slm",
    "merhaba",
    "selam",
    "tesekkur",
    "gorusuruz",
    # GUNCEL BILGI (web arama testi)
    "2026 dunya kupasi haberleri",
    "bugun hava durumu istanbul",
    "bitcoin fiyati 2026",
    "2026 ramazan bayrami ne zaman",
    "windows 11 son surum",
    # GENEL KULTUR (LLM testi)
    "turk iye'nin baskenti neresi",
    "python nedir",
    "fiba dunya siralamasi 2026",
    "en yuksek dag hangisi",
    "bir atomun yapisi nedir",
    # ANLAMSIZ GIRDI (edge case)
    "sdfgh",
    "x",
    "a b c",
    "12345",
    "?!?",
    # TEKNIK SORULAR
    "linux terminalde dosya nasil silinir",
    "python list comprehension ornegi",
    "git commit nasil yapilir",
    "windows powershell ile klasor olusturma",
    "deepseek API kullanimi",
    # KARISIK
    "turkiye ekonomisi 2026",
    "en iyi telefon 2026",
    "yapay zeka nedir kisa",
    "bugun ne yemeliyim",
    "hayatin anlami",
]

sonuclar = []
for i, soru in enumerate(sorular, 1):
    t0 = time.time()
    sonuc = cl.run_conversation(hedef=soru, provider="deepseek")
    sure = round(time.time() - t0, 2)
    kaynak = sonuc.get("kaynak", "llm")
    yanit = sonuc.get("yanit") or sonuc.get("sonuc", "") or "[HATA: " + str(sonuc.get("hata", "")) + "]"
    basarili = sonuc.get("basarili", False)
    yanit_kisa = yanit[:100].replace("\n", " ")

    # Kalite kontrol
    sorun = ""
    if not basarili:
        sorun = "HATA"
    elif kaynak == "oncelik_cache" and len(yanit) < 5:
        sorun = "CACHE BOS"
    elif kaynak == "web_arama" and len(yanit) < 30:
        sorun = "WEB AZ ICERIK"
    elif kaynak == "llm" and ("HATA" in yanit or "API" in yanit):
        sorun = "API HATA"
    elif not yanit or len(yanit.strip()) < 3:
        sorun = "BOS YANIT"

    sonuclar.append({
        "no": i, "soru": soru[:40], "kaynak": kaynak,
        "sure": sure, "yanit": yanit_kisa, "sorun": sorun
    })
    print(f"[{i:2d}] {kaynak:15s} {sure:5.2f}s {sorun or 'OK':15s} | {yanit_kisa}")

# Rapor
hata_say = sum(1 for s in sonuclar if s["sorun"])
print(f"\n=== RAPOR ===")
print(f"Toplam: {len(sonuclar)} soru")
print(f"Hata:   {hata_say}")
print(f"Basarili: {len(sonuclar)-hata_say}")
print(f"Cache:  {sum(1 for s in sonuclar if s['kaynak']=='oncelik_cache')}")
print(f"Web:    {sum(1 for s in sonuclar if s['kaynak']=='web_arama')}")
print(f"LLM:    {sum(1 for s in sonuclar if s['kaynak']=='llm')}")
print(f"Ort sure: {sum(s['sure'] for s in sonuclar)/len(sonuclar):.2f}s")

if hata_say > 0:
    print(f"\n=== HATALI CEVAPLAR ===")
    for s in sonuclar:
        if s["sorun"]:
            print(f"  [{s['no']}] {s['soru']} -> {s['sorun']}: {s['yanit'][:80]}")

# JSON kaydet
with open("test_sonuclari.json", "w", encoding="utf-8") as f:
    json.dump(sonuclar, f, ensure_ascii=False, indent=2)
print("\ntest_sonuclari.json kaydedildi")
