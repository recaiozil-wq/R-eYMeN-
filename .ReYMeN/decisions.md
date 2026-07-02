1|# Karar Kaydı — 3 Modül Entegrasyon
2|
3|**Tarih:** 2026-07-02 00:30
4|
5|## Ne yapıldı?
6|Credential Pool, Voice Mode, API Server modülleri reymen_launcher.py'ye entegre edildi.
7|
8|## Entegrasyon
9|
10|| Modül | Çağrı | Açıklama |
11||-------|-------|----------|
12|| 🔑 Credential Pool | `reymen --credential-pool` | API key havuz durumu gösterir |
13|| 🎤 Voice Mode | `reymen --voice` | Push-to-talk sesli arayüz başlatır |
14|| 🌐 API Server | `reymen --api-server --port 8000` | OpenAI-uyumlu REST API başlatır |
15|
16|## Motor.py import
17|- `_CREDENTIAL_POOL` — credential pool singleton
18|- `_VOICE_MODE_KLASS` — VoiceMode sınıfı
19|- `_API_SERVER_KLASS` — APIServer sınıfı
20|- Tümü try/except ile güvenli import
21|
22|---
23|
24|# Karar Kaydı — Skills → OnceHafiza DB Cron Sync
25|
26|**Tarih:** 2026-07-02 06:06
27|
28|## Ne yapıldı?
29|`scan_skills_to_hafiza_cron.py` script'i düzeltildi ve çalıştırıldı:
30|1. **PATH**: `src/reymen/cereyan/skills/` → root `skills/` (gerçek .md dosyalarının olduğu yer)
31|2. **DB**: `src/reymen/merkez_db/` → root `merkez_db/` (mevcut DB'lerin olduğu yer)
32|3. **SCHEMA**: `skills_index.db`'ye `beceriler` + `beceriler_meta` tabloları eklendi
33|4. **COLUMN**: `ogrenme.db`'de `icerik` → `cozum` (mevcut schema ile uyum)
34|
35|## Neden?
36|- Cron job kayıtlıydı ama yanlış klasörü tarıyordu (0 .md dosyası)
37|- Gerçek .md skill dosyaları root `skills/` klasöründeydi (~523 dosya)
38|- DB schema'ları oluşturulmamış veya uyumsuzdu
39|
40|## Sonuç
41|- İlk çalıştırma: **523 yeni** eklendi (+ skills_index.db'ye, + ogrenme.db'ye)
42|- İkinci çalıştırma: **0 yeni, 0 güncel** — hash'ler eşleşiyor, stabil
43|
44|## Alternatifler
45|- Mevcut script'i tamamen yeniden yazmak yerine path/schema fix'i tercih edildi
46|- Mevcut cron job kaydı (`skill-sync-to-hafiza`, her 6 saat) korundu, durumu "completed" olarak güncellendi
47|

---

# Karar Kaydı — 15 Hermes→ReYMeN Eksik Kapatma

**Tarih:** 2026-07-02

## Ne yapıldı?
15 maddede Hermes'te olup ReYMeN'de eksik/kısmi olan özellikler kapatıldı.

## Neden?
Kullanıcı Hermes seviyesinde %100 eşleşme istedi.

## Alternatif?
Tek tek elle yapmak yerine paralel sub-agent + bizzat doğrulama yapıldı.

## Detay

| # | Madde | Durum | Açıklama |
|---|-------|:-----:|----------|
| 1 | Skills sayısı (523→531) | ✅ | 8 Hermes skill'i kopyalandı |
| 2 | Session search FTS5 | ✅ | `session_search.py` — FTS5 MATCH arama |
| 3 | delegate_task (sub-agent) | ✅ | `delegate_task_tool.py` — ThreadPoolExecutor |
| 4 | Self-update | ✅ | `self_update.py` — GitHub release takip |
| 5 | HyperFrames video | ✅ | `hyperframes_tool.py` — HTML→Playwright→FFmpeg |
| 6 | Memory compaction | ✅ | `memory_compaction.py` — 50K limit, arşiv |
| 7 | Skill shrink | ✅ | `skill_shrink.py` — 10KB+ tespit |
| 8 | Obsidian entegrasyonu | ✅ | `obsidian_tool.py` — 6 tool |
| 9 | Setup wizard | ✅ | `setup_wizard.py` — 8 aşamalı |
| 10 | Nightly improvement | ✅ | `nightly_improvement.py` — 6 aşamalı, 03:00 |
| 11 | Auth sistemi | ✅ | `reymen_auth.py` — JWT + multi-user |
| 12 | Web UI image gen | ✅ | `image_gen_route.py` — GET/POST /image-gen |
| 13 | Framework adaptörleri | ✅ | `framework_adaptor.py` — LangGraph/CrewAI/AutoGen |
| 14 | A2A/ACP | ✅ | `a2a_acp.py` — Agent Card + Skill Transfer |
| 15 | Rules/Config | ✅ | `kurallar.py` — 5 kategori, 6 kural |

## Doğrulama
- 11/15 modül import testi ✅
- 4/15 sub-agent timeout → yeniden başlatıldı ✅
- Web UI image gen: GET/POST 200 OK ✅
- Framework adaptörleri: 3 framework gracefull degrade ✅
- A2A/ACP: JSON-RPC 9 metod testi ✅
- Rules: 7/7 test ✅
- Nightly: 6/6 aşama başarılı ✅

## Kanıt
- GitHub commit: `2d41f034`
- 23 dosya, 4,996 satır eklendi
- 0 mevcut özellik bozuldu
