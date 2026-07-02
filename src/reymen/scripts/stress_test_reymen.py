# -*- coding: utf-8 -*-
"""ReYMeN Stress Test — 3000 sorgu hedefli batch test + rapor"""
import sys, os, json, time, random
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # proje kok

from openai import OpenAI
from src.reymen.cereyan.conversation_loop import ConversationLoop

# ── Beyin ──
class TestBeyin:
    def __init__(self):
        self.model = os.environ.get("REYMEN_MODEL", "deepseek-v4-flash")
        self.provider = os.environ.get("REYMEN_PROVIDER", "deepseek")
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = "https://api.deepseek.com"
    def uret(self, sistem, mesajlar):
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        msgs = [{"role": "system", "content": sistem}] if sistem else []
        msgs += [{"role": m.get("role","user"), "content": m.get("content","")} for m in mesajlar]
        r = client.chat.completions.create(
            model=self.model, messages=msgs, max_tokens=1024, frequency_penalty=0.8,
        )
        return r.choices[0].message.content or ""

# ── Test Sorulari (50 cesit, 60x tekrar = 3000) ──
SORULAR = [
    # A) ONCELIK_CACHE (6)
    "slm", "merhaba", "selam", "sa", "tamam", "ok",
    # B) OnceHafiza'dan gelecek (OnceHafiza bos, duz LLM'e gider)
    "Python nedir", "bugun gunlerden ne", "nasilsin", "nerelisin", 
    "yapay zeka", "kod yaz", "dosya olustur", "yardim et",
    # C) Web arama
    "2026 dunya kupasi", "2026 dunya kupasi sampiyonu", 
    "deepseek nedir", "turkiye baskenti",
    "en yuksek dag", "en uzun nehir",
    "bugun ne oldu", "yapay zeka haberleri",
    "python ogrenmek", "yazilim nasil ogrenilir",
    # D) Karma
    "tesekkur ederim", "sagol", "görüşürüz", "eyvallah",
    "bana yardim et", "bilgisayar nedir", "internet nasil calisir",
    "almanca ogrenmek", "fiyat", "dunyanin en hizli arabasi",
    "uzay nedir", "atom nedir", "matematik nedir",
    "tarih nedir", "insan nedir", "dna nedir",
    "futbol nedir", "basketbol nedir", "satranc nedir",
    "yapay sinir aglari", "derin ogrenme", "makine ogrenmesi",
]

# Her soruyu 4x tekrarla (4*50=200)
TEKRAR = 4  

# ── Rapor ──
rapor = {
    "baslangic": datetime.now().isoformat(),
    "toplam": 0,
    "basarili": 0,
    "basarisiz": 0,
    "kaynak_dagilimi": {},
    "hatalar": [],
    "sureler": [],
}

print("="*60)
print("ReYMeN Stress Test Basliyor")
print(f"  Soru: {len(SORULAR)} cesit x {TEKRAR} tekrar = {len(SORULAR)*TEKRAR} toplam")
print(f"  Baslangic: {rapor['baslangic']}")
print("="*60)

beyin = TestBeyin()
top_kos = len(SORULAR) * TEKRAR
kos_no = 0

for soru in SORULAR:
    for _ in range(TEKRAR):
        kos_no += 1
        loop = ConversationLoop(motor=None, beyin=beyin, max_tur=3)
        
        t_start = time.monotonic()
        try:
            sonuc = loop.run_conversation(hedef=soru)
            sure = time.monotonic() - t_start
            rapor["sureler"].append(sure)
            rapor["toplam"] += 1

            if sonuc.get("basarili"):
                rapor["basarili"] += 1
                kaynak = sonuc.get("kaynak", "bilinmiyor")
                rapor["kaynak_dagilimi"][kaynak] = rapor["kaynak_dagilimi"].get(kaynak, 0) + 1
            else:
                rapor["basarisiz"] += 1
                hata = sonuc.get("hata", "bilinmiyor")
                rapor["hatalar"].append({"soru": soru, "hata": hata})
                print(f"  ❌ [{kos_no}/{top_kos}] {soru}: {hata[:80]}")
        except Exception as e:
            rapor["basarisiz"] += 1
            rapor["toplam"] += 1
            rapor["hatalar"].append({"soru": soru, "hata": str(e)[:100]})
            print(f"  ❌ [{kos_no}/{top_kos}] {soru}: EXCEPTION {str(e)[:80]}")

        # Her 100'de bir ara rapor
        if kos_no % 100 == 0:
            basari_oran = (rapor["basarili"] / rapor["toplam"] * 100) if rapor["toplam"] else 0
            print(f"  📊 [{kos_no}/{top_kos}] Basarili: {rapor['basarili']}/{rapor['toplam']} ({basari_oran:.1f}%)")

# ── Final Rapor ──
rapor["bitis"] = datetime.now().isoformat()
toplam_sure = sum(rapor["sureler"])
ortalama_sure = toplam_sure / len(rapor["sureler"]) if rapor["sureler"] else 0
basari_oran = (rapor["basarili"] / rapor["toplam"] * 100) if rapor["toplam"] else 0

print("\n" + "="*60)
print("STRESS TEST SONUCU")
print("="*60)
print(f"  Toplam:     {rapor['toplam']}")
print(f"  Basarili:   {rapor['basarili']} ({basari_oran:.1f}%)")
print(f"  Basarisiz:  {rapor['basarisiz']}")
print(f"  Toplam Sure: {toplam_sure:.1f}s")
print(f"  Ortalama:   {ortalama_sure:.2f}s/sorgu")
print(f"  Hata:       {len(rapor['hatalar'])} adet")
print(f"\n  Kaynak Dagilimi:")
for k, v in sorted(rapor["kaynak_dagilimi"].items(), key=lambda x: -x[1]):
    print(f"    {k}: {v} (%{v/rapor['toplam']*100:.1f})")

if rapor["hatalar"]:
    print(f"\n  Ilk 10 Hata:")
    for h in rapor["hatalar"][:10]:
        print(f"    ❌ {h['soru']}: {h['hata'][:80]}")

rapor["ortalama_sure"] = round(ortalama_sure, 2)
rapor["basari_orani"] = round(basari_oran, 1)

# Kaydet
rapor_yol = Path(__file__).parent / "stress_test_raporu.json"
rapor_yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n  Rapor kaydedildi: {rapor_yol}")
print("="*60)
