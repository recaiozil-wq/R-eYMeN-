#!/usr/bin/env bash
# ReYMeN — Tek komut kurulum (Linux/Mac)
# Kullanım: curl -fsSL https://raw.githubusercontent.com/recaiozil-wq/reymen-agean/main/install.sh | bash
set -euo pipefail

REPO="recaiozil-wq/reymen-agean"
BRANCH="main"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== ReYMeN Agent Kurulumu ===${NC}"
echo ""

# Python kontrol
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
        PY_MIN=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$PY_MAJ" -ge 3 ] && [ "$PY_MIN" -ge 10 ]; then
            PYTHON="$cmd"
            echo -e "${GREEN}✓ Python $PY_VER bulundu: $cmd${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}✗ Python 3.10+ gerekli. Yüklemek için:${NC}"
    echo "  sudo apt install python3 python3-pip python3-venv  # Debian/Ubuntu"
    echo "  sudo dnf install python3 python3-pip               # Fedora"
    echo "  brew install python3                                # Mac"
    exit 1
fi

# Git kontrol
if ! command -v git &>/dev/null; then
    echo -e "${RED}✗ git gerekli. Yüklemek için:${NC}"
    echo "  sudo apt install git   # Debian/Ubuntu"
    echo "  sudo dnf install git   # Fedora"
    echo "  brew install git       # Mac"
    exit 1
fi

# Projeyi klonla
if [ -d "ReYMeN-Ajan" ]; then
    echo -e "${YELLOW}⚠ Dizin 'ReYMeN-Ajan' zaten var. Güncelleniyor...${NC}"
    cd ReYMeN-Ajan
    git pull origin "$BRANCH"
else
    echo "Proje klonlanıyor..."
    git clone --depth 1 "https://github.com/$REPO.git"
    cd ReYMeN-Ajan
fi

# Sanal ortam
echo ""
echo "Sanal ortam oluşturuluyor..."
"$PYTHON" -m venv venv
source venv/bin/activate

# Bağımlılıklar
echo ""
echo "Bağımlılıklar yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== ReYMeN Agent v1.0 - Kurulum ==="
echo ""

# Git LFS kontrol
if ! command -v git-lfs &>/dev/null 2>&1; then
    echo "[!] Git LFS bulunamadi! LFS binary dosyalari inemez."
    echo "    Yüklemek icin: https://git-lfs.com"
    echo ""
fi

# LFS objelerini cek
if [ -d ".git" ]; then
    echo "[*] Git LFS objeleri cekiliyor..."
    git lfs pull 2>/dev/null || true
fi
echo -e "Sonraki adımlar:"
echo -e "  1. ${YELLOW}cd ReYMeN-Ajan && source venv/bin/activate${NC}"
echo -e "  2. ${YELLOW}cp .env.example .env${NC}"
echo -e "  3. ${YELLOW}chmod 600 .env${NC}"
echo -e "  4. .env dosyasını düzenle (en az DEEPSEEK_API_KEY)"
echo -e "  5. ${YELLOW}python reymen_launcher.py${NC}"
echo ""
echo -e "Detaylı bilgi: https://github.com/$REPO"
