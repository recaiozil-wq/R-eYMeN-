---
name: odysseus
id: odysseus
title: "Odysseus (FEDUS) — Lokal AI Platform"
description: "Piebie/PewDiePie'nin 110M aboneye duyurduğu açık kaynak, lokal AI platformu. Docker üzerinde çalışır, 4 konteyner ile ayağa kalkar."
tags: [fedus, piebie, local-ai, docker, odysseus]
category: software-development
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Piebie/PewDiePie'nin 110M aboneye duyurduğu açık kaynak, lokal AI platformu. Docker üzerinde çalışır, 4 konteyner ile ayağa kalkar. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Odysseus (FEDUS) — Lokal AI Platform

## Trigger
Kullanıcı "odysseus" dediğinde:
1. Tarayıcıda `http://localhost:7000` aç
2. Kullanıcı: admin
3. Şifre: Hermes2026!
4. Giriş butonuna basmadan bekle (kullanıcı onaylasın)

## Şifre Kurtarma (trigger: "odysseus şifre unuttum")
Kullanıcı "odysseus şifre unuttum" derse:

1. Container'a gir:
   ```bash
   docker exec -it odysseus-odysseus-1 python
   ```

2. Python'da bcrypt hash üret:
   ```python
   import bcrypt
   new_pass = "yeni_sifre"  # kullanıcıya sor
   hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
   print(hashed)
   ```

3. auth.json'u oku/güncelle:
   ```bash
   docker exec odysseus-odysseus-1 cat /app/data/auth.json
   # password_hash ve password alanlarını güncelle
   ```

4. Yeni hash'i yaz:
   ```bash
   docker exec odysseus-odysseus-1 sh -c 'echo "{\"username\":\"admin\",\"password\":\"yeni_sifre\",\"password_hash\":\"$HASH\"}" > /app/data/auth.json'
   ```

5. Restart:
   ```bash
   cd /path/to/odysseus && docker compose restart
   ```

6. Test et:
   ```bash
   curl -X POST http://localhost:7000/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"yeni_sifre","remember":true}'
   ```

## Nedir
Piebie'nin (PewDiePie, 110M abone) 31 Mayıs 2026'da yayınladığı, tamamen lokal çalışan açık kaynak AI platformu.

## Özellikler
- Tamamen lokal (kendi bilgisayarında çalışır)
- MIT lisanslı (kullan, değiştir, sat)
- Takip/telemetri/ücret yok
- Cookbook: donanımını tarar, 270+ açık model arasından uygun olanı önerir
- Ollama entegrasyonu ile yerel modeller

## Bölümler

| Bölüm | Ne Yapar |
|-------|----------|
| Chat | Ollama modellerinle (llama3.1:8b) veya API ile sohbet |
| Agent | Web araması, dosya okuma, shell komutu çalıştırma — tamamen otonom |
| Deep Research | Bir konu ver, internette araştırıp rapor yazar |
| Compare | İki modeli yan yana kör test — hangisi daha iyi? |
| Documents | AI destekli döküman editörü |
| Memory/Skills | Seni öğrenir, ChromaDB'ye kaydeder |
| Notes & Tasks | Görev/not + zamanlı hatırlatmalar |

## Giriş
- **URL:** http://localhost:7000
- **Kullanıcı:** admin
- **Şifre:** Hermes2026! (güncellendi)

## İlk Kurulum
1. Giriş yap → Settings
2. Ollama bağla: `http://host.docker.internal:11434`
3. Model seç (llama3.1:8b gibi)
4. Kullanmaya başla

## Docker Konteynerları
| Konteyner | Port | Durum |
|-----------|------|-------|
| odysseus-odysseus-1 | 127.0.0.1:7000->7000/tcp | Ana uygulama |
| odysseus-searxng-1 | 127.0.0.1:8080->8080/tcp | Arama motoru |
| odysseus-chromadb-1 | 127.0.0.1:8100->8000/tcp | Vektör DB |
| odysseus-ntfy-1 | 127.0.0.1:8091->80/tcp | Bildirim |

## Kontrol
```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Kurulum
Docker Desktop gerekli. Repo çekilir, `docker compose up` ile başlatılır.

## Temel Kullanım

### 💬 Sohbet (en basit)
Sol menü → **Yeni Sohbet** → model seç → yaz → cevap al
Tıpkı ChatGPT gibi, ama local.

### 🤖 Ajan (en güçlü)
Sol menü → **Araçlar** → **Ajan**
Bir görev ver: "şu siteyi araştır", "dosyayı oku ve özetle"
Kendi başına internette arar, dosya okur, kod çalıştırır.

### 🔍 Derin Araştırma
Sol menü → **Derin Araştırma**
Bir konu yaz → SearXNG ile internette tarar → kaynaklardan rapor yazar
Örnek: "RTX 4070 laptop için en iyi AI modelleri 2026"

### ⚖️ Karşılaştır
İki modeli aynı soruyla test et — kör test, hangisi daha iyi gör.

### 📝 Notlar / Görevler
Hatırlatmalar, yapılacaklar, zamanlı görevler.

## Hermes ile Farkı
- **Odysseus:** masada oturan asistan (konuş, çalış, görüntüle)
- **Hermes:** arka planda kendi işini yapan otonom ajan
- İkisi de lokal, ikisi de bedava
