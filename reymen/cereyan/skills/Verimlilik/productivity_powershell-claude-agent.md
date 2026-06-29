---
name: powershell-claude-agent
title: "PowerShell ile Claude Agent Başlatma"
description: "Windows'ta PowerShell üzerinden Claude Code CLI'ını (agent modunda) başlatma ve doğrulama adımları."
tags: [powershell, claude, windows, claude-code, agent]
category: productivity
audience: user
triggers: [claude agent, claude code, claude baslat, Claude CLI]
related_skills: [claude-agent-terminal-send-text]
---


> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Windows'ta PowerShell üzerinden Claude Code CLI'ını (agent modunda) başlatma ve doğrulama adımları. |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# PowerShell ile Claude Agent Başlatma

## Kullanıcı tercihi
- Tekrar tekrar onaylama yapma; durumu kendisi takip ediyor.
- Açıklamaları kısa tut, sonuca odaklan.
- Bekleme süreci takıldığında çözüm üret; aynı hatayı tekrar etme.
- Odaklanma engeli durumunda ekran görüntüsü al ve "Bulundu / Bulunamadı" şeklinde durumu raporla.

## Ön koşul
- Node.js v18+ ve npm kurulu olmalı.
- Claude Code kurulu değilse: `npm install -g @anthropic-ai/claude-code`.
- Windows'ta odaklanma engeli: VBS betiklerini kullanmak daha garantilidir.

## Ön koşul
- Node.js v18+ ve npm kurulu olmalı.
- Claude Code kurulu değilse: `npm install -g @anthropic-ai/claude-code`.

## Adımlar

1. **PowerShell'i aç**
   - `Win + X` → Windows PowerShell

2. **Exec. politikasını bypass et**
   - `powershell -ExecutionPolicy Bypass -Command "claude --version"`

3. **Claude'u doğrudan başlat**
   - CLI'de bazen stdin beklenir. Aşağıdakileri sırasıyla dene:
     - `claude`
     - `echo "" | claude`
     - `& "$env:APPDATA\npm\claude.cmd"` (full path)

4. **Kurulu değilse ve Node.js yoksa**
   - https://nodejs.org adresinden LTS sürümü kur.
   - Sonra `npm install -g @anthropic-ai/claude-code`.

5. **Agent modunda olup olmadığını kontrol et**
   - Claude ekranında slas komutları (`/code-review`, `/verify`, `/run`) görünüyorsa agent modu aktiftir.

## Bilinen sorunlar
- PowerShell'de npm çalışmıyorsa exec. politikası engelidir. Bypass kullan.
- `claude` komutu `Input must be provided` hatası verirse `echo "" | claude` ile aç.
- `$env:APPDATA\npm\claude.cmd` yolunu kontrol et; PowerShell env expansion yoksa direkt `C:\Users\<kullanici>\AppData\Roaming\npm\claude.cmd` kullan.

## Kaynaklar
- Claude Code dokümanları
