
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Cron No Agent Pattern |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Cron Job no_agent Pattern — Token-Free Otomasyon

## Ne Zaman Kullanılır

Periyodik olarak aynı komutu çalıştırman gerektiğinde, **LLM token harcamadan**.

| Durum | no_agent | Agent (varsayılan) |
|:------|:---------|:-------------------|
| Git push, status check, disk kontrol | ✅ 0 token | ❌ Gereksiz token |
| Veri topla, raporla, özet çıkar | ❌ | ✅ LLM gerekli |
| API polling, health check | ✅ | ❌ |
| Dosya kopyala, temizlik, yedek | ✅ | ❌ |

## Nasıl Kurulur — Windows (Python)

**⚠️ KRİTİK:** Windows'ta cron ortamında **bash yok**. `.sh` script'leri patlar:
```
WSL (11 - Relay) ERROR: CreateProcessCommon:818: execvpe(/bin/bash) failed:
No such file or directory
```

**Her zaman `.py` kullan.**

```python
# 1. Script'i profiles/<profil>/scripts/ altına yaz ( .py ile bitmeli)
scripts/hourly_check.py

# 2. Cron job oluştur
cronjob(
    action='create',
    name='job-adi',
    schedule='1h',           # veya '0 3 * * *' (cron format)
    repeat=168,              # sınırlı tekrar (opsiyonel)
    script='hourly_check.py',
    no_agent=True            # KRİTİK: token harcamaz
)
```

## Script Yapısı (Python)

```python
#!/usr/bin/env python3
import os, subprocess, sys
from datetime import datetime

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, "AppData", "Local", "hermes", "profiles",
                       "reymen", "cron", "output")
os.makedirs(LOG_DIR, exist_ok=True)

ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"✅ Sonuç: Başarılı — {ts}")
print(f"│ Detay 1")
print(f"│ Detay 2")
```

## Sayıcı (Counter) Deseni

Sınırlı tekrarlı işlerde kaç kez çalıştığını takip et:

```python
COUNTER = os.path.join(LOG_DIR, "counter.txt")
run_num = 0
try:
    with open(COUNTER) as f:
        run_num = int(f.read().strip())
except (FileNotFoundError, ValueError):
    pass
run_num += 1
with open(COUNTER, "w") as f:
    f.write(str(run_num))
print(f"Koşu #{run_num}")
```

## Teslimat

- `no_agent=True` → script stdout'u cron tarafından alınır, kullanıcıya **verbatim** iletilir
- Sessiz script (boş stdout) → hiçbir şey iletilmez (watchdog deseni)
- Hatalı çıkış (non-zero exit) → hata bildirilir

## Örnek: 7 Günlük Backup (Bu Session)

| Cron | Zaman | Script | no_agent |
|:-----|:------|:-------|:---------|
| Saatlik kontrol | Her 1h × 168 | `hourly_check.py` | ✅ |
| Full backup push | 03:00 × 7 | `daily_full_push.py` | ✅ |
| Memory backup push | 00:30 × 7 | `daily_memory_push.py` | ✅ |
| Haftalık rapor | 28.06 12:00 × 1 | `weekly_report.py` | ✅ |

Bakınız: `decisions.md` Karar #6 — 7 Günlük Otomatik Backup Sistemi
