
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Reymen Vs Hermes Karsilastirma |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# ReYMeN vs Varsayılan LLM (Hermes) Karşılaştırması

Bu tablo, ReYMeN (OnceHafiza sistemi) ile varsayılan LLM ajanı arasındaki farkları özetler. Kullanıcının Telegram'da gönderdiği analiz ekran görüntülerinden derlenmiştir.

## Özet Tablo

| Boyut | ReYMeN | Varsayılan LLM (Hermes) |
|:------|:-------|:------------------------|
| **Mimari** | Mühendislik: hafıza öncelikli, LLM son çare | LLM merkezli: her adım LLM |
| **Maliyet** | Düşük (cache + LLM'siz kararlar) | Yüksek (her şey LLM'den geçer) |
| **Hız** | Hızlı (cache'ten direkt) | Yavaş (LLM her turu bekler) |
| **Tutarlılık** | Yüksek (SQLite, kurallı) | Düşük (LLM rastgele) |
| **Esneklik** | Düşük (kurallar kısıtlar) | Yüksek (LLM her şeyi yapabilir) |
| **Unutkanlık** | Az (SQLite kalıcı) | Çok (yeni oturumda her şey unutulur) |
| **Retry garantisi** | Var (3 retry + circuit breaker) | Yok (LLM karar verir, sınırsız dener) |
| **Tool çeşitliliği** | Çok (50+ sabit + runtime + 80+ plugin) | Az (system prompt'taki kadar) |
| **Cross-oturum** | ✅ Dünkü bilgiyi bugün kullanır | ❌ Yeni oturumda her şeyi unutur |

## Karar Ağacı Karşılaştırması

### ReYMeN (Hafıza-Öncelikli)
```
Görev gelir
  ↓
ÖNCE HAFIZA (guven > 0.8?) → direkt döndür, 0 LLM
  ↓ (bulamazsa)
SONRA CACHE (selam/teşekkür?) → direkt döndür, 0 LLM
  ↓ (yoksa)
EN SON LLM → 90 tur max, 3 retry, CB kalıcı
```

### Varsayılan LLM (Hermes)
```
Görev gelir
  ↓
LLM düşünür: "Bu görev için hangi araçları kullanmalıyım?"
  ↓
Araçları seçer ve çağırır
  ↓
LLM: "Sonuç yeterli mi? Devam mı?"
  ↓
Gerekirse yeni araçlar seçer
  ↓
Kullanıcıya cevap döndürür
```

## LLM Çağrısı Karşılaştırması

| Durum | ReYMeN | Varsayılan LLM |
|:------|:-------|:----------------|
| Hafızada bilgi var (guven > 0.8) | ❌ LLM çağrılmaz | ✅ LLM çağrılır (memory okur, yine de düşünür) |
| Hafıza boş | ✅ LLM çağrılır | ✅ LLM çağrılır |
| Hata analizi | ❌ LLM'siz (regex + skor bazlı) | ✅ LLM hata mesajını okur, karar verir |
| Basit hesaplama | ❌ execute_code ile brute force | ✅ LLM'den geçer |
| "Merhaba" dediğinde | ❌ Cache'ten direkt | ✅ LLM selamı bile LLM'den |
| **Toplam LLM çağrısı** | **Minimum (sadece gerekli)** | **%100 her adım** |

## Araç Seçimi

| Özellik | ReYMeN | Varsayılan LLM |
|:--------|:-------|:----------------|
| Araç listesi | 50+ sabit + runtime üretim | ~30 araç system prompt'ta |
| Dinamik üretim | ✅ ARAC_URET ile runtime | ❌ Yok |
| Plugin modüller | ✅ 80+ plugin dinamik yük | ❌ Yok |
| check_fn | ✅ Ortama göre filtreleme | ❌ Yok |
| Her tur güncelleme | ✅ Yeni araç anında görünür | ❌ Her restart gerek |
| Tool seçimini yapan | LLM (ama kısıtlı liste) | LLM |
| Tool şeması | Native function calling + metin | Native function calling |
| Alt-ajan delegasyonu | ✅ delegate_task ile | ❌ Yok |

## Retry Sistemi

| Özellik | ReYMeN | Varsayılan LLM |
|:--------|:-------|:----------------|
| Maks deneme | 3 (mekanik) | Sınırsız (LLM karar verir) |
| Araç hatasında | Hata mesajını LLM'siz analiz et | LLM okur, alternatif dener |
| Örn: nmap yoksa | netstat dener (önceden tanımlı) | LLM: "nmap yok, netstat deneyeyim" |
| Circuit breaker | 3 hata → kalıcı dur | Yok |
| Budget | 90 tur max | Yok (LLM pes edene kadar) |

## ReYMeN'in En Büyük Avantajı

**Cross-oturum hafıza.** Varsayılan LLM bir sonraki oturumda her şeyi unutur:
- Kullanıcı aynı şeyi tekrar sorarsa → aynı LLM maliyetini tekrar öder
- ReYMeN SQLite sorgular → 5 saniyede cevap verir → sıfır maliyet

**Belirsiz görev tahmini (İyileştirme 4):**
ReYMeN "sistemi güvenli yap" gibi belirsiz bir girdiyi hafızasına danışarak yorumlar:
- Hafızada kali/network/nmap bilgisi var → "Port taraması mı demek istiyorsunuz?" diye sorar
- Varsayılan LLM ise direkt LLM'e gider, hafıza bağlamı olmadan cevap üretir

## Varsayılan LLM'in Kendi İtirafı
> Bir sonraki oturumda her şeyi unuturum. Kullanıcı aynı şeyi tekrar sorarsa, aynı LLM maliyetini tekrar öderim. ReYMeN SQLite'i sorgular, 5 saniyede cevap verir, sıfır maliyet.
