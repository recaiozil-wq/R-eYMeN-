# Güvenlik Politikası / Security Policy

## 🛡️ Desteklenen Sürümler

| Sürüm | Destek |
|:------|:-------|
| 0.9.x (beta) | ✅ Güvenlik yamaları |
| < 0.9 | ❌ Desteklenmiyor |

## 🔐 Güvenlik Açığı Bildirimi

ReYMeN'de bir güvenlik açığı bulursan:

1. **Herkese açık issue AÇMA**
2. **Telegram'dan iletişime geç:** @Pasa_38
3. Veya e-posta: (yakında)

### Beklenen yanıt süresi

- İlk dönüş: 48 saat içinde
- Düzeltme: 7 gün içinde

## ⚠️ Bilinen Güvenlik Uyarıları

### API Anahtarları

- `.env` dosyasını **asla** git'e gönderme
- `.env.example` dosyasını düzenleyip `.env` olarak kullan
- Linux'ta: `chmod 600 .env`
- API anahtarları log'a yazılmaz (filtre ile korunur)

### Token Güvenliği

- Telegram bot token'ları `.env`'de saklanır
- Her bot için ayrı token kullan
- Token sızdırılırsa: BotFather'da `/revoke` ile iptal et

### Çalıştırma Güvenliği

- `approvals.mode: smart` — tehlikeli işlemler için onay ister
- Sandbox modu: Dosya erişimi proje diziniyle sınırlanabilir
- PII redaction: Hassas veri otomatik temizlenir
