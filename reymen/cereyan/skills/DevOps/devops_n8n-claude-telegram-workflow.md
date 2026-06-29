---
name: n8n-claude-telegram-workflow
description: n8n + Claude/Cursor/OpenAI ile Telegram üzerinden workflow otomasyonu kurma. Tek mesajla/tek komutla tetiklenen workflow, sosyal medya otomasyonu, e-posta, YouTube clip otomasyonu, kopyala-yapıştır kur ve direkt çalıştır senaryoları için kullan. Trigger, agent modeli, credentials, paylaşım hedefi ve otomasyonu tek skill altında topla.
title: "N8N Claude Telegram Workflow"

audience: maintainer
tags: [automation, devops, system, telegram]
category: devops---

# n8n + Claude + Telegram Otomasyonu

## Amacı
Telefon/terminal üzerinden tek mesaj/tek komutla n8n workflow'unu tetiklemek. Arka planda Claude/Cursor/OpenAI ile içerik üretimi, mesajlaşma, paylaşım ve hatırlatma görevlerini otomatik yapmak. Kod bilgisi gerektirmeden kurulum yapmak.

## Kullanım
Kullanıcı "n8n", "workflow", "telegram bot", "otomasyon" veya "tek mesajla iş bitirme" gibi bir istek verdiğinde bu skill kullanılır.

## Adımlar

### 1) Gereksinimleri kontrol et
- n8n hesabı (bulut veya self-hosted)
- Telegram bot token ve chat ID
- AI modeli: Claude API, OpenAI API veya Cursor MCP
- İşlem yapılacak platformların API/credential bilgileri (Facebook, YouTube, Gmail vb.)

### 2) n8n workflow yapısı ve sağlık kontrolü
- **Yerel sunucu durumu**: kurulumdan sonra `http://localhost:5678/healthz` kontrolü yap
- **Hata ayıklama**: `~/.n8n/n8nEventLog.log` ve `~/.n8n/config` dosyalarını gözden geçir
- **Trigger**: Telegram bot mesajı, schedule veya webhook
- **Agent Model**: Claude/Cursor/OpenAI -> prompt + memory + araçlar
- **Credentials**: Her servis için API anahtarlarını n8n credential olarak ekle
- **İşlemler**: İçerik üretimi, paylaşım, mesajlaşma, e-posta
- **Çıktı**: Paylaşım, bildirim, dosya, otomasyon

### 3) Kurulum
1. n8n'e gir, yeni workflow oluştur
2. Trigger ekle (Telegram bot, zamanlı, veya webhook)
3. Agent modelini ekle (Claude veya OpenAI)
4. Gerekli credentials ekle
5. Paylaşılacak platformu seç (Facebook, YouTube, Telegram, email)
6. İlk workflow'u test et
7. Aktif et

### 4) Tek komutla tetikleme
- Telegram'da botuna mesaj yaz: "Yeni paylaşım yap"
- n8n trigger bu mesajı yakalar
- Agent modeli işlemi başlatır
- Sonucu paylaşır veya bildirim gönderir

### 5) Kurulum sonrası
- "Bir kere kur, sürekli çalışsın" prensibi
- Günlük içerik üretimi ve paylaşımı otomatik
- Manuel müdahale gerekmez

## Klasör Yapısı
- `references/bridge-api.md` — bridge endpoint dokümanı, sağlık kontrolü ve n8n yerinde workflow şablon referansları.

### Konum
- API sunucusu: `/_bridge/server.py`
- Bağlantı: `http://127.0.0.1:15680`
- Sağlık kontrolü: `GET http://127.0.0.1:15680/health`

### Endpoint'ler
- `POST /_bridge/queue/{chat_id}.json` - Mesaj kuyruğuna ekle
- `GET /_bridge/answers/{chat_id}.json` - Kuyruktan cevap al
- `GET /health` - Sunucu sağlık durumu

### Kullanım Akışı
1. Telegram'dan mesaj alınır
2. n8n veya benzeri bir katman `POST /_bridge/queue/{chat_id}.json` endpoint'ine mesajı gönderir
3. Hermes Agent kuyruğu dinler, mesajı işler
4. Sonuç `POST /_bridge/answers/{chat_id}.json` endpoint'ine yazılır
5. n8n yanlış yana dönüş yapar

### Dosyalar
- `n8n/workflow.json` - import edilebilir workflow şablonu
- `n8n/credentials.example.json` - credential placeholder örnekleri
- Obsidian: `_bridge/WORKFLOW_NOTES.md` - detaylı notlar

---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | n8n + Claude/Cursor/OpenAI ile Telegram üzerinden workflow otomasyonu kurma. Tek mesajla/tek komutla tetiklenen workflow, sosyal medya otomasyonu, e-posta, YouTube clip otomasyonu, kopyala-yapıştır kur ve direkt çalıştır senaryoları için kullan. Trigger, agent modeli, credentials, paylaşım hedefi ve otomasyonu tek skill altında topla. |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

