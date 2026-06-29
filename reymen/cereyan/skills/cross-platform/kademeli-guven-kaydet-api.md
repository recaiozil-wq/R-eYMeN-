
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Kademeli Guven Kaydet Api |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# `kaydet()` API ve `_kademeli_guven()` Referansı

## `_kademeli_guven(basari, hata)` — Sigmoid Güven Hesaplama

**Dosya:** `reymen/sistem/once_hafiza.py` (class OnceHafiza, static method)
**Karar:** #14 (H9+H10+H16)

### Formül

```python
import math
net = basari - hata - 1
guven = 1.0 / (1.0 + math.exp(-0.5 * net))
```

### Değer Tablosu

| basari | hata | net | guven | Açıklama |
|:-----:|:----:|:---:|:-----:|:---------|
| 1 | 0 | 0 | 0.5000 | İlk kayıt (başlangıç) |
| 2 | 0 | 1 | 0.6225 | 2. başarı |
| 3 | 0 | 2 | 0.7311 | 3. başarı |
| 5 | 0 | 4 | 0.8808 | 5. başarı |
| 10 | 0 | 9 | 0.9890 | 10. başarı |
| 1 | 1 | -1 | 0.3775 | 1 başarı + 1 hata |
| 1 | 3 | -3 | 0.1824 | 1 başarı + 3 hata |
| 5 | 2 | 2 | 0.7311 | 5 başarı + 2 hata |

### Özellikler

- İlk kayıt asla 1.0 olmaz (eski: 1.0 → yeni: 0.5, Karar #14)
- Hata başına güven düşüşü, başarı başına artıştan daha sert (sigmoid simetrik değil)
- 10 başarıdan önce 1.0 olmaz (eski: linear 1 basari + 0 hata = 1.0)
- `min_guven=0.5` başlangıç (eski: min_guven yoktu, direkt 1.0)

## `kaydet()` API

### Modül-level (standalone)

```python
from reymen.sistem.once_hafiza import kaydet

kaydet(
    hedef="görev tanımı",           # str, zorunlu
    cozum="çözüm içeriği",          # str, zorunlu
    kategori="kali/network/nmap",   # str, opsiyonel
    kaynak="web | video | kesif",   # str, opsiyonel (default: "kesif")
    kaynak_url="https://...",       # str|None, opsiyonel
)
```

### Class-level

```python
from reymen.sistem.once_hafiza import OnceHafiza
oh = OnceHafiza()
oh.kaydet(
    hedef="görev",
    cozum="çözüm",
    kategori="kali/network/nmap",
    kaynak="web",
    kaynak_url="https://nmap.org/docs.html"
)
```

### Geriye Dönük Uyumluluk

Eski çağrılar (`kaydet(hedef, cozum, kategori)`) çalışmaya devam eder.
`kaynak_url=None` varsayılan değerdir.

### Davranış

1. Aynı `hedef + kategori` varsa → UPDATE (basari_sayisi++, guven yeniden hesaplanır)
2. Yoksa → INSERT (guven=0.5 başlangıç)
3. `kaynak_url` UPDATE'te `COALESCE(?, kaynak_url)` ile korunur (null gönderilmezse eski korunur)
