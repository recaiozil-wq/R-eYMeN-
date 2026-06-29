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

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | Tum kullanicilar |
| **Ne** | Checklist/gap-closure workflow — kullanıcının verdiği eksik listesini sormadan adım adım tamamla. Layer-by-layer fix, tablo raporlama, her adımda derleme kontrolü. |
| **Nerede** | `productivity\workflow_eksik-listesi-tamamlama.md` |
| **Ne Zaman** | Gunluk is akisi iyilestirmesi gerektiginde |
| **Neden** | Workflow Eksik Listesi Tamamlama islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Checklist/gap-closure workflow — kullanıcının verdiği eksik listesini sormadan adım adım tamamla. Layer-by-layer fix, tablo raporlama, her adımda derleme kontrolü. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Tum kullanicilar
Ne: Checklist/gap-closure workflow — kullanıcının verdiği eksik listesini sormadan adım adım tamamla. Layer-by-layer fix, tablo raporlama, her adımda derleme kontrolü.
Nerede: `productivity\workflow_eksik-listesi-tamamlama.md`
Ne Zaman: Gunluk is akisi iyilestirmesi gerektiginde
Neden: Workflow Eksik Listesi Tamamlama islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Eksik Listesi Tamamlama — Gap Closure Workflow

Kullanıcının verdiği yapılandırılmış eksik listesini sormadan, adım adım, %100 uyumlu şekilde tamamla.

## Tetikleyici

Kullanıcı şu tarzda mesaj attığında kullan: "Eksikler: 1... 2...", teknik brifing, "şunları yap/düzelt/entegre et"

## Adımlar

### 1. Kategorize et
- 🔴 **Kritik** — çalışmasını engelleyen
- 🟡 **Orta** — kullanılabilirliği etkileyen
- 🟢 **Düşük** — temizlik/tamamlayıcı

### 2. Sorma, direkt yap
Sadece kullanıcının sahip olduğu bilgiyi (API anahtarı) sor. İzin isteme.

### 3. Layer-by-layer (içten dışa)
LLM fix → .env/config → pip install → modül entegrasyon → file lock → fallback → skill → başlatıcı → temizlik → dökümantasyon

### 4. Derleme kontrolü
```python
import ast
with open(f, encoding='utf-8') as fh: ast.parse(fh.read())
```

### 5. Tablo rapor
| # | Eksik | Durum | Detay |
## Kurallar
- **Sorma, direkt yap** — karar gerektirmeyen her işlemde otomatik ilerle
- **Checklist rapor** — tablo + emoji + kısa özet, Türkçe
- "Atla" derse alternatif yol dene, takılıp kalma
- **%100 uyum** — her madde çözülmüş veya neden çözülemediği belirtilmiş olmalı
