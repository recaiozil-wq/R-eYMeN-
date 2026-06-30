# ReYMeN — Tek komut kurulum (Windows PowerShell)
# Kullanım: irm https://raw.githubusercontent.com/Watcher-Hermes/ReYMeN-Ajan/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$Repo = "Watcher-Hermes/ReYMeN-Ajan-v2"
$Branch = "main"

Write-Host "=== ReYMeN Agent Kurulumu ===" -ForegroundColor Green
Write-Host ""

# Python kontrol
$python = $null
foreach ($cmd in @("python3", "python")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $python = $cmd
                Write-Host "✓ Python $major.$minor bulundu: $cmd" -ForegroundColor Green
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Host "✗ Python 3.10+ gerekli" -ForegroundColor Red
    Write-Host "İndir: https://www.python.org/downloads/"
    exit 1
}

# Git kontrol
try {
    & git --version | Out-Null
    Write-Host "✓ git bulundu" -ForegroundColor Green
} catch {
    Write-Host "✗ git gerekli" -ForegroundColor Red
    Write-Host "İndir: https://git-scm.com/downloads"
    exit 1
}

# Projeyi klonla
if (Test-Path "ReYMeN-Ajan") {
    Write-Host "⚠ Dizin 'ReYMeN-Ajan' zaten var. Güncelleniyor..." -ForegroundColor Yellow
    Set-Location "ReYMeN-Ajan"
    & git pull origin $Branch
} else {
    Write-Host "Proje klonlanıyor..."
    & git clone --depth 1 "https://github.com/$Repo.git"
    Set-Location "ReYMeN-Ajan"
}

# Sanal ortam
Write-Host ""
Write-Host "Sanal ortam oluşturuluyor..."
& $python -m venv venv
$venvActivate = Join-Path (Get-Location) "venv\Scripts\Activate.ps1"
. $venvActivate

# Bağımlılıklar
Write-Host ""
Write-Host "Bağımlılıklar yükleniyor..."
& python -m pip install --upgrade pip
& pip install -r requirements.txt

Write-Host ""
Write-Host "=== Kurulum Tamamlandı! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Sonraki adımlar:" -ForegroundColor Yellow
Write-Host "  1. . $venvActivate"
Write-Host "  2. Copy-Item .env.example .env"
Write-Host "  3. .env dosyasını düzenle (en az DEEPSEEK_API_KEY)"
Write-Host "  4. python reymen_launcher.py"
