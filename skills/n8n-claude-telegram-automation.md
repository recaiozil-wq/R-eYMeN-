---
name: n8n-claude-telegram-automation
description: n8n, Claude ve Telegram tabanlı otomasyon kurulumları ve workflow oluşturma.
title: "N8N Claude Telegram Automation"

audience: maintainer
tags: [automation, system, telegram]
category: automation---

# n8n + Claude + Telegram Otomasyonu
Bu video iş akışıyla tek bir Telegram mesajından başlatılan, Claude destekli n8n otomasyonu kurulumunu kapsar.

## Ne zaman yüklenir
- Kullanıcı n8n ile Claude ve Telegram entegrasyonu kurmak istediğinde.
- "Tek mesajla otomasyon", "Claude workflow", "Telegram botu otomatik yanıt" gibi ifadeler geçtiğinde.
- Sosyal medya, e-posta veya mesaj otomasyonu için n8n şablonu istenirse.

## Girdi
- Kullanıcının Telegram bot tokeni ve kanal/sohbet hedefi.
- Claude / MCP bilgisi: Model endpointi ve eğer kullanılıyorsa MCP server adresi.
- n8n erişim bilgisi: Instance adresi ve API/credentials.
- Otomasyon kapsamı: Sosyal medya paylaşımı, e-posta, içerik üretimi vb.

## Çıktı
- Kurulum doğrulama raporu.
- Executable n8n workflow tanımı/XML JSON export veya adım listesi.
- Deploy ve test sonrası Telegram üzerinden doğrulama talimatı.

## Kurallar
- Kapsamlı açıklama yerine adım adım komut/parametre ver.
- Kullanıcı otomasyonu tercih eder; soru sormadan makul varsayılanlarla ilerle.
- Credentials yerine gizli değerler `[REDACTED]` olarak gösterilir; dosyaya yazılmadan önce `.env` kuralları uygulanır.

## Adımlar
1. Gereksinimleri topla: n8n instance durumu, Claude API anahtarı, Telegram bot tokeni, MCP server bilgisi.
2. n8n workflow taslağını oluştur:
   Telegram trigger → Claude prompt node → iş akışı aksiyonları.
3. Eğer MCP kullanılıyorsa MCP server node'u ekle ve endpoint/header ayarlarını yap.
4. Sosyal medya / e-posta aksiyonlarını ekle (örn. X, YouTube, Google Sheets, Email).
5. Test çalıştır: n8n execute + Telegram kanalında test mesajı gönder.
6. Sabit çalışma ayarı: execution policy/webhook/polling periyodu.

## Varyantlar
- Yöntem 1: n8n + Claude + MCP server ile workflow.
- Yöntem 2: dış servislerle hazır şablon/entegrasyon kullanımı.

## Güvenlik Notları
- `.env` ve credentials dosyalarına asla ham anahtar yazma.
- Telegram bot gönderimi için kanal ID ve token kontrolü yap.
- n8n webhook/trigger’larını public yapma; sadece güvenli substitution kullan.
