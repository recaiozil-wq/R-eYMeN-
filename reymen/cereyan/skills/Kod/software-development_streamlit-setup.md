
> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Software Development_Streamlit Setup |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: streamlit-setup
description: >
title: "Streamlit Setup"
  isolation, first-run email bypass, port/IP access configuration, and
  Streamlit 1.58.0+ breaking changes.
platforms: [windows]
triggers:
  - user mentions streamlit, data app, dashboard
  - user says "streamlit run" and gets connection refused
  - user wants to restrict access to a streamlit app

audience: contributor
tags: [coding, development]
category: software-development---Install, configure, and run Streamlit data apps on Windows. Covers venv



# Streamlit Setup (Windows)

## Installation

Streamlit'i proje venv'ine kur (sistem Python'una değil):

```bash
# Hermes-ai venv'ine
cd /c/Users/marko/hermes-ai
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m pip install streamlit

# Veya herhangi bir proje venv'ine
cd /c/Users/marko/proje
python -m pip install streamlit
```

Alternatif (uv ile):
```bash
uv pip install streamlit
```

## Running

**Doğru Python yolunu kullan.** Windows'ta `streamlit` komutu PATH'te olmayabilir—venv'deki Python ile çağır:

```bash
# ❌ YANLIŞ — streamlit PATH'te yoksa çalışmaz
streamlit run app.py

# ❌ YANLIŞ — yanlış Python modülü
python -m streamlit run app.py   # sistem Python'u venv dışındaysa patlar

# ✅ DOĞRU — venv'deki Python'u doğrudan kullan
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m streamlit run app.py
```

## First Run: Email Prompt Bypass

Streamlit ilk çalıştırmada e-posta adresi sorar ve input'ta takılı kalır.
Bunu atlamak için:

```bash
python -m streamlit run app.py --server.headless=true
```

`--server.headless=true` parametresi email sorusunu tamamen bypass eder.
Alternatif: `--server.showEmailPrompt=False` da aynı işi görür (webui.bat'ta kullanılır).

## Port Configuration

```bash
# Varsayılan port (8501)
python -m streamlit run app.py

# Özel port
python -m streamlit run app.py --server.port=8501

# Headless + özel port
python -m streamlit run app.py --server.port=8501 --server.headless=true
```

## Access / IP Restriction

### Localhost Only (Varsayılan — Güvenli)
Streamlit **default olarak sadece localhost'u dinler.** Dışarıdan erişilemez.
Bu yeterli güvenlik sağlar:

```bash
# localhost:8501 — sadece bu bilgisayardan erişim
python -m streamlit run app.py
```

### LAN / Network Erişimi
```bash
# Tüm ağ arayüzlerinden dinle (dikkat: herkes erişebilir)
python -m streamlit run app.py --server.address=0.0.0.0
```

### ⚠️ `--server.allowIps` KALDIRILDI
**Streamlit 1.58.0+** sürümünde `--server.allowIps` parametresi tamamen kalkmıştır.
Bunun yerine şunları kullan:

| Amaç | Çözüm |
|------|-------|
| Sadece localhost | Varsayılan (hiçbir şey ekleme) |
| Belirli IP'ler | Windows Firewall ile kısıtlama |
| LAN erişimi | `--server.address=0.0.0.0` (herkese açık) |

Kullanılabilir parametreleri görmek için:
```bash
python -m streamlit run --help
```

### İlgili Parametreler
| Parametre | Açıklama |
|-----------|----------|
| `--server.port` | Port numarası (varsayılan: 8501) |
| `--server.address` | Bağlanılacak adres (0.0.0.0 = herkes, varsayılan: localhost) |
| `--server.headless` | true = email sorma, browser açma |
| `--server.showEmailPrompt` | false = email sormayı kapat |
| `--server.enableCORS` | true = CORS aç |
| `--browser.serverAddress` | Browser'da gösterilecek network adresi |
| `--browser.gatherUsageStats` | false = istatistik toplama |
| `--client.allowedOrigins` | iframe embed için origin izin listesi (IP kısıtlama değil) |

## Ek Parametreler

| Parametre | Açıklama |
|-----------|----------|
| `--browser.serverAddress` | Tarayıcıda gösterilecek adres (genelde `--server.address` ile aynı) |
| `--browser.gatherUsageStats` | `False` = kullanım istatistiği toplama |
| `--server.showEmailPrompt` | `False` = email sorma |
| `--server.enableCORS` | `True` = CORS açık (API çağrıları için gerekli) |

## Port Çakışması Çözümü

Port 8501 doluysa (ERR_CONNECTION_REFUSED değil, port çakışması):

```bash
# 1. Hangi process'in portu kullandığını bul
netstat -ano | grep ":8501 "

# 2. Streamlit process'lerini öldür
taskkill /F /PID <PID>

# 3. Tüm python streamlit process'lerini öldür (kesin çözüm)
taskkill /F /IM python.exe   # 🔴 DİKKAT: tüm python process'lerini öldürür

# 4. Farklı port dene
python -m streamlit run app.py --server.port=8510 --server.headless=true
```

Port 8501-8599 arası boş bir port bulmak için PowerShell:
```powershell
$port=8501; while($true){try{$s=[Net.Sockets.Socket]::new([Net.Sockets.AddressFamily]::InterNetwork,[Net.Sockets.SocketType]::Stream,[Net.Sockets.ProtocolType]::Tcp); $s.Bind([Net.IPEndPoint]::new([Net.IPAddress]::Loopback,$port)); $s.Close(); Write-Output $port; break}catch{$port++}}
```

## Background Process (Arka Planda Çalıştırma)

```bash
# terminal background=true ile başlat
cd /c/Users/marko/hermes-ai
C:/Users/marko/hermes-ai/venv/Scripts/python.exe -m streamlit run app.py --server.port=8501 --server.headless=true

# Doğrulama
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
# → 200 dönerse çalışıyor
```

## Pitfalls

1. **PATH'te streamlit yok** → `python -m streamlit` kullan veya venv'deki Python'a tam yol ver
2. **Email prompt'ta takılma** → `--server.headless=true` EKLEMEDEN çalıştırma
3. **`&` ile background yapma** → Hermes'te background=true kullan, shell `&` değil
4. **ERR_CONNECTION_REFUSED** → streamlit çalışmıyor demektir, process log'una bak
5. **`--server.allowIps`** → Streamlit 1.58.0+ yok, firewall veya localhost kullan
6. **Yanlış Python** → streamlit hangi Python'un site-packages'ine kurulduysa o Python'la çağır
7. **Port çakışması** → 8501 doluysa `taskkill /F /IM python.exe` (tüm python process'lerini öldürür, dikkatli kullan) veya farklı port dene
8. **Mevcut process'i kontrol etme** → önce `netstat -ano | grep ":8501 "` ile hangi PID'in kullandığını bul, sonra `taskkill /F /PID <PID>` ile sadece onu öldür
9. **Çift streamlit process'i** → streamlit 8501'i dinlerken ikinci bir instance başlatırsan port bind hatası alırsın—önce eski process'i öldür
