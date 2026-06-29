---
name: windows-guvenlik-izleme
id: windows-guvenlik-izleme
title: "Windows Güvenlik İzleme — Defender + Port Watchdog"
description: "Windows Defender tehdit bildirimlerini otomatik izle, açık portları tara, güvenlik ihlallerini raporla."
tags: [windows, güvenlik, defender, port, watchdog, cron]
category: windows-system-automation
audience: user
trigger: "Kullanıcı 'güvenlik izle', 'watchdog', 'tehdit kontrol' dediğinde veya Windows Defender bildirimi aldığında"


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | Windows ajani |
| **Ne** | "Windows Defender tehdit bildirimlerini otomatik izle, açık portları tara, güvenlik ihlallerini raporla." |
| **Nerede** | `windows\system\windows-system-automation_windows-guvenlik-izleme.md` |
| **Ne Zaman** | Windows sistem yonetimi gerektiginde |
| **Neden** | Windows System Automation Windows Guvenlik Izleme islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Windows ajanı |
| **Ne?** | Windows Defender tehdit bildirimlerini otomatik izle, açık portları tara, güvenlik ihlallerini raporla. |
| **Nerede?** | system/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: Windows ajani
Ne: "Windows Defender tehdit bildirimlerini otomatik izle, açık portları tara, güvenlik ihlallerini raporla."
Nerede: `windows\system\windows-system-automation_windows-guvenlik-izleme.md`
Ne Zaman: Windows sistem yonetimi gerektiginde
Neden: Windows System Automation Windows Guvenlik Izleme islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Windows Güvenlik İzleme

## Ne İşe Yarar
- Windows Defender tehdit algılamalarını periyodik kontrol eder
- Dışarıya açık beklenmeyen portları tespit eder
- Yeni sorun bulduğunda Hermes üzerinden raporlar
- State tutar: sadece **son kontrolden sonraki** olayları bildirir

## Kurulum

### 1. Script
Dosya: `~/.hermes/scripts/guvenlik_watchdog.ps1`

### 2. Cron Job (otomatik)
```json
{
  "schedule": "every 10m",
  "script": "guvenlik_watchdog.ps1",
  "no_agent": true,
  "name": "Guvenlik Watchdog (10dk)"
}
```

Hermes cron'a şu komutla oluşturuldu (tekrar gerekmez):
```
cronjob create schedule="every 10m" script=guvenlik_watchdog.ps1 no_agent=true name="Guvenlik Watchdog (10dk)"
```

### 3. Manuel çalıştırma
```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\marko\AppData\Local\hermes\scripts\guvenlik_watchdog.ps1"
```

## Nasıl Çalışır

| Bileşen | Açıklama |
|---------|----------|
| State dosyası | `~/.hermes/cache/guvenlik_son_kontrol.txt` — son kontrol zamanını saklar |
| Defender kontrolü | `Get-MpThreatDetection` ile son kontrolden sonraki tehditleri listeler |
| Port kontrolü | `Get-NetTCPConnection -State Listen` ile dışa açık portları tarar |
| Beklenen portlar | 22, 135, 139, 445, 5040, 5357, 7680, 9229, 27036, 11434, 5037, 56083 + 49664-49750 + 50000-51000 |
| Sistem portları | PID 4 (System) portları otomatik atlanır |
| Localhost portları | 127.0.0.1, ::1 portları güvenli kabul edilir |
| Sessiz mod | Sorun yoksa hiçbir çıktı üretmez (cron'da no_agent=True ile sessizdir) |

## Çıktı Formatı

Sorun bulunduğunda:
```
=== HERMES GUVENLIK UYARISI: N yeni sorun ===

[{"Type":"DEFENDER","ThreatID":...,"Source":"...","Action":true,...}]
```

## Beklenen Davranış

- **İlk çalışma:** Tüm geçmiş tehditleri raporlar (state sıfır)
- **Sonraki çalışmalar:** Sadece yeni tehditleri ve port değişikliklerini raporlar
- **Sorun yok:** Sessiz (hiçbir bildirim gitmez)
- **Cron job:** Her 10 dakikada bir otomatik çalışır

## Pitfall'lar

- PowerShell `Get-NetTCPConnection` bazen yük altında zaman aşımına uğrayabilir — try/catch ile korunur
- State dosyası silinirse bir sonraki çalışma tüm geçmişi yeniden raporlar
- `Get-MpThreatDetection` çıktısı büyükse kaynak metni 200 karakterle sınırlanır
- Bash üzerinden PowerShell çağırırken `$_` değişkeni çakışması olabilir — tırnak kaçışına dikkat
