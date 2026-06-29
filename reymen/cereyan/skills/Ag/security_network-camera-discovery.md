---
name: network-camera-discovery
description: >-
  IP kamera kesfi, RTSP/ONVIF port taramasi, canli goruntu akisi testi ve
  sifre brute force. Hikvision, Dahua, Axis, Reolink ve diger IP kameralar
  icin eksiksiz workflow. Kali Linux + Windows ortaminda calisir.
version: 1
license: MIT
metadata:
  hermes:
    tags: [camera, rtsp, onvif, hikvision, dahua, surveillance, ip-camera, security, kali, network]
audience: user
    platform: cross-platform
    lang: turkish
---


> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | >- |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Network Camera Discovery

## Ne Zaman Kullanilir

- Kullanici "kamera bul", "kamera izle", "canli goruntu", "guvenlik kamerasi", "RTSP" gibi bir sey soylediginde
- Agdaki IP kameralari tespit etme, port tarama, canli akis testi gerektiginde
- Hikvision/Dahua gibi markalarin varsayilan sifrelerini denemek gerektiginde
- CVE / exploit arastirmasi oncesi kamera bilgisi toplamak gerektiginde

## Adim Adim Workflow

### 1. Ag Taramasi ile Kamera Tespiti

Once agdaki tum cihazlari tara, MAC vendor'dan kamerayi tanimla.

```bash
# Adim 1a — Hizli tarama
sudo arp-scan --interface eth1 --localnet

# Adim 1b — Vendor dogrulama
sudo nmap -sn 192.168.0.0/24
```

Bilinen kamera MAC vendor'lari:
- **Hikvision**: E0:BA:AD, 00:25:9B, 04:13:8E
- **Dahua**: AC:CC:87, 30:0E:55
- **Axis**: 00:40:8C
- **Reolink**: 9A:A1:A4

### 2. Port Taramasi (Windows nmap ile)

Kali'den port taramasi timeout verebilir. Windows ana makinedeki nmap daha guvenilir.

```bash
# Kamera portlari
nmap -p 80,443,554,8000,8080,8554 <kamera-ip>
# ONVIF portlari
nmap -p 3702,5000,5001,7501,8899 <kamera-ip>
```

### 3. RTSP Baglantisi Testi

```bash
# curl ile OPTIONS testi (baglanti dogrulama)
curl -v rtsp://admin:admin@192.168.0.17:554/ 2>&1 | grep -E "RTSP|200|401"

# ffprobe ile stream testi
ffprobe -rtsp_transport tcp -timeout 3000000 \
  -i "rtsp://admin:admin@<ip>:554/Streaming/Channels/101" 2>&1 | head -20
```

### 4. Bilinen RTSP URL Desenleri

| Marka | URL |
|-------|-----|
| Hikvision (main) | `/Streaming/Channels/101` |
| Hikvision (alt) | `/h264/ch1/main/av_stream` |
| Hikvision (mpeg4) | `/mpeg4/ch1/main/av_stream` |
| Dahua | `/cam/realmonitor?channel=1&subtype=0` |
| Axis | `/axis-media/media.amp` |
| Generic | `/live`, `/video1`, `/1`, `/media/video1` |

### 5. Web Arayuzu ve ONVIF Kesfi

```bash
# Web kontrol
curl -s -o /dev/null -w "%{http_code}" http://192.168.0.17/

# ONVIF device service
curl -v http://admin:admin@<ip>:80/onvif/device_service 2>&1

# ISAPI (Hikvision)
curl -s -o /dev/null -w "%{http_code}" http://192.168.0.17/ISAPI/System/deviceInfo
```

### 6. Canli Goruntu

Sifre dogruysa:
```bash
# canli izle (Kali X11 veya Windows'ta)
ffplay -rtsp_transport tcp -x 640 -y 480 -i "rtsp://kullanici:sifre@<ip>:554/Streaming/Channels/101"

# snapshot
ffmpeg -rtsp_transport tcp -i "rtsp://kullanici:sifre@<ip>:554/Streaming/Channels/101" \
  -vframes 1 -y /tmp/snapshot.jpg 2>&1

# 10sn kayit
ffmpeg -rtsp_transport tcp -i "rtsp://kullanici:sifre@<ip>:554/Streaming/Channels/101" \
  -t 10 -c copy /tmp/kayit.mp4 2>&1
```

### 7. Sifre Deneme (Brute Force)

Tum standart sifreler basarisizsa kullaniciya iki secenek sunulur:
1. **Hydra ile brute force** (time alir, rockyou.txt ile)
2. **Alternatif yontemler** (SADP, CVE, fiziksel reset, NVR uzerinden)

Yaygin Hikvision sifreleri sirasiyla dene:
```
admin/admin → 12345 → 123456 → admin123 → hikvision123 → 2022 → 112233 → 888888 → hikvision → 666666
```

### 8. Sifre Bulunamazsa — Alternatif Cozumler

Hata kodu 401 ve tum sifreler basarisiz:
- **SADP aracı**: Hikvision resmi aracı, aynı subnet'teki kamerayı bulup sifre sıfırlayabilir
- **CVE taraması**: `searchsploit hikvision <model>` ile model bazlı exploit
- **Fiziksel reset**: Kamerada 10-30 sn reset butonu
- **NVR üzerinden**: Kamera NVR'a bağlıysa, NVR'dan stream al
- **Firmware exploit**: Eski firmware'lerde auth bypass (HGTV, vb.)
- **RTSP Digest vs Basic**: Kamera sadece Digest auth kabul ediyor olabilir

## Pitfall'lar

1. **curl RTSP OPTIONS basarili (200 OK) ama ffmpeg 401:** `curl` OPTIONS istegi bazen auth gerektirmez. ffmpeg ile stream testi yapmadan sifreyi dogrulamis sayma.
2. **ffprobe sessiz donuyor:** Cikti yoksa stderr'i kontrol et (`2>&1`). Bazen hata mesaji vermeden timeout yapar.
3. **Port taramasi Kali'dan timeout:** Windows ana makinedeki nmap'i kullan (`C:\Program Files (x86)\Nmap\nmap.exe`), Kali'dan tarama bazen ayni subnet'te bile yavas/guvenilmez.
4. **Kali host-only agda ise kamera gorulmez:** Kali bridged NIC'te degilse (host-only) ayni subnet'te degildir. Windows'tan nmap ile tara veya Kali'yi bridged'a gecir.
5. **Tum ONVIF portlari filtered:** Kamera ONVIF'i bloke ediyor olabilir. Guvenlik duvari arkasi.
6. **random MAC (Samsung hotspot):** Samsung cihazlar rastgele MAC kullanir — BSSID degisir, SSID'den takip et.

## Referans Dosyalari

Detayli komut listesi, URL desenleri ve sifre listesi icin:
`ag-taramasi-arp-vs-nmap` skill'indeki `references/kamera-tespit-rtsp-onvif.md`
