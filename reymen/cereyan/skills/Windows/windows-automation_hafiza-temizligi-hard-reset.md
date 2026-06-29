---
name: hafiza-temizligi-hard-reset
description: "Hermes Agent cache/session/state temizligi. IKI MOD: 'konusma gecmisimi sil' (sadece state.db + sessions) veya 'hard reset' (cache, history, log + her sey)."
title: "Hafiza Temizligi Hard Reset"
category: windows-automation
audience: user
tags: [automation, windows]
---


> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hermes Agent cache/session/state temizligi. IKI MOD: 'konusma gecmisimi sil' (sadece state.db + sessions) veya 'hard reset' (cache, history, log + her sey). |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hafıza Temizliği — Hard Reset

## İKİ MOD

### MOD A — "Konuşma geçmişimi sil" (LIGHT)
Sadece state.db + sessions gider. Cache, .hermes_history, logs, screenshots vb. **dokunulmaz.**

```
Tetikleyiciler: "konuşma geçmişimi sil", "sohbet geçmişini sil", "state sıfırla"
```

### MOD B — "Hard reset" / "Hafıza temizliği" (FULL)
state.db + sessions + cache + .hermes_history + logs + screenshots + model cache + snapshots.
**Skills, config, .env, memories, hooks, cron, SOUL.md korunur.**

```
Tetikleyiciler: "hard reset", "hafıza temizliği yap", "her şeyi sil", "cache sil"
```

---

## MOD A — Konuşma Geçmişi Sil (LIGHT)

```powershell
$h = "$env:LOCALAPPDATA\hermes"

# state.db boyutunu raporla
if (Test-Path "$h\state.db") {
    $size = [math]::Round((Get-Item "$h\state.db").Length / 1MB, 1)
    Write-Output "state.db: ${size}MB"
}

# SADECE state.db + sessions
Remove-Item "$h\state.db" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\state.db-wal" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\state.db-shm" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\sessions\*" -Recurse -Force -ErrorAction SilentlyContinue

# Doğrula
if (-not (Test-Path "$h\state.db")) { Write-Output "✓ state.db temizlendi" }
```

**Rapor:**
```
✓ Konuşma geçmişi silindi

Temizlenen:
  * state.db (X MB)
  * sessions/

Korunan:
  * cache/ (önbellekler korundu)
  * .hermes_history (komut geçmişi korundu)
  * logs/, screenshots/, image_cache/ (korundu)
  * Tüm config, skills, memories
```

---

## MOD B — Hard Reset (FULL)

```powershell
$h = "$env:LOCALAPPDATA\hermes"

# state.db boyutu
if (Test-Path "$h\state.db") {
    $size = [math]::Round((Get-Item "$h\state.db").Length / 1MB, 1)
    Write-Output "state.db: ${size}MB"
}

# Onay alındıktan sonra:
# 1. state.db + WAL
Remove-Item "$h\state.db" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\state.db-wal" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\state.db-shm" -Force -ErrorAction SilentlyContinue

# 2. Session
Remove-Item "$h\sessions\*" -Recurse -Force -ErrorAction SilentlyContinue

# 3. Cache
Remove-Item "$h\cache\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$h\audio_cache\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$h\image_cache\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$h\images\*" -Recurse -Force -ErrorAction SilentlyContinue

# 4. Komut geçmişi
Remove-Item "$h\.hermes_history" -Force -ErrorAction SilentlyContinue

# 5. Model/context cache
Remove-Item "$h\provider_models_cache.json" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\models_dev_cache.json" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\context_length_cache.yaml" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\ollama_cloud_models_cache.json" -Force -ErrorAction SilentlyContinue

# 6. Snapshot cache
Remove-Item "$h\.skills_prompt_snapshot.json" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\obsidian_sync_state.json" -Force -ErrorAction SilentlyContinue

# 7. Log ve geçici dosyalar
Remove-Item "$h\logs\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$h\screenshots\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$h\pastes\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$h\*creao*.png" -Force -ErrorAction SilentlyContinue
Remove-Item "$h\processes.json" -Force -ErrorAction SilentlyContinue
```

**Rapor:**
```
✓ Hard Reset tamamlandi

Temizlenenler:
  * state.db (X MB) — tum konusma gecmisi
  * sessions/ — session kayitlari
  * cache/ — tum onbellekler
  * .hermes_history — komut gecmisi
  * Model/context cache'leri
  * logs/, screenshots/ — gecici dosyalar

Korunanlar:
  * .env, config.yaml, skills/, memories/, hooks/
  * SOUL.md, auth.json, channel_directory.json
  * hermes-agent/, obsidian_rag_db/, cron/
  * memory_store.db — memory kayitlari
  * gateway_state.json — gateway baglantilari
```

---

## KORUNANLAR (TÜM MODLARDA)
`.env`, `config.yaml`, `skills/`, `memories/`, `hooks/`, `scripts/`,
`cron/`, `SOUL.md`, `hermes-agent/`, `auth.json`, `auth.lock`,
`channel_directory.json`, `gateway-service/`, `.git/`, `bin/`,
`obsidian_rag_db/`, `gateway_state.json`, `memory_store.db`,
`.clean_shutdown`, `.update_check`

## Güvenlik
- state.db silinmeden ÖNCE boyutu raporlanir
- MOD B (hard reset) icin kullanicidan "emin misin" onayi alinir
- MOD A (konusma gecmisi) dogrudan calisir, onay gerekmez
- Skills ve config ASLA silinmez