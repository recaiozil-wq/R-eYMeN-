#!/usr/bin/env bash
# ReYMeN — Linux/macOS tek komut kurulum
# Kullanim:
#   curl -fsSL https://raw.githubusercontent.com/Watcher-Hermes/ReYMeN-Ajan-v2/main/install.sh | bash
#
# Windows icin: kurulum.bat kullan

set -euo pipefail

REPO="Watcher-Hermes/ReYMeN-Ajan-v2"
BRANCH="main"
REPO_URL="https://github.com/$REPO.git"

# Renkler
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { printf "${GREEN}==>${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}==>${NC} %s\n" "$*"; }
error() { printf "${RED}==>${NC} %s\n" "$*"; }
header(){ printf "\n${CYAN}════════════════════════════════════════${NC}\n${BOLD} %s${NC}\n${CYAN}════════════════════════════════════════${NC}\n" "$*"; }

# Platform tespiti
detect_platform() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)       echo "unknown" ;;
    esac
}

PLATFORM=$(detect_platform)
HEDEF_DIZIN="${REYMEN_HOME:-$HOME/reymen}"

header "ReYMeN Agent Kurulumu"
info "Platform: $PLATFORM"
info "Hedef: $HEDEF_DIZIN"
echo ""

# ---------- 1. BAGIMLILIK KONTROLU ----------
info "(1/4) Bagimliliklar kontrol ediliyor..."
local eksik=0

# Python
if ! command -v python3 &>/dev/null; then
    error "python3 bulunamadi!"
    if [ "$PLATFORM" = "linux" ]; then
        echo "  Kurmak icin: sudo apt install python3 python3-pip python3-venv"
        echo "  veya: sudo dnf install python3 python3-pip"
        echo "  veya: sudo pacman -S python python-pip"
    elif [ "$PLATFORM" = "macos" ]; then
        echo "  Kurmak icin: brew install python3"
    fi
    eksik=1
else
    pyver=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d. -f1-2)
    if [ "$(echo "$pyver >= 3.11" | bc -l 2>/dev/null)" != "1" ] && [ "$pyver" != "3.11" ] && [ "$pyver" != "3.12" ] && [ "$pyver" != "3.13" ]; then
        warn "Python $pyver - Python 3.11+ onerilir"
    fi
    echo "  [OK] Python $pyver"
fi

# Git
if ! command -v git &>/dev/null; then
    error "git bulunamadi!"
    if [ "$PLATFORM" = "linux" ]; then
        echo "  sudo apt install git"
    elif [ "$PLATFORM" = "macos" ]; then
        echo "  brew install git"
    fi
    eksik=1
else
    echo "  [OK] Git $(git --version 2>&1 | cut -d' ' -f3)"
fi

if [ "$eksik" = "1" ]; then
    error "Eksik bagimliliklar. Once kurun, sonra tekrar dene."
    exit 1
fi

# ---------- 2. REPO + VENV ----------
info "(2/4) Repo klonlaniyor..."
if [ -d "$HEDEF_DIZIN" ]; then
    warn "$HEDEF_DIZIN zaten var. Sifirlaniyor..."
    rm -rf "$HEDEF_DIZIN"
fi

git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$HEDEF_DIZIN"
cd "$HEDEF_DIZIN"

info "(3/4) Sanal ortam olusturuluyor..."
python3 -m venv reymen_venv

if [ "$PLATFORM" = "windows" ]; then
    source reymen_venv/Scripts/activate 2>/dev/null || . reymen_venv/Scripts/activate
else
    source reymen_venv/bin/activate
fi

# pip guncelle
python3 -m pip install --upgrade pip -q

# Paketler
if [ -f requirements.txt ]; then
    pip install -r requirements.txt -q
else
    pip install requests python-dotenv -q
fi
echo "  [OK] Paketler yuklendi"

# ---------- 3. .env API ANAHTARLARI ----------
info "(4/4) API anahtarlari..."
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# ============================================================
# ReYMeN Agent - API Anahtarlari
# Bu dosyayi duzenleyip kendi anahtarlarini ekle
# ============================================================

# === ZORUNLU: En az bir LLM provider ===
# DeepSeek (en uyumlu, tavsiye edilen)
# Kayit: https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY=ANAHTARINI_BURAYA_YAZ

# === OPSIYONEL: Diger providerlar (yedek) ===
# DeepSeek kredisi bitince otomatik gecer
# OPENROUTER_API_KEY=ANAHTARINI_BURAYA_YAZ
# XAI_API_KEY=ANAHTARINI_BURAYA_YAZ
# GROQ_API_KEY=ANAHTARINI_BURAYA_YAZ

# === OPSIYONEL: Telegram Bot ===
# BotFather'dan al: https://t.me/BotFather
# /newbot komutu ile yeni bot olustur
# TELEGRAM_BOT_TOKEN=000000_ANAHTARINI_BURAYA_YAZ

# === OPSIYONEL: Harici servisler ===
# FIRECRAWL_API_KEY=ANAHTARINI_BURAYA_YAZ
# PERPLEXITY_API_KEY=ANAHTARINI_BURAYA_YAZ
# FAL_KEY=ANAHTARINI_BURAYA_YAZ
ENVEOF
    echo ""
    echo "  ============================================"
    echo "  !! .env dosyasi olusturuldu!"
    echo "  ============================================"
    echo ""
    echo "  Su dosyayi duzenle: $HEDEF_DIZIN/.env"
    echo "  DEEPSEEK_API_KEY satirina anahtarini yaz"
    echo "  Anahtar almasi: https://platform.deepseek.com/api_keys"
    echo ""
fi

# ---------- 4. BITIS ----------
header "Kurulum Tamamlandi!"
echo ""
echo "KULLANIM:"
echo ""
echo "  cd $HEDEF_DIZIN"
echo "  source reymen_venv/bin/activate"
echo "  python reymen_launcher.py"
echo ""
echo "SSS / HATA COZUMU:"
echo ""
echo "  DeepSeek kredisi bitti (402):"
echo "    .env'ye OPENROUTER_API_KEY ekle, fallback otomatik gecer"
echo ""
echo "  409 Conflict (Telegram bot):"
echo "    BotFather -> /mybots -> botun sec -> Revoke -> yeni token"
echo ""
echo "  ModuleNotFoundError:"
echo "    source reymen_venv/bin/activate && pip install -r requirements.txt"
echo ""
echo "GitHub: https://github.com/$REPO"
echo ""
