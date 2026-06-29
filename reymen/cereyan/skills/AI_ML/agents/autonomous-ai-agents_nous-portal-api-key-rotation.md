---
name: nous-portal-api-key-rotation
description: >
title: "Nous Portal API Key Rotation"
  yazma kuralları; DeepSeek/Nous endpoint yapılandırmasındaki yaygın hatalar
  ve kalıcı notlar.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [nous, deepseek, api-key, rotation, portal, dotenv, config]
category: autonomous-ai-agents
audience: user
tags: [agents, ai, api, automation]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | > |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_nous-portal-api-key-rotation.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Nous Portal Api Key Rotation islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | > |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: >
Nerede: `autonomous-ai-agents\autonomous-ai-agents_nous-portal-api-key-rotation.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Nous Portal Api Key Rotation islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek
Nous Portal üzerinden API anahtarı üretme, iptal etme ve Hermes .env’e



#Nous Portal API Key Rotation

## Amaç
Nous Portal’dan anahtar ürettikten sonra bunu Hermes’in doğru okuyacağı
 `.env` değişkenine yazmak ve “yanlış değişken adı” tuzağından kaçınmak.

## Doğru değişken adı
- Provider DeepSeek üzerinden yapılandırıldıysa kullanılacak env: `DEEPSEEK_API_KEY`
- `NOUS_API_KEY` şu anki Hermes yapılandırmasında okunmuyor.
  Bu değişkene ne kadar anahtar yazarsanız, körü körüne atlanır.

## Neden bazen geçersiz anahtarla 401 alınıyor?
- Portalda üretilen anahtarın numunesi/aktif olmaması.
- Kullanıcının portalda var olan ama kredisi bitmiş/iptal edilmiş anahtarı
  yeniden denemesı.
- Anahtarın `.env` değil, config.yaml gibi başka yere yapıştırılması.

##Kurallar
1. Yeni anahtar üretildiyse sadece `.env` dosyasına yaz.
2. Yapı: config.yaml => provider, base_url vs.
3. .env => sadece API key.
4. Hermes’te gözüken anahtar maskelenir; yayma.
5. Değişiklikten sonra oturumu yenile.

## .env yolu
- Windows: `C:\Users\<user>\AppData\Local\hermes\.env`

## Doğrulanma
```bash
hermes status
```
Model/Provider ve API key satırlarını kontrol et. Endpoint 200 dönüyorsa başarılı.

## Kalıcı öğrenme
- Yanlış değişken adı: `NOUS_API_KEY` yerine `DEEPSEEK_API_KEY`
- Geçersiz anahtarlar: portalda önce aktif olduğundan emin ol.
- Çözüm anahtarı: doğru değişken adı + aktif anahtar.
