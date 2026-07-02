# -*- coding: utf-8 -*-
"""ReYMeN Stress Test — bagimsiz script"""
import sys, os, json, time, concurrent.futures

PROJE = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan"
sys.path.insert(0, PROJE)
os.chdir(PROJE)

from openai import OpenAI
from src.reymen.cereyan.conversation_loop import ConversationLoop

class Beyin:
    def __init__(self):
        self.model = "deepseek-v4-flash"
        self.provider = "deepseek"
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

SORULAR = [
    "slm","merhaba","selam","sa","tamam","ok",
    "Python nedir","bugun gunlerden ne","nasilsin","nerelisin",
    "yapay zeka","kod yaz","dosya olustur","yardim et",
    "2026 dunya kupasi","deepseek nedir","turkiye baskenti",
    "en yuksek dag","en uzun nehir","python ogrenmek",
    "tesekkur ederim","sagol","görüşürüz","eyvallah",
    "bilgisayar nedir","internet nasil calisir",
    "dunyanin en hizli arabasi","uzay nedir","atom nedir",
    "tarih nedir","insan nedir","dna nedir",
    "futbol nedir","satranc nedir","derin ogrenme",
]
TEKRAR = 85  # 36*85 = 3060

rapor = {"basarili": 0, "basarisiz": 0, "kaynak_dagilimi": {}, "hatalar": [], "sureler": []}
beyin = Beyin()
top = len(SORULAR) * TEKRAR

print(f"Stress Test: {len(SORULAR)} soru x {TEKRAR} tekrar = {top}")
print("="*50)

for i, soru in enumerate(SORULAR):
    for k in range(TEKRAR):
        t0 = time.monotonic()
        try:
            # 30s timeout ile calistir (web arama takilmamasi icin)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                loop = ConversationLoop(motor=None, beyin=beyin, max_tur=3)
                fut = ex.submit(loop.run_conversation, hedef=soru)
                sonuc = fut.result(timeout=30)
            sure = time.monotonic() - t0
            rapor["sureler"].append(sure)
            if sonuc.get("basarili"):
                rapor["basarili"] += 1
                ks = sonuc.get("kaynak", "?")
                rapor["kaynak_dagilimi"][ks] = rapor["kaynak_dagilimi"].get(ks, 0) + 1
            else:
                rapor["basarisiz"] += 1
                rapor["hatalar"].append({"soru": soru, "hata": sonuc.get("hata","?")})
        except Exception as e:
            rapor["basarisiz"] += 1
            rapor["hatalar"].append({"soru": soru, "hata": str(e)[:100]})

        # Rate limit korumasi: her sorgu arasi 0.8s bekle
        time.sleep(0.8)

        n = i * TEKRAR + k + 1
        if n % 50 == 0 or n == 1 or n == top:
            o = rapor["basarili"]/max(n,1)*100
            print(f"  [{n}/{top}] %{o:.0f} basarili, {len(rapor['hatalar'])} hata", flush=True)
            # Arasira kaydet
            with open(os.path.join(PROJE, "reymen/scripts/stress_raporu_devam.json"), "w") as f:
                json.dump({"n":n, "top":top, "basarili":rapor["basarili"], "basarisiz":rapor["basarisiz"], "hata_sayisi":len(rapor["hatalar"])}, f)

# RAPOR
print("\n" + "="*50)
print("SONUC")
print("="*50)
ts = sum(rapor["sureler"])
ort = ts / len(rapor["sureler"]) if rapor["sureler"] else 0
oran = rapor["basarili"]/max(rapor["basarili"]+rapor["basarisiz"],1)*100
print(f"  Toplam:    {rapor['basarili']+rapor['basarisiz']}")
print(f"  Basarili:  {rapor['basarili']} (%{oran:.1f})")
print(f"  Basarisiz: {rapor['basarisiz']}")
print(f"  Sure:      {ts:.0f}s ({ort:.2f}s/soru)")
print(f"  Kaynaklar:")
for k,v in sorted(rapor["kaynak_dagilimi"].items(), key=lambda x:-x[1]):
    print(f"    {k}: {v}")
if rapor["hatalar"]:
    print(f"\n  Ilk 5 Hata:")
    for h in rapor["hatalar"][:5]:
        print(f"    ❌ {h['soru']}: {h['hata'][:80]}")

rpath = os.path.join(PROJE, "reymen/scripts/stress_raporu.json")
with open(rpath, "w", encoding="utf-8") as f:
    json.dump(rapor, f, ensure_ascii=False, indent=2)
print(f"\n  Rapor: {rpath}")
print("="*50)
