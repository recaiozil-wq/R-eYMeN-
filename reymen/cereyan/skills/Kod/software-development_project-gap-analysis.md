---
name: project-gap-analysis
title: "Proje Eksiklik Analizi"
description: >-
  Analyze a project by examining its file structure, code, configs, and
  environment — then compare against a target system to identify gaps
  systematically. Output: prioritized action plan with categories.
version: 1.1.0
tags: [planning, analysis, project, audit, migration]
platforms: [windows]
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Proje Eksiklik Analizi

## Ne Zaman Kullanılır

- Kullanıcı bir projeyi inceleyip eksiklerini sormak istediğinde
- Bir projeyi başka bir sisteme (Hermes Agent, referans proje) benzetmek gerektiğinde
- Kullanıcı "bunun eksikleri neler" veya "tamamlanınca nasıl olur" dediğinde
- Mevcut bir projeyi yükseltmek/port etmek için plan yapılırken

## Adım Adım

### Adım 1: Proje Yapısını Çıkar

Önce projenin fiziksel dosya yapısını tam olarak al:

```bash
# Klasör yapısı (derinlemesine)
ls -laR "PROJE_YOLU/" 2>&1

# Sadece .py dosyaları (boyutlarıyla)
ls -la "PROJE_YOLU/"*.py 2>&1
```

**ÖNEMLİ — Çift iç içe geçme kontrolü:** ZIP'ten çıkarılan projelerde sık görülür.
`C:\proje\proje\` şeklinde gereksiz bir katman varsa, doğru yapı `C:\proje\` olmalıdır.
Kontrol et:

```bash
ls -la "C:\proje\" 2>&1
# Eğer içinde sadece 1 klasör varsa ve adı projeyle aynıysa → çift iç içe geçmiş
```

**ZIP içeriğini kontrol et:** Projede `.zip` dosyası varsa içinde ne olduğuna bak:

```bash
unzip -l "dosya.zip" 2>&1
```

### Adım 2: Kilit Dosyaları Oku + Satır Sayısı Haritası

**Önce büyüklük haritası çıkar** — hangi dosyanın önemli olduğunu satır sayısı belirler:

```bash
# Tüm .py dosyalarının satır sayıları (büyükten küçüğe)
cd "SISTEM_YOLU" && wc -l *.py 2>/dev/null | sort -rn | head -30
```

Kurallar: 500+ satır = ana modül, 200-500 = önemli yardımcı, 50-200 = araç, <50 = basit wrapper.

**Sonra mutlaka okunması gerekenler:**
- `README.md` — proje ne işe yarar, sürüm geçmişi
- Ana giriş dosyası (`main.py`, `app.py`, `cli.py`)
- Config/ayar dosyaları (`.env`, `config.yaml`, `config.json`)
- Bağımlılıklar (`requirements.txt`, `pyproject.toml`)
- Proje talimatı (`CLAUDE.md`, `PROJE_REHBERI.md`, `AGENTS.md`)
- Kimlik/ajan dosyası (`SOUL.md`, kullanıcı varsa)

Her dosyayı `read_file()` ile oku, içeriğini anla.

**Çoklu repo karşılaştırmasında:** 10-15 dosyayı sistematik oku. Okuma sırası ve derin-dalış tekniği için → [references/deep-dive-methodology.md](references/deep-dive-methodology.md)

### Adım 3: Karşılaştırma Yap

**ÖNCE ŞUNU NETLEŞTİR: Aynı sistemi mi karşılaştırıyoruz?**
Kullanıcı "şunu şuna benzet" dediğinde, ikisinin aynı yazılım mı yoksa farklı projeler mi olduğunu kontrol et:

- Aynı kaynaktan türemiş (fork/kopya) mı?
- İsim benzer ama kod tabanı farklı mı? (ör: R>eYMeN ≠ Nous Hermes Agent)
- Biri diğerinin etrafına yazılmış yardımcı araçlar mı?
- Bunu netleştirmezsen yanlış karşılaştırma yaparsın.
- **Fark büyükse "bu kötü değil, farklı işler için" diye çerçevele** — 2 farklı hedefi olan aracı kıyaslamak anlamsız.

Kategorileri netleştirdikten sonra hedef sistem (ör: Hermes Agent) ile mevcut projeyi şu başlıklarda karşılaştır:

| Kategori | Neye Bak |
|----------|----------|
| **Çalıştırma** | LLM provider, API anahtarları, bağımlılıklar kurulu mu? |
| **Konfigürasyon** | .env var mı? Config dolu mu? |
| **CLI** | Komut satırı arayüzü var mı? Kaç alt komut? |
| **Provider** | Kaç LLM destekleniyor? Fallback var mı? |
| **Gateway** | Telegram, Discord, Web, SMS — hangi kanallar var? |
| **MCP** | Model Context Protocol desteği var mı? |
| **Skill/Beceri** | Kaç beceri var? Kategorize edilmiş mi? FTS5 indeksli mi? |
| **Hafıza** | Kalıcı/vektörel/oturum hafızası dolu mu? |
| **Güvenlik** | HITL, PII filtresi, circuit breaker, rate limit? |
| **Plugin** | Dışarıdan eklenti yükleme var mı? |
| **Test** | Test dosyası, CI/CD var mı? |

Detaylı karşılaştırma şablonu → [references/3-system-comparison.md](references/3-system-comparison.md)
Dosya-dosya karşılaştırma tekniği → [references/file-by-file-comparison.md](references/file-by-file-comparison.md)

**Derinlemesine Dosya-Dosya Karşılaştırma formatı:**

Büyük fark olan durumlarda (örn: 59 dosya vs 7.078 dosya) modül bazlı tablo kullan:

```
╔══════════════════════════════════╤════════╤════════╤══════════════╗
║ MODÜL / ÖZELLİK                 │ Hermes │ R>eYMeN│ Açıklama     ║
╠══════════════════════════════════╪════════╪════════╪══════════════╣
║ **1. ÇEKİRDEK**                 │        │        │              ║
║----------------------------------│--------│--------│--------------║
║ conversation_loop.py             │ evet   │ main.py│ R'de 321 st  ║
║ context_engine.py                │ evet   │ ctx_mgr│ R'de 205 st ✓║
║ trajectory_compressor.py         │ evet   │ ❌ YOK │              ║
```

Her satır için ✅ (var/çalışıyor), ❌ (yok), ⚠️ (var ama zayıf) kullan.
Satır sayısı belirt (kaç satır kod, karşılaştırma kolaylığı için).

### Adım 4: Eksikleri Kategorize Et

Her eksik için öncelik seviyesi ata:

| Öncelik | Anlamı |
|---------|--------|
| **[FAZ 1 - KRITIK]** | Güvenlik/çalışma engeli, hemen düzelt |
| **[FAZ 2 - YUKSEK]** | Performans/maliyet, sonraki adım |
| **[FAZ 3 - ORTA]** | Çoklu platform/genişletme |
| **[FAZ 4 - DUSUK]** | Gelişmiş özellik, isteğe bağlı |

**Kritik ayrım:** Kütüphane kurulumuyla çözülebilen eksikler (pip install) ile kod değişikliği gerektiren eksikleri ayır. Claude Code'a verirken ilk grubu "yapılacaklar" listesinden çıkar, sadece kod gerektirenleri bırak.

**Faz sistemi şablonu:**

```
═════════════════════════════════════════════
FAZ 1 — KRITIK (önce bunlar)
═════════════════════════════════════════════

**N. Özellik adı** (ilgili dosya)
   Şu an: mevcut durum
   Olması gereken: hedef
   Hermes'te: referans dosyalar
   İş: iş günü tahmini

═════════════════════════════════════════════
FAZ 2 — YUKSEK
═════════════════════════════════════════════
...
```

Her eksik için iş günü tahmini ver (1 gün, 2-3 gün, 1 hafta vb.). Toplamı alta yaz.

**"Bu farklılık kötü mü?"** sorusu gelirse:
- İki sistemin hedefi farklıysa (genel amaçlı vs özel amaçlı) fark normaldir
- Özgün özellikleri vurgula: Sistem A'da olup B'de olmayan ne var?
- Orantıyı göster: dosya sayısı, araç sayısı, CLI komut sayısı
- "Hermes İsviçre çakısı, R>eYMeN tornavida" gibi metafor kullan

### Adım 5: Kategori Harfi Sistemi

Büyük eksik listelerinde (20+ madde) kategori harfleri kullan:

| Harf | Anlamı | Örnek |
|------|--------|-------|
| **A** | Güvenlik | file_safety, path_security, redact |
| **B** | Skill Sistemi | skill_commands, skills_hub |
| **C** | CLI | hermes_cli/, providers komutları |
| **D** | İzleme | rate_limit, budget, checkpoint |
| **E** | Niş Araçlar | gateway platformları, model metadata |

**Sıralama stratejisi:** Her zaman **kolaydan zora** git, kritik sırasıyla değil.
- A kategorisi kritik ama bazı E maddeleri daha kolay olabilir
- Hızlı kazanımlarla başla (15dk'da yazılabilecek dosyalar)
- Zorlaştıkça kullanıcıya ilerleme tablosu göster

Rapor formatı:
```
══════════════════════════════
A - GÜVENLİK (5/13 tamam)
══════════════════════════════
✅ file_safety.py
❌ threat_patterns.py
...
```

### Adım 6: İlerleme Tablosu Güncelleme

Eksikler kapatıldıkça KARŞILAŞTIRMA TABLOSUNU GÜNCELLE:
- ❌ YOK → ✅ olarak işaretle
- ⚠️ KISMI → ✅ olarak işaretle
- Kaç yeni dosya eklendiğini belirt
- Toplam satır sayısı değişimini göster

Format:
```
❌→✅ DUZELENLER:
║ context_references.py    ❌→✅ referans yönetimi
║ trajectory.py            ❌→✅ adım geçmişi
║ 28/28 basarili ✅
```

Kullanıcı özellikle "kontrol et eksiklikleri yaz" dediğinde:
1. Import testi yap (her dosya import edilebiliyor mu?)
2. Fiziksel dosya varlığını kontrol et
3. Güncellenmiş tabloyu göster
4. Hala eksik olanları kategorize et

### Adım 7: Batch Dosya Oluşturma

Her batch'te aynı anda yazılabilecek bağımsız dosyaları grupla.

**İKİ MOD: Sıralı (write_file) ve Paralel (delegate_task)**

#### Mod A — Sıralı Batch (Küçük işler, <5 dosya)

Her dosyayı tek tek write_file ile yaz:

```python
write_file(path="dosya1.py", content="# -*- coding: utf-8 -*-\\n\\\"\\\"\\\"...")
write_file(path="dosya2.py", content="# -*- coding: utf-8 -*-\\n\\\"\\\"\\\"...")
```

#### Mod B — Paralel Batch (Büyük işler, 5-20 dosya) ★ ÖNERİLEN

`delegate_task` ile 3 paralel subagent'a böl, her biri 3-7 dosya yazsın:

```
Batch 1 → subagent A: tool_A, tool_B, tool_C, tool_D, tool_E
Batch 1 → subagent B: tool_F, tool_G, tool_H, tool_I, tool_J
Batch 1 → subagent C: tool_K, tool_L, tool_M
```

**Kanıtlanmış Ölçek:** 10 batch'te 65+ tool, 12 gateway, 5 transport, 3 memory plugin — tüm testler %100 geçti. Bu pattern 100+ dosyaya kadar ölçeklenebilir. Detaylı batch dökümü ve dersler → [references/10-batch-implementation-example.md](references/10-batch-implementation-example.md)

**"Copilot olarak yap" deseni** — Kullanıcı "copilot olarak yap" veya "copilot sende düzelt" dediğinde:
- `delegate_task(goal=..., context=..., toolsets=["terminal","file"])` kullan
- Her subagent 3-7 dosya yazsın (max 3 paralel)
- Subagent'lar `write_file` ile yazar, `python -c "import ..."` ile doğrular
- Bu = "copilot" demenin Hermes yoludur. Ayrı bir CLI ajanı başlatmak gerekmez.
- Kullanıcı "onay gerekmez" dediyse tüm batch'leri art arda üret, hiçbir şey sorma.

**"Onay gerekmez" + "sonuna kadar sırasıyla" akışı (kanıtlanmış):**
1. Eksik listesini çıkar
2. 3 paralel delegate_task ile batch'i uygula
3. Her subagent sonucunu bekle (senkron)
4. Sonuçları özetle, karşılaştırma tablosunu güncelle
5. Hemen sonraki batch'e geç — ASLA "devam edeyim mi" diye sorma
6. Tüm batch'ler bitince toplu rapor ver, test suite çalıştır
7. "tamam" yaz ve bekle

**Nasıl yapılır:**

```python
# Paralel 3 subagent, her biri 3-5 tool
delegate_task(
  goal="Create 5 tools in tools/: a, b, c, d, e",
  context="Project path, pattern, style rules",
  toolsets=["terminal", "file"]
)
```

**Her subagent şunları yapar:**
1. `write_file` ile her bir tool'u ayrı ayrı yazar
2. `python -c "import tools.a; print('OK')"` ile doğrular
3. Sonucu özetler

**Avantajları:**
- 3x hız (paralel çalışma)
- Her subagent'ın kendi terminal+file ortamı (izole)
- Batch sonu 20+ dosya tek seferde yazılabilir
- Import testleri de paralel

**Sınırlar (bu kullanıcı için):**
- max 3 paralel task (delegation.max_concurrent_children)
- subagent'lar leaf'tir (daha fazla delegate edemez)
- Her subagent sadece terminal+file kullanır (web/vision gerekmez)

#### Şablon

Her dosya için şablon:

```python
# -*- coding: utf-8 -*-
"""dosya_adi.py — Kisa Aciklama.

Detayli aciklama (ne ise yarar, nasil kullanilir).
"""


class SinifAdi:
    ...


if __name__ == "__main__":
    # Test blogu
```

**Kurallar:**
- Her dosyada `# -*- coding: utf-8 -*-` ve docstring ✅
- Her dosyada `if __name__ == "__main__":` test blogu ✅
- try/except ile graceful degrade ✅
- Her batch sonrası import testi ZORUNLU ✅

### Adım 8: Progress Tracking (Eksik Listesi)

Uzun analizlerde todo tool ile adımları takip et:

```txt
todos = [
  {"id": "1", "content": "Sistem A yapısını tara", "status": "in_progress"},
  {"id": "2", "content": "Sistem B yapısını tara", "status": "pending"},
  ...
]
```

Bitince `completed`, bloklanınca `cancelled` yap.

### Adım 9: Eksikleri Batch'ler Halinde Uygula

Eksik listesi ve öncelikler hazırsa, sıra kod'a dökmeye gelir.

**Strateji: Kolaydan Zora**
Kritik sırası DEĞİL, zorluk sırası kullan (küçük dosya → az bağımlı → harici API gerektirmeyen).

**HER BATCH SU UC ADIMI ICERMELIDIR (asla atlama):**

```
1. DOSYAYI YAZ    → tools/shell.py
2. ENTEGRE ET     → motor.py'ye import ekle + Motor.__init__'te kullan
3. TEST ET        → python -c "from motor import Motor; print('OK')"
```

**Entegrasyon matrisini her batch oncesi cikar:**
```
Yeni Dosya             → Nereye Import     → Nasil Kullanilacak
───────────────────────────────────────────────────────────────
iteration_budget.py    → main.py            → AIAgentOrchestrator.budget
credential_pool.py     → beyin.py, main.py  → _anahtar_bul()
tools/*.py             → motor.py           → tool_registry uzerinden
```

**Kesinlikle YAPMA:** Once 80 dosyayi yaz, sonra "entegre ederim" deme.
Her batch: YAZ + ENTEGRE ET + TEST ET. Sonra sonraki batch.

**Her batch sonu KARSILASTIRMA TABLOSUNU GUNCELLE:**
- Tablodaki ❌'i ✅ yap
- Eklenen dosya sayisini ve satir sayisini not et
- Kisa rapor: "{N} dosya eklendi, {M} satir, {K}/{T} basarili"

**Batch ilerleme raporu FORMATI (kisa, kullaniciya goster):**
```
Yeni eklenen N tool dosyasi:
  tools/shell.py       → KOMUT_CALISTIR
  tools/python_exec.py → PYTHON_CALISTIR

tools/ klasoru: X dosya
  shell, python_exec, file_ops, ...

Test: 4/4 arac calisiyor
```

**Tum batch'ler bittiginde FULL SCAN yap:**
1. Syntax kontrolu: `ast.parse()` ile tum .py dosyalari
2. Import testi: 45+ modul import edilebiliyor mu?
3. Entegrasyon dogrulama: Her dosya ana sisteme bagli mi?
4. Runtime test: `test_suite.py` calistir
5. Karsilastirma tablosu: Tum ❌'ler ✅ olmus mu?
6. Eksik referans/kullanim kontrolu: Hic import edilmemis dosya var mi?

**Full scan raporu:**
```
=== FULL SCAN ===
Syntax hata: 0
Import hata: 0
Test: 33/33 gecti
Platform: 11 kayitli
Karsilastirma: %100 tamam
```

Detayli kontrol listesi → [references/integration-verification.md](references/integration-verification.md)
Batch implementasyon sablonu → [references/batch-implementation.md](references/batch-implementation.md)
Karsilastirma tablosu odakli calisma akisi → [references/comparison-driven-implementation.md](references/comparison-driven-implementation.md)

### Adım 10: Full Verification Scan

Son adim: tum dosyalari, import'lari, syntax'i ve runtime'i dogrula.

**FINAL karsilastirma formati — eski veriyi referans gosterme:**
Son batch'ten sonra karsilastirma tablosunu guncellerken, **tools/ klasorundeki gercek dosyalari say**, onceki sayiya guvenme:
```bash
for f in tools/*.py; do basename "$f" .py; done | sort > /tmp/current.txt
for f in ../hedef/tools/*.py; do basename "$f" .py; done | sort > /tmp/target.txt
echo "Eksik: $(comm -23 /tmp/target.txt /tmp/current.txt | wc -l)"
echo "Fazla: $(comm -13 /tmp/target.txt /tmp/current.txt | wc -l)"
```

Detay → [references/full-verification-scan.md](references/full-verification-scan.md)

**Katmanli Dogrulama:**
| Katman | Ne Kontrol Edilir | Kriter |
|--------|-------------------|--------|
| Fiziksel | Dosya var mi? | `path.exists()` |
| Syntax | Derleniyor mu? | `ast.parse()` 0 hata |
| Import | Modul yukleniyor mu? | `__import__()` basarili |
| Entegrasyon | Ana sisteme bagli mi? | Hedef dosyada import satiri var mi? |
| Runtime | Calisiyor mu? | `test_suite.py` veya main blogu |

### Adım 11a: Yüzde-Tamamlama + Benzersiz Özellikler

Sadece eksik listesi değil, her sistemin **yüzde tamamlama** oranını ve **diğerinde olmayan benzersiz özelliklerini** de göster:

```txt
SISTEM A'da olan ama SISTEM B'de olmayan:
  - Feature X

SISTEM B'de olan ama SISTEM A'da olmayan:
  - Feature Z

DURUM: Sistem A %75 TAMAM, Sistem B %60 TAMAM
```

Yüzde hesabı basit: (✅ sayısı / toplam kriter) × 100. 8-15 kriter yeterli.

### Adım 11b: Puanlı Karşılaştırma (Skor Kartı)

Kullanıcı "karşılaştır puanla" veya "kıyasla" dediğinde yüzde yerine **0-10 puan skalası** kullan. 7 kategoride puanla, her kategoriyi 3-5 alt kritere böl:

| # | Kategori | Neye Bakılır |
|:-:|----------|-------------|
| 1 | Kod Olgunluğu & Derinlik | dosya sayısı, kod satırı, hata yönetimi, docstring, modülerlik |
| 2 | Özgünlük & Kimlik | kendi mimarisi, rakiplerden farkı, özgün araçlar, bağımsızlık |
| 3 | Kod Kalitesi | try/except, docstring kapsamı, renkli çıktı, --help, bütünsel geliştirme |
| 4 | Çalışma Kararlılığı | startup başarısı, kesintisiz çalışma, gateway bağlantısı, test geçme oranı |
| 5 | Ekosistem & Araçlar | skill sistemi, cron, bellek katmanları, plugin, gateway platform |
| 6 | Kullanıcı Deneyimi | kurulum, kullanım, CLI, dökümantasyon, hata mesajları |
| 7 | Proje Ömrü & Bakım | ekip büyüklüğü, güncelleme sıklığı, arka plandaki ekip |

Detaylı format ve şablon → [references/scored-comparison-format.md](references/scored-comparison-format.md)
Puanlı + dosya-dosya hibrit format → [references/hybrid-scored-table-format.md](references/hybrid-scored-table-format.md)

**Kullanıcı skor tablosunu beğenirse** (örn: "bu özet culaude 4.8 verecem" derse), skor tablosunun tamamını ayrı bir fix-prompt dosyası olarak kaydet. Dosya adı: `Masaüstü/claude-4.8-fix-prompt.md`. Kullanıcı bu prompt'u Claude Code'a yapıştırarak eksikleri topluca giderebilir.

**Kullanıcı "10 dak bir kontrol et aşamaları ve puanla ver" derse:**
- 10 dakikada bir çalışan cron job oluştur, Telegram'a puanlı rapor göndersin
- Her rapor bir öncekiyle karşılaştırmalı olsun
- Cron adı: `claude-ilerleme-kontrol`, schedule: `10m`, deliver: `telegram:<chat_id>`

Sadece eksik listesi değil, her sistemin **yüzde tamamlama** oranını ve **diğerinde olmayan benzersiz özelliklerini** de göster:

```txt
SISTEM A'da olan ama SISTEM B'de olmayan:
  - Feature X

SISTEM B'de olan ama SISTEM A'da olmayan:
  - Feature Z

DURUM: Sistem A %75 TAMAM, Sistem B %60 TAMAM
```

Yüzde hesabı basit: (✅ sayısı / toplam kriter) × 100. 8-15 kriter yeterli.

**Kullanıcı "bu kadar büyük fark var" derse:**
- Hemen "bu kötü bir şey değil" diye çerçevele
- İki sistemin farklı hedefleri olduğunu belirt
- Özgün özellikleri sırala (A'da olup B'de olmayan)
- "Hermes İsviçre çakısı, seninki tornavida" metaforu
- Büyük farkın büyük kısmı referans sistemin ihtiyaç fazlası özellikleri

### Adım 12: Rapor Dosyası + Özet

Özet olarak şunları söyle:
- Kaç eksik bulundu (her kategoride)
- En kritik 2-3 madde
- En kısa yol (alternatif varsa)
- Eksikler kapatıldıysa güncel durum tablosu
- "Ne zaman dönersen başlarız"

Rapor yolunu `C:\Users\marko\OneDrive\Desktop\eksiklikler.txt` olarak kullan (OneDrive masaüstü, asla `Desktop` kısayolu değil).

## Pitfalls

1. **Yüzeysel analiz** — Sadece dosya isimlerine bakıp geçme. Her kilit dosyayı oku.
2. **Önceliksiz liste** — 25 maddeyi önceliksiz sıralarsan kullanıcı nereden başlayacağını bilemez. Her zaman KRITIK > BUYUK > ORTA > KUCUK sırala.
3. **Alternatif yolu atlama** — Bazen en kısa çözüm mevcut sistemi değiştirmek değil, başka bir sistemi adapte etmektir. Bunu da belirt.
4. **OneDrive masaüstü yolu** — Doğru yol: `C:\\Users\\marko\\OneDrive\\Desktop\\`, asla `C:\\Users\\marko\\Desktop\\` kullanma.
5. **Kullanıcıyı detayla boğma** — Tablo formatında özet ver (✅/❌/⚠️), uzun paragraflar yazma. Kullanıcı Türkçe, kısa ve direkt ister. Detay isteyene detay ver, sormayana özet ver.
6. **"Bu kadar büyük fark var" tepkisini öngör** — Karşılaştırmaya hemen "ama bu kötü değil, farklı işler için" çerçevesini koy. Yoksa kullanıcı moralini bozabilir.
7. **Claude Code'a fazla yükleme** — Tüm eksikleri aynı anda Claude Code'a verme. Fazlara böl, her faz bittiğinde import testi yap. Büyük eksik listelerinde (10+ madde) `Masaüstü/claude-4.8-fix-prompt.md` dosyasına yaz, kullanıcı dosyayı VS Code Claude terminaline yapıştırsın. Prompt'u şöyle başlat: "Sen bir AI kod geliştirme uzmanısın. Aşağıdaki tüm maddeleri sırayla uygula. Her adımda önce mevcut durumu kontrol et, sonra düzelt, sonra test et."
8. **Uzun çalışma oturumlarında hız kesme** — Bu kullanıcı "tüm gün çalışabilirsin" dediğinde ara vermeden devam et. Batch'leri art arda üret, her batch sonu sadece kısa ✅/❌ raporu ver, uzun açıklama yapma. İş bitince toplu rapor ver.
9. **Kullanıcı "sorma" dediğinde ASLA sorma** — Bu kullanıcı "sorma", "bekleme", "karar ver", "neden her seferinde onay istiyorsun" gibi ifadeler kullandığında, HİÇBİR ŞEY SORMA. Düşük riskli kararları KENDİN VER. Onay isteme, en olumlu/izinli yoldan devam et. Ara adım sorma, ilerleme raporu verme, seçenek sunma. Sadece geri dönüşü olmayan işlemlerde (credential değişikliği, dosya silme) sor. Uzun calisma oturumlarinda her batch sonu sadece ✅/❌ goster, "devam edeyim mi" diye sorma. Kullanıcı "devam" diyene kadar batch'leri art arda üret. İş bitince sadece "tamam" yaz ve bekle.
10. **Kategori sistemi kullan** — 20+ maddelik eksik listesini A-B-C-D-E harfleriyle kategorize et. Kullanıcıya "ona ne yaptın" diye sorduğunda harf bazında cevap ver. "E-Niş" bitince "A-Güvenlik"e geç gibi.
11. **Her seferinde karşılaştırma tablosunu güncelle** — Eksik kapatınca ana tablodaki ❌'i ✅ yap ve kullanıcıya göster. Aksi halde kullanıcı "hala eksik mi" diye tekrar sorar. Tabloyu güncellerken formatı bozma — kullanıcı tablodan takip ediyor.
12. **Dosya yaz + entegre et + test et (ÜÇ adım birlikte, KRITIK)** — Dosyayi yazip birakip sonra "entegre ederim" deme. Her dosyayi yazar yazmaz:
    - Hedef sisteme import et (`from hedef_modul import Sinif`)
    - Ana sinifta initialize et (`self.yeni_bilesen = Sinif()`)
    - `python -c "from motor import Motor; print('OK')"` ile dogrula
    - Bu kural atlanirsa kullanici "bu kadar kisa surede bu kadar dosya olmaz" diyerek hakli sekilde uyarir. 80 dosya yazip entegre etmemek = 0 is.
    - ENTEGRASYON OLMADAN 0 IS: 80 dosya yazip ana sisteme baglamamak, 0 dosya yazmakla ayni seydir. Kullanici entegrasyonu dogrulamak icin import zincirini kontrol eder. motor.py'de import yoksa = o dosya yok demektir. HIZLI OLMAK ICIN ENTEGRASYONU ATLAMA — kullanici hizdansa entegrasyonu tercih ediyor.
13. **Entegrasyonu dogrulamadan "bitti" deme** — `from motor import Motor` calisiyorsa motor.py hazir demektir. Calismiyorsa dosyalari yazmis olsan bile "bitti" sayilmaz. Kullanici entegrasyonu test eder ve yakalar.
14. **Tum kategorileri bitirince full scan yap** — Son adimda tum dosyalari tara: syntax (ast.parse), import (her modulu yukle), integration (hedef dosyada import satiri var mi?), runtime (test_suite.py). 0 hata garantisi olmadan teslim etme. Full scan raporunu kullaniciya goster.
15. **Uzun oturumlarda adim adim ilerle, raporu sonda ver** — Her batch sonu sadece ✅/❌ tablosu goster, uzun aciklama yapma. Kullanici "devam" dedikce batch'leri art arda uret. Is bitince toplu rapor ver. Araya aciklama sokma.
16. **"Sadece tamam de" kurali (uzun oturumlar icin)** — Kullanici "devam" dediginde veya buyuk bir liste verdiginde, tum is bitene kadar HICBIR SEY soyleme. Ara adim sorma, ara rapor verme, ilerleme paylasma. Her batch sonu sadece kisa ✅/❌ veya "Batch X: Y dosya" gibi tek satir. TUM IS BITINCE sadece "tamam" yaz, bekle. Kullanici "devam" dedikce batch'leri art arda uret. "Bir sey daha ekleyeyim mi" diye sorma. "Su da lazim mi" diye sorma. Sadece calis, is bitince "tamam" de. Kullanici "enter bas" dediginde cevap vermeyi bekle, yeni is gelince calismaya devam et. Ihlal = kullanicinin "neden her defasinda ilerleme onay istiyorsun" demesiyle sonuclanir.
17. **Eski karsilastirma verisine guvenme, her seferinde yeniden say** — Ayni oturumda bile onceki batch'lerdeki sayilar guncelligini kaybeder. Son karsilastirmada `ls tools/*.py | wc -l` ile gercek sayiyi al, onceki degiskene guvenme. `comm -23` ile hedef sistemle karsilastir. Ara batch'lerde "X tool eklendi" dersin ama FINAL raporda gercek sayiyi bas.
18. **"Copilot olarak yap" dendiginde Claude Code CLI kullanma, delegate_task kullan** — Kullanici "copilot" dediginde veya "copilot sende duzelt" dediginde, ayri bir CLI ajani (Claude Code, Codex) baslatma. Bunun yerine `delegate_task` ile subagent'lara bol. Bu 10 kata kadar daha hizli (3 paralel subagent) ve entegrasyonu otomatik (subagent'lar dosyayi yazar, sen motor.py'ye import edersin). Ayri CLI ajani baslatmak: (a) pty gerektirir (yavas), (b) proje baglamini kaybeder, (c) sonucu manuel entegre etmen gerekir. delegate_task ile 65 tool 10 batch'te (her batch 3 paralel) basariyla implemente edildi.
    
    **Büyük eksik listelerini (10+ madde) Claude Code'a göndermek için fix-prompt dosyası:** `Masaüstü/claude-4.8-fix-prompt.md` yoluna yaz. Kullanıcı dosyayı VS Code Claude terminaline yapıştırır. Prompt formatı:
    ```
    # BAŞLIK — TÜM ZAYIFLIKLARI GİDERME PROMPTU
    Sen bir AI kod geliştirme uzmanısın. Aşağıdaki tüm maddeleri sırayla uygula.
    
    ## PROJE 1 — [proje adı ve yolu]
    ### [Harf]. [KONU BAŞLIĞI]
    - madde
    - madde
    
    ## SIRALAMA
    | Sıra | Ne | Neden |
    ```
    
    **Claude Code çalışırken 10 dakikada bir ilerleme takibi:** `cronjob` ile periyodik kontrol kur, Telegram'a puanlı rapor gönder. Cron adı: `claude-ilerleme-kontrol`, schedule: `10m`, deliver: `telegram:<chat_id>`. Her raporda Python dosya sayısı, skill sayısı, MEMORY boyutu, test sayısı gibi metrikler karşılaştırmalı gösterilir.

Hermes Referans Testlerini Düzeltme → [references/hermes-reference-test-fix.md](references/hermes-reference-test-fix.md)

19. **Claude Code'un test dosyasi kirliligini temizle** — Claude Code projeyi analiz ederken kendi kendine test_bulk_*.py (1000+ satir anlamsiz assert), test_gen_*.py (import edilemeyen tool'lari test eden), ve generate_tests.py/son_push.py gibi uretec dosyalari olusturur. Bunlar pytest'i dakikalarca asili birakir, 25.000+ satir gereksiz kod ekler. Her Claude Code calismasindan sonra bu dosyalari sil — referans icin [references/claude-code-test-cleanup.md](references/claude-code-test-cleanup.md).
