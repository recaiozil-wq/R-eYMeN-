---
name: agent-project-bootstrap
title: "Agent Projesi Bootstrap"
description: "Kod tamam ama config/install/run eksik olan multi-service AI ajan projelerini ayağa kaldırma deseni. .env, Windows launcher, Hermes Agent entegrasyonu, health check."
tags: [bootstrap, setup, deployment, windows, multi-service, agent, integration]
audience: contributor
category: software-development


---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | "Kod tamam ama config/install/run eksik olan multi-service AI ajan projelerini ayağa kaldırma deseni. .env, Windows launcher, Hermes Agent entegrasyonu, health check." |
| **Nerede** | `misc\agent-systems\agent-project-bootstrap.md` |
| **Ne Zaman** | Genel AI/ML gorevlerinde |
| **Neden** | Agent Project Bootstrap islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |


## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Kod tamam ama config/install/run eksik olan multi-service AI ajan projelerini ayağa kaldırma deseni. .env, Windows launcher, Hermes Agent entegrasyonu, health check. |
| **Nerede?** | agent-systems/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

Kim: AI gelistiricisi
Ne: "Kod tamam ama config/install/run eksik olan multi-service AI ajan projelerini ayağa kaldırma deseni. .env, Windows launcher, Hermes Agent entegrasyonu, health check."
Nerede: `misc\agent-systems\agent-project-bootstrap.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Agent Project Bootstrap islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Agent Projesi Bootstrap

Bir AI ajan projesi geldiğinde — kodların tamamı yazılmış, hiçbir şey çalıştırılmamış — bu skill adımları sırasıyla uygula.

## Temel İlkeler

1. **Önce mevcut yapıyı anla** — dosya sayısı, import zinciri, requirements.txt, .env
2. **Derleme kontrolü** — `python -m py_compile *.py` tüm dosyalarda
3. **Bağımlılıkları kur** — `pip install -r requirements.txt`
4. **Çalışma testi** — import testi + kısa ReAct döngüsü
5. **Hata varsa atla** — bir bileşen çalışmıyorsa alternatife geç (bu kullanıcının tercihi)

## .env-Driven Konfigürasyon Deseni

Kodda sabitlenmiş CONFIG dict'i varsa, .env'den okuyacak şekilde dönüştür:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

DOT_ENV = Path(__file__).parent / ".env"
if DOT_ENV.exists():
    load_dotenv(DOT_ENV, override=True)

def _env_anahtar(anahtar, varsayilan=""):
    deger = os.environ.get(anahtar, "").strip()
    if not deger or deger == "***":
        return varsayilan
    return deger

CONFIG = {
    "default_provider": _env_anahtar("PROVIDER", "lmstudio"),
    "api_key": _env_anahtar("API_KEY"),
}
```

**Kural:** API anahtarları asla koda gömülmez. `.env` dosyasında saklanır.

## Windows Başlatıcı (.bat)

Çok modlu `.bat` dosyası (start/agent/dashboard/gateway/doctor). Şu yapıyı kullan:

```
@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%1"=="start"     goto :start_all
if "%1"=="agent"     goto :start_agent
if "%1"=="dashboard" goto :start_dashboard
if "%1"=="doctor"    goto :doctor
```

## Health Check (Doctor)

Projenin sağlık kontrolü için Python betiği:
- .env'deki anahtarları tara (boş/*** olanları işaretle)
- Modül varlığını kontrol et
- Özet tablosu göster

## Hermes Agent Entegrasyonu

Hermes Agent (Nous Research) ayrı bir repo olarak kalır. Reymen Proje'den bir wrapper ile çağrılır:

```
proje/
  hermes_cli.py       # Hermes CLI wrapper (env sync + subprocess)
  reyemen.bat         # Başlatıcı (hermes komutu dahil)
  main.py             # ReAct ajanı
  gateway_runner.py   # Multi-channel gateway
  dashboard/          # Web UI
  telegram_bot/       # Telegram bot
```

Wrapper'ın yaptığı:
1. Reymen .env'den Hermes .env'ye anahtar senkronizasyonu
2. Hermes CLI'ı subprocess olarak çağırma
3. Çıktıyı kullanıcıya yansıtma

Detaylı desen: `references/hermes-entegrasyonu.md`

## Kullanıcı Tercihi: "Atla" (Skip Debugging)

Bu kullanıcı hataları debug etmekle vakit kaybetmek istemez. Bir yol çalışmazsa:
- Alternatif yola hemen geç (LM Studio hata → DeepSeek API'ye geç)
- API anahtarı yoksa → "ekle" de, bekleme
- Kullanıcıya soru sorma — en mantıklı alternatifi seç ve devam et

## Tuzaklar

- `.env`'yi `read_file` ile okuyamazsın (güvenlik engeli) — `terminal` ile oku
- LM Studio jinja template hatası ("Only user and assistant roles are supported") → model sorunu, çözmeye çalışma, alternatif provider'a geç
- Windows'ta `pip install` Hermes venv'ine kurulabilir — `--target` gerekmez
- `__init__.py` eksik olabilir — import'lar sessizce çalışmayabilir
