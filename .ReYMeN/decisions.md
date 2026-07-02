# Karar Kaydı — 3 Modül Entegrasyon

**Tarih:** 2026-07-02 00:30

## Ne yapıldı?
Credential Pool, Voice Mode, API Server modülleri reymen_launcher.py'ye entegre edildi.

## Entegrasyon

| Modül | Çağrı | Açıklama |
|-------|-------|----------|
| 🔑 Credential Pool | `reymen --credential-pool` | API key havuz durumu gösterir |
| 🎤 Voice Mode | `reymen --voice` | Push-to-talk sesli arayüz başlatır |
| 🌐 API Server | `reymen --api-server --port 8000` | OpenAI-uyumlu REST API başlatır |

## Motor.py import
- `_CREDENTIAL_POOL` — credential pool singleton
- `_VOICE_MODE_KLASS` — VoiceMode sınıfı
- `_API_SERVER_KLASS` — APIServer sınıfı
- Tümü try/except ile güvenli import

---

# Karar Kaydı — Skills → OnceHafiza DB Cron Sync

**Tarih:** 2026-07-02 06:06

## Ne yapıldı?
`scan_skills_to_hafiza_cron.py` script'i düzeltildi ve çalıştırıldı:
1. **PATH**: `src/reymen/cereyan/skills/` → root `skills/` (gerçek .md dosyalarının olduğu yer)
2. **DB**: `src/reymen/merkez_db/` → root `merkez_db/` (mevcut DB'lerin olduğu yer)
3. **SCHEMA**: `skills_index.db`'ye `beceriler` + `beceriler_meta` tabloları eklendi
4. **COLUMN**: `ogrenme.db`'de `icerik` → `cozum` (mevcut schema ile uyum)

## Neden?
- Cron job kayıtlıydı ama yanlış klasörü tarıyordu (0 .md dosyası)
- Gerçek .md skill dosyaları root `skills/` klasöründeydi (~523 dosya)
- DB schema'ları oluşturulmamış veya uyumsuzdu

## Sonuç
- İlk çalıştırma: **523 yeni** eklendi (+ skills_index.db'ye, + ogrenme.db'ye)
- İkinci çalıştırma: **0 yeni, 0 güncel** — hash'ler eşleşiyor, stabil

## Alternatifler
- Mevcut script'i tamamen yeniden yazmak yerine path/schema fix'i tercih edildi
- Mevcut cron job kaydı (`skill-sync-to-hafiza`, her 6 saat) korundu, durumu "completed" olarak güncellendi
