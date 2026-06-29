---
name: github-self-update
title: "GitHub Self-Update — Projenin Kendi Reposundan Güncellenmesi"
tags: [devops, github, self-update, git, automation]
description: Pattern for any project to self-update from its own GitHub repo via git pull. Covers repo creation, self-update script with protected files, push mechanism, and cron job scheduling. Independent of upstream forks — the project pulls from itself.
version: 1.0.0
author: marko
license: MIT
platforms: [windows, linux, macos]
audience: maintainer
related_skills: [fork-sync, hermes-backup-otomasyonu, cron-job-bakimi]
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Pattern for any project to self-update from its own GitHub repo via git pull. Covers repo creation, self-update script with protected files, push mechanism, and cron job scheduling. Independent of upstream forks — the project pulls from itself. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# GitHub Self-Update — Kendi Reposundan Güncellenme

## Overview

When a project (fork, derivative, or standalone) needs to **update itself from its own GitHub repo** — not from an upstream. The project's own GitHub repo becomes the source of truth for distribution, and the local copy pulls from it.

Use cases:
- Fork that has diverged from upstream and now self-maintains
- Derivative project (like ReYMeN on Hermes çekirdeği) that needs independent updates
- Any project where "canonical" = the GitHub repo, not a local source

## Trigger

- "bu proje kendi repo'sundan güncellensin"
- "Hermes'ten bağımsız güncelleme"
- "self-update mekanizması kur"
- "git pull ile güncelleme"

## Architecture

```
GitHub (public)          Yerel (Windows)
  ┌─────────┐            ┌──────────────────────┐
  │ RePo    │  ──pull──▶ │  .hermes_sync.sh     │
  │ master  │  ◀──push── │  --sync / --push      │
  └─────────┘            │  Protected: motor.py  │
                         │  main.py, beyin.py... │
                         └──────────────────────┘
```

**Kural:** Pull sırasında protected dosyalara dokunulmaz (git stash/pop korur).
Push sırasında her şey gönderilir.

## Adımlar

### 1. GitHub Reposu Oluştur

```bash
# Public yap ki kimlik doğrulama gerektirmesin (pull için)
gh repo create PROJE-ADI --public --description "..." --push --source .
# Var olanı public yap
gh repo edit ORG/PROJE-ADI --visibility public --accept-visibility-change-consequences
```

**Neden public?** Cron job ve self-update script'i token gerektirmeden `git pull` yapabilir.

### 2. Self-Update Script'i Yaz (`.hermes_sync.sh`)

Temel yapı:

```bash
#!/bin/bash
REPO_URL="https://github.com/ORG/PROJE-ADI.git"
PROJE_DIR="/c/Users/kullanici/.../proje"

# Korunacak dosyalar (asla üzerine yazılma)
PROTECTED_FILES=("motor.py" "main.py" "beyin.py")

case "${1:-status}" in
  --sync)
    git -C "$PROJE_DIR" stash --include-untracked 2>/dev/null
    git -C "$PROJE_DIR" pull origin master 2>&1
    git -C "$PROJE_DIR" stash pop 2>/dev/null || true
    ;;
  --push)
    git -C "$PROJE_DIR" add -A
    git -C "$PROJE_DIR" commit -m "Guncelleme: $(date '+%Y-%m-%d')" 2>/dev/null
    git -C "$PROJE_DIR" push origin master 2>&1
    ;;
  *)
    git -C "$PROJE_DIR" fetch origin 2>/dev/null
    BEHIND=$(git -C "$PROJE_DIR" rev-list --count HEAD..origin/master 2>/dev/null)
    echo "Geri: ${BEHIND:-0} commit"
    ;;
esac
```

### 3. Protected Files (Kritik)

Self-update sırasında **asla değiştirilmemesi gereken** dosyalar. Bunlar projeye özel kodlardır (fork'ta değiştirilen çekirdek dosyalar).

Örnek korunan dosyalar:
- Çekirdek motor (motor.py, main.py, beyin.py)
- Güvenlik katmanı (guardrails.py)
- Özel öğrenme/sistem dosyaları
- Projeye özel araçlar

**Mekanizma:** `git stash` + `git pull` + `git stash pop` — stash alınan değişiklikler pull'dan sonra geri uygulanır. Eğer remote aynı dosyayı değiştirmişse, stash pop çakışma verir ve yerel sürüm korunur.

### 4. Cron Job ile Otomatik Güncelleme

```bash
hermes cron create \
  --name "proje-guncelleme" \
  --schedule "0 3 * * 1" \
  --prompt "Projeyi GitHub'dan guncelle: bash /path/to/.hermes_sync.sh --sync" \
  --enabled-toolsets '["terminal"]'
```

### 5. Push (Yerel Değişiklikleri Gönderme)

Script'in `--push` flag'i yerel değişiklikleri GitHub'a gönderir:

```bash
bash .hermes_sync.sh --push
```

Bu, projede yapılan değişikliklerin remote'a yedeklenmesini sağlar.

## Verification

Script çalışıyor mu kontrol et:

```bash
bash .hermes_sync.sh              # Durum: geri/ileri commit sayısı
bash .hermes_sync.sh --dry-run    # Detaylı durum
bash .hermes_sync.sh --sync       # Güncelleme dene (test)
bash .hermes_sync.sh --log        # Geçmiş log
```

## Common Pitfalls

1. **Protected dosya çakışması**: Remote protected dosyayı değiştirirse, stash pop çakışma verir. Çözüm: çakışan dosyayı elle çöz veya `git checkout --ours` kullan.
2. **GitHub token expiy**: Push için geçerli token gerekir. `gh auth status` ile kontrol et.
3. **Windows satır sonları**: Git `core.autocrlf` ayarı CRLF/LF karışıklığına yol açabilir. `.gitattributes` ekle.
4. **Büyük projelerde git pull yavaş**: İlk seferde tüm repo indirilir; sonraki pull'lar sadece delta çeker.
5. **Hermes çalışmıyorsa cron çalışmaz**: Cron job Hermes üzerinde çalışır. Hermes kapalıyken güncelleme yapılamaz.

## Related Skills

- `fork-sync`: Upstream ile karşılaştırma ve ilk senkronizasyon
- `hermes-backup-otomasyonu`: Hermes özel yedekleme
- `cron-job-bakimi`: Cron job yönetimi ve bakımı

## References

- `references/reymen-self-update.md` — ReYMeN projesi için uygulama detayları
