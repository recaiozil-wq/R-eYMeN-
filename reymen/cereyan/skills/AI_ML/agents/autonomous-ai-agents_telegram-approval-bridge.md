---
name: telegram-approval-bridge
description: Multi-model LLM bridge with file-based Telegram approval gates. Use when the user wants alternating Claude+Ollama reasoning with manual 'devam/dur' control between turns.
title: "Telegram Approval Bridge"
version: 1.0.0
author: Hermes Agent + User
license: MIT
metadata:
  hermes:
    tags: [bridge, approval, claude, ollama, telegram, file-signal]
category: autonomous-ai-agents
audience: user
tags: [agents, ai, automation, telegram]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Multi-model LLM bridge with file-based Telegram approval gates. Use when the user wants alternating Claude+Ollama reasoning with manual 'devam/dur' control between turns. |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_telegram-approval-bridge.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Telegram Approval Bridge islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Multi-model LLM bridge with file-based Telegram approval gates. Use when the user wants alternating Claude+Ollama reasoning with manual 'devam/dur' control between turns. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: Multi-model LLM bridge with file-based Telegram approval gates. Use when the user wants alternating Claude+Ollama reasoning with manual 'devam/dur' control between turns.
Nerede: `autonomous-ai-agents\autonomous-ai-agents_telegram-approval-bridge.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Telegram Approval Bridge islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Telegram-Onaylı LLM Köprü

İki LLM arasında dönüşümlü problem çözme + her turda insan onayı (file-signal üzerinden). `bridge_tg.py` üzerinden çalışır.

## Kullanım

### Gereksinimler
- `claude` CLI kurulu ve PATH'te
- `ollama` + hedef model çekirdekte (`ollama list` ile doğrula)
- Masaüstü yazma izinleri: `C:\Users\marko\Desktop\`

### Çalıştırma
```bash
python C:\Users\marko\Desktop\bridge_tg.py
```

### Akış
1. Script ilk turda `bridge_status.txt` yazar.
2. Hermes/Ollama cevaplarını okuyarıp Telegram ile paylaş.
3. Kullanıcı `devam` (devam) veya `dur` (durdur) der.
4. `C:\Users\marko\Desktop\bridge_signal.txt` dosyasına yaz (sadece `devam` veya `dur`, küçük harf).
5. Script sinyali okur, yükümlüyü siler, bir sonraki tura geçer.
6. Tüm loglar bittiğinde Hem Hermes skill klasörüne Hem Obsidian Vault'a yazılır.

### Güvenlik
- `MAX_TURN=5`, zaman aşımı `300sn` → otomatik `dur`.
- Yalnızca dosya tabanlı iletişim; ağ/port yok.

## Yapılandırma

`bridge_tg.py` içindeki sabitler:
- `OLLAMA_MODEL` → kullanılacak Ollama modeli (ör: `dolphin-llama3:latest`)
- `signal_file` / `status_file` → masaüstü yolları
- `MAX_TURN` → maksimum tur sayısı

## Çıktılar
- Skill: `C:\Users\marko\AppData\Local\hermes\skills\telegram-onayli-kopru.md`
- Obsidian: `C:\Users\marko\OneDrive\Belgeler\Obsidian Vault\Telegram Kopru.md`

## Pitfall
- `bridge_signal.txt` içine başka bir şey yazma; "devam"/"dur" dışında algılanmaz.
- Script çalışırken dosyaları elle silme; çakışma olur.
