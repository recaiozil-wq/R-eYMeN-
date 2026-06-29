---
name: talimat-uygulama
title: Talimat Uygulama Ajanı
description: YouTube/video talimatlarını çıkar, terminal ile uygula, decisions.md'ye kaydet.
category: sistem
---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | ReYMeN ajani |
| **Ne** | YouTube/video talimatlarını çıkar, terminal ile uygula, decisions.md'ye kaydet. |
| **Nerede** | `reymen\talimat-uygulama.md` |
| **Ne Zaman** | ReYMeN yapilandirmasi gerektiginde |
| **Neden** | Talimat Uygulama islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |

Kim: ReYMeN ajani
Ne: YouTube/video talimatlarını çıkar, terminal ile uygula, decisions.md'ye kaydet.
Nerede: `reymen\talimat-uygulama.md`
Ne Zaman: ReYMeN sistemi yapilandirmasi gerektiginde
Neden: Talimat Uygulama islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Talimat Uygulama

> **Kategori:** sistem/ogrenme

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Hermes ajanı. Kullanıcı video URL'si paylaştığında. |
| **Ne?** | Video'daki talimatları/adımları çıkarır, terminal ile uygular, decisions.md'ye kaydeder. |
| **Nerede?** | Terminal + `.ReYMeN/decisions.md` |
| **Ne Zaman?** | Kullanıcı YouTube/video URL'si paylaştığında. |
| **Neden?** | Manuel denemek/not almak yerine otomatik uygula + kaydet. |
| **Nasıl?** | Transcript çek → adımları çıkar → terminal çalıştır → decisions.md'ye Ne/Neden/Alternatif ile kaydet. |

## Akış

```
YouTube URL gelir
  ↓
1. Transcript al (yt-dlp / Whisper)
  ↓
2. Talimatları çıkar (6 adım)
  ↓
3. Terminal ile uygula
  ├─ Başarılı → devam
  └─ Hata → alternatif dene (max 3)
  ↓
4. decisions.md'ye kaydet:
   - Ne yapıldı?
   - Neden?
   - Alternatif düşünüldü mü?
```

## Örnek

Power BI + MCP server videosu:
1. Transcript al (328 satır)
2. 6 talimat çıkar
3. Adım 1'de takıl (Power BI Desktop yok)
4. Karar #2 olarak kaydet
