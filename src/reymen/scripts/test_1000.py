"""ReYMeN 1000 soru toplu test — otomatik soru uret (background'da calisir)"""
import os, sys, json, time, random, itertools, string
from dotenv import load_dotenv
load_dotenv(".env", override=True)
BASLANGIC_ZAMAN = time.strftime('%Y-%m-%d %H:%M:%S')

sys.path.insert(0, os.path.abspath("."))
from src.reymen.cereyan.conversation_loop import ConversationLoop

cl = ConversationLoop(motor=None, beyin=None, max_tur=3)

# ── Soru uretici ────────────────────────────────────────────────────
selam = ["slm", "merhaba", "selam", "hey", "naber", "selamun aleykum", "iyi misin", "nasilsin", "merhaba nasilsin", "slm naber"]
tesekkur = ["tesekkur", "tesekkurler", "sagol", "sagolasin", "eyvallah", "thanks", "mukkemmel", "harika", "iyi", "tamamdir"]
veda = ["bye", "gorusuruz", "hadi", "hadi bakalim", "görüşürüz", "kapan", "cikis", "sonlandir", "tmm", "tamamdir"]
onay = ["ok", "tamam", "olur", "peki", "anlasildi", "anladim", "kabul", "yap", "basla", "hadi yap"]

ulkeler = ["turkiye", "almanya", "fransa", "ispanya", "italya", "japonya", "cin", "hindistan", "brezilya", "rusya"]
teknoloji = ["python", "javascript", "rust", "go", "java", "linux", "windows", "docker", "kubernetes", "git"]
konular = ["ekonomi", "savas", "deprem", "secim", "uzay", "iklim", "saglik", "egitim", "spor", "sanat"]
sifat = ["2026", "guncel", "son", "yeni", "en iyi", "en kotu", "populer", "onemli", "buyuk", "kucuk"]
fiil = ["nedir", "nasil yapilir", "ne zaman", "nerede", "kim", "fiyati", "haberleri", "tarihi", "ozellikleri", "neden"]

# 3000 soru uret
random.seed(42)
sorular = []

# 1. Selamlasma/temel (300)
for _ in range(60):
    sorular.append(random.choice(selam))
    sorular.append(random.choice(tesekkur))
    sorular.append(random.choice(veda))
    sorular.append(random.choice(onay))
    sorular.append(random.choice(selam) + " " + random.choice(tesekkur))

# 2. Guncel bilgi (900)
for _ in range(900):
    k = random.choice(konular)
    u = random.choice(ulkeler)
    s = random.choice(sifat)
    f = random.choice(fiil)
    sorular.append(f"{s} {u} {k} {f}")

# 3. Teknik (600)
for _ in range(600):
    t = random.choice(teknoloji)
    f = random.choice(fiil)
    sorular.append(f"{t} {f}")

# 4. Anlamsiz girdi (600)
anlamsiz_kok = ["asdf", "qwerty", "zxcv", "123", "test", "xyz", "abc", "foo", "bar", "baz"]
for _ in range(600):
    sorular.append(random.choice(anlamsiz_kok) + random.choice(string.ascii_lowercase[:5]))

# 5. Karisik (600)
for _ in range(600):
    tip = random.randint(1, 4)
    if tip == 1:
        sorular.append(f"{random.choice(ulkeler)} {random.choice(fiil)}")
    elif tip == 2:
        sorular.append(f"{random.choice(teknoloji)} {random.choice(sifat)}")
    elif tip == 3:
        sorular.append(f"{random.choice(konular)} {random.choice(sifat)} {random.choice(fiil)}")
    else:
        sorular.append(f"{random.choice(sifat)} {random.choice(konular)}")

sorular = sorular[:3000]
random.shuffle(sorular)

# ── Test ─────────────────────────────────────────────────────────────
print(f"BASLADI: {len(sorular)} soru (3000 test)")
print(f"BASLANGIC: {time.strftime('%Y-%m-%d %H:%M:%S')}")
sys.stdout.flush()

sonuclar = []
hata_say = 0
for i, soru in enumerate(sorular, 1):
    t0 = time.time()
    try:
        sonuc = cl.run_conversation(hedef=soru, provider="deepseek")
        sure = round(time.time() - t0, 2)
        kaynak = sonuc.get("kaynak", "llm")
        yanit = sonuc.get("yanit") or sonuc.get("sonuc", "") or ""
        basarili = sonuc.get("basarili", False)

        sorun = ""
        if not basarili:
            sorun = "HATA"
            hata_say += 1
        elif kaynak == "oncelik_cache" and len(yanit) < 3:
            sorun = "CACHE_BOS"
            hata_say += 1
        elif kaynak == "web_arama" and len(yanit) < 30:
            sorun = "WEB_AZ"
        elif kaynak == "llm" and ("HATA" in yanit or "API" in yanit):
            sorun = "API_HATA"
            hata_say += 1
        elif not yanit:
            sorun = "BOS"
            hata_say += 1

        sonuclar.append({"no": i, "soru": soru[:60], "kaynak": kaynak, "sure": sure, "sorun": sorun})

        if i % 50 == 0:
            print(f"[{i}/{len(sorular)}] hata={hata_say} cache={sum(1 for s in sonuclar if s.get('kaynak')=='oncelik_cache')} web={sum(1 for s in sonuclar if s.get('kaynak')=='web_arama')} llm={sum(1 for s in sonuclar if s.get('kaynak')=='llm')}")
            sys.stdout.flush()
    except Exception as e:
        hata_say += 1
        sonuclar.append({"no": i, "soru": str(soru)[:60], "kaynak": "EXCEPTION", "sure": 0, "sorun": str(e)[:50]})

# ── Rapor ────────────────────────────────────────────────────────────
bitis = time.time()
sure_top = sum(s.get("sure", 0) for s in sonuclar)
cache_say = sum(1 for s in sonuclar if s.get("kaynak") == "oncelik_cache")
web_say = sum(1 for s in sonuclar if s.get("kaynak") == "web_arama")
llm_say = sum(1 for s in sonuclar if s.get("kaynak") == "llm")
oneri_say = sum(1 for s in sonuclar if s.get("kaynak") == "oneri_uret")
once_say = sum(1 for s in sonuclar if s.get("kaynak") == "once_hafiza")
exc_say = sum(1 for s in sonuclar if s.get("kaynak") == "EXCEPTION")
hatali_sorun = [s for s in sonuclar if s.get("sorun") and s.get("kaynak") != "EXCEPTION"]

RAPOR = f"""
========================================
REYMEN 3000 SORU TEST RAPORU
========================================
Baslangic: {BASLANGIC_ZAMAN}
Bitis: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}
Toplam: {len(sonuclar)} soru
Sure: {sure_top:.0f}s ({sure_top/60:.1f}dk)

KAYNAK DAGILIMI:
  Cache:       {cache_say:4d} (%{cache_say*100//len(sonuclar):2d})
  Web:         {web_say:4d} (%{web_say*100//len(sonuclar):2d})
  LLM:         {llm_say:4d} (%{llm_say*100//len(sonuclar):2d})
  Oneri:       {oneri_say:4d} (%{oneri_say*100//len(sonuclar):2d})
  OnceHafiza:  {once_say:4d} (%{once_say*100//len(sonuclar):2d})
  Exception:   {exc_say:4d}

HATA: {hata_say} soru
BASARILI: {len(sonuclar)-hata_say} soru
BASARI ORANI: %{(len(sonuclar)-hata_say)*100//len(sonuclar)}

HATA DETAY:
"""

for s in hatali_sorun[:20]:
    RAPOR += f"  [{s['no']}] {s['soru'][:50]} -> {s['sorun']}\n"

if hata_say > 20:
    RAPOR += f"  ...ve {hata_say-20} hata daha (test_sonuc.json'da tam liste)\n"

# JSON kaydet
with open("test_3000_sonuc.json", "w", encoding="utf-8") as f:
    json.dump({"rapor": RAPOR, "sonuclar": sonuclar}, f, ensure_ascii=False, indent=2)

print(RAPOR)
print("\ntest_1000_sonuc.json kaydedildi")
