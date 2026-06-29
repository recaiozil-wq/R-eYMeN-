---
name: web-dogrulama-dongusu
description: WEB → UYGULA → PUANLA → KARAR döngüsü — web'den bilgi al, sandbox'ta test et, puanla, kazananı hafızaya kaydet
category: cross-platform
version: 1.0.0
triggers:
  - web doğrulama
  - puanlama
  - karşılaştırma
  - eski bilgi tazeleme
  - güven düşük
  - başarısız retry
  - geçerlilik süresi
  - çelişkili bilgi
  - hafıza boş
---


> **Kategori:** web-dogrulama-dongusu

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | WEB → UYGULA → PUANLA → KARAR döngüsü — web'den bilgi al, sandbox'ta test et, puanla, kazananı hafızaya kaydet |
| **Nerede?** | web-dogrulama-dongusu/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# WEB → UYGULA → PUANLA → KARAR Döngüsü

## 5 Tetikleyici

| # | Tetikleyici | Koşul | Ne Zaman? | Öncelik |
|:-:|:-----------|:------|:----------|:-------:|
| 1 | **Hafıza Boş** | `once_hafiza.ara()` → boş | Yeni tool/konu soruldu | 🥇 |
| 2 | **Görev Başarısız** | 2. hata üst üste | Retry 1 hata verdi | 🥈 |
| 3 | **Güven Düşük** | `guven_skoru < 0.5` | Belirsiz sonuç döndü | 🥉 |
| 4 | **Geçerlilik Süresi** | `gecerlilik_tarihi < bugün` | Bilgi eski, tool güncel | ④ |
| 5 | **Çelişki** | Video/kullanıcı hafızayla uyuşmaz | Farklı yöntem önerildi | ⑤ |

## Akış

```
Tetikleyici ateşlendi
       ↓
┌── ADIM 1: WEB'DEN ARA ──────────────────┐
│ 3 kaynak minimum                        │
│ resmi doc  → guven=0.9                  │
│ stackoverflow → guven=0.7               │
│ blog       → guven=0.5                  │
│ reddit     → guven=0.4                  │
└──────────────────────────────────────────┘
       ↓
┌── ADIM 2: UYGULA (Sandbox) ──────────────┐
│ Yeni yöntem  → sandbox'ta çalıştır       │
│ Eski yöntem  → sandbox'ta çalıştır       │
│ Aynı koşullar, ayrı ayrı test            │
└──────────────────────────────────────────┘
       ↓
┌── ADIM 3: PUANLA (0-1) ─────────────────┐
│ hiz:      kaç saniye?                    │
│ basari:   hata var mı? (0/1)            │
│ cikti:    çıktı doğru mu? (0/1)         │
│ guvenlik: güvenli mi? (0/1)             │
│ kaynak:   kaynak güvenilirliği (0.4-0.9)│
│ PUAN = (hiz*0.15 + basari*0.3 +         │
|   cikti*0.25 + guvenlik*0.2 +      |
|         kaynak*0.1)                      |
       ↓
┌── ADIM 4: KARAR ────────────────────────┐
│ Yeni - Eski > 0.2 → Yeniye geç ✅      │
│ Fark < 0.2         → Eski korun 🔒     │
│ Yeni başarısız     → Eski devreye gir 🔄│
│ İkisi de başarısız → Kullanıcıya sor ❓ │
└──────────────────────────────────────────┘
       ↓
┌── ADIM 5: KAYDET ──────────────────────┐
│ Kazanan → ana kayıt (UPDATE, guven↑)   │
│ Kaybeden → arşiv (silinmez, flag_udp=1)│
│ Test sonuçları → hafızaya eklenir      │
│ web_arama_sebebi → metadata'ya yazılır │
└──────────────────────────────────────────┘
```

## Puanlama Formülü

```python
PUAN = (hiz * 0.15) + (basari * 0.3) + (cikti * 0.25) + (guvenlik * 0.2) + (kaynak * 0.1)

hiz:      0-1 (normalize: 1 = <1sn, 0 = >30sn)
basari:   1 = hata yok, 0 = hata var
cikti:    1 = doğru çıktı, 0 = yanlış
guvenlik: 1 = güvenli, 0 = riskli
kaynak:   0.4-0.9 (reddit→doc)
```

## Öncelik Sırası

```
1. Hafıza boş       → ANINDA web (bekleme yok)
2. Görev başarısız  → 2. hatada web (hızlı)
3. Güven < 0.5      → web (öncelikli)
4. Geçerlilik geçmiş → ARKA PLANDA web
5. Çelişki          → web (hakem karar)
```

## Hafıza Kayıt Formatı

```json
{
  "anahtar": "nmap udp tarama karsilastirma",
  "kategori": "kali/network/nmap",
  "guven_skoru": 0.95,
  "kullanim_sayisi": 1,
  "web_arama_sebebi": "guven_dusuk | hafiza_bos | gorev_basarisiz | gecerlilik_suresi | celiski",
  "test_sonuclari": {
    "yeni_yontem": {"puan": 0.85, "hiz": 0.9, "basari": 1.0, "cikti": 1.0, "guvenlik": 0.8, "kaynak": 0.7},
    "eski_yontem": {"puan": 0.65, "hiz": 0.5, "basari": 0.8, "cikti": 0.7, "guvenlik": 1.0, "kaynak": 0.9}
  },
  "kazanan": "yeni_yontem",
  "karar_gerekcesi": "Fark 0.2 > esik → Yeniye gecildi"
}
```

## Örnek: nmap UDP Tarama

**SORU:** "nmap için en hızlı UDP tarama yöntemi?"

**Tetikleyici:** Hafıza boş (nmap UDP hakkında kayıt yok) → 🥇 ANINDA web

**Web kaynakları:**
1. nmap.org docs → guven=0.9 → `nmap -sU --min-rate=1000 -p 1-1000`
2. stackoverflow → guven=0.7 → `nmap -sU -T5 --max-retries=1`
3. blog → guven=0.5 → `nmap -sU -sV -p-`

**PUAN tablosu:**
| Yöntem | Hız | Başarı | Çıktı | Güv. | Kaynak | Toplam |
|:-------|:---:|:------:|:-----:|:----:|:------:|:------:|
| A: `--min-rate=1000` | 0.83 | 1.0 | 1.0 | 1.0 | 0.9 | **0.95** |
| B: `-T5 --max-retries=1` | 0.57 | 1.0 | 1.0 | 1.0 | 0.7 | **0.87** |
| C: `-sV -p-` | 0.0 | 0.0 | 0.0 | 1.0 | 0.5 | **0.225** |

**Karar:** A kazandı (fark=0.725 > 0.2 → ✅ Yeniye geç)
Hız avantajı (5.2sn vs 45.3sn) ve resmi docs kaynağı belirleyici oldu.

### Puan Ağırlık Profilleri

Varsayılan: hiz(0.15) + basari(0.3) + cikti(0.25) + guvenlik(0.2) + kaynak(0.1)

Alternatif profiller:
| Profil | hiz | basari | cikti | guvenlik | kaynak | Kullanım |
|:-------|:---:|:------:|:-----:|:--------:|:------:|:---------|
| **Denge** | 0.20 | 0.30 | 0.20 | 0.15 | 0.15 | Genel amaçlı |
| **Hız odaklı** | 0.40 | 0.20 | 0.15 | 0.10 | 0.15 | Port tarama, benchmark |
| **Güvenlik odaklı** | 0.10 | 0.20 | 0.20 | 0.40 | 0.10 | Firewall, yetki işlemleri |
| **Doğruluk odaklı** | 0.10 | 0.30 | 0.40 | 0.10 | 0.10 | Rapor, analiz |

## 5 Kategori Hata Analizi (11 Hata)

| Kat | Hata | Tanım | Çözüm |
|:----|:-----|:------|:------|
| **K1** Tetikleyici | İçerik eskimiş ama tarih gelmemiş | metadata'ya `version` alanı ekle |
| | Tool versiyon farkı görünmez | Periyodik web tarama (7 günde 1) |
| **K2** Puanlama | Ağırlıklar sabit | Göreve göre profil seç (yukarıdaki tablo) |
| | Başarı 0/1 binary | `basari = basarili_adim / toplam_adim` sürekli |
| **K3** Hafıza | Kaynak URL metadata'da gömülü | `kaydet()`'e `kaynak_url` parametresi eklendi (Karar #14) |
| | guven=1.0 ilk başarıda çok yüksek | `_kademeli_guven()` sigmoid: `1/(1+e^(-0.5*(basari-hata-1)))` (Karar #14) |
| | Kullanılmayan kayıtlar temizlenmez | 30 günde bir temizlik cron'u |
| **K4** İletişim | Ajan çökerse diğeri habersiz | 30sn heartbeat + 3 kaçırma alarmı |
| | Timeout sabit (120sn) | Dinamik: `port_sayisi * 0.1sn` min30 max600 |
| | Mesaj kaybolursa | ACK protokolü + 3 retry |
| **K5** Öğrenme | Yanlış bilgi guven=1.0 ile kaydedilir | Kullanıcı düzeltmesi 0.8 başlar |
| | Zehirli web kaynağı | <0.6 kaynak reddedilir, sandbox test şart |
| | Çok hızlı güven artışı | Bayesian guven, 10 denemeden önce 1.0 olmaz |

## LLM Maliyeti

- Web arama: **0 LLM** (tool)
- Puanlama: **0 LLM** (formül)
- Karar: **0 LLM** (eşik kontrolü)
- Kod üretme: **1 LLM** (yeni yöntem uyarlama)

## Referans Dosyaları

| Dosya | Açıklama |
|:------|:---------|
| `scripts/simulate_web_loop.py` | WUPS döngüsü simülasyonu (5 tetikleyici + nmap UDP testi + 5 kategori hata analizi) |
| `references/kademeli-guven-kaydet-api.md` | `_kademeli_guven()` sigmoid formülü, değer tablosu, `kaydet()` API dokümantasyonu |
