---
name: hermes-telegram-sync
description: "Hermes Agent ile Telegram bot arasinda kopru kurar. Iki yonlu senkronizasyon saglar: Telegram'dan mesaj geldiginde Hermes Agent'a iletilir, Hermes Agent'in cevabi Telegram'a gonderilir. Skill kutuphanesi, .env ayarlari ve vault verisi her iki tarafta da ayni kalir."
title: "Hermes Telegram Sync"

audience: user
tags: [agents, ai, automation, sync, telegram]
category: autonomous-ai-agents---

# Hermes – Telegram Köprü

## Amaç
Hermes Agent ile Telegram’daki otomasyonu tek çatı altında toplamak. Artık iki ayrı sistem değil; tek kaynak, tek skill seti, tek doğruluk.

## Mimari
- **Kaynak:** Hermes Agent (`C:\Users\marko\AppData\Local\hermes\`)
- **Yönlendirici:** `_bridge/router.py` (queue/answers klasörleri)
- **Dışarıdan tetikleme:** Telegram → n8n webhook veya doğrudan HTTP POST
- **İç tetikleme:** Hermes Agent herhangi bir skill sonucu → router.py’ye yaz → Telegram’a gönder

## Kurulum Adımları

### 1. Ortak Değişkenleri bul
Şu değerler her iki tarafta da aynı olmalı:
- Telegram bot token (`TELEGRAM_BOT_TOKEN`)
- Chat ID (`TELEGRAM_CHAT_ID`)
- Hermes Agent home (`HERMES_HOME`)
- Obsidian vault path (`OBSIDIAN_VAULT`)

Bu değerleri `.env` dosyasından oku. İki farklı `.env` varsa birleştir.

### 2. Köprüyü başlat
```powershell
python "C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\_bridge\router.py"
```

Arka planda çalisin ya da Windows görev zamanlayicisina ekle.

**Ön kontrol:** köprüyü baslatmadan önce n8n’in çalismasini dogrula.
- `localhost:5678` açik mi?
- `localhost:15680` açik mi?

n8n kapaliysa önce n8n’i baslat. Aksi takdirde köprü baslasa da iletim basarisiz olur.

`_bridge/router.py` tek basina HTTP sunucu degildir; n8n workflow’undan tetiklenmelidir.

### 3. n8n workflow’u bağla
n8n’de şu düzen kullan:
```
Telegram Trigger → HTTP Request (localhost:15680/obsidian/write) → Telegram Send
```

Eğer Hermes Agent bir cevap üretecekse, n8n onu beklemeli ya da webhook dönmeli.

### 4. Test
- Telegram’dan “test” yaz
- n8n yakalar, Hermes’e iletir
- Hermes cevabı `_bridge/answers/<chat_id>.json`’a yazar
- n8n bu dosyayı okuyup Telegram’a gönderir

## Kuralları
- Tek kaynak `.env` → değişiklikler her yere yansır
- Skill silme/yenileme sadece Hermes tarafında yapılır; Telegram’a manuel güncelleme yok
- .env değişirse tetikle: `python C:\Users\marko\hermes-ai\env_watcher.py`

## Kontrol Listesi
- [ ] Telegram bot token ve chat ID aynı mı
- [ ] Hermes Agent ayarları `.env`’de güncel mi
- [ ] `_bridge/router.py` çalışıyor mu
- [ ] n8n workflow bağlı mı
- [ ] Test mesajı iki yönlü geçiyor mu

## Sorun Giderme
- “PermissionError 10013” → portu 127.0.0.1:0 ile rastgele aç
- n8n çalışmıyorsa → `localhost:5678` yerine doğrudan router’a HTTP POST yap
- .env değişikliği görünmüyorsa → env_watcher.py’yi çalıştır



---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Hermes Agent ile Telegram bot arasinda kopru kurar. Iki yonlu senkronizasyon saglar: Telegram'dan mesaj geldiginde Hermes Agent'a iletilir, Hermes Agent'in cevabi Telegram'a gonderilir. Skill kutupha |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_hermes-telegram-sync.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Hermes Telegram Sync islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hermes Agent ile Telegram bot arasinda kopru kurar. Iki yonlu senkronizasyon saglar: Telegram'dan mesaj geldiginde Hermes Agent'a iletilir, Hermes Agent'in cevabi Telegram'a gonderilir. Skill kutuphanesi, .env ayarlari ve vault verisi her iki tarafta da ayni kalir. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: "Hermes Agent ile Telegram bot arasinda kopru kurar. Iki yonlu senkronizasyon saglar: Telegram'dan mesaj geldiginde Hermes Agent'a iletilir, Hermes Agent'in cevabi Telegram'a gonderilir. Skill kutupha
Nerede: `autonomous-ai-agents\autonomous-ai-agents_hermes-telegram-sync.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Hermes Telegram Sync islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


## Alternatif: Dosya Bazlı Kurtarma (n8n'siz)

Eğer n8n kapalıysa veya kurulum istemiyorsan, **dosya bazlı kurtarma** yöntemi kullanılabilir. Bu yöntem n8n gerektirmez.

### Mimari Farkı
| Yöntem | Araç | Karmaşıklık |
|--------|------|------------|
| n8n köprüsü | n8n + router.py | Yüksek |
| **Dosya bazlı kurtarma** | Cron job + takildi.txt | **Düşük** |

### Nasıl Çalışır
```
Local Hermes takılır → C:\Users\marko\takildi.txt oluşturur
Telegram Hermes cron job'u (her 15 dk) → dosyayı bulur
→ Tor'da araştırma yapar → çözümü Telegram'a bildirir
→ takildi.txt silinir
```

### Cron Job Detayı
- **Job adı:** Takilma-Izleyici
- **Çalıştığı yer:** Telegram Hermes (bu session)
- **Kontrol sıklığı:** 15 dakikada bir
- **Yüklü skill:** tor-browser-arama
- **Local Hermes'te gereken:** takili-kalma skill'i aktif olmalı (5. kural: Telegram Kurtarma Sinyali)

### ÖNEMLİ Kısıt
Local Hermes'in kendi başına web'de arama (Tor Browser, web_search, web_extract) yeteneği YOKTUR. Bu nedenle araştırma her zaman Telegram Hermes tarafından yapılır.

### Referans
Detaylı akış için: `takili-kalma` skill'indeki `references/kurtarma-akisi.md`
