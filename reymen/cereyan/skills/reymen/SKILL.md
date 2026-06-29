---
name: reymen-hafiza-oncelikli-akis
description: ReYMeN hafıza-öncelikli karar ağacı — isle() API'si, 3 iyileştirme, kategori/guven_skoru/gecerlilik sistemi
category: reymen
version: 2.1.0
triggers:
  - hafiza
  - once hafiza
  - karar agaci
  - isle api
  - memory first
  - cache bypass
  - circuit breaker
  - retry
  - cron job
  - guven hesaplama
  - kademeli guven
  - kaynak url
---


> **Kategori:** reymen-hafiza-oncelikli-akis

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | ReYMeN hafıza-öncelikli karar ağacı — isle() API'si, 3 iyileştirme, kategori/guven_skoru/gecerlilik sistemi |
| **Nerede?** | reymen-hafiza-oncelikli-akis/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# ReYMeN Hafıza-Öncelikli Akış

## Genel Akış (Karar Ağacı)

```
Görev gelir
  ↓
① ÖNCE HAFIZA (guven_skoru > 0.8?)
  ├─ EVET → direkt döndür (0 LLM çağrısı)
  └─ HAYIR → devam
              ↓
② SONRA CACHE (selam/teşekkür vs?)
  ├─ EVET → direkt döndür (0 LLM çağrısı)
  └─ HAYIR → devam
              ↓
③ EN SON LLM (DeepSeek)
  ├─ Her turda 1 API call
  ├─ Maks 90 tur (IterationBudget)
  ├─ Maks 3 retry (exponential backoff)
  └─ 3 ardışık hata → KALICI circuit breaker
       ├─ Otomatik açılmaz (CIRCUIT_BREAKER_KALICI=True)
       └─ Kullanıcıya bildirilir + durur
```

## API Kullanımı

### `isle(hedef, islev, kategori)` — Ana API
Hafızaya bak, varsa döndür, yoksa çalıştır, kaydet, döndür.

```python
from reymen.hafiza.gorev_once_kontrol import isle

# Hafıza öncelikli: önce bak, yoksa çalıştır
sonuc = isle(
    "nmap ile port tara 127.0.0.1",
    lambda: terminal("nmap -sV -T4 127.0.0.1"),
    kategori="kali/network/nmap",
)

if sonuc["hafizada"]:
    print(f"Hafızadan geldi (guven: {sonuc['guven_skoru']})")
else:
    print(f"Yeni calisti: {sonuc['cikti']}")
```

### `hafizada_ara(hedef, kategori)` — Sorgula
```python
kayit = hafizada_ara("servis versiyon tespiti", kategori="kali/network/nmap")
if kayit["bulundu"]:
    if kayit["guven_seviyesi"] == "belirsiz":
        print("Düşük güven, doğrula!")
    elif kayit["gecerlilik_durumu"] == "gecersiz":
        print("Bilgi eski, yenile!")
    else:
        print(f"Guvenilir kayit: {kayit['icerik'][:100]}")
```

### `kaydet_isle(hedef, kategori, sonuc, basarili)` — Otomatik güven skorlu
```python
kaydet_isle(
    "localhost UDP taramasi",
    "kali/network/nmap",
    "6 UDP port bulundu (137/netbios, 1900/upnp, ...)",
    basarili=True,
)
```

### ESKİ KAYDI GÜNCELLE (yeni kayıt açma)
```python
from reymen.hafiza.hafiza_genislet import hafiza

# Mevcut kaydı bul, metadata'sını güncelle
hafiza.kayit_guncelle(
    kayit_id=1972,
    yeni_icerik=mevcut_icerik + yeni_bilgi,
    yeni_metadata={
        "kullanim_sayisi": mevcut_meta["kullanim_sayisi"] + 1,
        "guven_skoru": guven_skoru_hesapla(),
        "son_kullanim": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "flag_udp": True,
    },
)
# ❌ SAKIN: gorev_sonrasi_hafiza() ile yeni kayıt açma
```

## Veri Yapısı (Metadata)

Her hafıza kaydında şu alanlar zorunludur:

| Alan | Tip | Açıklama |
|:-----|:----|:---------|
| `guven_skoru` | float 0.0-1.0 | `_kademeli_guven()` sigmoid. İlk kayıt=0.5. >0.8 = LLM atla |
| `son_kullanim` | str "%Y-%m-%d %H:%M" | Her kullanımda güncellenir |
| `kategori` | str | "kali/network/nmap", "dron", "cad", "windows/terminal/network" |
| `gecerlilik_tarihi` | str "%Y-%m-%d" | +180 gün (varsayılan). Geçmişse "gecersiz" |
| `kullanim_sayisi` | int | Her isabetli kullanımda +1 |
| `basari_sayisi` | int | Başarılı kullanım sayısı |
| `hata_sayisi` | int | Başarısız kullanım sayısı |
| `kaynak_url` | str | Kaynak URL (varsa). Web/video'dan gelen bilgilerde doldurulur |

### Güven Hesaplama (`_kademeli_guven`)

```
guven = 1 / (1 + e^(-0.5 * (basari - hata - 1)))
```

| Durum | Güven | Açıklama |
|:------|:-----|:---------|
| İlk başarı | 0.50 | Eski: 1.0'dı, çok yüksekti (H16) |
| 3 başarı | 0.73 | Kademeli artış |
| 10 başarı | 0.99 | Güvenilir kabul edilir |
| 1 başarı + 3 hata | 0.18 | Güvensiz, hata oranı yüksek |
| 1 başarı + 1 hata | 0.38 | Belirsiz eşiğinde |

**Karar #14** — `sistem/once_hafiza.py` güncellendi: `basari/(basari+hata)` lineer formül yerine `_kademeli_guven()` sigmoid kullanılır.

### Kategori Tespiti (Otomatik)
```python
"nmap ile port tara"      → "kali/network"
"px4 drone ucur"          → "dron"
"solidworks kur"          → "cad"
"ekran goruntusu al"     → "windows"
"python decorator nedir"  → "genel"
```

## 3 İyileştirme (conversation_loop.py)

### 1. Zorunlu Hafıza Kontrolü
- `guven_skoru > 0.8` ise → LLM çağrılmaz
- Direkt hafızadan döndür
- Tahmini %60 maliyet düşüşü
- Kod: `conversation_loop.py` satır ~425

### 2. Mekanik Retry
- `CB_MAX_HATA = 3` (önceden 5'ti)
- `CIRCUIT_BREAKER_KALICI = True` — otomatik açılmaz
- 3 başarısız API call → kalıcı dur + kullanıcıya bildirim
- Kod: `conversation_loop.py` satır ~165-168, ~463-477

### 3. Tool Öncelik Sırası
```
1. Hafıza (guven > 0.8) — 0 LLM
2. Cache (ONCELIK_CACHE) — 12 pattern, 0 LLM
3. LLM (DeepSeek) — maks 90 tur
```
- Cache pattern'leri: selam, teşekkür, bye, hadi, tamam, ok
- Kod: `conversation_loop.py` satır ~95-108, ~475-491

## Cross-Agent Desteği

Farklı ajanlar kendi `.AjanAdi/notes/` hafızalarını kullanabilir:

```python
from reymen.hafiza.gorev_once_kontrol import cross_agent_ekle, cross_agent_tara, isle

# Kali ajanının hafızasını ekle
cross_agent_ekle("Kali", "/home/kali/hermes_projesi")

# Tüm cross-agent klasörlerinde ara
bulunanlar = cross_agent_tara("nmap tarama")

# Kali için isle() API'si
sonuc = isle(
    "nmap ile port tara",
    lambda: terminal("nmap -sV 10.0.0.1"),
    kategori="kali/network/nmap",
)
```

## Pitfall'lar

- **ASLA** aynı konuda ikinci bir kayıt açma. `kayit_guncelle()` kullan.
- **guven_skoru < 0.5** → "belirsiz" kabul edilir, hafıza atlaması yapmaz.
- **gecerlilik_tarihi** geçmişse → kayıt gösterilmez, yeniden dene.
- **Cache** sadece EXACT veya STARTSWITH eşleşmesi yapar. "merhaba nasılsın" → cache'den gider. "merhaba dünya" → gider. "nasılsın" → gitmez.
- Cross-agent klasörü yoksa sessizce atlanır, hata vermez.
- **ZAMANLANMIŞ GÖREVLERİ KONTROL ET**: Manuel backup/push yapmadan ÖNCE `cronjob(list)` ile mevcut cron'ları kontrol et. Eğer zaten zamanlanmış bir cron job'u varsa (örn `reymen-daily-memory-push`), manuel işlem yapma — cron'un çalışmasını bekle veya tetikle. Gereksiz manuel push = kullanıcı uyarısı ("Zamanlanmis Gorevler neden almadın").
- **guven=1.0 ilk kayıtta KULLANMA**: `_kademeli_guven()` fonksiyonunu kullan. İlk kayıt en fazla 0.5 olabilir (Karar #14). Eski: `guven = basari/(basari+hata)` → artık kullanılmaz.
- **`kaydet()` çağrısında `kaynak_url` parametresini doldur** — bilgi web'den veya videodan geldiyse URL mutlaka eklenmeli.

## Çıkış Koşulları (8 adet)

| # | Koşul | Detay |
|:-:|:------|:------|
| 1 | guven_skoru > 0.8 | Hafızadan direkt, LLM yok |
| 2 | Cache eşleşmesi | Selam/teşekkür direkt döndür |
| 3 | budget(90) doldu | IterationBudget devam_etmeli_mi=false |
| 4 | GOREV_BITTI | LLM "bitti" dedi |
| 5 | tool.tamamlandi=true | Tool "bitti" sinyali |
| 6 | Takılma (3x) | Aynı eylem 3x tekrar |
| 7 | Circuit breaker (3x) | 3 ardışık hata, kalıcı dur |
| 8 | Ctrl+C | Kullanıcı iptali |

## Referanslar
- `references/hermes-import-2026-06-21.md` — 125 session → ReYMeN hafıza toplu import detayı
