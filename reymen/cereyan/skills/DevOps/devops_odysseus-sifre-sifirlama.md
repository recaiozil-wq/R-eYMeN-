---
name: odysseus-sifre-sifirlama
description: Odysseus admin şifresini sıfırla — giriş yapılamadığında kullan.
title: "Odysseus Sifre Sifirlama"
tags: [odysseus, sifre, reset, docker, admin]
category: devops
audience: maintainer
platforms: [windows]
when_to_use: |
  - Odysseus'a giriş yapılamıyor
  - Admin şifresi unutuldu
  - "Not authenticated" hatası alınıyor
procedure:
  - "1. Container içinden bcrypt ile yeni hash üret ve auth.json'a yaz:"
  - |
    docker exec odysseus-odysseus-1 bash -c "python3 -c \"
    import json, bcrypt
    new_password = 'YeniSifre123!'
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    with open('/app/data/auth.json') as f:
        d = json.load(f)
    d['users']['admin']['password_hash'] = hashed
    d['users']['admin']['password'] = hashed
    with open('/app/data/auth.json', 'w') as f:
        json.dump(d, f, indent=2)
    print('Yeni sifre:', new_password)
    \""
  - "2. Odysseus'u yeniden başlat:"
  - "docker compose -f C:/Users/marko/Desktop/odysseus/docker-compose.yml restart odysseus"
  - "3. Giriş test et (doğru endpoint /api/auth/login):"
  - 'curl -s -X POST http://localhost:7000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"YeniSifre123!\"}"'
  - '{"ok":true,"username":"admin"} dönerse başarılı'
pitfalls:
  - "API endpoint /api/auth/login — /api/v1/ değil"
  - "password_hash VE password alanlarının ikisi de güncellenmeli"
  - "Restart şart — auth.json restart'ta yükleniyor"
  - "Mevcut şifre: Hermes2026! (2026-06-11 sıfırlandı)"
verification:
  - 'curl /api/auth/login → {"ok":true} dönmeli'
  - "http://localhost:7000 tarayıcıdan açılıp giriş yapılabilmeli"
status: published
confidence: 1.0
source: learned
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Odysseus admin şifresini sıfırla — giriş yapılamadığında kullan. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Odysseus şifre sıfırlama — Docker container içinden bcrypt hash yazarak admin şifresini değiştirme yöntemi.
