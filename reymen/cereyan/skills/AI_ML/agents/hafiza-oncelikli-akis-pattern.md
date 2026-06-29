
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Hafiza Oncelikli Akis Pattern |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hafıza-Öncelikli Akış Pattern

Session: 2026-06-21 (oluşturuldu), 2026-06-21 (2. güncelleme — 3 iyileştirme: hafiza zorunlu atlama, cache, mekanik retry)

Kullanıcı düzeltmesi: Akış `Görev → Sonuç → Kaydet` idi, `Görev → ÖNCE HAFIZAYA BAK → ...` olması gerekiyordu.

## 3 İyileştirme Özeti

Bu session'da 3 iyileştirme eklendi (conversation_loop.py):

1. **Zorunlu Hafıza Kontrolü (İyileştirme #1):** guven_skoru > 0.8 ise LLM çağrılmaz, direkt hafızadan döndürülür. `hafizada_ara()` sonucu `bulundu=True` ve `guven_skoru > 0.8` ise `sonuc["yanit"]` hazırlanır, `budget.gorev_tamamla()` ile döngü kapatılır, LLM hiç çağrılmaz.

2. **Mekanik Retry (İyileştirme #2):** `CIRCUIT_BREAKER_MAX_HATA=3`, `CIRCUIT_BREAKER_KALICI=True`. 3 ardışık hata sonrası circuit breaker kalıcı olarak açık kalır (otomatik açılmaz). Kullanıcıya "[KALICI DURDURMA] 3/3 ardisik hata. 3 deneme hakkiniz doldu." mesajı gönderilir.

3. **Cache Öncelik (İyileştirme #3):** `ONCELIK_CACHE` dict'i conversation_loop.py'de tanımlıdır (12 pattern: merhaba, selam, teşekkür, tesekkur, sagol, gorusuruz, bye, hadi, tamam, ok). Hafıza kontrolünden sonra, LLM döngüsünden ÖNCE cache kontrolü yapılır. Eşleşme varsa direkt cache'ten döndürülür.

Kod yeri: conversation_loop.py satır ~98 (ONCELIK_CACHE tanımı), ~488 (cache kontrolü kodu).

## Karar Akışı (Güncel)

```
Görev
  ↓
1. hafizada_ara(hedef, kategori)    ← gorev_once_kontrol.py
  ├─ bulundu + guven > 0.8 → direkt döndür (0 LLM)
  └─ bulunamadı / guven < 0.8 → devam
                                 ↓
2. ONCELIK_CACHE kontrolü          ← conversation_loop.py
  ├─ eslesme var → direkt döndür (0 LLM)  
  └─ yok → devam
            ↓
3. LLM döngüsü (90 max)
  ├─ 3 retry, 3 hata → CB kalıcı
  └─ basarili → gorev_sonrasi_hafiza() kaydet
```

## isle() API — Birleşik Hafıza-Öncelikli Çalıştırma

**Dosya:** `reymen/hafiza/gorev_once_kontrol.py`

```python
from reymen.hafiza.gorev_once_kontrol import isle

sonuc = isle(
    "nmap ile port tara",
    lambda: terminal("nmap -sV 127.0.0.1"),
    kategori="kali/network/nmap",
)
if sonuc["hafizada"]:
    print("Hafızadan geldi, lambda çalışmadı!")
```

**Dönüş:** `{"hafizada": True/False, "icerik": "", "cikti": "", "guven_skoru": 0-1, "gecerlilik_durumu": "", "basarili": True/False}`

## hafizada_ara() — Kategori + Güven Skoru Filtreli Sorgulama

```python
from reymen.hafiza.gorev_once_kontrol import hafizada_ara
kayit = hafizada_ara("servis versiyon tespiti", kategori="kali/network/nmap")
if kayit["bulundu"] and kayit["guven_seviyesi"] != "belirsiz":
    print(f"Guvenilir: {kayit['guven_skoru']}")
```

## kaydet_isle() — Otomatik Güven Skorlu Kaydetme

```python
kaydet_isle("nmap UDP taramasi", "kali/network/nmap", "nmap -sU -T4...", basarili=True)
# → guven_skoru=1.0
```

## kayit_guncelle() — Mevcut Kaydı Güncelle (YENİ KAYIT AÇMA)

Bu session'da öğrenilen kritik teknik. `gorev_sonrasi_hafiza()` yeni kayıt açar. Aynı bilgiyi genişletiyorsan `kayit_guncelle()` kullan.

```python
hafiza.kayit_guncelle(kayit_id=1972, yeni_metadata={
    "kullanim_sayisi": 3, "guven_skoru": 1.0,
    "flag_udp": True, "gecerlilik_tarihi": "2027-06-21"
})
```

## Metadata Şeması

```python
{
    "guven_skoru": 1.0,             # basari/(basari+hata)
    "son_kullanim": "2026-06-21",   # son kullanım
    "kategori": "kali/network/nmap", # görev kategorisi
    "gecerlilik_tarihi": "2026-12-18", # +180 gün varsayılan
    "kullanim_sayisi": 3,           # kaç kez kullanıldı
    "basari_sayisi": 3,
    "hata_sayisi": 0,
}
```

**Güven skoru:** basari/(basari+hata), ikisi de 0 ise 0.5
**Geçerlilik:** bugün < tarih → gecerli, bugün > tarih → gecersiz
**Kategori tahmini:** `_kategori_eslesme()`: "nmap port" → kali/network, "drone" → dron, "solidworks" → cad, "ekran" → windows

## Cross-Agent

```python
cross_agent_ekle("Kali", "/home/kali/hermes_projesi")
bulunanlar = cross_agent_tara("nmap tarama")
```

## Hata Çözüm DB

`.ReYMeN/hata_cozumleri.md` — her yeni hata analiz edilip kaydedilir.

## Test (2026-06-21)

| Test | Sonuç |
|:-----|:------|
| Kategori eşleşme (5 tür) | 5/5 |
| Güven skoru (4 değer) | 4/4 |
| Geçerlilik kontrolü (3 durum) | 3/3 |
| isle() API: hafizada=True, lambda çalışmadı | ✅ |
| isle() hata: kaydedildi | ✅ |
| kaydet_isle() → guven_skoru=1.0 | ✅ |
| kayit_guncelle() → yeni kayıt açılmadı | ✅ |
| 125 Hermes session import (2.6 sn) | ✅ |
| 55 ACP test | PASS |

## İyileştirme 4 — oneri_uret() Belirsiz Görev Tahmini

**Dosya:** `reymen/hafiza/gorev_once_kontrol.py`

Belirsiz görev geldiğinde (örn. "sistemi güvenli yap") direkt LLM'e gitmeden önce hafızaya dayalı tahmin üretir.

```python
from reymen.hafiza.gorev_once_kontrol import oneri_uret

oneri = oneri_uret("sistemi güvenli yap")
# {'oneri_uretilen': True, 
#  'kategori': 'kali/network/nmap',
#  'aciklama': 'port taraması / servis tespiti',
#  'guven_skoru': 0.8,
#  'oneri': '"sistemi güvenli yap" dediniz...'}
```

**Çalışma prensibi:**
1. Selamlaşma kontrolü: sadece selam kelimeleri varsa False döndür
2. 5 kategori ağacı taranır, tetikleyici kelimelere göre adaylar belirlenir
3. Her aday kategori için `hafizada_ara()` çağrılır
4. Puan = kelime_eşleşme × 0.3 + guven_skoru × 0.7
5. En yüksek puan seçilir
6. Kullanıcıya anlamlı bir öneri metni oluşturulur

**Entegrasyon:** conversation_loop.py'de hafıza kontrolü başarısız olunca otomatik çağrılır.
