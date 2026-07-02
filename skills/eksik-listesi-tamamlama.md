---
title: Eksik Listesi Tamamlama (Gap Closure)
name: eksik-listesi-tamamlama
description: Checklist/gap-closure workflow — kullanıcının verdiği eksik listesini sormadan adım adım tamamla. Layer-by-layer fix, tablo raporlama, her adımda derleme kontrolü.
tags:
  - workflow
  - integration
  - troubleshooting
audience: user
---

# Eksik Listesi Tamamlama — Gap Closure Workflow

Kullanıcının verdiği yapılandırılmış eksik listesini sormadan, adım adım, %100 uyumlu şekilde tamamla.

## Tetikleyici

Kullanıcı şu tarzda mesaj attığında kullan: "Eksikler: 1... 2...", teknik brifing, "şunları yap/düzelt/entegre et"

## Adımlar

### 0. Ön tarama (Pre-check)
Her maddeyi çözmeye başlamadan ÖNCE mevcut durumu kontrol et. Bazı maddeler zaten tamamlanmış olabilir (örn. CHANGELOG.md, LICENSE zaten var). Tamam olanları işaretle, sadece eksik olanlarla ilgilen. Bu gereksiz iş yükünü önler.

### 1. Kategorize et
- 🔴 **Kritik** — çalışmasını engelleyen
- 🟡 **Orta** — kullanılabilirliği etkileyen
- 🟢 **Düşük** — temizlik/tamamlayıcı

### 2. Aynı seviyedeki maddeleri sırala
Aynı priority seviyesindeki maddelerde **önce kolay olanları yap** (config dosyaları, tek dosya oluşturma), **sonra büyük işleri** (skill üretimi, kod bölme, kopya temizlik). Batch oluşturma gereken işlerde (örn. 15+ SKILL.md) **delegate_task kullan** — sub-agent paralel üretsin, ana thread temiz kalsın. Ölçüm/analiz gerektiren maddelerde **bir .py script yaz** (bir kere çalıştır, her seferinde aynı sonucu verir) — terminal'de manuel komut yerine tekrarlanabilir script tercih et.

### 3. Sorma, direkt yap
Sadece kullanıcının sahip olduğu bilgiyi (API anahtarı) sor. İzin isteme.

### 4. Layer-by-layer (içten dışa)
LLM fix → .env/config → pip install → modül entegrasyon → file lock → fallback → skill → başlatıcı → temizlik → dökümantasyon

### 5. Derleme kontrolü
```python
import ast
with open(f, encoding='utf-8') as fh: ast.parse(fh.read())
```

### 5b. Doğrula (Verify After Fix) — ZORUNLU ADIM
Her fix'ten SONRA, çalıştığını kanıtla:
1. **Syntax:** `python -c "ast.parse(open('f').read())"`
2. **Import:** `python -c "from modul import sey"`
3. **İçerik:** `grep -n "hedef" dosya` ile değişiklik satırını göster
4. **Önce/Sonra kanıtı:** Ham çıktıyı göster, yorum katma

**Kural:** Kanıt göstermeden "✅ düzeltildi" YASAK. Her fix = kanıt.

### 6. Periyodik izleme cron kur (batch sonrası)
Batch tamamlandıktan sonra, eksiklerin kalıcı takibi için bir cron job kur:
- Schedule: her saat başı (`0 * * * *`) veya günde bir (`0 9 * * *`)
- Prompt: eksik listesini tara, sadece hala eksik olanları raporla
- Workdir: proje kök dizini
- Deliver: origin (kullanıcıya otomatik gelsin)
- enabled_toolsets: terminal + file (web gerekmez)
Bu cron, yeni eksikler eklenirse kullanıcının haberi olmasını sağlar.

### 7. Tablo rapor
| # | Eksik | Durum | Detay |

### 8. Final consolidated rapor
Tüm maddeler bittiğinde TEK bir özet tablo ver:
```
┌──────────────────────────────────────────────┐
│ ÖZET: N/N madde tamamlandı                   │
├──────────────────┬───────────────────────────┤
│ Yeni oluşturulan │ X dosya + Y cron + Z      │
│                  │ script + N SKILL          │
│ Kalan işler     │ sadece hala eksik olanlar  │
└──────────────────┴───────────────────────────┘
```
Format: tablo + emoji + kısa öz Türkçe. Detayları göm, özeti ver.

## Kurallar
- **Sorma, direkt yap** — karar gerektirmeyen her işlemde otomatik ilerle
- **Checklist rapor** — tablo + emoji + kısa özet, Türkçe
- **Önce kolay, sonra zor** — aynı priority seviyesinde küçük işleri bitir, büyük işlere sonra geç
- **Script > terminal komutu** — ölçüm/analiz gereken yerde tekrarlanabilir .py script yaz
- "Atla" derse alternatif yol dene, takılıp kalma
- **%100 uyum** — her madde çözülmüş veya neden çözülemediği belirtilmiş olmalı
