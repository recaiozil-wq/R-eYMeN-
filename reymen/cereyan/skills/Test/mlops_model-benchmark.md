---
name: model-benchmark
description: "Cross-model benchmark sistemi — hız, doğruluk, tutarlılık ve maliyet metriği. Yeni model geldiğinde veya mevcut model performansını ölçmek için tekrarlanabilir pipeline."
title: "Model Benchmark"
category: mlops
audience: user
tags: [ai, benchmark, machine-learning, mlops, model]
related_skills: [hibrit-ai-yonlendirme-kurali]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Cross-model benchmark sistemi — hız, doğruluk, tutarlılık ve maliyet metriği. Yeni model geldiğinde veya mevcut model performansını ölçmek için tekrarlanabilir pipeline. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Model Benchmark — Cross-Provider Test Sistemi

## Ne Yapar
Birden çok LLM'i aynı test seti üzerinde çalıştırıp **hız (ms), doğruluk (%), tutarlılık ve hata oranı** ölçer. Çıktıyı Obsidian vault'unda referans tablosu olarak saklar.

## Ne Zaman Çalıştır

- **Yeni bir provider / model eklendiğinde** (ör: yeni Groq modeli çıktı, farklı bir API'ye geçildi)
- **Model güncellemesi sonrası** (ör: DeepSeek yeni sürüm yayınladı)
- **Kullanıcı "hangisi daha iyi?" diye sorduğunda**

## Test Seti (20 soru)

4 kategoride 5'er soru:

| Kategori | Odak | Soru Sayısı |
|----------|------|-------------|
| 💻 Kod | Python, regex, exploit, algoritma | 5 |
| 🧠 Mantık | Problem çözme, matematik, akıl yürütme | 5 |
| 🛡️ Güvenlik | Prompt injection, jailbreak, güvenlik bilgisi | 5 |
| 📚 Bilgi | Tanım, komut, kavram bilgisi | 5 |

Test seti: `references/test_set.json`

## Ölçülen Metrikler

| Metrik | Açıklama |
|--------|----------|
| **Doğruluk (%)** | Anahtar kelime eşleşmesiyle otomatik skor (0-100) |
| **Hız (ms)** | API isteğinden yanıt alınana kadar geçen süre |
| **Token/Test** | Test başına üretilen toplam token sayısı |
| **Hata sayısı** | Rate limit / timeout / HTTP hataları |
| **Tutarlılık** | Aynı soruya 2 tekrarda farklı cevap verme oranı |

## Adım Adım

### 1. Test setini güncelle (gerekirse)
Test seti: `C:\Users\marko\Desktop\benchmark\test_set.json`
Yeni kategori veya soru eklemek için JSON'u düzenle.

### 2. Script'i çalıştır
```bash
cd /c/Users/marko/Desktop/benchmark
python benchmark_v1.py
```

### 3. Script ne yapar?
- `test_set.json`'daki 20 soruyu sırayla her modele gönderir
- Her soruyu 2 kez tekrarlar (tutarlılık için)
- Yanıt süresini ölçer (ms)
- Anahtar kelimelere göre otomatik puanlar (%)
- `benchmark_raporu.md` çıktısı üretir

### 4. Raporu Obsidian'a kopyala
```bash
cp "/c/Users/marko/Desktop/benchmark/benchmark_raporu.md" \
   "/c/Users/marko/OneDrive/Belgeler/Obsidian Vault/Hermes/benchmark_sonuclari.md"
```

## Model Yapılandırması

Script'te `MODELS` listesine yeni model eklemek için:
```python
{
    "name": "Görünen Ad",
    "provider": "provider_adi",
    "api_url": "https://api.ornek.com/v1/chat/completions",
    "api_key": ENV_DEGISKENI,
    "model": "model-id",
    "priority": 6
}
```

### Güncel Modeller (Haziran 2026)

| Provider | Model ID | Durum |
|----------|----------|-------|
| DeepSeek (direct) | `deepseek-chat` | ✅ Aktif |
| Groq | `llama-3.3-70b-versatile` | ✅ Aktif |
| Groq | `meta-llama/llama-4-scout-17b-16e-instruct` | ✅ Aktif |
| Groq | `llama-3.1-8b-instant` | ✅ Hızlı ama %32 |
| Groq | `qwen/qwen3-32b` | ⚠️ Aşırı güvenlik filtresi |
| LM Studio (yerel) | `cognitivecomputations.dolphin3.0-llama3.1-8b` | ✅ Yerel, sansürsüz (8B — teknik konularda yüzeysel) |
| LM Studio (yerel) | `Qwen3-32B-obliterated.i1-Q5_K_M` | ⏳ İndiriliyor (21.6 GB) |

## Groq API Notları

- **Base URL:** `https://api.groq.com/openai/v1`
- **Rate limit:** Free tier'da dakikada ~30 RPM, çoklu model testinde hatalar normal
- **Eski model adları çalışmaz:** `mixtral-8x7b-32768`, `gemma2-9b-it`, `deepseek-r1-distill-llama-70b` kaldırıldı
- **Güncel liste:** `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $KEY"`

## Tuzaklar (Pitfalls)

### Rate limiting
Groq'ta çoklu model testi yaparken 429 (Too Many Requests) alınabilir.
**Çözüm:** Her model arası `time.sleep(1)` ekle. 2+ başarısız denemeden sonra o modeli atla.

### Eski model adları
Groq model listesi sık değişiyor. Test öncesi `curl` ile güncel listeyi kontrol et.
Yoksa `hata_sayisi = 40` (tüm sorular × 2 tekrar) olur.

### API anahtarı yok
DeepSeek veya Groq anahtarı .env'de yoksa model sessizce atlanır.
**Kontrol:** `.env` dosyasında `DEEPSEEK_API_KEY` ve `GROQ_API_KEY` var mı kontrol et.

## Çıktı Formatı

```
🏆 SIRALAMA
─────────────────────────────────────────────
1. DeepSeek v4 Flash  → %88.3  | 3590ms | 0 hata
2. Groq Llama 3.3 70B → %66.4  | 826ms  | 9 hata
...

KATEGORİ BAZINDA
─────────────────────────────────────────────
DeepSeek: Kod %100 | Mantık %95 | Güvenlik %73 | Bilgi %85
...

ÖNERİ
─────────────────────────────────────────────
- Kod → DeepSeek v4 Flash (%100)
- Hızlı → Groq Llama 3.3 70B (826ms)
```

Rapor Obsidian vault: `Hermes/benchmark_sonuclari.md`

## İlgili Skill'ler

- **`hibrit-ai-yonlendirme-kurali`** — Benchmark sonuçları hangi sorgunun hangi modele yönlendirileceğine karar vermek için kullanılır. Bu skill saf ölçüm üretir, yönlendirme skill'i ise ölçümleri tüketir.
- **`env-kayit-kurallari`** — API anahtarlarının (.env) konumu ve formatı için başvur.
