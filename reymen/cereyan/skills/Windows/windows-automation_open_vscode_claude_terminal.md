
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Open_Vscode_Claude_Terminal |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: open_vscode_claude_terminal
description: VS Code’da Claude sohbet/terminalini otomatik açma. Önce terminal panelini açar, sonra `claude` komutunu gönderir. Komut bulunamazsa hata durumunu loglar ve ekran görüntüsü alır. Klavye+Fare odaklaması ile çalışan ana akış.
title: "Open VS Code Claude Terminal"

audience: user
tags: [automation, windows]
category: windows-automation---

# VS Code Claude Terminal Açıcı

## Amaç
VS Code içinde Claude ile konuşmaya hazır hale gel. Oyun ekranı gibi farklı pencereler arasında otomatik geçiş yap.

## Akış
1. VS Code zaten açık mı? Açık değilse başlat.
2. `vscode_focus_scoped.ps1` script'ini çalıştır:
   ```
   powershell -ExecutionPolicy Bypass -File "C:\Users\marko\AppData\Local\hermes\scripts\vscode_focus_scoped.ps1"
   ```
3. **Metin gönderme işlemini ayrı bir adımda yap** — bu skill sadece VS Code'u öne çıkarır, metin gönderme için `claude-agent-terminal-send-text` skill'ini kullan.
4. Ekran görüntüsü al:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "C:\Users\marko\AppData\Local\hermes\scripts\screenshot.ps1"
   ```
   Çıktı `C:\Users\marko\AppData\Local\hermes\scripts\screen.png` olarak kaydedilir.

   Alternatif (sistem Python mss):
   ```powershell
   cmd.exe /c "C:\Users\marko\AppData\Local\Python\PythonCore-3.14-64\python.exe" C:\Users\marko\AppData\Local\hermes\scripts\screenshot_mss.py
   ```
   > ⚠️ cmd.exe üzerinden Python çalıştırmak stdout çıktısını göstermez. Başarı kontrolü için dosyayı `ls -la` ile kontrol et.
5. Görsel analizi yap — model vision desteklemiyorsa ekran görüntüsünü Telegram kullanıcısına gönder.

## Bilinen Sorunlar
- `vscode_focus_scoped.ps1` içinde `[FocusWin]::IsIconic($h)` hatası alınabilir ("method not found") — bu PowerShell sürümü kaynaklıdır. Script yine de "FOCUSED_VSCODE" döndürürse odaklanma çalışmıştır.
- `SetForegroundWindow` bazen `False` döner; ekran görüntüsü ile teyit et.
- `claude` komutu sistem PATH'inde yoksa hata verir. PATH: `C:\\Users\\marko\\AppData\\Roaming\\npm\\claude.cmd`
- DeepSeek ve benzeri modelsiz modeller vision desteklemez; ekran görüntüsü analizi yapılamaz.
- **PowerShell'de `;` ile komut zincirleme hata verir** — her komut ayrı terminal() çağrısı olmalıdır.
- **screenshot.ps1 ekranın alt kısmını kesebilir** — çözüm: `screenshot_v2.py` (Python 3.14 + mss) kullan, `monitors[1]` ile tam çözünürlük.
- **Fare tıklama koordinatı:** pyautogui.position() anlık konumu okur, tıklamayı yakalamaz. En güvenilir yol: kullanıcıya sor.

## Scriptler (tam yollar)
- `C:\\Users\\marko\\AppData\\Local\\hermes\\scripts\\vscode_focus_scoped.ps1` — VS Code'u öne çıkarır
- `C:\\Users\\marko\\AppData\\Local\\hermes\\scripts\\send_text_to_claude_terminal.vbs` — ⚠️ sabit metin gönderir (VBS, değişken metin için PowerShell SendKeys kullan)
- `C:\\Users\\marko\\AppData\\Local\\hermes\\scripts\\screenshot.ps1` — ekran görüntüsü alır (PowerShell + WinForms, ⚠️ bazen alt kısmı keser)
- `C:\\Users\\marko\\AppData\\Local\\hermes\\scripts\\screenshot_mss.py` — ekran görüntüsü alır (sistem Python 3.14 + mss, `monitors[1]`)
- `C:\\Users\\marko\\AppData\\Local\\hermes\\scripts\\screenshot_v2.py` — **TERCİH EDİLEN** tam ekran görüntüsü (sistem Python 3.14 + mss, monitors[1] kullanır, stdout'a sonuç döndürür)
- **Ekran görüntüsü kesik çıkarsa screenshot_v2.py dene**

## İlgili Skill'ler
- `claude-agent-terminal-send-text` — metin gönderme ve Enter basma işlemleri için
