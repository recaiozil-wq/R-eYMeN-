
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Memory Management Pattern |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Memory Yönetimi — Consolidation Pattern

## Ne Zaman

Hermes memory limiti 50K'ya çıktı ama yine de dolabilir. Her session'da memory'ye eklenen bayat entry'ler (teknik test detayları, eski session notları, tamamlanmış iş kayıtları) zamanla birikir.

## Consolidation Sinyalleri

- `memory` tool'u "Memory at X/Y chars" hatası veriyor
- Aynı konuda birden çok entry var (ör: 37 tane test coverage entry'si)
- Eski tarihli entry'ler (>1 hafta) hala duruyor ama artık skill'de kayıtlı

## Adımlar

### 1. Bayat Entry'leri Belirle

Şu tür entry'ler silinebilir:
- **Session-specific test sonuçları:** `test_X.py -> 55 test, tamami PASS`
- **Eski API değişiklikleri:** `sistem_talimati.py API refactored (2026-06-20)`
- **Tamamlanmış fix'ler:** `8-process 409 Conflict root cause`
- **Artık skill'de olan bilgiler:** eğer skill'de kayıtlıysa memory'den sil

### 2. Batch Operation Kullan

Tek seferde birden çok entry'yi sil/ekle/değiştir:

```python
memory(action='add', target='memory', operations=[
    # Sil — old_text eşleşmesi İLK KARAKTERDEN itibaren tam olmalı
    {"action": "remove", "old_text": "test_learning_loop_ek.py: closed_learning_loop.py icin"},
    
    # Kısalt — replace, eski uzun metin → yeni kısa metin
    {"action": "replace",
     "content": ".env kuralı: write_file KULLANMA (siler). terminal echo >> yap.",
     "old_text": "Profil .env'lerine asla write_file() kullanma..."},
     
    # Ekle — yeni kural/bilgi
    {"action": "add", "content": "KONTROL KURALI: ..."},
])
```

### 3. old_text Eşleşmesi — Kritik Detay

Eşleşme **tam metin değil, substring**. Şu kurallar geçerli:

```
Entry: "sistem_sinyalleri.py bug fixes: (1) kaydet() shutdown guard..."
old_text: "sistem_sinyalleri.py bug fixes: (1)"  ✅ ESLEŞİR
old_text: "sistem_sinyalleri.py bug fixes"         ✅ ESLEŞİR
old_text: "shutdown guard"                         ✅ ESLEŞİR
old_text: "bug fixes"                               ✅ ESLEŞİR (tek entry'de varsa)
```

**Ancak** — redacted token'lar (***) ile eşleşme YAPMAZ:

```
Entry: "... ReYMeN bot token: 8774151638:AAFNMVK12XjC..."  
old_text: "8774151638:***"  ❌ ESLEŞMEZ
old_text: "8774151638:"     ✅ ESLEŞİR (tireye kadar)
```

### 4. Replace vs Remove

| İşlem | Kullanım |
|:------|:---------|
| **remove** | Entry tamamen silinecekse |
| **replace** | Entry kısaltılacaksa (content + old_text) |
| **add** | Yeni entry eklenecekse |

replace için `new_text` değil `content` kullan — `new_text` patch tool'una ait.

### 5. Batch all-or-nothing

Tüm operation'lar ya hep ya hiç uygulanır. Biri başarısız olursa hiçbiri uygulanmaz. Bu yüzden:

- ÖNCE en riskli eşleşmeyi test et (küçük batch dene)
- Her batch'te old_text'leri dikkatlice kontrol et
- Eşleşme bulamazsa hata döner: "Operation N: no entry matched"

## Gerçek Hayat Örneği (2026-06-21)

**Önce:** 12.280/2.200 chars (%558) — 47 entry, çoğu bayat
**Sonra:** 1.429/2.200 chars (%64) — 9 entry, kaliteli
**Kazanç:** ~10.850 karakter (%88 azalma)

| Adım | İşlem | Entry Sayısı |
|:----:|:------|:------------:|
| 1 | 37 stale entry sil | 47 → 10 |
| 2 | 2 uzun entry kısalt | ~800 → ~150 |
| 3 | 1 yeni kural ekle | 10 → 11 |
| **Toplam** | **40 işlem** | **12.280 → 1.429** |
