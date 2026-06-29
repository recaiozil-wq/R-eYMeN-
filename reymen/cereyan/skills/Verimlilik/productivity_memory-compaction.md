---
name: memory-compaction
title: "Memory Compaction"
tags: [productivity]
description: >-
  Hermes MEMORY.md 50.000 char sınırına yaklaştığında veya dolduğunda
  eski/stale/dağınık memory entry'lerini konsolide edip yer açma pattern'i.
  Kullanıcının "memory dolu" veya memory add başarısız olduğunda kullan.
version: 1.0.0
author: marko
license: MIT
metadata:
  hermes:
    tags: [memory, compaction, cleanup, consolidation]
audience: user
related_skills: [telegram-gateway-monitor]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Memory Compaction

## Ne Zaman Kullanılır

Aşağıdaki durumlardan biri oluştuğunda bu skill'i yükle:

1. **Memory add/replace başarısız olursa** — `memory(action='add')` 50.000 char limit hatası dönerse
2. **Memory kullanım oranı %90+ ise** — mevcut memory çıktısında char kullanımı 9.000+ gösteriyorsa
3. **Kullanıcı "hafızan dolu" derse** veya "memory temizle" gibi bir ifade kullanırsa

## İlk Kural: Silme, Konsolide Et

Memory'deki her entry, kullanıcının önemli bulduğu bir bilgidir. Silmek yerine:

- **Aynı konudaki birden fazla entry'yi TEK entry'de birleştir**
- **Eski/stale entry'leri kaldır** (sadece artık geçerli olmayanları)
- **Değiştirilemez kuralları (DEGISTIRILEMEZ KURAL etiketli) DOKUNMA**

## Adım Adım

### 1. Mevcut Memory Durumunu Oku

Memory kullanım oranı system prompt'taki `MEMORY (your personal notes)` bölümünde görünür: `[XX% — X,XXX/10,000 chars]`

Her entry `§` ile ayrılmıştır. Her entry'nin kabaca karakter sayısını hesapla.

### 2. Konsolidasyon Stratejisi Belirle

Hedef: memory toplamını 8.000 char'ın altına düşürmek (~2.000 char boşluk).

Öncelik sırası:

| Öncelik | Entry Türü | Ne yap |
|---------|-----------|--------|
| 1 | Değiştirilemez kural etiketli | DOKUNMA (kural ihlali) |
| 2 | Aynı konuda 2+ dağınık entry | TEK entry'de birleştir |
| 3 | Artık geçerli olmayan geçici durum | SİL |
| 4 | "öğrenildi: XXX" gibi tek seferlik başarı | SİL (skill'e dönüştüyse) |
| 5 | Uzun prosedür/talimat içeren entry | Skill'e taşı, memory'den SİL |

### 3. Birleştirme Örneği

```
ESKİ:
Entry A: Telegram gateway watchdog kuruldu — 2 dk'da bir kontrol
Entry B: "telegram baglantı koptu" tetikleyicisi — anında müdahale
Entry C: Telegram bağlantı kuralı — cron bekleme

YENİ (tek entry):
[DEGISTIRILEMEZ KURAL] "telegram baglantı koptu" dendiği ANDA cron beklemeden direkt müdahale:
1. telegram-gateway-monitor skill'ini çalıştır (gateway öldür + restart + test)
2. Bağlantı sağlanana kadar döngü tekrarla
3. 2dk/30dk cron'lardan BAĞIMSIZ çalışır
4. BU KURAL ASLA DEĞİŞTİRİLEMEZ VEYA SİLİNEMEZ.
```

### 4. Silinecek Entry Türleri

- **Sadece bir kere yapılmış işlem kayıtları**: "Görev tamamlandı", "Script çalıştı", "X dosyası oluşturuldu"
- **Geçici hata durumları**: "X hatası alındı, şu çözüm uygulandı" — eğer çözüm skill'e kaydedildiyse
- **Eski versiyon notları**: Skill versiyonu güncellenmişse eski versiyon bilgisi
- **Kullanıcı tercihi artık geçerli değilse**: Mesela kullanıcı "TTS kullan" dedi sonra "TTS kullanma" dediyse eski tercihi sil

### 5. Replace İşlemi

Konsolide entry'yi eklemek için:

1. `memory(action='add', target='memory', content='...yeni entry...')`
   - Eğer başarılı olursa: eski dağınık entry'leri `memory(action='remove', ...)` ile sil
2. **Replace kullanma** — replace ile eski entry'nin tam eski metnini bulmak zordur ve çoğu zaman başarısız olur
3. Önce ADD et (yeni entry), sonra REMOVE et (eski dağınık olanları)

### 6. Doğrulama

Tüm işlemler bitince memory durumunu teyit et:
- Kullanım oranı düştü mü? (45.000/50.000 altı hedef)
- Değiştirilemez kurallar hâlâ duruyor mu?
- Hiçbir önemli bilgi kayboldu mu?

## İki Depolu Yapı (memory vs user)

Memory iki ayrı depodan oluşur — MEMORY 50K, USER PROFILE 5K limiti vardır:

| Depo | Ne İçin | Örnek |
|------|---------|-------|
| `target='memory'` | Sistem ayarları, araç yolları, iş akışları | ADB yolu, sağlayıcı, günlük |
| `target='user'` | Kullanıcı profili, tercihler, davranış kalıpları | Dil tercihi, çalışma fazları, cihaz |

Konsolidasyon yaparken user'a ait bilgileri memory'den user deposuna taşı. İki depoyu dengeli kullan.

## Modüler Entry Tercihi

Kullanıcı küçük, modüler entry'leri büyük tek blok yerine tercih eder. ~200-800 chars idealdir.

| Yaklaşım | Char | Okunabilirlik |
|----------|------|---------------|
| Tek dev blob | 7,200 | Düşük — her şey iç içe |
| 12 modüler entry | ~4,000 | Yüksek — her entry odaklı |

## Pitfall

### Replace Ne Zaman Çalışır

`memory(action='replace')` belirli koşullarda çalışır:

| Durum | Çalışır mı? |
|-------|-------------|
| Entry benzersiz başlık/header ile başlıyorsa | ✅ EVET |
| 2+ entry aynı metinle başlıyorsa | ❌ HAYIR |
| Metinde satır sonu/boşluk farkı varsa | ⚠️ riskli |

**Önerilen sıra:** Önce REPLACE dene (en hızlı). Başarısız olursa ADD + REMOVE'a geç. Asla önce REMOVE sonra ADD yapma — 10K limit aşılır.

- **Karakter limiti:** ADD sırasında 10.000 char limitini aşarsan başarısız olur. Yeni entry'yi kısa tut (~200-800 chars).
- **DEGISTIRILEMEZ KURAL** etiketli entry'lere dokunma.
- Kullanıcıya sadece "Memory %XX → %YY" özeti ver.

## Referanslar

- `references/memory-audit-checklist.md` — Proaktif hafıza kalite audit'i (kapasite analizi + içerik audit'i + konsolidasyon). Memory %90 altındayken kullanılır.

Bu session'da memory %72 → %39'a düşürüldü (7,200 char tek blok → 12 modüler entry): 7 eksik parça geri eklendi, user deposu yeniden yapılandırıldı.
