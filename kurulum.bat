@echo off
chcp 65001 >nul
title ReYMeN Agent v1.0 - Tam Kurulum

echo ============================================
echo  ReYMeN Agent v1.0 - Kurulum
echo ============================================

:: Git LFS kontrol
where git-lfs >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Git LFS bulunamadi! LFS binary dosyalari inemez.
    echo     Yuklemek icin: git lfs install
    echo.
)

:: Git LFS objelerini cek
if exist ".git" (
    echo [*] Git LFS objeleri cekiliyor...
    git lfs pull 2>nul
)
echo.
echo NOT: ReYMeN bagimsiz bir ajandir, Hermes gerektirmez.
echo.
echo ============================================

:: Baslangic kontrolleri
setlocal enabledelayedexpansion

:: ---------- 1. GEREKSINIM KONTROLLERI ----------
set ADIM=0

:: 1.0 Windows surumu (ayrik blok, parantez yok)
set /a ADIM+=1
echo ^(1/5^) Windows kontrolu...
ver | find "10." >nul && goto win_ok
ver | find "11." >nul && goto win_ok
echo [^^!] Windows 10 veya 11 gerekli^^!
echo     Mevcut:
ver
pause
exit /b
:win_ok
echo [OK] Windows 10+

:: 1.1 Python
set /a ADIM+=1
echo ^(2/5^) Python kontrolu...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [!!] Python bulunamadi! Yukleniyor...
    winget install Python.Python.3.12 --silent --accept-package-agreements
    if !errorlevel! neq 0 (
        echo [^^!] Otomatik basarisiz^^! Suradan el ile indir:
        echo     https://www.python.org/downloads/release/python-3129/
        echo     Kurarken "Add Python to PATH" isaretle
        pause
        exit /b
    )
)
python -c "import sys; exit(0) if sys.version_info >= (3,12) else exit(1)" >nul 2>&1
if !errorlevel! neq 0 (
    echo [^^!] Python 3.12+ gerekli^^!
    python --version
    pause
    exit /b
)
for /f "tokens=*" %%i in ('python --version 2^>nul') do set PYVER=%%i
echo [OK] %PYVER%

:: 1.2 Git
set /a ADIM+=1
echo ^(3/5^) Git kontrolu...
git --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [!!] Git bulunamadi! Yukleniyor...
    winget install Git.Git --silent --accept-package-agreements
    if !errorlevel! neq 0 (
        echo [^^!] Basarisiz^^! https://git-scm.com/download/win
        pause
        exit /b
    )
)
for /f "tokens=*" %%i in ('git --version') do set GITVER=%%i
echo [OK] %GITVER%

:: 1.3 Node.js (MCP sunuculari icin)
set /a ADIM+=1
echo ^(4/7^) Node.js kontrolu...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [!!] Node.js bulunamadi! Yukleniyor...
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements
    if !errorlevel! neq 0 (
        echo [^^!] Basarisiz^^! https://nodejs.org adresinden el ile indir
        pause
        exit /b
    )
)
for /f "tokens=*" %%i in ('node --version') do set NODEVER=%%i
echo [OK] Node.js %NODEVER%

:: 1.4 FFmpeg (video/ses isleme)
set /a ADIM+=1
echo ^(5/7^) FFmpeg kontrolu...
ffmpeg -version >nul 2>&1
if !errorlevel! neq 0 (
    echo [!!] FFmpeg bulunamadi! Yukleniyor...
    winget install "FFmpeg (Shared)" --silent --accept-package-agreements 2>nul
    winget install Gyan.FFmpeg --silent --accept-package-agreements 2>nul
    where ffmpeg >nul 2>&1
    if !errorlevel! neq 0 (
        echo [^^!] Otomatik basarisiz^^! Elle indir:
        echo     https://ffmpeg.org/download.html
        echo     veya: winget install Gyan.FFmpeg
    )
)
where ffmpeg >nul 2>&1 && echo [OK] FFmpeg || echo [-] FFmpeg kurulu degil (video/ses kisitli calisir)

:: ---------- 2. REPO + VENV ----------
set /a ADIM+=1
echo ^(6/7^) Repo ve Python ortami...

:: Proje dizinini bul
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "reymen_launcher.py" (
    if exist "ReYMeN-Ajan" (
        cd ReYMeN-Ajan
    ) else (
        echo [!!] Proje dosyalari bulunamadi!
        echo     Bu script ReYMeN-Ajan klasoru icinde calistirilmali.
        echo     veya: git clone https://github.com/recaiozil-wq/reymen-agean.git
        pause
        exit /b
    )
)

:: Disk alani kontrolu (en az 500MB)
:: NOT: Turkish Windows'ta "bytes free" yerine "bayt" kullan
for /f "tokens=3" %%a in ('dir /-c "%CD%" 2^>nul ^| find "bytes"') do set FREE=%%a
if not defined FREE (
    for /f "tokens=3" %%a in ('dir /-c "%CD%" 2^>nul ^| find "bayt"') do set FREE=%%a
)
set FREE=%FREE:,=%
if defined FREE (
    if %FREE% LSS 500000000 (
        echo [^^!] Uyari: Disk alani az (500MB alti)^^!
    )
)

:: ---------- 2. SANAL ORTAM VE PAKET KURULUMU ----------
set "VENV_DIR=reymen_venv"

:: 1) reymen_venv zaten varsa direkt oraya atla
if exist "reymen_venv\Scripts\activate" (
    set "VENV_DIR=reymen_venv"
    goto venv_hazir
)

:: 2) Standart venv varsa oraya atla
if exist "venv\Scripts\activate" (
    set "VENV_DIR=venv"
    goto venv_hazir
)

:: 3) Hiçbiri yoksa sıfırdan reymen_venv oluştur
echo [..] Sanal ortam bulunamadi, yeni ortam olusturuluyor: %VENV_DIR%
python -m venv "%VENV_DIR%"
if !errorlevel! neq 0 (
    echo [!!] Sanal ortam olusturulamadi!
    echo     Cozum: Gecici olarak Windows Defender Gercek Zamanli Korumayi kapatin.
    pause
    exit /b
)

:venv_hazir
echo [OK] Aktif Sanal Ortam: %VENV_DIR%
call "%VENV_DIR%\Scripts\activate"

:: pip guncellemesi
python -m pip install --upgrade pip --quiet

:: Bağımlılıkların pyproject.toml üzerinden kurulması
if exist pyproject.toml (
    echo [..] Bagimliliklar pyproject.toml uzerinden yukleniyor...
    pip install -e . --quiet
) else (
    echo [..] pyproject.toml bulunamadi, temel paketler yukleniyor...
    pip install requests python-dotenv --quiet
)

if !errorlevel! equ 0 (
    echo [OK] Tüm paketler basariyla yuklendi.
) else (
    echo [^^!] Paket yukleme hatasi^^!
    echo     Cozum: Manuel olarak terminalde 'pip install -e .' komutunu calistirin.
    pause
    exit /b
)

:: ---------- 3. .env API ANAHTARLARI ----------
set /a ADIM+=1
echo ^(7/7^) API anahtarlari...

if not exist ".env" (
    (
        echo # ============================================================
        echo # ReYMeN Agent - API Anahtarlari
        echo # Bu dosyayi duzenleyip kendi anahtarlarini ekle
        echo # ============================================================
        echo.
        echo # === ZORUNLU: En az bir LLM provider ===
        echo # DeepSeek (en uyumlu, tavsiye edilen)
        echo # Kayit: https://platform.deepseek.com/api_keys
        echo DEEPSEEK_API_KEY=ANAHTARINI_BURAYA_YAZ
        echo.
        echo # === OPSIYONEL: Diger providerlar (yedek) ===
        echo # DeepSeek kredisi bitince otomatik gecer
        echo # OPENROUTER_API_KEY=ANAHTARINI_BURAYA_YAZ
        echo # XAI_API_KEY=ANAHTARINI_BURAYA_YAZ
        echo # GROQ_API_KEY=ANAHTARINI_BURAYA_YAZ
        echo.
        echo # === OPSIYONEL: Telegram Bot ===
        echo # BotFather'dan al: https://t.me/BotFather
        echo # /newbot komutu ile yeni bot olustur
        echo # Alinan tokeni buraya yapistir
        echo TELEGRAM_BOT_TOKEN=0000000000:ANAHTARINI_BURAYA_YAZ
        echo.
        echo # === OPSIYONEL: Harici servisler ===
        echo # FIRECRAWL_API_KEY=ANAHTARINI_BURAYA_YAZ
        echo # PERPLEXITY_API_KEY=ANAHTARINI_BURAYA_YAZ
        echo # FAL_KEY=ANAHTARINI_BURAYA_YAZ
    ) > .env
    echo.
    echo ============================================
    echo  .env dosyasi olusturuldu!
    echo ============================================
    echo.
    echo  SIMDI SU ISLEMLERI YAP:
    echo.
    echo  1. Asagidaki dosya notepad ile acilacak
    echo  2. DEEPSEEK_API_KEY satirina anahtarini yaz
    echo     Ornek: DEEPSEEK_API_KEY=sk-abc123...
    echo     Alma: https://platform.deepseek.com/api_keys
    echo  3. TELEGRAM_BOT_TOKEN varsa onu da ekle
    echo  4. Kaydet ve kapat
    echo.
    echo  API anahtari yoksa ucretsiz al:
    echo  https://platform.deepseek.com adresine git
    echo  Hesap ac -> API Keys -> Yeni key olustur
    echo.
    pause
    start notepad .env
)

echo.
echo ============================================
echo    KURULUM TAMAMLANDI!
echo ============================================
echo.
echo  KULLANIM:
echo.
echo  --- SECENEK 1: Terminal'de calistir ---
echo      reymen_venv\Scripts\activate
echo      python reymen_launcher.py
echo.
echo  --- SECENEK 2: Telegram Bot ---
echo      1. .env dosyasina TELEGRAM_BOT_TOKEN ekle
echo      2. BotFather'dan token al (/newbot)
echo      3. Baslat:
echo         reymen_venv\Scripts\activate ^&^& python reymen/ag/telegram_bot.py
echo.
echo  --- SSS / HATA COZUMU ---
echo.
echo  "DEEPSEEK_API_KEY kredisi bitti" (402 hatasi):
echo     .env'ye OPENROUTER_API_KEY ekle, fallback otomatik gecer
echo.
echo  "409 Conflict" (Telegram bot baglanamiyor):
echo     BotFather -> /mybots -> botunu sec
echo     API Token -> Revoke -> Yeni token al
echo     Yeni tokeni .env'ye yaz, tekrar baslat
echo.
echo  "ModuleNotFoundError" / "No module named 'beyin'":
echo     reymen_venv\Scripts\activate
echo     pip install -e .
echo.
echo  "pip/pyton komutu calismiyor" (AppLocker):
echo     PowerShell (Yonetici):
echo     Set-MpPreference -DisableRealtimeMonitoring $true
echo     Sonra tekrar dene
echo.
echo  GitHub: https://github.com/recaiozil-wq/reymen-agean
echo.
pause
