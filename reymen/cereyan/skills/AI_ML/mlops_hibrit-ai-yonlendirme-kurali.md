---
name: hibrit-ai-yonlendirme-kurali
title: "Hibrit AI Yönlendirme Kuralı"
description: "Sorgu uzunluğuna ve içeriğine göre Ollama (yerel) veya DeepSeek (uzak) arasında otomatik yönlendirme kuralları."
tags: [routing, model-selection, ollama, deepseek, fallback]
category: mlops
audience: user
related_skills: [hibrit-ai-mimarisi, dolphin-llama3]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Sorgu uzunluğuna ve içeriğine göre Ollama (yerel) veya DeepSeek (uzak) arasında otomatik yönlendirme kuralları. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Hibrit AI Yönlendirme Kuralı

## Ana Kural

| Koşul | Hedef | Açıklama |
|-------|-------|----------|
| <40 kelime, basit sorgu | **Ollama** (dolphin-llama3) | Hızlı, ücretsiz, offline |
| ≥40 kelime veya "analiz/kod/tasarla" içerir | **DeepSeek** (deepseek-chat) | Yüksek kalite, güçlü analiz |
| DeepSeek bağlantısı koparsa | **Ollama** (otomatik fallback) | Kesintisiz hizmet |

## Tetikleyici Kelimeler (DeepSeek'e yönlendirir)
- `analiz`, `analiz et`
- `kod`, `kodla`, `yaz (kod)`
- `tasarla`, `tasarım`
- Uzun metin (>40 kelime) içeren her sorgu
- Çok adımlı planlama gerektiren işler

## Fallback Mekanizması (Gerçek Davranış)

```
1. Varsayılan: Aktif provider (DeepSeek / nous / custom)
2. API hatası → api_max_retries (varsayılan: 3) kere tekrar dene
3. Tüm denemeler başarısız → fallback_providers listesine bak
4. fallback_providers boşsa → hata ver, session düşer
```

**Önemli:** `api_max_retries: 3` + `fallback_providers: []` (boş) birlikte tehlikelidir:
- Kredi bittiğinde DeepSeek "insufficient_quota" döndürür
- Hermes her mesajda 3 kere dener, her seferinde hata alır
- Yedek provider olmadığı için session düşer
- Kullanıcı "Hermes çalışmıyor / hafızasını unuttu" hisseder

**Doğru yapılandırma:**
```yaml
# config.yaml
fallback_providers:
  - provider: custom
    model: dolphin-llama3:latest
    base_url: http://localhost:11434/v1
```

**Pitfall — Kredi vs Bağlantı Hatası:**
- Bağlantı hatası (timeout/DNS): API'ye hiç ulaşılamaz → Ollama'ya düşer
- Kredi bitti/API key geçersiz: API ulaşılabilir ama 401/402/403 döner → api_max_retries'i doldurur, sonra fallback yoksa çöker
- Yeni API key alınınca: Hermes hemen çalışmaya başlar, memory/config kaybolmaz — "unuttu" hissi yanıltıcıdır, aslında sadece provider çalışmıyordur

## Kullanıcı Deneyimi

Kullanıcı farkına varmaz — geçiş otomatiktir.
Sadece her iki model de çökerse bildirim gönderilir.
