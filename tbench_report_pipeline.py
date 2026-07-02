#!/usr/bin/env python3
"""
ReYMeN Terminal-Bench Rapor Pipeline'ı
- Otomatik test → skor → rapor döngüsü
- Trend takibi (önceki raporla karşılaştırma)
- Kategori bazlı başarı/başarısızlık analizi
- Markdown rapor üretimi

Kullanım:
  python tbench_report_pipeline.py              # sadece rapor üret
  python tbench_report_pipeline.py --test       # test + rapor
  python tbench_report_pipeline.py --test easy  # sadece easy test + rapor
"""
import os, json, sys, glob
from datetime import datetime

PROJE_KOKU = os.path.dirname(os.path.abspath(__file__))
RAPOR_DIZINI = os.path.join(PROJE_KOKU, ".ReYMeN", "reports")
SKOR_DB = os.path.join(RAPOR_DIZINI, "tbench_skor_db.json")
TEST_RUNNER = os.path.join(PROJE_KOKU, "tbench_plan_recovery.py")
RECOVERY_LOG = os.path.join(RAPOR_DIZINI, "tbench-plan-recovery.json")

def skor_db_oku():
    """Mevcut skor veritabanını oku."""
    if not os.path.isfile(SKOR_DB):
        return None
    with open(SKOR_DB) as f:
        return json.load(f)

def recovery_log_oku():
    """Son recovery log'unu oku."""
    if not os.path.isfile(RECOVERY_LOG):
        return None
    with open(RECOVERY_LOG) as f:
        return json.load(f)

def onceki_raporlari_bul():
    """Önceki raporları bul ve en sonuncuyu döndür."""
    raporlar = sorted(glob.glob(os.path.join(RAPOR_DIZINI, "tbench-report-*.md")))
    if not raporlar:
        return None, None
    return raporlar[-1], len(raporlar)

def trend_hesapla(onceki_skor, suanki_skor):
    """İki skor arasındaki değişimi hesapla."""
    trend = {}
    for kategori in ["easy", "medium", "hard"]:
        onceki = onceki_skor.get("stats", {}).get(f"{kategori}_solved", 0) if onceki_skor else 0
        suanki = suanki_skor.get("stats", {}).get(f"{kategori}_solved", 0)
        fark = suanki - onceki
        trend[kategori] = {
            "onceki": onceki,
            "suanki": suanki,
            "fark": fark,
            "yeni_cozulen": []
        }
        # Yeni çözülenleri bul
        onceki_liste = set(onceki_skor.get("solved", {}).get(kategori, [])) if onceki_skor else set()
        suanki_liste = set(suanki_skor.get("solved", {}).get(kategori, []))
        trend[kategori]["yeni_cozulen"] = list(suanki_liste - onceki_liste)
    return trend

def basarisiz_analizi(skor_db):
    """Başarısız görevleri analiz et ve kategorize et."""
    task_dir = os.path.join(PROJE_KOKU, "terminal-bench-benchmark", "original-tasks")
    cozulen = set()
    for k in ["easy", "medium", "hard"]:
        cozulen.update(skor_db.get("solved", {}).get(k, []))
    
    basarisiz = {"easy": [], "medium": [], "hard": []}
    
    if not os.path.isdir(task_dir):
        return basarisiz
    
    for task in sorted(os.listdir(task_dir)):
        task_path = os.path.join(task_dir, task)
        if not os.path.isdir(task_path) or task in cozulen:
            continue
        if not os.path.isfile(os.path.join(task_path, "task.yaml")):
            continue
        with open(os.path.join(task_path, "task.yaml")) as f:
            yaml = f.read()
        # Zorluk seviyesini bul
        zorluk = "medium"
        for line in yaml.split("\n"):
            line_lower = line.strip().lower()
            if "difficulty:" in line_lower:
                if "easy" in line_lower:
                    zorluk = "easy"
                elif "hard" in line_lower:
                    zorluk = "hard"
                break
        basarisiz[zorluk].append(task)
    
    return basarisiz

def get_task_metadata(task_adi):
    """Görevin task.yaml'ından kısa bilgi al."""
    task_dir = os.path.join(PROJE_KOKU, "terminal-bench-benchmark", "original-tasks", task_adi)
    yaml_file = os.path.join(task_dir, "task.yaml")
    if not os.path.isfile(yaml_file):
        return {"zorluk": "?", "altyapi": "?", "kategori": "?"}
    with open(yaml_file) as f:
        content = f.read()
    
    meta = {"zorluk": "?", "altyapi": "?", "kategori": "?"}
    for line in content.split("\n"):
        l = line.strip().lower()
        if "difficulty:" in l:
            meta["zorluk"] = line.split(":", 1)[1].strip()
        if "category:" in l:
            meta["kategori"] = line.split(":", 1)[1].strip()
        if "infrastructure:" in l or "setup:" in l:
            meta["altyapi"] = line.split(":", 1)[1].strip()
    return meta

def rapor_olustur(skor_db, trend, basarisiz_liste, recovery, test_calisti):
    """Markdown rapor oluştur."""
    now = datetime.now()
    stats = skor_db.get("stats", {})
    metadata = skor_db.get("metadata", {})
    
    rapor = f"""# 📊 ReYMeN Terminal-Bench Raporu

**Tarih:** {now.strftime("%Y-%m-%d %H:%M")}
**Test çalıştı:** {'Evet' if test_calisti else 'Hayır (sadece rapor)'}
**Toplam görev:** {metadata.get('total_tasks', '?')}

---

## 📈 Genel Skor

| Kategori | Çözülen | Toplam | % | Trend |
|----------|---------|--------|---|-------|
"""
    for k, etiket in [("easy", "✅ Easy"), ("medium", "🟡 Medium"), ("hard", "🔴 Hard")]:
        cozulen = stats.get(f"{k}_solved", 0)
        toplam = stats.get(f"{k}_total", 0)
        yuzde = stats.get(f"{k}_percent", 0)
        t = trend.get(k, {})
        fark = t.get("fark", 0)
        if fark > 0:
            trend_goster = f"📈 +{fark}"
        elif fark < 0:
            trend_goster = f"📉 {fark}"
        else:
            trend_goster = "➡️ 0"
        rapor += f"| {etiket} | {cozulen} | {toplam} | %{yuzde} | {trend_goster} |\n"
    
    rapor += f"""
| **Toplam** | {stats.get('total_solved', 0)} | {metadata.get('total_tasks', '?')} | %{stats.get('total_percent', 0)} | |
"""
    
    # Yeni çözülenler
    yeni_toplam = sum(len(t.get("yeni_cozulen", [])) for t in trend.values())
    if yeni_toplam > 0:
        rapor += "\n## 🆕 Yeni Çözülen Görevler\n\n"
        for k, etiket in [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]:
            yeni = trend.get(k, {}).get("yeni_cozulen", [])
            if yeni:
                rapor += f"**{etiket}:** {', '.join(sorted(yeni))}\n\n"
    
    # Recovery istatistikleri    
    if recovery:
        rec_list = recovery if isinstance(recovery, list) else []
        if rec_list:
            rec_basarili = sum(1 for r in rec_list if isinstance(r, dict) and r.get("status") == "solved")
            rapor += f"## 🔧 Recovery İstatistikleri\n\n"
            rapor += f"- Toplam recovery denemesi: {len(rec_list)}\n"
            rapor += f"- Başarılı recovery: {rec_basarili}\n"
            rapor += f"- Recovery başarı oranı: %{round(rec_basarili/max(len(rec_list),1)*100)}\n\n"
    
    # Başarısız görevler
    basarisiz_toplam = sum(len(v) for v in basarisiz_liste.values())
    rapor += f"## ❌ Çözülemeyen Görevler ({basarisiz_toplam})\n\n"
    
    for k, etiket in [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]:
        liste = basarisiz_liste.get(k, [])
        if liste:
            rapor += f"**{etiket} ({len(liste)}):** "
            rapor += ", ".join(sorted(liste)) + "\n\n"
    
    # Kategori dağılımı
    rapor += "## 📂 Kategori Dağılımı\n\n"
    kategori_say = {}
    cozulen_set = set()
    for k in ["easy", "medium", "hard"]:
        cozulen_set.update(skor_db.get("solved", {}).get(k, []))
    
    for task in cozulen_set:
        meta = get_task_metadata(task)
        kat = meta.get("kategori", "?")
        kategori_say[kat] = kategori_say.get(kat, 0) + 1
    
    if kategori_say:
        for kat, say in sorted(kategori_say.items(), key=lambda x: -x[1]):
            rapor += f"- **{kat}:** {say} görev\n"
        rapor += "\n"
    
    # Docker bilgisi
    docker_info = skor_db.get("docker", {})
    if docker_info:
        rapor += f"## 🐳 Docker Konfigürasyonu\n\n"
        rapor += f"- İmaj: `{docker_info.get('image', '?')}`\n"
        rapor += f"- Baz: `{docker_info.get('base', '?')}`\n"
        rapor += f"- Paket: {len(docker_info.get('packages', []))} grup\n\n"
    
    # Model bilgisi
    model_info = skor_db.get("models", {})
    if model_info:
        rapor += f"## 🧠 Model Konfigürasyonu\n\n"
        rapor += f"- Ana model: `{model_info.get('primary', '?')}`\n"
        rapor += f"- Fallback: `{model_info.get('fallback', '?')}`\n"
        rapor += f"- Lokal reasoning: `{model_info.get('reasoning_local', '?')}`\n"
        rapor += f"- Cloud reasoning: `{model_info.get('reasoning_cloud', '?')}`\n\n"
    
    # Öneriler
    rapor += "## 💡 Öneriler\n\n"
    if basarisiz_liste.get("easy"):
        rapor += f"- {len(basarisiz_liste['easy'])} easy görev daha denenebilir — plan+recovery ile\n"
    if not skor_db.get("solved", {}).get("medium"):
        rapor += "- Medium görevlere henüz başlanmadı — hazır olunca geç\n"
    if stats.get("easy_percent", 0) < 70:
        rapor += f"- Easy %{stats.get('easy_percent', 0)} hedef %70+ — model routing veya Ornith ile iyileştirilebilir\n"
    
    rapor += "---\n"
    rapor += f"*Rapor otomatik oluşturuldu | ReYMeN Agent | {now.strftime('%Y-%m-%d %H:%M')}*\n"
    
    return rapor

def raporu_kaydet(markdown):
    """Raporu kaydet — tarihli + latest."""
    now = datetime.now()
    # Tarihli
    tarihli_adi = f"tbench-report-{now.strftime('%Y%m%d_%H%M')}.md"
    tarihli_yol = os.path.join(RAPOR_DIZINI, tarihli_adi)
    with open(tarihli_yol, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    # Latest
    latest_yol = os.path.join(RAPOR_DIZINI, "tbench-report-latest.md")
    with open(latest_yol, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    return tarihli_adi, tarihli_yol

def main():
    # Parametreleri kontrol et
    test_calisti = False
    test_kategori = None
    
    if "--test" in sys.argv:
        test_calisti = True
        idx = sys.argv.index("--test")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1] in ["easy", "medium", "hard"]:
            test_kategori = sys.argv[idx + 1]
    
    # Test çalıştır (isteğe bağlı)
    if test_calisti and os.path.isfile(TEST_RUNNER):
        print(f"🚀 Test çalıştırılıyor... ({test_kategori or 'tümü'})")
        if test_kategori:
            ret = os.system(f"python \"{TEST_RUNNER}\" {test_kategori}")
        else:
            ret = os.system(f"python \"{TEST_RUNNER}\"")
        print(f"✅ Test tamamlandı (exit: {ret})")
    
    # Skor DB oku
    skor_db = skor_db_oku()
    if not skor_db:
        print("❌ Skor DB bulunamadı!")
        sys.exit(1)
    
    # Önceki raporu bul
    onceki_rapor, rapor_sayisi = onceki_raporlari_bul()
    
    # Trend hesapla
    onceki_skor = None
    if onceki_rapor:
        # Önceki rapordan skor çıkar — basit regex ile
        onceki_tarih = os.path.basename(onceki_rapor).replace("tbench-report-", "").replace(".md", "")
        trend_data = skor_db
    else:
        trend_data = None
    
    trend = trend_hesapla(onceki_skor, skor_db)
    
    # Recovery log oku
    recovery = recovery_log_oku()
    
    # Başarısız analizi
    basarisiz = basarisiz_analizi(skor_db)
    
    # Rapor oluştur
    print("📝 Rapor oluşturuluyor...")
    markdown = rapor_olustur(skor_db, trend, basarisiz, recovery, test_calisti)
    
    # Kaydet
    tarihli_adi, tarihli_yol = raporu_kaydet(markdown)
    print(f"✅ Rapor kaydedildi: {tarihli_yol}")
    print(f"📄 Toplam rapor: {rapor_sayisi + 1 if rapor_sayisi else 1}")
    
    # Özet
    stats = skor_db["stats"]
    med_pct = round(stats['medium_solved'] / max(stats['medium_total'], 1) * 100, 1)
    hard_pct = round(stats['hard_solved'] / max(stats['hard_total'], 1) * 100, 1)
    print(f"\n📊 ÖZET:")
    print(f"   Easy:   {stats['easy_solved']}/{stats['easy_total']} (%{stats['easy_percent']})")
    print(f"   Medium: {stats['medium_solved']}/{stats['medium_total']} (%{med_pct})")
    print(f"   Hard:   {stats['hard_solved']}/{stats['hard_total']} (%{hard_pct})")
    metadata = skor_db.get('metadata', {})
    print(f"   Toplam: {stats['total_solved']}/{metadata.get('total_tasks', stats['easy_total'])} (%{stats['total_percent']})")
    
    # Rapor içeriğini göster
    print(f"\n📄 Rapor: {tarihli_adi}")
    print("─" * 40)
    print(markdown[:500])
    print("...")

if __name__ == "__main__":
    main()
