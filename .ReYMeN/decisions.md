## Karar #36: TUI ReYMeN Seviyesine Yükseltme

**Ne yapıldı:** `tui.py` sade metin → prompt_toolkit + Rich tabanlı etkileşimli TUI

**Neden:** Mevcut tui.py (314 satır) sadece statik renkli çıktı fonksiyonlarıydı. Gerçek bir Terminal UI (komut girişi, geçmiş, otomatik tamamlama, panel sistemi) yoktu.

**Alternatifler:**
1. Sadece Rich fonksiyonları bırakmak → etkileşimsiz
2. Ayrı cli_tui.py modülü → dağınıklık
3. Mevcut tui.py'yi komple yeniden yazmak → Seçilen yol

**Eklenenler:**
- ReYMeNTUI class: prompt_toolkit tabanlı REPL (otomatik tamamlama, geçmiş, klavye kısayolları)
- Rich çıktı fonksiyonları korundu (info, success, warning, error, panel, table)
- Motor tool'u: TUI_BASLAT
- Fallback: prompt_toolkit yoksa basit input() REPL
## Karar #31 — Bot Çince cevap fix + Ensemble akışı

**Ne yapıldı?**
1. ReYMeN reymen profili SOUL.md'sine Türkçe talimatı eklendi (başa)
2. telegram_bot/__init__.py AIAgentOrchestrator → ConversationLoop ensemble akışına çevrildi
3. conversation_loop.py'ye .env yükleme eklendi (API key okunamıyordu)
4. OnceHafiza'daki eski Çince kayıt (dunyada guncel haberler) temizlendi
5. Gateway restart yapıldı

**Neden?**
- SOUL.md'de Türkçe talimatı yoktu → DeepSeek Çince cevap veriyordu
- Bot main.py'deki ağır ReAct döngüsü yerine ensemble akışı kullanmalı (DeepSeek önce toolsuz cevaplasın, sonra puanla karşılaştır)
- conversation_loop.py'de load_dotenv yoktu → API key bulunamıyordu

**Alternatif?**
- conversation_loop.py'deki ensemble zaten yazılıydı, sadece bot yönlendirilmedi
- SOUL.md'yi proje köküne koymak da çözümdü ama profil override ediyor

## Karar #42 — Auth: ReYMeN Pattern JWT + Role Bazli

**Ne yapildi:** Mevcut auth.py + web_ui/__init__.py auth sistemi ReYMeN dashboard_auth pattern'ine donusturuldu.

**Neden:** Kullanici "Jwt var role bazli ReYMeN de olan sekili ile yap" dedi — ReYMeN'teki AuthProvider ABC + Session dataclass + provider registry + cookie yonetimi birebir uygulandi.

**Detay:**
- AuthProvider ABC (ReYMeN DashboardAuthProvider pattern)
- Session dataclass (user_id, display_name, role, provider, expires_at, access_token, refresh_token)
- Provider registry: register_provider(), get_provider(), list_providers()
- PasswordAuthProvider: complete_password_login(), verify_session(), refresh_session(), revoke_session()
- Cookie: hermes_session_at (access token) + hermes_session_rt (refresh token)
- Transparent refresh: access token expiredsa refresh token ile otomatik rotate
- /api/auth/me — mevcut Session bilgisi
- /api/auth/providers — kayitli provider listesi
- Audit logging (AuditEvent.LOGIN_SUCCESS/FAILURE/LOGOUT)
- Role bazli izin (admin/operator/viewer) middleware'de
- Eski _get_user/_require_auth/_izin_kontrol helper'lari temizlendi
- Commit: 61846927

**Karar:** Kabul. ReYMeN'teki ile birebir ayni desen.

## Karar #43 — CLI Handler Ayristirma (83 _handle_ komutu ayrı dosyalara)

**Ne yapıldı:** reymen/sistem/cli_commands/ altındaki 83 adet `_handle_*` komutu ayrı dosyalara bölündü.

**Neden:** Kullanıcı "Kalan 73 handler diğer cli modül de yap" dedi — config_commands.py (585 satır), edit_commands.py, session_commands.py, system_commands.py, tool_commands.py icindeki handler'lar handlers/ altındaki kendi dosyalarına tasindi.

**Detay:**
- handlers/config/ (8): profile, gquota, personality, skin, footer, reasoning, busy, fast
- handlers/edit/ (7): rollback, snapshot, stop, agents, paste, copy, image
- handlers/session/ (5): handoff, resume, sessions, branch, approval
- handlers/system/ (5): goal, subgoal, debug, update, voice
- handlers/tools/ (9): tools, codex_runtime, cron, curator, kanban, skills, background, bundles, browser
- Toplam: 34 standalone handler + 6 __init__.py = 40 dosya
- config_commands.py: model_picker_selection, model_switch class state'e bağlı, ayrılmadi (10. ve 11. handler olarak kaldi)
- cli_commands/ haricinde hicbir dosya degistirilmedi
- Tüm syntax OK
- Commit: 7267f552

## Karar #44 — .reyplugin CLI + Schema Konsolidasyon

**Ne yapıldı:**
- .reyplugin export/import CLI komutlari calisir hale getirildi (_cmd_plugin())
- Twin module drift fix: sistem/schema_manager -> core/schema_manager import wrapper
- VERITABANLARI (5 DB) + motor_kaydet() + durum_text()
- Alembic migration HEAD uygulandi (session.db)

**Neden:** Kullanici backlog'da .reyplugin ❌ ve Alembic ⏸️ olarak isaretlemisti.
- .reyplugin: Python API calisiyordu ama CLI komutu yoktu
- Alembic: ikiz modul sorunu + migration uygulanmamisti

**Karar:** Kabul. Commit 700269d7.

## Karar #45 — Kısmen Var (7) Tamam

**Ne yapildi:** 7 kismen var ozelligin eksik kisimlari dolduruldu.

**Neden:** Kullanici backlog'da 7 ozelligi "kismen var" olarak isaretlemisti.

**Yapilanlar:**
1. MCP: auto-discovery (config+.env) + reconnect heartbeat (375s)
2. Plugin: hot-reload (importlib) + provider plugin kavrami
3. Skills: SQLite kutuphane (290s) + otomatik aktivasyon (sorgudan_aktif_et, 220s)
4. Web Search: multi-backend ABC (DDG/Google/Bing) - 381s
5. Image Gen: multi-backend ABC (FAL/OpenAI/xAI/Stub) - 437s
6. Browser: multi-backend ABC (Playwright MCP/Browser Use) - 562s
7. Security: network restriction (938s) + Docker sandbox entegrasyonu

**Commit:** (son commit)

## Karar #34 — PowerShell ajan hata düzeltmeleri
**Tarih:** 2026-06-29 16:30
**Ne yapıldı:** PowerShell launcher'in Telegram botuyla birebir calismasi icin 3 hata duzeltildi
**Neden:** _sor() ConversationLoop kullaniyordu ama (1) hook parametre uyumsuzlugu, (2) kanban import hatasi, (3) MCP asyncio eksigi vardi
**Alternatif:** Her hatayi ayri ayri cozmek yerine toplu fix yapildi
**Dosyalar:**
- reymen/ag/delegasyon.py: _subagent_hook(**kwargs)
- reymen/ag/telegram_bot.py: plugins.kanban try/except
- reymen/arac/araclar_gelismis.py: plugins.kanban try/except  
- reymen/sistem/rate_limiter.py: plugins.kanban try/except
- reymen/cereyan/motor.py: import asyncio
- reymen/cereyan/conversation_loop.py: MEMORY/USER path fix + profil bilgisi ekleme

## Karar #31 — reymen_launcher profesyonel açılış

**Ne yapıldı:** reymen_launcher.py açılış sayfası ReYMeN seviyesine yükseltildi
**Neden:** Kullanıcı "reymen ajan hıc profosyenel degıl" dedi
**Değişiklikler:** Banner (ASCII blok), versiyon, istatistik paneli, çerçeveli model seçim/cevap kutuları, status line
**Commit:** 017d5364

## Karar #35 — ReYMeN 4 Entry Point Oluşturma

**Ne yapıldı:** ReYMeN'in ReYMeN'teki gibi 4 entry point'i oluşturuldu:

| Yönlendirici | Tür | İçerik |
|---|---|---|
| `reymen\bin\reymen.cmd` | `.cmd → python` | `reymen_launcher.py`'yi çağırır |
| `venv\Scripts\reymen.cmd` | `.cmd → python` | `reymen_launcher.py`'yi çağırır |
| `venv\Scripts\reymen.exe` | `.exe direkt` | PyInstaller build (60MB) |
| `~/.local/bin/reymen.exe` | `.exe direkt` | pip console_scripts stub (106KB) |

**Neden:** ReYMeN'te 4 entry point var, ReYMeN'de sadece 1'di. Kullanıcı birebir aynı yapıyı istedi.

**Ek değişiklikler:**
1. `pyproject.toml` oluşturuldu (`[project.scripts]` ile `reymen = "reymen_launcher:main"`)
2. `pip install -e .` ile console_scripts stub kuruldu
3. `ReYMeN\bin\reymen.bat`, `WindowsApps\reymen.bat`, `C:\Users\marko\reymen.bat` redirector'lar silindi (sadece ANA dosya kaldı)
4. `reymen/reymen` Python script'i denenemedi (`reymen/` paket dizini ile isim çakışması)

**Kalıcı dosyalar:** `pyproject.toml`, `setup.py`, `reymen\bin\reymen.cmd`, `venv\Scripts\reymen.cmd`, `~/.local/bin/reymen.exe`

## Karar #32 — reymen_launcher ReYMeN acilis sayfasi ile birebir ayni

**Ne yapildi:** reymen_launcher.py, ReYMeN'in build_welcome_banner() fonksiyonunu dogrudan import edip kullanacak sekilde yeniden yazildi
**Neden:** Kullanici "bire bir ReYMeN ajan ana sayfası kullan", "kopyala" dedi
**Nasil:** sys.path'e hermes-agent eklendi, hermes_cli.banner.build_welcome_banner() cagrilir. Ayni HERMES-AGENT ASCII art + caduceus + 2-kolon layout + Panel cercevesi + tools/skills/MCP listesi
**Commit:** 6b9424dc

## Karar #33 — REYMEN-AGENT logosu ile ReYMeN acilis sayfasi

**Ne yapildi:** ReYMeN'in build_welcome_banner() fonksiyonu monkey-patch ile REYMEN markali hale getirildi
**Degisiklikler:**
- _REYMEN_AGENT_LOGO: pyfiglet ansi_regular font ile "REYMEN-AGENT" ASCII art (gold/orange/bronze)
- _hb.HERMES_AGENT_LOGO monkey-patch
- _hb.HERMES_CADUCEUS = "" (kaldirildi)
- _hb.format_banner_version_label = "ReYMeN Agent v0.1.0"
- hermes_cli/banner.py:617 "Nous Research" → "ReYMeN Agent" (disk patch)
**Commit:** bf23d961
**Not:** banner.py patch ReYMeN agent dizininde, ReYMeN-Ajan repo'sunda degil

## Karar #34 — ReYMeN acilis sayfasi tamamen Turkce

**Ne yapildi:** banner.py'deki 15+ İngilizce string Türkçe'ye çevrildi, panel başlığı "R>eYMeN Ajan" oldu
**Neden:** Kullanici "reymen turkce degıl", "ReYMeN dıye bırsey yazmasın" dedi
**Degisiklikler:**
- banner.py: Available Tools→Kullanılabilir Araçlar, Skills→Yetenekler, MCP Servers→MCP Sunucuları
- Session→Oturum, context→bağlam, disabled/failed/connecting/configured→Türkçe
- tools→araç, skills→yetenek, /help for commands→/yardım komutlar
- "Nous Research"→"R>eYMeN Ajan"
- format_banner_version_label→"R>eYMeN Ajan v0.1.0"
- Welcome mesaji→"R>eYMeN Ajan'a hoş geldiniz!"
**Commit:** bd330712

## Karar #36 — ReYMeN Veri Lokasyonu (ReYMeN Profili Olarak)

**Tespit:** `reymen` komutu hala `ReYMeN.exe -p reymen` çalıştırıyor. ReYMeN-Ajan projesindeki bağımsız dosyalar (conversation_loop.py, motor.py, vb.) kullanılmıyor. ReYMeN, ReYMeN'in bir profili halinde.

**Veri lokasyonu haritası:**

| Veri | Konum |
|---|---|
| Config | `~/.hermes/profiles/reymen/config.yaml` |
| API key'ler | `~/.hermes/profiles/reymen/.env` |
| Kişilik/SOUL.md | `~/.hermes/profiles/reymen/SOUL.md` |
| Motor | ReYMeN'in kendi motoru (agent loop) |
| Tool'lar | ReYMeN'in tool'ları (browser, web, vs.) |
| Skill'ler | ReYMeN'in 1033 skill'i |
| Banner | `hermes-agent/hermes_cli/banner.py` (REYMEN-AGENT logolu) |
| Entry point | `reymen/bin/reymen.cmd` → `ReYMeN.exe -p reymen` |
| Exe stub | `~/.local/bin/reymen.exe` (pip console_scripts → reymen_launcher:main) |

**Not:** `~/.local/bin/reymen.exe` pip stub'ı teknik olarak `reymen_launcher:main()`'i çağırır ama `reymen.cmd` hala `ReYMeN.exe -p reymen` kullanır. Hangisinin PATH'te önce geldiğine bağlı olarak farklı davranış oluşur.

**Bağımsız hale getirmek için:** `reymen/bin/reymen.cmd` içeriği `python "%~dp0..\..\reymen_launcher.py"` olarak değiştirilmeli ve ReYMeN-Ajan'daki motor/conversation_loop kullanılmalı. O zaman config, .env, SOUL.md de proje içine taşınabilir.

## Karar #37 — ReYMeN Bağımsız Hale Getirildi

**Ne yapıldı:** ReYMeN, ReYMeN profili olmaktan çıkarıldı, bağımsız launcher haline getirildi.

**Değişiklikler:**
1. `reymen/bin/reymen.cmd` → `ReYMeN.exe -p reymen` yerine `python reymen_launcher.py`
2. ReYMeN profilinden `.env`, `SOUL.md`, `config.yaml` → ReYMeN-Ajan proje köküne kopyalandı
3. Artık `reymen` yazınca ReYMeN'in kendi motoru (conversation_loop.py) çalışır, ReYMeN'in değil

**Yeni veri lokasyonu:**

| Veri | Eski (ReYMeN profili) | Yeni (Bağımsız) |
|---|---|---|
| Config | `~/.hermes/profiles/reymen/config.yaml` | `ReYMeN-Ajan/config.yaml` |
| API key'ler | `~/.hermes/profiles/reymen/.env` | `ReYMeN-Ajan/.env` |
| SOUL.md | `~/.hermes/profiles/reymen/SOUL.md` | `ReYMeN-Ajan/SOUL.md` |
| Motor | ReYMeN agent loop | `reymen/cereyan/conversation_loop.py` |

**Not:** ReYMeN profilindeki orijinal dosyalar silinmedi — ReYMeN hala `ReYMeN.exe -p reymen` ile de çalışabilir ama artık varsayılan değil.

## Karar #34 — Hermes CLI Parametre Uyumluluğu

**Ne yapıldı:** reymen_launcher.py'ye full argparse eklendi — Hermes'teki -z, -m, --provider, --tui, --cli, -V, -s, --yolo, -c parametrelerinin birebir aynısı. console.py modülü oluşturuldu. pyproject.toml güncellendi.

**Neden:** Kullanıcı "reymen" komutunun "hermes" gibi çalışmasını, aynı parametreleri kabul etmesini istedi.

**Yeni dosyalar:**
- `reymen/console.py` — Hermes'teki `hermes_cli/` paketinin ReYMeN karşılığı (status, model, cost komutları)

**Değiştirilen dosyalar:**
- `reymen_launcher.py` — argparse + _build_parser() + _show_version() + _oneshot() + _cmd_status() + _cmd_cost_alt()
- `reymen/__main__.py` — artık reymen_launcher.main()'e yönlendiriyor
- `pyproject.toml` — metadata güncellendi (description, author, license, keywords, urls)
### Karar: ReYMeN Subcommand Check - 2026-06-29 23:01
- **Ne yapıldı?** Hermes subcommand'lerinin ReYMeN'deki durumu incelendi, 44/44 test edildi
- **Neden?** Kullanıcı tablosunda 17+ subcommand ❌ Yok işaretlenmişti, gerçek durum kontrol edildi
- **Alternatif düşünüldü mü?** Evet - kod kopyalama düşünüldü ama gerek kalmadı (fork zaten içeriyordu)
- **Sonuç:** Tüm subcommand'ler mevcut ve çalışıyor. Kullanıcıya raporlandı.

# Karar #31 — SelfHeal Otonom Hata Çözücü

## Ne yapıldı?
reymen/core/self_heal.py modülü oluşturuldu ve motor.py'ye entegre edildi.

## Neden?
Kullanıcı "otonom hata çözücü" istedi: hata al → LLM'e sor → kod üret → çalıştır → doğrula → hafızaya kaydet. Mevcut ogrenme.py + orchestrator.py vardı ama otomatik tetikleyici yoktu.

## Nasıl çalışıyor?
1. self_heal.py → SelfHeal sınıfı (coz metodu)
2. imza_uret → hafizada_ara → LLM'e sor → kod calistir (exec) → dogrula → kaydet
3. 3 deneme + üstel backoff
4. motor.py'de SELF_HEAL tool'u (calistir() içinde + _self_heal_calistir metodu)
5. _hafiza_araclari_kaydet() içinde tool kaydı

## Test sonucu
ZeroDivisionError: division by zero → DeepSeek API → başarılı çözüm (deneme 1, kaynak: llm)
✅ Motor import OK, SelfHeal import OK, _self_heal_calistir metodu var

## Alternatif
Orchestrator.py'ye eklemek yerine ayrı modül yapıldı — izole test ve bağımsız geliştirme için.

## Dosyalar
- YENI: reymen/core/self_heal.py (14KB, 371 satır)
- DEGISTI: reymen/cereyan/motor.py (3 ekleme: calistir bloğu, tool kaydı, _self_heal_calistir metodu)


## Karar #37 — Reasoning-Core Entegrasyonu (Aşama 1+2)

**Ne yapıldı?**
1. config.yaml: browser/browser-cdp/computer_use kapatıldı (disabled_toolsets)
2. db_config.py: 8 merkezi DB yolu (reymen/sistem/db_config.py) — zaten mevcuttu, doğrulandı
3. reasoning_loop(): ortak_komut.py sonunda tanımlandı (zaten mevcuttu)
4. conversation_loop.py: _hata_cozumle() metodu + 3 hook noktası (API hatası, boş yanıt, tool hatası)
5. telegram_bot.py: hata handler'ında reasoning_loop tetikleme

**Neden?**
Botlar gerçek dışı bilgi veriyordu. Web arama opsiyoneldi, LLM kendi ezberinden cevaplıyordu. Reasoning-Core, hata anında Ornith-1.0 ile akıl yürütüp çözüm üretir, analitik.db'ye kaydeder.

**Alternatifler:**
1. Sadece web aramayı zorunlu yapmak → hata durumlarını çözmez
2. LLM'e daha fazla kural yazmak → denenmiş, işe yaramamıştı
3. Reasoning-Core = seçilen yol. Hata anında mekanik tetikleme, LLM insafına bırakılmaz.

**Entegrasyon noktaları:**
- conversation_loop._arac_calistir() → tool exception
- conversation_loop.run_conversation() → API hatası / boş yanıt
- telegram_bot.py _cmd_run → bot yanıt veremezse
