---
name: windows-system-automation
title: "Windows System Automation"
tags: [coding, development, windows]
description: Windows sistem otomasyonu — fare hareketi, imleç kontrolü, PowerShell + .NET desenleri ve ekran görüntüsü alma.
version: 1.0.0
author: marko
license: MIT
metadata:
  hermes:
    tags: [windows, automation, powershell, mouse, screenshot]
audience: contributor
related_skills: [hermes-agent]
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows sistem otomasyonu — fare hareketi, imleç kontrolü, PowerShell + .NET desenleri ve ekran görüntüsü alma. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Windows System Automation

Windows'ta UI/sistem otomasyonu için PowerShell + .NET desenleri.

## Fare Hareketi

Standart desen: PowerShell betiği oluştur, çalıştır.

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(X, Y)
```

Çok adımlı hareket için betiği dosyaya yaz, sonra çalıştır.

Örnek: `C:\Users\<user>\AppData\Local\hermes\scripts\move_mouse.ps1`

## Ekran Görüntüsü

PowerShell ile ekran görüntüsü alma:

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Add-Type -Language CSharp -TypeDefinition @'
using System;
using System.Drawing;
using System.Windows.Forms;
public static class ScreenshotHelper
{
    public static void Save(Size size, string path)
    {
        using (Bitmap bmp = new Bitmap(size.Width, size.Height))
        {
            using (Graphics g = Graphics.FromImage(bmp))
            {
                g.CopyFromScreen(0, 0, 0, 0, bmp.Size);
            }
            bmp.Save(path);
        }
    }
}
'@ -ReferencedAssemblies System.Windows.Forms, System.Drawing
[ScreenshotHelper]::Save($bounds.Size, 'C:\path\screen.png')
```

## Pitfall: PowerShell komutu içinde değişken kaybolması

Bash/MSYS üzerinden PowerShell çağırırken `$` içeren komutlar bozulabilir. Yöntem:
1. İçeriği `printf` veya `write_file` ile `.ps1` dosyasına yaz.
2. `powershell -ExecutionPolicy Bypass -File <path>` ile çalıştır.

Böylece kaçış karakterleri ve yorumlama sorunları önlenir.

## Cron Job (no_agent=True) + Watchdog Pattern

Hermes cron job'larında `no_agent=True` ile LLM harcamadan script bazlı watchdog çalıştırma:

**Ne zaman kullanılır:**
- Periyodik kontrol/backup görevleri (disk alanı, ağ bağlantısı, dosya senkronizasyonu)
- Çıktısı doğrudan Telegram'a iletilecek script'ler
- LLM çağırmaya gerek olmayan deterministik işlemler

**Oluşturma adımları:**
1. Script'i `C:\Users\<user>\AppData\Local\hermes\scripts\<name>.py` yaz
2. `cronjob(action='create', script=<name>.py, no_agent=True, schedule='...', deliver='telegram:chat_id')`
3. Script stdout'u otomatik olarak Telegram'a iletilir
4. Boş stdout = sessiz geçiş (değişiklik yoksa bildirim gitmez)
5. Non-zero exit = hata bildirimi

**Örnek: auto_backup.py**
```python
#!/usr/bin/env python3
def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120, shell=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()
# git add/commit/push logic
```
Cron: `script=auto_backup.py, no_agent=True, schedule='0 4 * * *'`

Detaylı şablon ve açıklamalar için → `references/cron-watchdog-pattern.md`

## Script Temizlik Politikası

Zamanla `scripts/` klasörü test/deneme script'leriyle dolar. Temizlik prosedürü:

1. **Aktif script** = `.bat`, `.ps1`, `.py` olarak `scripts/` kökünde kalır
2. **Eski denemeler** = `scripts/_archive/` altına taşınır (silme, her zaman geri alınabilir)
3. **Etkin kalan script kriterleri:**
   - `find_caret.py`, `screenshot_v2.py`, `move_mouse.ps1` gibi fonksiyonel script'ler
   - `vscode_yaz.bat`, `focus_telegram.ps1` gibi sık kullanılan tetikleyiciler
   - `sync_skills_to_obsidian.bat`, `auto_backup.py` gibi cron/otomasyon script'leri
4. **Arşive taşınanlar:**
   - Tek kullanımlık test script'leri (test_*, ss_*, click_*)
   - Aynı işi yapan alternatif denemeler (camera_capture.py, camera_ctypes.py vs.)
   - Artık kullanılmayan eski koordinat script'leri (click_619_232.py, get_click_coord.py)
   - Eski send_wifi_* varyantları

**Temizlik sonrası hedef:** 45-50 aktif script, gerisi `_archive/` altında.

## Gerçek Kamera Çekimi (Donanım)

Kullanıcı sadece ekran görüntüsü değil, kamera donanımından fotoğraf çekimini istiyor.

Öncelikli yaklaşım sırası:
1. Kamera uygulamasını aç: `cmd.exe /c start microsoft.windows.camera:`
2. Kamerayı açmak için UI tetikleme yapmaya çalış; eğer Space/Ok tuşu denk gelmiyorsa doğrudan donanım yakalama kullan.
3. Windows'daki gerçek çekim için hazır bir PowerShell'i dosyaya yaz ve çalıştır. Örnek dosya: `C:\\Users\\<user>\\AppData\\Local\\hermes\\scripts\\camera_real.ps1`
4. Çıktıyı `C:\\Users\\<user>\\Desktop\\camera_real.jpg` olarak kaydet ve kontrol et.

Hazır scriptNot: PowerShell UWP `MediaCapture` kullanır. Dosya oluşmazsa Windows Runtime async yönetimi nedenleriyle sorun yaşanmış olabilir; o durumda alternatif olarak kamera uygulaması manuel tetiklemek beklenir.

## Windows Error Handling Pipeline (Planlı)

ReYMeN'de eksik olan uçtan uca hata yönetim hattı. Ekran hatası çıktığında otomatik tespit → hata kodu üret → Claude çözümü → uygula.

Detaylı mimari: `references/windows-error-pipeline.md`

**Özet:**
1. **HataWatchdog** — sürekli ekran OCR, hata dialog'u tespiti (threading + Event)
2. **HataKoduUretici** — `HATA-XXXX: kategori: özet` formatında kod, `.ReYMeN/hata_kodlari/` klasörü
3. **TerminalHataParser** — PowerShell/cmd çıktısından hata parse etme
4. **CozumUygulayici** — kullanıcının Claude'dan getirdiği çözümü otomatik uygulama

⚠️ **Plan aşamasında** — `hata_cozucu.py` Claude Code ile yazılacak, sonra entegre edilecek.

## Claude Code İş Birliği Deseni

Bazı durumlarda modül/çözüm doğrudan Hermes ile yazmak yerine **Claude Code CLI'a sorulur**, kullanıcı çözümü alır, Hermes entegre eder.

**Ne zaman kullanılır:**
- Büyük/yeni modüller (500+ satır)
- Bağımsız test edilmesi gereken karmaşık yapılar
- Kullanıcının tercih ettiği durumlar

**Akış:**
1. Hermes, Claude Code'a sorulacak **soru metnini** hazırlar (açık, adım adım, teknik kurallarla)
2. Kullanıcı soruyu Claude Code terminaline yapıştırır
3. Kullanıcı çözümü alıp Hermes'e iletir
4. Hermes dosyayı Reymen projesine yazar, entegre eder, derleme testi yapar