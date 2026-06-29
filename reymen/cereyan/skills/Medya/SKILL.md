---
name: video-ogrenme-ajani
description: YouTube videolarından öğrenme — transcript indir, bölümle, hata tespit et, skill çıkar, hafızaya kaydet
category: video
version: 1.0.0
triggers:
  - video
  - youtube
  - öğrenme
  - transcript
  - eğitim
  - python video
  - hata tespit
  - kod doğrulama
  - sandbox test
  - retry mekanizması
  - çelişkili bilgi
  - kullanıcı hatası
  - web doğrulama
  - puanlama
  - karşılaştırma
  - UDP tarama
  - wups döngüsü
---


> **Kategori:** video-ogrenme-ajani

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Video ajanı |
| **Ne?** | YouTube videolarından öğrenme — transcript indir, bölümle, hata tespit et, skill çıkar, hafızaya kaydet |
| **Nerede?** | video-ogrenme-ajani/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Video Öğrenme Ajanı

## Mimari

```
YouTube URL
   ↓
① yt-dlp ile transcript indir (varsa)
   ↓
② Transcript yoksa → Whisper ile ses→yazı
   ↓
③ Bölümlere ayır: Giriş | Teknik Adımlar | Sonuç
   ↓
④ Hafızada ara: kategori eşleşmesi var mı?
   ├─ VAR → video ile karşılaştır, eksikleri bul
   └─ YOK → yeni kategori oluştur
   ↓
⑤ Hata tespit et (hafıza + kurallar)
   ↓
⑥ Hataları düzelt, eksikleri tamamla
   ↓
⑦ Birleşik skill + hafıza kaydı
```

## Video Bölümleme

| Bölüm | Tespit | Çıktı |
|:------|:-------|:------|
| Giriş | "merhaba", "bugün", "bu videoda" | Konu + hedef |
| Teknik adımlar | Kod blokları, komutlar, kurulum | Adım adım rehber |
| Sonuç/özet | "özet", "sonuç", "görüşmek üzere" | Kazanımlar listesi |

## Hata Tespit Kuralları

1. **Parametre sırası**: `scan(host, ports)` vs `scan(host, arguments='...', ports='...')` → python-nmap'te `ports=` keyword gerekli
2. **Port formatı**: `'22-443'` string → doğru, ama `PortScanner.scan()`'de `ports='22-443'` keyword arg olmalı
3. **Sudo kontrolü**: nmap SYN scan (`-sS`) root gerektirir → video belirtmemişse uyar
4. **Exception handling**: `try/except` yoksa uyar
5. **Result parse**: `nm['127.0.0.1'].all_tcp()` vs `nm['127.0.0.1']['tcp']` → ikinci daha doğru

## Örnek Akış

**Video:** "Python ile nmap kullanımı"

```
Transcript parse:
  Giriş: "Bugün python-nmap kütüphanesini öğreneceğiz"
  Adım 1: pip install python-nmap
  Adım 2: import nmap
  Adım 3: nm = nmap.PortScanner()
  Adım 4: nm.scan('127.0.0.1', '22-443')
  Sonuç: "Portlarımızı taradık"

Hafıza kontrolü → kali/network/nmap var (guven=1.0)
Karşılaştırma:
  ✅ nmap CLI bilgisi hafızada
  ❌ python-nmap API bilgisi hafızada YOK
  ❌ '22-443' positional arg → ports='22-443' olmalı
  ❌ sudo gereksinimi belirtilmemiş
  ❌ exception handling yok
  ❌ sonuç parse edilmemiş

Düzeltilmiş çıktı → video/python/nmap kategorisine kaydet
```

## LLM Maliyeti

- Hafıza hit (mevcut kategori): **0 LLM çağrısı**
- Video transcript analizi: **1 LLM çağrısı** (yeni içerik)
- Hata tespit (hafıza karşılaştırma): **0 LLM çağrısı**
- Düzeltilmiş kod üretme: **1 LLM çağrısı** (yeni)

## Referanslar

- python-nmap docs: https://pypi.org/project/python-nmap/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- Whisper: https://github.com/openai/whisper

## 3 Hata Senaryosu Akışı

### Senaryo 1 — Kod Hatası

```
Video'dan parse edilen kod
       ↓
① 5 hata tespit (kural bazlı, 0 LLM)
   🔴 MAJOR: ports keyword arg, sudo eksik, exception handling
   🟡 MINOR: result parse, hardcoded arg
       ↓
② Düzeltilmiş kod üret (1 LLM)
       ↓
③ Sandbox doğrulama (3 test)
   Test 1: Syntax check
   Test 2: Çalıştırma (timeout=30sn)
   Test 3: Hata yolu mock
   └─ 3/3 PASS → kod onaylandı
       ↓
   ⚠️ BAŞARISIZ: max 3 retry (2sn→4sn→8sn)
      → circuit breaker → kullanıcıya bildir
       ↓
④ Hafıza kaydet
   UPDATE: eski kayıt guven 0.9→1.0
   YENİ: hata spesifik kayıt (guven=0.95)
```

### Senaryo 2 — Çelişkili Bilgi

```
HAFIZA: nmap CLI (guven=1.0)
VİDEO:  python API (yeni)
       ↓
① Karar ağacı (0 LLM)
   Aynı kategori mi?  → HAYIR → EK BİLGİ
   Aynı bağlam mı?    → HAYIR → FARKLI YÖNTEM
       ↓
② Web doğrulama (çelişki varsa)
   python-nmap docs: "keyword arg önerilir"
       ↓
③ Eski bilgi işaretleme (3 durum)
   A) Web farklı → flag_udp=1, guven 1.0→0.3
   B) Zaman aşımı >180g → guven *= 0.5
   C) Kullanıcı düzeltti → flag_udp=1, guven=0.2
       ↓
④ Hafıza: cross_ref ekle
   kali/network/nmap ↔ video/python/nmap
```

### Senaryo 3 — Bilinmeyen Hata

```
nm.scan('127.0.0.1', '-p 22-443')  # -p prefix
       ↓
① Hafızada benzer ara (0 LLM)
   Bulundu → direkt çözüm (guven > 0.8)
   Bulunamadı → devam
       ↓
② Retry döngüsü (max 3, exponential backoff)
   Deneme 1: yöntem A (strip prefix)
   Deneme 2: yöntem B (prefix'siz)
   Deneme 3: yöntem C
       ↓
③ Web arama (opsiyonel)
   stackoverflow/docs kontrol
       ↓
④ Kullanıcıya sor (son çare)
   Format: KOD + HATA + DENEDİKLERİM + SORU
   → Cevap gelince:
     1. Hafızaya kaydet (guven=1.0, kaynak=kullanıcı)
     2. Eski kaydı flag_udp=1 yap
```

## WUPS Döngüsü (Web → Uygula → Puanla → Karar)

Hafızadaki bilgi ile web'den gelen yeni bilgi çeliştiğinde veya hafıza boş olduğunda kullanılır.

### 5 Tetikleyici (Öncelik Sıralı)

| # | Tetikleyici | Koşul | Aksiyon |
|:-:|:------------|:------|:--------|
| T1 | **Hafıza Boş** | `once_hafiza.ara()` → None | Anında web ara |
| T2 | **Görev Başarısız** | 2 ardışık hata | Web'de çözüm ara |
| T3 | **Güven Düşük** | `guven_skoru < 0.5` | Web'den doğrula |
| T4 | **Geçerlilik Süresi** | `gecerlilik_tarihi < bugün` | Arka planda web tazele |
| T5 | **Çelişki** | Video/kullanıcı ≠ hafıza | Web'den hakem karar |

### Adımlar

```
ADIM 1 — WEB'DEN ARA
  3 kaynak minimum: resmi doc(0.9), stackoverflow(0.7), blog(0.5), reddit(0.4)
  En yüksek guvenli kaynağın önerisini al

ADIM 2 — UYGULA (Sandbox)
  Yeni yöntem (web'den): sandbox'ta çalıştır
  Eski yöntem (hafızadan): sandbox'ta çalıştır
  İkisi AYNI KOŞULLARDA test edilir

ADIM 3 — PUANLA (0-1 arası)
  Kriterler: hız(0.2) + başarı(0.3) + çıktı(0.2) + güvenlik(0.15) + kaynak(0.15)
  Ağırlıklar göreve göre değişebilir (hız_odakli, guvenlik_odakli, denge)

ADIM 4 — KARAR
  Yeni > Eski + 0.2 fark → YENİYE GEÇ
  |Yeni - Eski| < 0.2 → ESKİ KORUNUR (stable)
  Yeni başarısız → ESKİ DEVAM
  İkisi başarısız → KULLANICIYA SOR

ADIM 5 — KAYDET
  Kazanan → UPDATE (guven artar)
  Kaybeden → arşiv (guven düşer, silinmez)
  Test sonuçları → hafızaya eklenir
```

### Puanlama Detayı

```python
hiz_puan = max(0, 1 - (sure_sn / 30))     # 1sn=1.0, 30sn=0.0
basari_puan = 0 if hata_var else 1          # binary
cikti_puan = 1 if cikti_dogru else 0
guvenlik_puan = 1.0  # varsayılan güvenli
kaynak_puan = {doc: 0.9, so: 0.7, blog: 0.5, reddit: 0.4}

toplam = hiz*0.2 + basari*0.3 + cikti*0.2 + guvenlik*0.15 + kaynak*0.15
```

### Bilinen Hatalar (5 Kategori, 11 adet)

| Kat | Konu | Açıklama | Çözüm |
|:----|:-----|:---------|:------|
| K1 | Tetikleyici | İçerik eskimiş ama tarih gelmemiş; versiyon farkı görünmez | metadata'ya `version` alanı ekle, periyodik web tara |
| K2 | Puanlama | Ağırlıklar sabit; başarı 0/1 binary | Göreve göre ağırlık profili; sürekli başarı metriği |
| K3 | Hafıza | URL kolon yok; guven=1.0 çok yüksek; temizlik yok | Ayrı source_url kolonu; Bayesian guven; 30g temizlik |
| K4 | İletişim | Heartbeat yok; timeout sabit; ACK yok | 30sn heartbeat; dinamik timeout; ACK protokolü |
| K5 | Öğrenme | Yanlış kayıt; zehirli web; hızlı güven artışı | Kullanıcı kaydı 0.8 başlar; <0.6 kaynak reddedilir; Bayesian |
| K6 | **Operasyonel** | Mevcut otomasyon kontrol edilmeden manuel aksiyon alındı → cron job'lar atlandı | Her aksiyon öncesi `cronjob list` ile mevcut görevleri kontrol et; terminal kilitliyse `process kill` ile temizle |

## Pre-flight Checklist (Her Aksiyon Öncesi)

1. **Cron job'ları kontrol et** — `cronjob list()` ile mevcut otomasyonu tara. Aynı işi zaten yapan bir cron varsa manuel yapma.
2. **Terminal durumunu kontrol et** — Önceki komut asılı kaldıysa `process kill` ile temizle. Terminal yanıt vermiyorsa yeni terminal oturumu aç.
3. **Gateway durumunu kontrol et** — `hermes cron status` ile scheduler'ın çalıştığını doğrula. Gateway yoksa `hermes -p reymen gateway start`.
4. **Hafızada ara** — `once_hafiza.ara()` ile benzer çözüm var mı kontrol et. Varsa direkt uygula.
5. **Web'de doğrula (gerekirse)** — T1-T5 tetikleyicilerinden biri aktifse WUPS döngüsünü başlat.

## Destek Dosyaları

| Dosya | Açıklama |
|:------|:---------|
| `references/python-nmap-api.md` | python-nmap API kullanımı, hata yönetimi, tarama türleri, önemli uyarılar |
| `references/cron-management.md` | ReYMeN cron job listesi, remote'lar, push script'leri, sorun giderme |
| `scripts/simulate_video_learning.py` | Video öğrenme simülasyonu (Görev 1-4'ü çalıştırır) |
