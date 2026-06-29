
> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Security_Guvenlik Izleme Sistemi |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: guvenlik-izleme-sistemi
description: Windows Task Scheduler tabanli guvenlik izleme — bilinmeyen islem/USB/giris/pyautogui tespiti
title: "Guvenlik Izleme Sistemi"

audience: user
tags: [pentest, security]
category: security---

# Guvenlik Izleme Sistemi (Windows Task Scheduler)

## Guncel Durum (2026-06-11)
Hermes cron API'si yerine Windows Task Scheduler kullaniliyor.
Bu sayede API token israfi yok — script Telegram'a direkt baglaniyor.

## Genel Ilke: Cron'dan Bagimsiz Calisma
Periyodik polling gerektiren islerde (her 2 dk / 5 dk / 30 dk) Hermes cron kullanma.
Bunun yerine Windows Task Scheduler kullan:
- 0 API token harcanir
- Hermes guncellense/kapansa bile calisir
- Dogrudan Telegram Bot API'ine baglanir
- Script ciktisi sadece olay varsa gonderilir (sessiz normal)

### Task Scheduler'a Gecis Adimlari
1. Scripti `~/.hermes/scripts/` altina koy
2. Uygun Python yolunu bul (`hermes-agent venv/Scripts/python.exe`)
3. `schtasks /create /tn Adi /tr \"'python.exe' 'script.py'\" /sc minute /mo N /f`
4. Hermes cron'u sil: `cronjob action='remove' job_id=ID`
5. Dogrula: `schtasks /query /tn Adi /fo list /v`

## Bilesenler

### 1. Windows Task Scheduler
- **Gorev Adi:** `Hermes-GuvenlikIzleme`
- **Tetikleyici:** Her 2 dakikada bir
- **Calisan:** `python security_monitor.py`
- **Calistiran:** `C:\\Users\\marko\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\pythonw.exe` (windowless — terminal acilmaz)
- **MultipleInstances:** IgnoreNew (zaten calisiyorsa yenisini baslatma)
- **Script:** `C:\\Users\\marko\\.hermes\\scripts\\security_monitor.py`
- **Yedek konum:** `AppData/Local/hermes/scripts/security_monitor.py`
- **Login Modu:** Interactive only (kullanici girisi varken calisir)
- **Dogrulama:** `schtasks /query /tn Hermes-GuvenlikIzleme /fo list /v`

### 2. Tespit Edilenler

| Risk | Olay | Aciklama |
|------|------|----------|
| YUKSEK 🔴 | Bilinmeyen PyAutoGUI | pyautogui kullanan ama bilinmeyen script |
| YUKSEK 🔴 | Yeni USB cihaz | Fiziksel temas gostergesi |
| YUKSEK 🔴 | Ekran kilidi atlatma | Biri fiziksel olarak dokundu |
| YUKSEK 🔴 | Basarisiz giris | 10dk icinde hatali sifre denemeleri |
| ORTA 🟡 | Bilinmeyen Python sureci | Kullanici gorevi olmayan script |
| DUSUK 🔵 | (genisletilebilir) | |

### 3. Uyari Mekanizmasi
- **Yeni olay:** 60 saniye icinde 10 kez Telegram uyarisi (6 sn ara)
- **Eski olay (hala aktif):** 2 dk'da 1 hatirlatma
- **Tehdit yok:** Tamamen sessiz

### 4. Kill Switch
Kullanici Telegram'da "kontrol" dediginde:
```
shutdown /s /t 30 /c "Hermes guvenlik kapatmasi - kullanici talebi"
```
Bilgisayar 30 saniye icinde kapanir.

### 5. Bilinen Scriptler (Alarm Gecerli Degil)
- hermes.exe, gateway, vscode_bot.py, mcp_server/app.py
- tor_multi_search.py, gmod_trainer.py, claude_send.py
- send_clipboard.py, send_to_claude.py, birlesik_arama.py
- tor_hizli_arama.py, env_watcher.py, gorsel_onaylama.py
- sync_skills_to_obsidian.py, security_monitor.py, app.py

### 6. Bilinen PyAutoGUI Scriptler
- tor_multi_search.py, gmod_trainer.py, gorsel_onaylama.py

## Tamamlayici Guvenlik Onlemleri (Kontrol Listesi)

Guvenlik izleme sisteminin yaninda su onlemler de alinmalidir:

| # | Onlem | Durum | Nasil |
|:---:|---|---|---|
| 1 | **Pagefile temizligi** | ✅ Ayarlanmis | `ClearPageFileAtShutdown = 1` (HKLM registry) |
| 2 | **Tor Browser iz temizleme** | ✅ Startup otomatik | `hermes_tor_cleanup.bat` → `hermes_iz_temizle.py` |
| 3 | **Paylasimli klasor (Kali)** | ✅ Kapali | VirtualBox'ta `<none>` — Windows-Kali arasi kopru yok |
| 4 | **Port/Firewall** | ✅ Guvende | Firewall Block + NAT arkasinda |
| 5 | **IP korumasi** | ⚠️ Kural | Kali'den islem yaparken Tor/VPN sart. Windows host'tan asla direkt baglanti |
| 6 | **Defender** | ⚠️ Dikkat | Exploit/payload dosyalarini host'a asla kopyalama. Kali'de tut |
| 7 | **Windows log** | ℹ️ Normal | Sadece VM'in acilip kapandigini gosterir. Kali icini gormez |

### Upgrade/Modify islemi gerektiginde

Registry degisikligi icin admin yetkisi gerekir:
```powershell
Start-Process cmd.exe -Verb runAs -ArgumentList '/c reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v ClearPageFileAtShutdown /t REG_DWORD /d 1 /f > C:\Users\marko\pagefile_result.txt 2>&1'
```
UAC prompt gelir — kullanici "Evet" dedikten sonra sonuc dosyadan okunur.

- **python.exe vs pythonw.exe:** Scheduled Task'te `python.exe` kullanmak her calistiginda bir cmd penceresi acilir (2dk'da bir acilip kapanir). Cozum: `pythonw.exe` kullan — hic pencere acmaz, arka planda sessiz calisir.
- **MultipleInstances=IgnoreNew:** Task zaten calisiyorsa yeni instance baslatilmaz. Bu sayede 2dk'lik intervalde bir onceki script hala calisiyorsa atlanir.
- **schtasks /change sifre sorabilir:** Task'i `python.exe`'den `pythonw.exe`'ye cevirirken "run as password" sorabilir. Bos birakilabilir ama guvenlik policysine takilabilir.
- `references/kurulum-adimlari.md` — Windows Task Scheduler kurulum adimlari

## Dogrulama

```bash
schtasks /query /tn Hermes-GuvenlikIzleme /fo list /v
```

## Durum Dosyasi
`%LOCALAPPDATA%/hermes/security_state.json`

## Kaynak
LuNiZz/siber-guvenlik-sss + canlı Windows taraması (2026-06-11)
Obsidian: vault/Hermes/windows-guvenlik-taramasi.md

## Referans Dosyalari
- `references/kurulum-adimlari.md` — Windows Task Scheduler kurulum adimlari
- `references/windows-log-kali-guvenligi.md` — Windows log + Kali guvenlik analizi
- `references/windows-forensics-attack-perspective.md` — Forensic bakis acisiyla korunma