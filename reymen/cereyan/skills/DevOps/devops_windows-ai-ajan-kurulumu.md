---
name: windows-ai-ajan-kurulumu
title: Windows AI Ajan Kurulumu
description: Windows'ta AI ajani kurulumu, LM Studio ayarlari, .bat baslatici, pip/venv yonetimi
tags: [windows, lm-studio, ai-agent, setup]
audience: user
---


> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows'ta AI ajani kurulumu, LM Studio ayarlari, .bat baslatici, pip/venv yonetimi |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows AI Ajan Kurulumu

## Gerekliler
- Python 3.11+ (python.org)
- LM Studio (lmstudio.ai)

## Adimlar
1. pip install -r requirements.txt
2. LM Studio'yu ac, model yukle (dolphin3.0-llama3.1-8b), server baslat (localhost:1234)
3. .env dosyasina API anahtarlarini yaz
4. reyemen.bat start ile calistir

## Puf Noktalari
- LM Studio `system` mesaji kabul etmez → `user`'a cevir (beyin.py)
- .bat dosyasi shebang gerektirmez, direkt `python main.py` calistirir
- `***` maskeli env degerleri `startswith("***")` ile kontrol edilmeli — tam esitlik (`== "***"`) yetmez
- JSON yazma yarisi icin `FileLock` kullan
- .env dosyasi Python ile yazilmalı (PowerShell/Pipe ile tirnak sorunu)
- Provider fallback zinciri: LM Studio → DeepSeek → OpenAI/Anthropic/Groq
- `setup_keys.py --kontrol` ile hangi provider'larin aktif oldugunu gorebilirsin

## Kullanici Tercihleri (Unutmaman Gerekenler)
- `sorma`: karar gerekiyorsa en mantikli secenegi kendin sec, uygula, sonra haber ver
- `bekleme`: isi background'da baslat, hemen cevap ver
- `arkada calissin`: terminal(background=true, notify_on_complete=true) kullan
- detayli analiz yap: yuzeysel grep yerine satir satir oku, import zincirini kontrol et
- XRAY protocolu uygula: once dosya yapisi, sonra import zinciri, sonra runtime test
