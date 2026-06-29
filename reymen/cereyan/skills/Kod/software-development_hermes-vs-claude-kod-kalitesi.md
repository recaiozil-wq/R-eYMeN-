---
name: hermes-vs-claude-kod-kalitesi
title: Hermes vs Claude 4.8 Kod Yazim Karsilastirmasi
description: "Claude 4.8 kod yazim tarzindan ogrenilenler: hata yonetimi, docstring, renkli cikti, CLI her yerde"
tags: [coding-standards, quality, claude, learning]
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Kali ajanı |
| **Ne?** | Claude 4.8 kod yazim tarzindan ogrenilenler: hata yonetimi, docstring, renkli cikti, CLI her yerde |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hermes vs Claude 4.8 — Kod Yazim Dersleri

## Farklar
- Ben (Hermes): kucuk odakli patch, tek sorunu cozer, hata yonetimi eksik
- Claude 4.8: butunsel, ozellik + CLI + hata + dokumantasyon bir arada

## Ogrenilenler
1. try/except her fonksiyonda olmali
2. Renkli cikti (Renk sinifi) buyuk fark yaratir
3. Docstring her fonksiyona yazilmali
4. Her modul kendi --help'ine sahip olmali
5. Butunsel dusun: ozellik + kullanim + hata + dokumantasyon

## Uygulama
- Yeni kod: once docstring, sonra try/except, sonra islev
- Patch: hata yonetimini eklemeden gecme
- CLI: her modul icin en az --help
- Renk: terminal ciktilarinda Renk sinifi kullan

## Ornek: Checkpoint/Resume Deseni
Claude'in batch_runner.py'sinde gorulen desen:
- `SonucYoneticisi` class'i checkpoint dosyasina tamamlanan gorev ID'lerini kaydeder
- Yeni instance baslatildiginda checkpoint'i yukler, tamamlananlari atlar
- Bu sayede yarida kalan toplu islemler kaldigi yerden devam eder
- Thread-safe (`threading.Lock` ile)
```python
class SonucYoneticisi:
    def _checkpoint_yukle(self):
        if self._checkpoint.exists():
            data = json.loads(self._checkpoint.read_text())
            self._tamamlanan_idler = set(data.get("tamamlanan", []))
    def zaten_tamamlandi_mi(self, gorev_id):
        return gorev_id in self._tamamlanan_idler
```
- `startswith("***")` ile env kontrolu — tam esitlik (`== "***"`) yanlis negatif verir
- XRAY: kod analizinde `references/xray-protokolu.md` protokolunu kullan

## Tespit Edilen Patternler (Claude 4.8'den)

| Pattern | Nerede Kullanilir |
|---------|------------------|
| Provider Registry | 23 LLM provider, base.py + dict registry |
| MCP Server | JSON-RPC 2.0, stdio protocol, 8 tool |
| ACP Adapter | FastAPI + WebSocket, session yonetimi |
| TrajectoryCompressor | LLM ile yapisal ozet, token budget, rule-based fallback |
| PluginYukleyici | Dinamik import, motor'a arac kaydetme |
| FileLock | JSON yazma yarisinda threading.Lock yetmez |
| Test Suite | try/except'li 13 test, her modul icin ayri test fonksiyonu |
| `setup_keys.py` | `--liste`, `--kontrol`, interaktif API kurulumu |
| `AgentRuntime` | Ana ajana kabuk, thread-safe kilit, BackgroundReview |
| `HataSiniflandirici` | Gozlem stringlerini 6 kategoride siniflandir |
| `DashboardChannel` | Gateway mesajlarini dashboard log tamponuna iletir |

## Klasik Hatalar (Bu Sesssionda Bulunan)

| Hata | Sebep | Cozum |
|------|-------|-------|
| `AttributeError: no attribute 'learning'` | __init__'te attribute henuz tanimlanmadan kullanildi | self.learning satirini kullanimdan ONCE yerlestir |
| `.env'de DEE...n` bozuk satirlar | write_file ile tirnak/karakter kaybi | .env dosyasi Python ile yazilmali (pipe degil) |
| `== "***"` yanlis negatif | Deger "*** DeepSeek..." gibi basliyor | startswith("***") kullan |

## Claude'un Metodolojisi (R>eYMeN projesinden)
1. Once buyuk ozellikler (CLI, Web, MCP, Plugin) — en degerli, en gorunur
2. Sonra mevcut kodu guncelle (sadece yeni ekleme degil, eskisini de iyilestir)
3. Sonra test + kurulum kolayligi (test_suite.py, setup_keys.py)
4. En son runtime ve context yonetimi (agent_runtime.py, TrajectoryCompressor)

Her dosyada: docstring + try/except + argparse CLI — ucunu birden asla atlama.

## Kullanici Tercihleri (Sistem Gelistirme Icın)

Bu kullanici icin gecerli calisma prensipleri (windows-ai-ajan-kurulumu skill'i ile ortak):
- `sorma`: karar gerekiyorsa en mantikli secenegi kendin sec, uygula, sonra haber ver
- `govdeyi arkaya at`: isi background'da baslat, hemen cevap ver
- `xray analiz`: yuzeysel grep yerine satir satir oku, import zincirini kontrol et, calisma testi yap
- `sıra ile basla`: birden cok bilesen varsa oncelik sirasina koy, teker teker bitir
- `surekli izle`: tek seferlik kontrol yetmez, periyodik olarak degisiklikleri takip et
