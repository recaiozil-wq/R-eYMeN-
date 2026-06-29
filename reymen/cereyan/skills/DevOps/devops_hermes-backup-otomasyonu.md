---
name: hermes-backup-otomasyonu
title: "Hermes Backup Otomasyonu"
tags: [automation, backup, devops, system]
description: >-
  Hermes tam yedek otomasyonu. Gunluk no_agent diff+sync (21:00) +
  haftalik LLM bakim (Carsamba). Startup .bat ile flag tabanli tetikleme.
version: 1.1.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [yedek, github, backup, cron, otomasyon, sync]
audience: maintainer
related_skills: [gece-3-github-yedek]
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hermes Backup Otomasyonu

## Amaç

`hermes-full-backup` reposunu otomatik güncel tutar:
- **Günlük:** skills + memory + state.db diff'i alır, sadece farkları push eder
- **Haftalık:** Çarşamba günü bilgisayar ilk açıldığında LLM ile bakım yapar

## Bileşenler

### 1. Günlük Sync Script (no_agent)

- **Dosya:** `C:\Users\marko\AppData\Local\hermes\scripts\sync_hermes_backup.py`
- **Cron Job ID:** `86ef5e46f92e`
- **Adı:** `gunluk-backup-sync`
- **Zaman:** Her gün 21:00
- **Tür:** no_agent=true (LLM harcamaz)

**Yaptıkları:**
1. Backup repo'sunu git pull ile günceller
2. `skills/` klasörünü karşılaştırır (SHA256 hash ile)
3. Fark varsa skills'i kopyalar
4. `Hermes Memor/` (MEMORY.md + USER.md) karşılaştırıp kopyalar
5. `state.db` boyut/mtime karşılaştırması yapar, fark varsa zip'ler
6. Değişiklik varsa commit + push eder
7. Fark yoksa sessiz kalır (watchdog pattern)

### 2. Startup .bat (Çarşamba Flag)

- **Dosya:** `C:\Users\marko\AppData\Local\hermes\scripts\haftalik-bakim-startup.bat`
- **Hedef:** `C:\Users\marko\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\haftalik-bakim-startup.bat`

**Yaptıkları:**
1. wmic ile haftanın gününü kontrol eder
2. Çarşamba (3) ise:
   - `haftalik-bakim.flag` dosyası oluşturur
   - Gateway çalışmıyorsa başlatır (Start-ScheduledTask)
3. Çarşamba değilse sessiz çıkar

### 3. Haftalık LLM Bakım Cron

- **Cron Job ID:** `066c3c1ed9e3`
- **Adı:** `haftalik-bakim-carsamba`
- **Zaman:** Çarşamba günleri 4 saatte bir (`0 */4 * * 3`)
- **Skills:** `obsidian-vault-path-fix`, `tam-sistem-yetkisi`

**Yaptıkları:**
1. `C:\Users\marko\AppData\Local\hermes\haftalik-bakim.flag` dosyasını kontrol eder
2. **Flag VARSA:**
   - Flag'i siler
   - GitHub'daki skills ile local'dekini karşılaştırır (silinmiş skill var mı?)
   - Config'i kontrol eder (güncel mi?)
   - Gereksiz/eski skill'leri temizler
   - Sonucu raporlar
3. **Flag YOKSA:** Sessizce biter (LLM harcamaz)

## Cron Job'lar

| Job ID | Adı | Zaman | Tür | Açıklama |
|--------|-----|------|-----|----------|
| `86ef5e46f92e` | gunluk-backup-sync | Her gün 21:00 | no_agent | Diff+sync skills+memory+state.db |
| `066c3c1ed9e3` | haftalik-bakim-carsamba | Çarşamba 4 saatte bir | LLM | Flag varsa bakım yap |

## Dosyalar

| Dosya | Konum | Açıklama |
|-------|-------|----------|
| `sync_hermes_backup.py` | `scripts/` | Günlük diff+sync scripti |
| `haftalik-bakim-startup.bat` | `scripts/` + `Startup/` | Çarşamba flag oluşturma |
| `haftalik-bakim.flag` | `HERMES_HOME/` | Geçici flag dosyası |
| `backup-sync.log` | `logs/` | İşlem logu |

## Akış Şeması

```
Her gun 21:00
  → no_agent script calisir
  → skills + memory + state.db diff
  → fark varsa push et
  → fark yoksa sessiz

Bilgisayar acilir (startup)
  → .bat calisir
  → Carsamba mi?
    → EVET: flag olustur + gateway baslat
    → HAYIR: sessiz cik

Carsamba 00:00/04:00/08:00/12:00/16:00/20:00
  → LLM cron calisir
  → flag var mi?
    → EVET: bakim yap + flag sil
    → HAYIR: sessiz cik
```

## Kullanıcı Komutlu Full Backup — "sıkıl ve memory guncellensın"

Kullanıcı `"sıkıl ve memory guncellensın"` (veya `"skill ve memory guncelle"`) dediğinde, otomatik cron'lardan bağımsız olarak **manuel 3-repo full backup** tetiklenir.

### Zorunlu Adımlar (Hiçbiri Atlanmaz)

1. **`Watcher-Hermes/hermes-skills`** — Skill güncellemeleri push edilir
2. **`Watcher-Hermes/hermes-memory-backup`** — MEMORY.md + USER.md (token temizlenmiş) push edilir
3. **`Watcher-Hermes/hermes-full-backup`** — Skills klasörü **komple silinir**, yeniden kopyalanır, git add + commit + push main yapılır

### hermes-full-backup İçin Özel Adımlar

```bash
cd /c/Users/marko/hermes-full-backup
git pull origin main
rm -rf skills/
cp -r /c/Users/marko/AppData/Local/hermes/skills/ skills/
git add -A
git commit -m "Full backup $(date +%Y-%m-%d_%H:%M)"
git push origin main
```

### Neden 3 Repo?

| Repo | İçerik | Amaç |
|------|--------|------|
| `hermes-skills` | SKILL.md + references | Canlı skill kütüphanesi (geliştirme) |
| `hermes-memory-backup` | MEMORY.md + USER.md | Hafıza snapshot (token temiz) |
| `hermes-full-backup` | skills/ + memory/ + config/ | Tam felaket kurtarma (bare metal restore) |

Bu kural MEMORY'de kayıtlıdır ve her oturumda uygulanır. Atlama yapılırsa kullanıcı uyarır.

## Kurtarma

Manuel tetikleme:
```bash
# Gunluk sync
python3 /c/Users/marko/AppData/Local/hermes/scripts/sync_hermes_backup.py

# Haftalik bakim (flag elle olustur)
echo "%date% %time%" > /c/Users/marko/AppData/Local/hermes/haftalik-bakim.flag
# Sonra cron'u bekle veya Hermes'ten cronjob action='run' job_id='066c3c1ed9e3'
```

## Referans Dosyaları

Bu skill'in şu referans dosyaları vardır:
- `references/mnemosyne-migration.md` — Mnemosyne memory provider'a geçiş planı
- `references/backup-repo-yapisi.md` — Yeni repo organizasyonu
- `references/skill-github-sync-workflow.md` — Skill güncellemesi → GitHub push adımları
- `references/memory-manual-backup.md` — MEMORY.md + USER.md manuel yedekleme

## Bilinen Sorunlar

1. **Skills backup remote branch korumasi** (2026-06-16 itibarıyla): `Watcher-Hermes/hermes-skills` reposu **canlı ve erişilebilir** ancak **public repo branch koruma kuralları** nedeniyle doğrudan push reddediliyor:
   - Hata: `push declined due to repository rule violations`
   - Sebep: Public repo'da branch koruma aktif (signed commit, PR zorunluluğu, vs.)
   - Çözüm: Private repo'ya push et, veya `main` branch'ine `master:main` formatında push dene. Branch koruması kaldırılana kadar skills güncellemeleri local'de kalır, GitHub'a itilemez.

   **Yeni repo yapısı (14 Haziran 2026 itibarıyla):**
   - `Watcher-Hermes/hermes-mouse` → windows-automation skill'leri
   - `Watcher-Hermes/hermes-skills` → diğer tüm skill'ler
   - `Watcher-Hermes/obsidian-vault` → Obsidian vault yedekleri

   `sync_hermes_backup.py` script'i remote URL'i `Watcher-Hermes/hermes-skills` olarak güncellenmeli.

2. **MEMORY.md/USER.md snapshot pattern**: Mnemosyne gibi yeni bir memory provider'a geçişten önce, mevcut MEMORY.md ve USER.md içeriği Obsidian vault `08-Backup/` klasörüne markdown olarak yedeklenmeli. Bu, eski hafızanın kaybolmamasını garanti eder. Örnek: `08-Backup/MEMORY-yedek-2026-06-14.md`

3. **Token backup'ı GitHub push protection'a takılır**: Skill referans dosyalarında gerçek PAT varsa push bloke olur. `git push --force origin master` ile boş repo'ya bile göndermek için önce `.git`'i silip yeniden başlat gerekebilir.
