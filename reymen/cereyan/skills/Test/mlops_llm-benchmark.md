---
name: llm-benchmark
description: LLM model karsilastirma benchmark'i. DeepSeek, Groq modellerini hiz/dogruluk/tutarlilik acisindan test eder. Yeni model eklendiginde guncelle.
title: "LLM Benchmark"
category: mlops
audience: user
tags: [ai, benchmark, machine-learning, mlops]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | LLM model karsilastirma benchmark'i. DeepSeek, Groq modellerini hiz/dogruluk/tutarlilik acisindan test eder. Yeni model eklendiginde guncelle. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# LLM Benchmark — Scaling Laws Test

## Ne Yapar
Elimizdeki tüm LLM'leri (DeepSeek, Groq, Ollama) aynı test seti üzerinde çalıştırıp hız, doğruluk, tutarlılık ve maliyet açısından sıralar.

## Ne Zaman Kullanılır
- Yeni bir model/provider eklendiğinde
- Model değişikliği sonrası performans düşüşü kontrolü
- Hangi modelin hangi task için uygun olduğuna karar vermek

## Kullanım
```bash
cd /c/Users/marko/Desktop/benchmark
python benchmark_v1.py
```

## Test Seti (20 soru)
- Kod (5): regex, privilege escalation, hash, list reverse, decorator
- Mantık (5): lamba problemi, market sorusu, saat açısı, tavşan-tavuk, fibonacci
- Güvenlik (5): SQL injection, netstat, XSS, port scan, jailbreak
- Bilgi (5): başkent, HTTP 404, chmod, RAM vs ROM, asal sayı

## Her Model İçin Ölçülenler
- Latency (ms) — ortalama yanıt süresi
- Doğruluk (%) — anahtar kelime eşleşme skoru (0-100)
- Tutarlılık (%) — 2 tekrarda aynı skor
- Hata sayısı — rate limit / timeout / API hatası

## Mevcut Sonuçlar (13.06.2026)
| Sıra | Model | Doğruluk | Hız | Hata |
|------|-------|----------|-----|------|
| 1 | DeepSeek v4 Flash | %88.3 | 3590ms | 0 |
| 2 | Groq Llama 3.3 70B | %66.4 | 826ms | 9 |
| 3 | Groq Llama 4 Scout | %59.7 | 526ms | 9 |
| 4 | Groq Llama 3.1 8B | %32.0 | 259ms | 30 |
| 5 | Groq Qwen3 32B | %25.2 | 413ms | 29 |

## Güncelleme
Yeni model eklemek için:
1. `references/benchmark_v1.py` — MODELS listesine yeni giriş ekle
2. `references/test_set.json` — gerekirse soru ekle/çıkar
3. `python benchmark_v1.py` çalıştır
4. Sonuçları bu skill'in "Mevcut Sonuçlar" bölümüne yaz

## Yaygın Hatalar (Pitfalls)

### Groq model adları sık değişir
Groq, model adlarını sık günceller. Eski adlar (`mixtral-8x7b-32768`, `gemma2-9b-it` vb.) çalışmayabilir.
**Belirti:** Tüm sorularda hata (40/40), `HTTP 404`.
**Çözüm:** Koşturmadan önce mevcut model listesini kontrol et:
```bash
curl -s "https://api.groq.com/openai/v1/models" -H "Authorization: Bearer $GROQ_KEY" | python -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin).get('data',[])]"
```
Script'teki MODELS listesini güncel listeyle eşleştir.

### DeepSeek model adı deprecation
`deepseek-chat` 2026/07/24'te kullanımdan kalkıyor. Yerine `deepseek/deepseek-v4-flash` kullan.

### Rate limiting
Groq ücretsiz kullanımda rate limit düşüktür. 20+ soruda 8-9 hata almak normaldir.
Hata sayısı yüksekse (>5) önce model adını kontrol et, rate limit ise 2. çalıştırmada aynı seviyede kalır.

### API anahtarı yoksa model atlanır
Script, API_KEY boşsa o modeli atlar. `.env` dosyasının güncel olduğunu doğrula.

## Bağımlılıklar
- requests (API çağrıları)

## Dosyalar
- `references/benchmark_v1.py` — ana benchmark script'i
- `references/test_set.json` — 20 soruluk test seti
- `references/provider-models.md` — güncel model listesi çekme yöntemleri
