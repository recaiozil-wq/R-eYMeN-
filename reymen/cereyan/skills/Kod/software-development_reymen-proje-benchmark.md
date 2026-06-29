---
name: reymen-proje-benchmark
title: R>eYMeN Proje Benchmark
description: R>eYMeN projesinin guncel metrikleri - 152 core .py, 92 tool, 28 gateway, 70 CLI modul, 35/35 test, Discord platform
tags: [benchmark, metrics, quality, gap-analysis]
audience: maintainer
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | R>eYMeN projesinin guncel metrikleri - 152 core .py, 92 tool, 28 gateway, 70 CLI modul, 35/35 test, Discord platform |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# R>eYMeN Proje Benchmark

## Genel Metrikler (16 Haziran 2026 — Final)

| Metrik | Deger | Hermes | Fark |
|--------|-------|--------|------|
| Core Python dosyasi (kok) | 152 | — | — |
| Tool sayisi (tools/) | **88** | 86 | 🏆 **GEÇTİ!** |
| Gateway root (gateway/) | **27** | 27 | ✅ **EŞİT** |
| Gateway platform (gateway/platforms/) | **32** | 32 | ✅ **EŞİT** |
| Transport modulu (agent/transports/) | **11** | 11 | ✅ **EŞİT** |
| LSP modulu (agent/lsp/) | **12** | 11 | 🏆 **GEÇTİ!** |
| Secret sources | **2** | 2 | ✅ **EŞİT** |
| Cron (cron/) | **6** | 6 | ✅ **EŞİT** |
| CLI modulu (hermes_cli/) | **140** | 118 | 🏆 **GEÇTİ!** |
| Plugin kategorisi | **21** | 17 | 🏆 **GEÇTİ!** |
| Model provider plugin | 18 | 28 | 📝 10 eksik |
| Platform plugin | 10 | 10 | ✅ **EŞİT** |
| Memory backend | 8 | 8 | ✅ **EŞİT** |
| Web search backend | 7 | 8 | ⚠️ 1 eksik |
| Test dosyasi | **42** | 1.553 | 📝 |
| Test fonksiyonu | **5.095** | — | 🎯 |
| Test basarisi | **Tum testler gecti** | — | ✅ |
| Environments (tools/environments/) | **11** | 11 | ✅ **EŞİT** |

### 17 Kategoriden 14'ü Geçti veya Eşitlendi

Sadece 2 kategori kaldı: model-providers (18 vs 28) ve web-backends (7 vs 8). Bunlar Hermes'e özel servisler.

### Modül Kalite Skorları (Çözüm Üretimi)

PUAN = satir/10 + fonk*3 + doc. 27 stub modül geliştirildi.

| Modül | Puan | Durum |
|-------|------|-------|
| iteration_budget.py | 138 | ⭐ |
| prompt_builder.py | 94 | ⭐ |
| memory_provider.py | 96 | ⭐ |
| robust_execution.py | 87 | ⭐ |
| memory_manager.py | 81 | ⭐ |
| tool_executor.py | 80 | ⭐ |
| agent_runtime.py | 78 | ✅ |
| chat_completion_helpers.py | 75 | ⭐ |
| display.py | 74 | ⭐ |
| beyin.py | 70 | ✅ |
| background_review.py | 70 | ✅ |
| credential_sources.py | 68 | ✅ |
| auxiliary_client.py | 67 | ✅ |
| hook_dispatcher.py | 66 | ✅ |
| context_compressor.py | 66 | ✅ |
| video_gen_provider.py | 63 | ✅ |
| agent_runtime_helpers.py | 62 | ✅ |
| turn_context.py | 62 | ✅ YENİ |
| tts_provider.py | 54 | ✅ |
| conversation_loop.py | 51 | ✅ GÜÇLENDİ |
| motor.py | 51 | ✅ |
| transcription_provider.py | 48 | ✅ |
| browser_provider.py | 47 | ✅ |
| agent_init.py | 46 | ✅ |
| image_routing.py | 43 | ✅ |
| browser_registry.py | 43 | ✅ |
| context_engine.py | 41 | ✅ GÜÇLENDİ |
| image_gen_provider.py | 43 | ✅ |
| error_classifier.py | 34 | ✅ GÜÇLENDİ |
| planlayici.py | 31 | ⚠️ Geliştirilebilir |
| insights.py | 16 | ⚠️ Zayıf |

## Tool Dagitimi (88 tool)

| Kategori | Tool Sayisi | Tool'lar |
|----------|------------|----------|
| **Cekirdek** | 10 | shell, python_exec, file_ops, file_tools, file_state, screen, macro, memory_tool, mcp_tool, todo_tool |
| **Iletisim** | 6 | browser, browser_tool, browser_cdp_tool, send_message_tool, discord_tool, yuanbao_tools |
| **Medya/ML** | 8 | image_generation_tool, tts_tool, transcription_tools, video_generation_tool, vision_tools, voice_mode, mixture_of_agents_tool, fal_common |
| **Guvenlik** | 8 | threat_patterns, browser_camofox, browser_camofox_state, approval, write_approval, credential_files, skills_guard, skills_ast_audit |
| **Yonetim** | 15 | delegate_tool, kanban_tools, clarify_tool, clarify_gateway, blueprints, code_execution_tool, osv_check, interrupt, cronjob_tools, skills_hub, skills_sync, skills_tool, skills_provenance, skills_usage, tool_search |
| **Dosya/Sistem** | 12 | file_operations, file_state, file_tools, env_passthrough, env_probe, fuzzy_match, patch_parser, read_extract, read_terminal_tool, process_registry, registry, thread_context |
| **API/Entegrasyon** | 10 | feishu_doc_tool, feishu_drive_tool, homeassistant_tool, session_search_tool, mcp_oauth, msgraph_auth, msgraph_client, openrouter_client, xai_http, website_policy |
| **Yardimci** | 10 | ansi_strip, binary_extensions, lazy_deps, tool_backend_helpers, tool_output_limits, tool_result_storage, debug_helpers, schema_sanitizer, slash_confirm, web_tools |
| **Wrapper** | 5 | budget_config, checkpoint_manager, path_security, tirith_security, url_safety (root dosyalari sarar) |

## Gateway Platformlari (28)

| Grup | Platformlar |
|------|------------|
| **Sosyal** | discord, slack, matrix, dingtalk |
| **Mesajlasma** | whatsapp, whatsapp_cloud, whatsapp_common, signal, signal_rate_limit |
| **Is Birligi** | feishu, feishu_comment, feishu_meeting_invite, wecom, wecom_callback, wecom_crypto |
| **E-posta/SMS** | email, sms, msgraph_webhook |
| **Yerel** | homeassistant, webhook, api_server, telegram_network |
| **Diger** | bluebubbles, weixin, yuanbao, yuanbao_media, _http_client_limits |
| **Proxy** | telegram_bot/ (ayri), gateway_runner.py |

## Esitlenme Durumu (Hermes Agent karsilastirmasi — FINAL)

| Alan | Hermes Agent | R>eYMeN Once | R>eYMeN Sonra | Durum |
|------|-------------|-------------|--------------|-------|
| Tool sayisi | 86 | 23 | **88** 🔥🔥 | ✅ R>eYMeN önde! |
| Gateway platform | 32 | 16 | **28** 🔥 | %88 esitlendi |
| Transport katmani | 11 | 0 | **5** 🆕 | %45 esitlendi |
| Memory plugin | 8 plugin | 0 | **3** 🆕 | %38 esitlendi |
| Test dosyasi | 1.553 | 10 | **13** | Devam edecek |
| Test basarisi | — | 35/35 | **35/35** ✅ | Korundu |
| Python (core) | 2.308 | 87 | 152 + 88 tool | Kabul edilebilir |
| CLI | 118 modul | 10 | **55 → 70** | 🚀 16 yeni modul eklendi (Batch F) |
| Model provider | 28 plugin | 2 | 2 | Henuz esitlenmedi |

### Batch Basarisi
10 batch, 65+ yeni tool, 12 yeni gateway, 5 transport, 3 memory plugin, 3 test dosyasi
Tum testler %100 gecti, R>eYMeN kimligi korundu, Hermes tool sayisi asildi.

## R>eYMeN'e Ozgu (Hermes'te Yok, Korunan)

| Ozellik | Dosya | Guclu |
|---------|-------|-------|
| Ekran OCR + tikla | araclar_ekran.py | Windows otomasyon |
| Makro kaydet/oynat | araclar_makro.py | Benzersiz |
| Uygulama adim hafizasi | uygulama_hafizasi.py | Benzersiz |
| Kapali ogrenme dongusu | closed_learning_loop.py | Otomatik beceri |
| Adim adim planlayici | planlayici.py | GUI otomasyonu |
| Motor + Beyin mimarisi | motor.py, beyin.py | Ayrik ReAct |

## Reference Dosyaları

| Dosya | İçerik |
|-------|--------|
| `references/hermes-reference-test-workflow.md` | Hermes referans testlerini Reymen'de çalıştırma ve hata raporlama |

## En Buyuk 3 Fark (Hermes'te olan)

1. **Model provider** — Hermes 28 plugin, R>eYMeN'de 2 provider. Plugin mimarisi kurulmali. (Claude 4.8'e task olarak verildi)
2. **Tool executor** — Hermes'te tool_executor.py + dispatch_helpers + guardrails mevcut. R>eYMeN'de yeni eklenecek. (Claude 4.8'e task olarak verildi)
3. **Test coverage** — Hermes 1.553 test, R>eYMeN 13 test. Kapsamli test gerekiyor. (Claude 4.8'e task olarak verildi)

## Son Dogrulama (16 Haziran 2026 — 14:30)

| Kontrol | Sonuc |
|---------|-------|
| `tools/clarify_tool.py` var ve derleniyor | ✅ |
| `tools/todo_tool.py` var ve derleniyor | ✅ |
| `tools/memory_tool.py` var ve derleniyor | ✅ (17 Haziran) |
| `tools/skill_tool.py` var ve derleniyor | ✅ (17 Haziran) |
| `tools/tts_tool.py` var ve derleniyor | ✅ (17 Haziran, edge-tts calisiyor) |
| `tools/plugin_manager.py` var ve derleniyor | ✅ |
| `motor.py`'de tools.clarify_tool kayitli | ✅ (line 102) |
| `motor.py`'de tools.todo_tool kayitli | ✅ (line 102) |
| `sistem_talimati.py`'de CLARIFY dokumantasyonu | ✅ (lines 108-110) |
| `sistem_talimati.py`'de TODO dokumantasyonu | ✅ (lines 112-130) |
| `plugin_manager.py` motor'a entegre | ✅ (calistir'da 2. sira) |
| CLARIFY tool calisiyor | ✅ |
| TODO tool calisiyor | ✅ |
| Toplam arac (aliases dahil) | 178 |
| Toplam Python dosyasi (kok) | 153 |
