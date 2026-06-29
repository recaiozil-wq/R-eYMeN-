---
name: video-ogrenme-ajani
title: Video Öğrenme Ajanı
description: YouTube/Video'dan skill çıkarma pipeline'ı — transcript al, bölümle, hafızayla karşılaştır, hata tespit et, kaydet.
category: video
Kim: Video icerik ureticisi
Ne: YouTube/Video'dan skill çıkarma pipeline'ı — transcript al, bölümle, hafızayla karşılaştır, hata tespit et, kaydet.
Nerede: `video\video-ogrenme-ajani.md`
Ne Zaman: Video isleme veya analiz gerektiginde
Neden: Video Ogrenme Ajani islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Video Öğrenme Ajanı


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | Video icerik ureticisi |
| **Ne** | YouTube/Video'dan skill çıkarma pipeline'ı — transcript al, bölümle, hafızayla karşılaştır, hata tespit et, kaydet. |
| **Nerede** | `video\video-ogrenme-ajani.md` |
| **Ne Zaman** | Video isleme veya analiz gerektiginde |
| **Neden** | Video Ogrenme Ajani islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Video ajanı. Kullanıcı YouTube URL'si paylaştığında devreye girer. |
| **Ne?** | YouTube eğitim videolarındaki bilgiyi otomatik çıkarır, analiz eder, skill'e dönüştürür ve ReYMeN hafızasına kaydeder. |
| **Nerede?** | `reymen/cereyan/once_hafiza.py` → `ogrenmeler.db` (kategori: `video/*`). yt-dlp + Whisper (fallback). |
| **Ne Zaman?** | Kullanıcı YouTube URL'si gönderdiğinde. Veya cron ile periyodik video taraması yapıldığında. |
| **Neden?** | Video'daki bilgiyi manuel özetlemek yerine otomatik çıkar, hataları tespit eder, düzeltir ve hafızaya kaydeder. Aynı video tekrar gelirse hafızadan direkt döndürür (0 LLM). |
| **Nasıl?** | yt-dlp ile transcript → bölümlere ayır → skill çıkar → hafızadaki eski bilgiyle karşılaştır → hata tespit et → düzelt → kaydet. |

---

## Pipeline

```
YouTube URL
    │
    ▼
┌─────────────────────────────┐
│ 1. Transcript Çekme          │
│    ├─ yt-dlp (birincil)      │
│    │   yt-dlp --write-auto-sub
│    │   --sub-langs tr,en
│    │   --skip-download
│    │   --output "%(id)s"
│    │   URL
│    │   └─ .vtt/.srt dosyası
│    │
│    └─ Whisper (fallback)     │
│        ├─ yt-dlp --extract-audio
│        │   --audio-format wav
│        │   URL
│        └─ whisper modeli ile
│           transkript çıktısı
│
│   Çıktı: transcript (düz metin)
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ 2. Bölümleme                 │
│    ├─ Giriş / Tanıtım        │
│    │   (ilk %20, genel bakış)│
│    ├─ Teknik / Uygulama      │
│    │   (orta %60, adımlar)   │
│    └─ Sonuç / Test           │
│        (son %20, özet/test)  │
│                              │
│   Çıktı: bölümlenmiş metin   │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ 3. Skill Çıkarma             │
│    ├─ Paket/kurulum adımları │
│    ├─ Kod parçacıkları       │
│    ├─ API kullanım şekli     │
│    ├─ Hata/çözüm desenleri   │
│    └─ Cross-reference linki  │
│                              │
│   Çıktı: structured skill    │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ 4. Hafızaya Kaydet           │
│    ├─ kaydet(                │
│    │   hedef='video_xxx',    │
│    │   kategori='video/...', │
│    │   icerik='...',         │
│    │   basari=True           │
│    │ )                       │
│    │                         │
│    └─ Aynı hedef+kategori    │
│       varsa UPDATE yapar     │
│       (yeni ID açılmaz)      │
└─────────────────────────────┘
```

---

## Transcript Çekme Stratejisi

### Birincil: yt-dlp (otomatik altyazı)
```bash
yt-dlp --write-auto-sub --sub-langs "tr,en" --skip-download \
       --convert-subs srt --output "%(id)s" "URL"

yt-dlp --write-sub --sub-langs "tr,en" --skip-download \
       --convert-subs srt --output "%(id)s" "URL"
```

### Fallback: Whisper (ses → yazı)
```bash
yt-dlp --extract-audio --audio-format wav --output "%(id)s" "URL"
whisper "video_id.wav" --model small --language tr --output_format txt
```

---

## Bölümleme Algoritması

1. **Zaman damgası bazlı**: Varsa SRT/VTT zamanlarına göre
2. **Kelime sıklığı bazlı**: Teknik terim yoğunluğu → Teknik bölüm
3. **Regex işaretçileri**:
   - Giriş: "merhaba", "bugün", "başlayalım", "göstereceğim"
   - Teknik: "şimdi", "yapmanız gereken", "kod", "terminal", "kurulum"
   - Sonuç: "özet", "sonuç", "teşekkürler", "kanala abone ol"

---

## Skill Çıkarma Formatı

```yaml
skill:
  kaynak: "<video URL>"
  baslik: "<video başlığı>"
  kanal: "<kanal adı>"
  adimlar:
    - adim: 1
      islem: "paket kurulumu"
      komut: "pip install ..."
    - adim: 2
      islem: "kod yazma"
      kod: "..."
  hatalar:
    - hata: "..."
      cozum: "..."
  cross_ref:
    - kategori: "kali/network/nmap"
    - kategori: "video/python/nmap"
```

---

## Hafızaya Kaydetme

```python
kaydet(
    hedef=f'{konu}_video_ogrenme',
    kategori=f'video/{alan}/{konu}',
    icerik=skill_metni,
    basari=True
)

# Cross-reference ekleme
kaydet(
    hedef=f'{konu}_kali_karsilastirma',
    kategori='cross-platform/network',
    icerik=karsilastirma_metni,
    basari=True
)
```

---

## Hata Tespit Senaryoları

### Senaryo 1 — Kod Hatası
Video'da hata bulundu → ajan tespit etti + düzeltilmiş kodu yazdı
**Doğrula:** Sandbox'ta çalıştır (timeout=120s)
- 3 deneme: farklı parametre → farklı kütüphane → alternatif yaklaşım
- 3 başarısız → circuit breaker

### Senaryo 2 — Çelişkili Bilgi
Hafızadaki eski bilgi vs Video'daki yeni yöntem
**Karşılaştır:** Web'den doğrula (PyPI, GitHub, resmi doküman)
Web kaynağı her zaman kazanır (güncel)

### Senaryo 3 — Bilinmeyen Hata
Hata anlaşılamadı → hafıza kontrol → web kontrol (3 kaynak)
3'te de yoksa → circuit breaker → kullanıcıya bildir
