
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Open_Vscode_Focus |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: open_vscode_focus
description: Oyun ekranından VS Code’a hızlı geçiş. Çalışma alanı sıfırlanmadan öndeki pencereyi kapatır veya en sona alır, ardından VS Code’u sıfırdan başlatır ve odaklar.
title: "Open VS Code Focus"

audience: user
tags: [automation, windows]
category: windows-automation---

# VS Code Focus

- Rol: sistem seviyesinde pencere geçişi
- Amaç: oyun uygulaması ile VS Code arasında hızlı ve tekrarlanabilir geçiş

## Doğrulanmış düşük riskli sıralama
1. Öndeki pencereyi kapat veya minimize et
2. VS Code açık değilse başlat
3. VBS ile Alt+Tab denemesi yap, ardından Alt tuş bypass’ını uygula
4. Ekran görüntüsü ile doğrula; ön planda VS Code değilse pencere taramasına geç
5. Terminali VS Code içinde aç ve komutu gönder

## Bilinen sıkıntılar
- Windows, `SetForegroundWindow` ve benzeri Win32 odak çağrılarını engelleyebilir.
- PowerShell’de `System.Windows.Forms.SendKeys` ve `Add-Type` Win32 tanımları bazen yüklenmez.
- Alt+Tab kuyruğu; kullanıcının zaten görülen pencere sırasına göre değişir.

## Scriptler
- `open_vscode.ps1`
- `switch_to_vscode.ps1`
- `wake_screen.ps1`
- `launch_claude_alt.vbs`

## Kaynak
- Hermes Agent
