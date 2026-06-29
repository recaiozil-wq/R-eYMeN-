---
name: claude-code-cli-autonomous
description: "Claude Code CLI (print mode) ile otonom kodlama görevleri — Hermes → Claude Code delegasyonu, onay gerektirmez, planlı çalışma."
title: "Claude Code CLI Autonomous"
version: 1.0.0
author: marko
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [claude-code, cli, agent, autonomous, coding, delegation]
category: autonomous-ai-agents
audience: user
tags: [agents, ai, automation]


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Claude Code CLI (print mode) ile otonom kodlama görevleri — Hermes → Claude Code delegasyonu, onay gerektirmez, planlı çalışma." |
| **Nerede** | `autonomous-ai-agents\autonomous-ai-agents_claude-code-cli-autonomous.md` |
| **Ne Zaman** | Ilgili gorev gerektiginde |
| **Neden** | Autonomous Ai Agents Claude Code Cli Autonomous islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Claude Code CLI (print mode) ile otonom kodlama görevleri — Hermes → Claude Code delegasyonu, onay gerektirmez, planlı çalışma. |
| **Nerede?** | autonomous-ai-agents/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Otonom ajan gelistiricisi
Ne: "Claude Code CLI (print mode) ile otonom kodlama görevleri — Hermes → Claude Code delegasyonu, onay gerektirmez, planlı çalışma."
Nerede: `autonomous-ai-agents\autonomous-ai-agents_claude-code-cli-autonomous.md`
Ne Zaman: Ilgili gorev gerektiginde
Neden: Autonomous Ai Agents Claude Code Cli Autonomous islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Claude Code CLI — Otonom Kodlama Görevleri

## Overview

Hermes, Claude Code CLI'ı (`claude -p` print mode) kullanarak otonom kodlama görevleri yürütür. Print mode **hiçbir onay sormaz** — `--allowedTools` ile izin verilen araçları doğrudan kullanır. VS Code agent modundan daha stabildir.

## Ne Zaman Kullanılır

- Karmaşık kodlama görevleri (modül kurulumu + script yazımı + test)
- Çok adımlı otomasyon (araştır → kodla → test et → raporla)
- Hermes'in yapamayacağı uzun soluklu işlemler (10+ döngü)
- Python modülü kurulumu + test içeren görevler

## Kullanma

```bash
# Temel kullanım
cat <gorev_dosyasi.txt> | claude -p "Gorevi uygula" --allowedTools "Read,Edit,Write,Bash" --max-turns 30
```

### Parametreler

| Parametre | Değer | Açıklama |
|---|---|---|
| `-p` | (flag) | Print mode — non-interactive, onay sormaz |
| `--allowedTools` | `"Read,Edit,Write,Bash"` | İzin verilen araçlar |
| `--max-turns` | 10-50 | Maksimum döngü sayısı |
| `--output-format` | `json` (opsiyonel) | JSON çıktı almak için |
| `--workdir` | (dizin) | Çalışma dizini |

### İzin Verilen Araç Kombinasyonları

| Görev Türü | allowedTools |
|---|---|
| Sadece kod okuma/yazma | `"Read,Edit,Write"` |
| Kod + komut çalıştırma | `"Read,Edit,Write,Bash"` |
| Sadece analiz | `"Read"` |

## Görev Dosyası Formatı

Görev dosyası `.txt` olarak yazılır, `cat` ile pipe edilir:

```txt
Görev: <başlık>
## Hedef
<net açıklama>

## Yapılacaklar
1. <adım 1>
2. <adım 2>
3. <adım 3>

## Notlar
- <önemli bilgiler>
- <dizin yolları>
- <kısıtlamalar>
```

## Örnek: Hermes Agent Toolkit

```bash
cat /c/Users/marko/Desktop/_claude_task.txt | claude -p \
  "Bu gorevi eksiksiz uygula. Once sistemde neler var kontrol et, \
  sonra eksik modulleri kur, sonra test scriptini olustur, sonra test et. \
  Her adimi raporla." \
  --allowedTools "Read,Edit,Write,Bash" \
  --max-turns 30
```

## Claude Code CLI Bilgileri

- **Yol:** `~/.local/bin/claude` (veya `C:\Users\marko\.local\bin\claude`)
- **Sürüm:** 2.1.169
- **Python 3.14** global: `C:\Users\marko\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- **pip:** `C:\Users\marko\AppData\Local\Python\bin\pip`

## Çıktı Formatı

Claude Code bitince şunları döndürür:
1. Yapılan işlemlerin özeti
2. Oluşturulan dosyalar
3. Test sonuçları
4. Varsa hatalar

## İş Akışı

1. Görev dosyasını yaz (`write_file`) — net adımlar, dizin yolları, kısıtlamalar
2. Pipe et: `cat <dosya> | claude -p "görev" --allowedTools "Read,Edit,Write,Bash" --max-turns 30`
   - `timeout=600` kullan (uzun görevlerde)
   - `workdir` parametresini mutlaka ver (örn. `C:\Users\marko`)
3. Çıktıyı oku ve raporla
4. **Post-Execution:** Sonucu değerlendir:
   - Oluşturulan dosyaları kontrol et (var mı, çalışıyor mu)
   - Test sonuçlarını doğrula
   - **skill/memory olarak kaydet** — bu bir kazanımdır
   - Obsidian notu yaz (Hermes Memories/)
5. Claude'ın çıktısını kullanıcıya kısa raporla (tablo tercih edilir)

## Önemli Uyarılar

- `--max-turns` MUTLAKA ayarla (yoksa sonsuz döngü)
- `--allowedTools` ile izinleri kısıtla (gereksiz yetki verme)
- Uzun görevlerde timeout=600 kullan
- Claude Code CLI OAuth ile giriş yapmış olmalı (`claude auth status`)
