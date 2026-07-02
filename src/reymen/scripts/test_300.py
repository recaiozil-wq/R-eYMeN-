"""ReYMeN 300 soru test - hizli, output gorunur"""
import os, sys, json, time, random, string
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv
load_dotenv(".env", override=True)

from src.reymen.cereyan.conversation_loop import ConversationLoop
cl = ConversationLoop(motor=None, beyin=None, max_tur=3)

random.seed(42)
sorular = []
selam = ["slm","merhaba","selam","hey","naber","selamun aleykum","iyi misin","nasilsin","tesekkur","sagol","bye","hadi","tamam","ok","tmm","eyvallah","x","y","neden"]
ulkeler = ["turkiye","almanya","fransa","ispanya","italya","japonya","cin","hindistan","brezilya","rusya"]
teknoloji = ["python","javascript","rust","go","java","linux","windows","docker","kubernetes","git"]
konular = ["ekonomi","savas","deprem","secim","uzay","iklim","saglik","egitim","spor","sanat"]
sifat = ["2026","guncel","son","yeni","en iyi","en kotu","populer","onemli","buyuk","kucuk"]
fiil = ["nedir","nasil yapilir","ne zaman","nerede","kim","fiyati","haberleri","tarihi","ozellikleri","neden"]
anlamsiz = ["asdf","qwerty","zxcvbn","123456","test123","xyzabc","foobar"]

# 300 soru
for _ in range(30): sorular.append(random.choice(selam))
for _ in range(90): sorular.append(f"{random.choice(sifat)} {random.choice(ulkeler)} {random.choice(konular)} {random.choice(fiil)}")
for _ in range(60): sorular.append(f"{random.choice(teknoloji)} {random.choice(fiil)}")
for _ in range(60): sorular.append(random.choice(anlamsiz) + random.choice(string.ascii_lowercase[:3]))
for _ in range(60):
    t = random.randint(1,4)
    if t==1: sorular.append(f"{random.choice(ulkeler)} {random.choice(fiil)}")
    elif t==2: sorular.append(f"{random.choice(teknoloji)} {random.choice(sifat)}")
    elif t==3: sorular.append(f"{random.choice(konular)} {random.choice(sifat)} {random.choice(fiil)}")
    else: sorular.append(f"{random.choice(sifat)} {random.choice(konular)}")

random.shuffle(sorular)
sorular = sorular[:300]

print(f"BASLADI: {len(sorular)} soru")
sys.stdout.flush()

sonuclar = []
hata_say = 0
for i, soru in enumerate(sorular, 1):
    t0 = time.time()
    try:
        sonuc = cl.run_conversation(hedef=soru, provider="deepseek")
        kaynak = sonuc.get("kaynak", "llm")
        yanit = sonuc.get("yanit") or sonuc.get("sonuc", "") or ""
        basarili = sonuc.get("basarili", False)
        sure = round(time.time() - t0, 2)

        sorun = ""
        if not basarili or not yanit: sorun = "HATA"; hata_say += 1
        elif "HATA" in yanit and kaynak=="llm": sorun = "API_HATA"; hata_say += 1

        sonuclar.append({"no": i, "soru": soru[:50], "kaynak": kaynak, "sure": sure, "sorun": sorun})

        if i % 30 == 0:
            c = sum(1 for s in sonuclar if s.get("kaynak")=="oncelik_cache")
            w = sum(1 for s in sonuclar if s.get("kaynak")=="web_arama")
            l = sum(1 for s in sonuclar if s.get("kaynak")=="llm")
            print(f"[{i:3d}/{len(sorular)}] hata={hata_say} cache={c} web={w} llm={l}")
            sys.stdout.flush()
    except Exception as e:
        hata_say += 1
        sonuclar.append({"no": i, "soru": str(soru)[:50], "kaynak": "EXC", "sure": 0, "sorun": str(e)[:40]})

# Rapor
bitis = time.time()
c = sum(1 for s in sonuclar if s.get("kaynak")=="oncelik_cache")
w = sum(1 for s in sonuclar if s.get("kaynak")=="web_arama")
l = sum(1 for s in sonuclar if s.get("kaynak")=="llm")
o = sum(1 for s in sonuclar if s.get("kaynak")=="oneri_uret")
h = sum(1 for s in sonuclar if s.get("kaynak")=="once_hafiza")
ort_sure = sum(s.get("sure",0) for s in sonuclar)/max(len(sonuclar),1)

RAPOR = f"""
========================================
REYMEN 300 SORU TEST
========================================
Toplam: {len(sonuclar)} soru
Sure: {sum(s.get('sure',0) for s in sonuclar):.0f}s
Hata: {hata_say}
Basari: {len(sonuclar)-hata_say} (%{(len(sonuclar)-hata_say)*100//max(len(sonuclar),1)})

KAYNAK: cache={c} web={w} llm={l} oneri={o} hafiza={h}
ORTALAMA SURE: {ort_sure:.2f}s

HATALAR:
"""
hatali = [s for s in sonuclar if s.get("sorun")]
for s in hatali[:10]:
    RAPOR += f"  [{s['no']}] {s['soru'][:45]} -> {s['sorun']}\n"
if len(hatali) > 10:
    RAPOR += f"  ...ve {len(hatali)-10} hata daha\n"

print(RAPOR)

# JSON kaydet
with open("test_300_sonuc.json", "w", encoding="utf-8") as f:
    json.dump({"rapor": RAPOR, "sonuclar": sonuclar}, f, ensure_ascii=False, indent=2)
print("test_300_sonuc.json kaydedildi")
