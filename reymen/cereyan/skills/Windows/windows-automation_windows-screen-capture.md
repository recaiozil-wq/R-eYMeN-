
> **Kategori:** automation

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Automation_Windows Screen Capture |
| **Nerede?** | automation/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: windows-screen-capture
description: Windows ekran görüntüsü alma iş akışı. Tam ekran, aktif pencere, alan seçimli kesme ve panoya kopyalama senaryolarını kapsar.
title: "Windows Screen Capture"

audience: user
tags: [automation, screen, windows]
category: windows-automation---

# Windows Screen Capture

Windows ekran görüntüsü alma iş akışı; kullanıcı komutuna göre uygun yakalama yöntemini seçer.

## Variables
- OUT = `C:\Users\marko\Desktop\ekran_gorselleri\`

## Capture Shortcuts
1. Tam ekran: `Win + PrtScn` → `C:\Users\marko\Pictures\Screenshots\ekran_.png`
2. Alan seçmeli kesme: `Win + Shift + S` → geçici panoya
3. Aktif pencere: `Alt + PrtScn` → panoya
4. Panodaki görüntüyü dosyaya aktar: PowerShell + `System.Windows.Forms.Clipboard::GetImage()`

## Workflow
1. Kullanıcı "ekran al" / "şu pencereyi al" / "kes" komutunu verir.
2. Yakalama modunu belirle: full | window | region | clipboard.
3. `scripts/screenshot.py` dosyasını çalıştır; burada Fallback zinciri otomatik uygulanır.
4. Çıktı `OUT` altında zaman damgalı .png olarak kaydedilir.
5. Telegram veya diğer hedeflere `.png` yolunu ilet.

## Fallback
- `Win+Shift+S` sonrası pano boşsa → aktif pencere boyutunu al, PyAutoGUI ile tara.
- PowerShell panoya kopya başarısız olursa → PyAutoGUI tam ekran.
- PyAutoGUI başarısız olursa → MSS tara.

## Multi-monitor Fix
Çoklu ekran nedeniyle bitmap hatası alındı. Çözüm: **sadece birincil ekran** sınırlarını kullan.

```powershell
[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
```

`AllScreens` yerine `PrimaryScreen` kullan; genişlik/yükseklik tam ekran boyutunu verir.

Not: `System.Windows.Forms` yüklü değilse `Add-Type -AssemblyName System.Windows.Forms` çağır.

## Verification
- Çıktı sabit yolda (ör. `C:\Users\marko\Desktop\screenshot.png`) oluşmalı.
- Dosya boyutu 0 olmamalı.
- Görsel bakış doğrulaması: `screenshot.png` ile vision analizi yap.

## User Preferences
- Çok az açıklama, direkt sonuç.
- Dosya kaydetme: `C:\Users\marko\Desktop\ekran_gorselleri\` ana kayıt klasörü.
- Kayıt isimlendirme: zaman damgası + ekran_al / aktif_pencere.

## References
- [references/shortcuts.md](references/shortcuts.md)
