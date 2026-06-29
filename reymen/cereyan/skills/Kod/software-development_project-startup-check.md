---
name: project-startup-check
description: Proje açılış taraması — bağımlılık, araç, yapılandırma ve klasör kontrolleri ile eksiklikleri otomatik tamir et. Her oturum/çalışmada ilk adım.
title: "PRoject Startup Check"
platforms: [windows, macos, linux]

audience: contributor
tags: [coding, development]
category: software-development---

# Project Startup Check

## Amaç
Her proje açılışında aynı kalıba göre eksikleri tara, eksik olanı tamir et, akışı tekrar başlat.
Tekrar tekrar yapılacak kontrol listesi buna göre otomatikleştirilir.

## İki Seviye Kontrol

Bu skill iki farklı kontrollü kapsar:
1. **Full System Inventory** — donanım + temel yazılım envanteri (pre-project, sistemin ne kaldırabileceğini görmek için)
2. **Project-Level Check** — belirli bir proje için bağımlılık/konfigürasyon kontrolü (her oturum başında)

---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Proje açılış taraması — bağımlılık, araç, yapılandırma ve klasör kontrolleri ile eksiklikleri otomatik tamir et. Her oturum/çalışmada ilk adım. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

## SEVİYE 1 — FULL SYSTEM INVENTORY

Yeni bir proje türü seçmeden önce sistemin ne kaldırabileceğini görmek için.

### 1a — DONANIM
```bash
# CPU
powershell -Command "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List"
# RAM
powershell -Command "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, Capacity, Speed | Format-List"
# GPU + VRAM
powershell -Command "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | Format-List"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null
# Disk
powershell -Command "Get-CimInstance Win32_LogicalDisk | Where-Object DriveType -eq 3 | Select-Object DeviceID, Size, FreeSpace | Format-Table -AutoSize"
```

### 1b — YAZILIM SÜRÜMLERİ
```bash
echo "Python: $(python3 --version 2>&1)" && echo "Node: $(node --version)" && echo "npm: $(npm --version)"
echo "Git: $(git --version)" && echo "Docker: $(docker --version 2>&1)"
echo "Docker Compose: $(docker compose version 2>&1)"
gh --version 2>&1 | head -1
code --version 2>&1 | head -1
playwright --version 2>&1
```

### 1c — ARAÇ DURUMU
```bash
# Docker daemon çalışıyor mu?
docker ps 2>&1 | head -3

# Ollama modelleri
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'  {m[\"name\"]}') for m in d.get('models',[])]" 2>&1

# ADB
adb --version 2>&1 | head -1

# WSL
wsl -l -v 2>&1
```

### 1d — GLOBAL PAKETLER
```bash
# npm globals
npm list -g --depth=0 2>&1

# Python ML araçları
python3 -m pip list 2>&1 | grep -iE "fastapi|uvicorn|flask|django|numpy|pandas|torch|pillow|opencv|playwright|pydantic|httpx|requests"
```

### 1e — KABİLİYET ANALİZİ
Tabloyu doldur ve proje türüne karar ver:

| Kabiliyet | Sorgu | Proje Türü |
|-----------|-------|------------|
| GPU + CUDA | `nvidia-smi` → VRAM >= 6GB | AI/ML, local LLM, image gen |
| Docker çalışıyor | `docker ps` | Containerized web/microservice |
| Ollama modelleri var | `/api/tags` | Local AI, RAG, chatbot |
| Node + npm | `node --version` | Web app (Next.js, Express) |
| ADB + Android SDK | `adb --version` | Mobile automation, reverse |
| Python ML stack | pip list'te torch/numpy | Data science, ML pipeline |

### 1f — EKSİK KURULUM (Opsiyonel)
Taramada çıkan eksikler için tek satırlık kurulumlar:
```bash
npm i -g pnpm typescript @railway/cli
python3 -m pip install fastapi uvicorn redis celery sqlalchemy psycopg
# Docker Desktop başlatma (daemon kapalıysa)
"/c/Program Files/Docker/Docker/Docker Desktop.exe" &
sleep 8 && docker ps  # doğrulama
```

---

## SEVİYE 2 — PROJECT-LEVEL CHECK

### Kullanım Zorunluluğu
- Yeni bir projeye başlanırken ilk olarak bu skill'i uygula.
- Proje köküne geçmeden önce aşağıdaki adımları sırasıyla çalıştır.

### Genel Kural
1. Listeyi elle veya script ile kontrol et.
2. Eksik/hatalı olanı ilk sırada tamir et.
3. Tüm akışı temiz bir ortam ile tekrar başlat.

## Standard Kontrol Listesi
1. **Sürüm kontrolleri**
   - `node --version` ve `npm --version`
   - `python --version` ve `pip --version`
2. **Proje bağımlılıkları**
   - `requirements.txt` var mı? VEYA `pyproject.toml` + `uv.lock` var mı?
   - **uv.lock varsa**: `uv sync` kullan — pip DEĞİL. uv-managed venv'lerde pip bulunmaz.
   - **requirements.txt varsa**: `pip install -r requirements.txt`
   - Gerekli paketler kurulu mu? (pip list ile doğrula)
3. **README kurulum adımlarına göre doğrulama**
   - Projenin README.md'sini aç, kurulum adımlarını tek tek oku
   - Her adımı mevcut durumla karşılaştır (klonlama, venv, config, başlatma)
   - Sadece dependency kontrolü yapıp geçme — README'deki SIRALI adımları birebir takip et
   - Özellikle config dosyası oluşturma adımını atlama (config.example.toml → config.toml gibi)
4. **Yardımcı araçlar**
   - `adb version` (Android test için) — yoksa `android-api-apk-manager` kurulum adımlarını otomatik uygula
   - `java -version` ve `javac -version`
   - Opsiyonel APK taraması: `python android_scan.py` — PATH hatası alırsan komutu tırnakla tekrar dene. Çıktı `[]` ise hata olmayan boş sonuç; tekrar dönme.
5. **Görüntü/analiz araçları**
   - `ollama list` (LLM/embedding/vision için)
6. **Yapılandırma dosyaları**
   - `.env` var mı?
   - `package.json`, `app.json`/`app.config.js` var mı?
7. **Temel klasörler
   - Android/Expo projesi: `android/`, `app/src/main/`, `assets/` var mı?
   - Genel proje: `src/`, `components/`, `navigation/` gibi kök klasörler var mı?
7. **Son doğrulama**
   - Projeye özel başlatma komutunu çalıştır (ör. `npx expo start --clear`).

## Hızlı Örnek (Expo projesi)
```bash
cd /c/Users/marko/OneDrive/Desktop/hermes_v7
npx expo start --clear
```

---

## SEVİYE 3 — MİMARİ ANALİZ

Kullanıcı "önce proje yapısını analiz et", "dizin yapısını göster", "mevcut mimariye uygun geliştir" dediğinde veya hiç bilmediğin bir projeye ilk bakışta. Seviye 1-2'den bağımsız çalışabilir.

### 3a — Kök Dizin Yapısı
```bash
ls -la /path/to/project
```
Ayırt edici dosyaları işaretle:

| Dosya | Anlamı |
|-------|--------|
| `app.py` / `main.py` / `index.js` | Giriş noktası — framework ve middleware burada |
| `pyproject.toml` / `setup.py` | Python projesi, bağımlılıklar |
| `package.json` | Node/JS projesi |
| `Cargo.toml` / `go.mod` | Rust/Go projesi |
| `docker-compose.yml` | Container altyapısı |
| `Dockerfile` | Tek container build |
| `.env.example` | Yapılandırma şablonu |

### 3b — Dizin Derinlik Haritası
Her klasörü tek satırda tanımla:

```
core/       → çekirdek (auth, db, middleware, session)
routes/     → API endpoint'leri (FastAPI router'ları)
src/        → iş mantığı (LLM, agent, tools, memory, MCP)
services/   → harici servis arayüzleri (search, hwfit, stt)
static/     → frontend (SPA: index.html + app.js + CSS + js/)
mcp_servers/→ MCP sunucuları
integrations/ → Harici entegrasyonlar
config/     → Konfigürasyon dosyaları
```

### 3c — Mimari Modeli Belirle

| Model | Belirti | Örnek |
|-------|---------|-------|
| Monolith SPA | FastAPI + statik frontend, tek app.py | Odysseus, Hermes |
| Microservice | docker-compose.yml + çoklu servis | Odysseus stack (4 container) |
| Full-stack | pages/, components/, SSR | Next.js, Django |
| CLI tool | Tek entry point, terminal çıktısı | gh CLI, docker CLI |

### 3d — Kritik Dosyaları Oku (sıralı)

1. **Giriş noktası** (app.py) — framework, middleware (CORS, auth, timeout), route register pattern
2. **Proje tanımı** (pyproject.toml / package.json) — bağımlılıklar, versiyon
3. **En büyük route dosyası** — hangi özellik en çok kod barındırıyor?
4. **Frontend yapısı** (index.html + app.js) — SPA mı? Kaç JS modülü? CSS boyutu?
5. **Ana servis** (src/agent_loop.py veya eşdeğeri) — en kritik iş mantığı

### 3e — Rapor Formatı

```
proje/
├── core/         → çekirdek (N dosya: auth, db, session)
├── routes/       → N adet route, en büyük: X (N KB), Y (N KB)
├── src/          → iş mantığı (N dosya: LLM, agent, tools)
├── services/     → N servis (search, hwfit, memory)
└── static/       → SPA frontend (1 HTML + N JS modül + N KB CSS)

Mimari:     Monolith SPA (Docker Compose ile çoklu container)
Framework:  FastAPI (Python) + vanilla JS frontend
DB:         SQLite (SQLAlchemy) + ChromaDB (vektör)
Veri akışı: Kullanıcı → Nginx → FastAPI → src/ → SQLite/ChromaDB
```

### Pitfall'lar
- **Dosya boyutuna bakmadan analiz yapma** — en büyük dosyalar en önemli özellikleri gösterir
- **Frontend yapısını atlama** — style.css 1.2MB ise frontend ağırlıklı bir projedir
- **Sadece ls yapıp geçme** — her klasörü oku, en az 1-2 dosyayı açıp incele
- **Kullanıcıya "şu dosyayı oku da ne yaptığını anla" deme** — doğrudan oku ve özetle
- **Mimari model yanlış seçilirse geliştirme kararları da yanlış olur**
- **uv.lock varsa pip kullanma** — uv-managed `.venv` içinde pip bulunmaz. `pip install` hata verir. `uv sync` kullan.
- **README'deki sırayı atlama** — config dosyası kopyalama, `.env` oluşturma gibi adımlar atlanırsa proje çalışmaz. Her adımı birebir kontrol et.
- **Tek servis sanma** — proje çoklu servis çalıştırabilir (örn: FastAPI backend 8080 + Streamlit WebUI 8501). Tümünü başlat.

### Örnek Referans
Bu analiz yöntemi Odysseus projesinde uygulandı:
`references/odysseus-mimari-analiz.md`

---

## Notlar
- Her adımda eksik varsa önce onu kur/oluştur, sonra bir sonraki adıma geç.
- Kullanıcı tercihi: eksik olduğunda beklemeden devam et; onay sorusundan kaçın.
- Bu protokol her yeni proje açılışında tekrar kullanılır.
