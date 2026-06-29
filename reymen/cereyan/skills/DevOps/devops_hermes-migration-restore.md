---
name: hermes-migration-restore
title: "Hermes Migration Restore"
tags: [automation, devops, system, tor]
description: >-
  Hermes Agent'i yeni bir bilgisayara tek GitHub linkiyle full restore etme.
  Skills, state.db (hafıza+session), config template ve restore script'ini
  tek repoda toplar. Güncelleme için -Update parametresiyle tekrar çalıştırılır.
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [migration, restore, backup, setup, windows, state-db, git]
audience: maintainer
related_skills:
      - github-repo-management
      - gece-3-github-yedek
      - obsidian-vault-kurallari
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

# Hermes Migration & Restore

## Amaç

Hermes Agent'in **tüm yapılandırmasını, skill'lerini, hafızasını ve konuşma geçmişini** tek bir GitHub reposu (`hermes-full-backup`) + tek PowerShell scriptiyle yeni bilgisayara taşımak. Tek link: `github.com/latent-hermes/hermes-full-backup`. Güncellemelerde aynı script `-Update` parametresiyle çalışır.

## Repo Yapısı

```
hermes-full-backup/
├── skills/                          # Tüm Hermes skill'leri (30+ kategori)
├── Hermes Memor/
│   ├── MEMORY.md                    # Kalıcı hafıza (sistem notları)
│   └── USER.md                      # Kullanıcı profili
├── hermes-full-restore.ps1          # Ana restore + update scripti
├── hermes-config-template.yaml      # Config şablonu (API anahtarları maskeli)
├── hermes-state-part001.zip         # state.db parça 1 (55MB)
├── hermes-state-part002.zip         # state.db parça 2 (50MB)
├── README.md                        # Anlaşılır kurulum kılavuzu
├── LiveTranscriber/                 # Projeler (dokunulmaz)
├── AmbientEar/
├── gmod_trainer.py
└── test.txt
```

## Kullanım

### İlk Kurulum (yeni bilgisayar)

```powershell
# 1. Hermes Agent'i kur (https://hermes-agent.nousresearch.com/docs)
# 2. Repoyu klonla
git clone https://github.com/latent-hermes/hermes-full-backup.git
cd hermes-full-backup

# 3. Restore scriptini çalıştır
powershell -ExecutionPolicy Bypass -File .\hermes-full-restore.ps1

# 4. API anahtarlarını gir
notepad %USERPROFILE%\AppData\Local\hermes\.env

# 5. Hermes'i başlat
hermes
```

### Güncelleme (mevcut kurulumu yenile)

```powershell
powershell -ExecutionPolicy Bypass -File %USERPROFILE%\hermes-backup\hermes-full-restore.ps1 -Update
```

## Script İç Akışı

### Restore (ilk kurulum)

1. **Repo klonlama**: `git clone` → `%USERPROFILE%\hermes-backup`
2. **Hermes durdurma**: Varsa çalışan Hermes process'i kill
3. **Skills yükleme**: `skills/` → `%AppData%\Local\hermes\skills/`
4. **state.db geri yükleme**:
   - `part001.zip` + `part002.zip` binary birleştir (Stream.Write ile)
   - `Expand-Archive` ile çıkar
   - `state.db`, `state.db-wal`, `state.db-shm` kopyala
5. **Config kontrol**: `config.yaml` yoksa template'den oluştur
6. **.env uyarısı**: Yoksa manuel giriş için hatırlat

### Update (-Update)

- Sadece `git pull` + skills + state.db günceller
- Mevcut `config.yaml` ve `.env`'ye **dokunmaz**

## state.db Yedekleme (Bu Skill'i Güncelleme)

state.db 240MB+ boyutunda olduğu için GitHub 100MB dosya limitine takılır. Çözüm:

### Sıkıştırma + Parçalama

```python
import zipfile, os

hermes_dir = r"C:\Users\marko\AppData\Local\hermes"
files = ["state.db", "state.db-wal", "state.db-shm"]

# 1. Zip (max compression)
with zipfile.ZipFile('state-backup.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for f in files:
        zf.write(os.path.join(hermes_dir, f), f)

# 2. 55MB chunk'lara böl
chunk_size = 55 * 1024 * 1024
with open('state-backup.zip', 'rb') as f:
    data = f.read()
for i in range(0, len(data), chunk_size):
    part = i // chunk_size + 1
    with open(f'hermes-state-part{part:03d}.zip', 'wb') as pf:
        pf.write(data[i:i + chunk_size])
```

### Restore (birleştirme) — PowerShell

```powershell
$stream = [System.IO.File]::OpenWrite($mergedZip)
foreach ($part in @($part1, $part2)) {
    $partData = [System.IO.File]::ReadAllBytes($part)
    $stream.Write($partData, 0, $partData.Length)
}
$stream.Close()
Expand-Archive -Path $mergedZip -DestinationPath $extractDir -Force
```

## Önemli Kurallar

### Güncelleme Koruma

`-Update` modunda `config.yaml` ve `.env` **ASLA** değiştirilmez. Sadece:
- `skills/` güncellenir
- `state.db` güncellenir

### Hassas Dosyalar

- `.env` — API anahtarları (GitHub'a pushlanmaz, manuel girilir)
- `config.yaml` — API anahtarları içerebilir (template maskeli)
- `state.db` — Session geçmişi (GitHub'da zip+split ile)

### GitHub Push Protection

Skills içinde token referansları varsa (`github_pat_` veya `ghp_`):
1. Önce `grep -rl` ile tespit et
2. `[GİZLİ-TOKEN]` ile değiştir (Python `re.sub`)
3. `git commit --amend` + `git push --force`

Detay: `github-repo-management` skill'inin **Push Protection** bölümü.

## Pitfall'lar

1. **state.db kilitli olabilir** — Hermes çalışırken state.db kilitlenir. Zip almadan önce `Stop-Process -Name hermes` ile durdur.
2. **state.db-wal büyüyebilir** — WAL dosyası checkpoint yapılmamışsa state.db ile aynı boyutta olabilir. İkisini de yedekle.
3. **GitHub 100MB limiti** — 240MB state.db, zip'te ~105MB olur. 55MB chunk'lara bölünmeli.
4. **Git LFS gerekmez** — Parçalama + birleştirme, LFS kurulumundan daha basit.
5. **İlk clone büyük olabilir** — skills + state.db ~200MB. `git clone --depth 1` kullanılabilir.
6. **Restore sırasında Hermes kapalı olmalı** — Script otomatik kapatır, ama el ile kapatmak daha güvenli.
7. **🔥 KRİTİK: Repodaki diğer dosyalara dokunma** — Repo'da Hermes dışı projeler de var (AmbientEar, LiveTranscriber, gmod_trainer, test.txt, state zips). Bunları asla silme/taşıma/değiştirme. Sadece `skills/`, `Hermes Memor/`, `hermes-config-template.yaml`, `hermes-full-restore.ps1` ve `README.md` güncellenir. Diğer dosyalar için kullanıcıdan açık onay al.
8. **GitHub Push Protection — PAT token kalıntıları** — GitHub'ın secret scanning push protection'ı, kısmi/truncated token'ları bile (`ghp_hE...KxUM`, `github...eT6B`) yakalar. Çözüm: commit'leri squash et, token hiç GitHub'a ulaşmasın:
