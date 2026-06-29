
> **Kategori:** productivity

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | > |
| **Nerede?** | productivity/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: windows-mouse-automation
description: >
title: "Windows Mouse Automation"
  Script’ler C:\Users\marko\AppData\Local\hermes\scripts\ altindadir.
version: 1.0.0
author: marko
license: MIT
metadata:
  hermes:
    tags: [windows, mouse, automation, powershell, cursor, screenshot]
category: productivity
audience: user
tags: [mouse, productivity, tools, windows]
---Windows’ta PowerShell + System.Windows.Forms ile fare imlecini hareket ettirme ve ekran goruntusu alma ornekleri.



# Windows Mouse Automation

## Bilinen calisan scriptler

- `move_mouse.ps1` : 8 adimda egrili hareket (220 ms bekleme)
  calistir: `powershell -ExecutionPolicy Bypass -File C:/Users/marko/AppData/Local/hermes/scripts/move_mouse.ps1`
- `visible_move.ps1` : orta ekranda sekiz hareket daha buyuk adimlarla (500 ms bekleme)
  calistir: `powershell -ExecutionPolicy Bypass -File C:/Users/marko/AppData/Local/hermes/scripts/visible_move.ps1`
- `screenshot.ps1` : imleci 300,200’e tasir, 1.2 sn bekler, ekran goruntusu alir
  cikti: `C:/Users/marko/AppData/Local/hermes/scripts/screen.png`
  calistir: `powershell -ExecutionPolicy Bypass -File C:/Users/marko/AppData/Local/hermes/scripts/screenshot.ps1`

## Bilinen calisma durumu

- PowerShell `pwsh` PATH’te olmadiginda `PowerShell` kullanilmali.
- Script’ler tekrar tekrar bastirilmali.
- Kodlarda C# tipi ekleme hatasi olursa `-ReferencedAssemblies System.Windows.Forms, System.Drawing` eklenmeli.
- Bash ici tırnak allta karakter bozulmamasi icin script dosyasina yazip sonra calistirmak daha guvenli.

## Istenirse yeniden kullanma ornegi

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(500, 400)
```
