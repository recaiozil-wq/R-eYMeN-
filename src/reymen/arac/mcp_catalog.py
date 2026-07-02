# -*- coding: utf-8 -*-
"""mcp_catalog.py — MCP Sunucu Kataloğu.

ReYMeN'teki MCP Catalog'un ReYMeN uyarlaması.
Önceden tanımlı MCP sunucularını listeler ve
tek komutla kurulum sağlar.

ToolRegistry'e kayıt için:
    TOOL_META = {...}
    def run(...)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional

TOOL_META = {
    "ad": "mcp_catalog",
    "versiyon": "1.0.0",
    "aciklama": "Önceden tanımlı MCP sunucularını listeler ve kurar.",
    "kategori": "mcp",
    "parametreler": {
        "islem": {
            "tip": "str",
            "aciklama": "İşlem: 'listele', 'kur', 'bilgi'",
            "zorunlu": True,
        },
        "sunucu_adi": {
            "tip": "str",
            "aciklama": "Kurulacak/bilgisi alınacak sunucu adı (kur/bilgi için)",
            "zorunlu": False,
        },
    },
    "ornek": (
        'MCP_CATALOG(islem="listele")\n'
        'MCP_CATALOG(islem="kur", sunucu_adi="github")\n'
        'MCP_CATALOG(islem="bilgi", sunucu_adi="filesystem")'
    ),
}

# Katalog: ad -> kurulum bilgisi
KATALOG = {
    "github": {
        "adi": "GitHub MCP",
        "aciklama": "GitHub API: issue, PR, repo, dosya yönetimi",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
    },
    "filesystem": {
        "adi": "Dosya Sistemi MCP",
        "aciklama": "Dosya okuma, yazma, listeleme, arama",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "env": {},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    },
    "puppeteer": {
        "adi": "Puppeteer MCP",
        "aciklama": "Tarayıcı otomasyonu: sayfa yükleme, ekran görüntüsü, JS çalıştırma",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": {},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
    },
    "sqlite": {
        "adi": "SQLite MCP",
        "aciklama": "SQLite veritabanı: sorgu, şema, tablo yönetimi",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite", "."],
        "env": {},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
    },
    "brave-search": {
        "adi": "Brave Search MCP",
        "aciklama": "Brave Search API ile web araması",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": ""},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
    },
    "fetch": {
        "adi": "Web Fetch MCP",
        "aciklama": "Web sayfalarını indirme ve içerik çıkarma",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "env": {},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
    },
    "sequential-thinking": {
        "adi": "Sıralı Düşünme MCP",
        "aciklama": "Karmaşık problemler için adım adım düşünme zinciri",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": {},
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/sequential-thinking",
    },
    "playwright": {
        "adi": "Playwright MCP",
        "aciklama": "Tarayıcı otomasyonu: sayfa, tıklama, form, ekran görüntüsü",
        "komut": "npx",
        "args": ["-y", "@playwright/mcp"],
        "env": {},
        "dokuman": "https://github.com/microsoft/playwright-mcp",
    },
    "browser-use": {
        "adi": "Browser Use",
        "aciklama": "AI destekli tarayıcı otomasyonu: görsel + DOM tabanlı",
        "komut": "python",
        "args": ["-m", "browser_use"],
        "env": {},
        "dokuman": "https://github.com/browser-use/browser-use",
    },
}


def _katalog_yolu() -> Path:
    """Katalog dosyasının yolu."""
    return Path.cwd() / ".ReYMeN" / "mcp_catalog.json"


def _katalog_kaydet():
    """Katalog durumunu JSON'a kaydet (hangi sunucular kuruldu vs)."""
    dosya = _katalog_yolu()
    durum = {
        s["adi"]: {"kurulu": False, "env_var": list(s.get("env", {}).keys())}
        for s in KATALOG.values()
    }
    dosya.parent.mkdir(parents=True, exist_ok=True)
    dosya.write_text(json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8")


def listele() -> str:
    """Katalogdaki tüm MCP sunucularını listele."""
    satirlar = ["📦 MCP Sunucu Kataloğu", "=" * 40, ""]

    for ad, bilgi in KATALOG.items():
        env_str = ""
        if bilgi.get("env"):
            gerekli = [f"${k}" for k in bilgi["env"].keys()]
            env_str = f" 🔑 {', '.join(gerekli)}"

        satirlar.append(f"  {ad}")
        satirlar.append(f"    {bilgi['adi']}: {bilgi['aciklama']}{env_str}")
        satirlar.append("")

    satirlar.append(f"Toplam: {len(KATALOG)} sunucu")
    satirlar.append("Kullanım: MCP_CATALOG(islem='kur', sunucu_adi='github')")
    return "\n".join(satirlar)


def bilgi(sunucu_adi: str) -> str:
    """Belirli bir MCP sunucusu hakkında detaylı bilgi."""
    if sunucu_adi not in KATALOG:
        mevcut = ", ".join(KATALOG.keys())
        return f"[MCP_CATALOG] '{sunucu_adi}' bulunamadı. Mevcut: {mevcut}"

    bilgi = KATALOG[sunucu_adi]
    satirlar = [
        f"📖 {bilgi['adi']}",
        f"  Açıklama: {bilgi['aciklama']}",
        f"  Komut: {bilgi['komut']} {' '.join(bilgi['args'])}",
    ]

    if bilgi.get("env"):
        satirlar.append(f"  Gerekli env: {', '.join(bilgi['env'].keys())}")
    if bilgi.get("dokuman"):
        satirlar.append(f"  Doküman: {bilgi['dokuman']}")

    # Config'de var mı kontrol et
    config_yolu = Path.cwd() / "config.yaml"
    if config_yolu.exists():
        cfg = config_yolu.read_text(encoding="utf-8")
        if f"mcp_servers:" in cfg and sunucu_adi in cfg:
            satirlar.append(f"  Durum: ⚙️ config.yaml'da tanımlı")

    return "\n".join(satirlar)


def _config_ekle(sunucu_adi: str) -> bool:
    """Sunucuyu config.yaml'a MCP sunucusu olarak ekle."""
    bilgi = KATALOG.get(sunucu_adi)
    if not bilgi:
        return False

    config_yolu = Path.cwd() / "config.yaml"
    yaml_ek = (
        f"\n  {sunucu_adi}:\n"
        f"    command: {bilgi['komut']}\n"
        f"    args: {json.dumps(bilgi['args'])}\n"
    )
    if bilgi.get("env"):
        env_yaml = "\n".join(
            f"      {k}: \"${{{k}}}\"" for k in bilgi["env"]
        )
        yaml_ek += f"    env:\n{env_yaml}\n"

    try:
        if config_yolu.exists():
            icerik = config_yolu.read_text(encoding="utf-8")
            if "mcp_servers:" not in icerik:
                icerik += "\n\n# MCP Sunuculari\nmcp_servers:\n"
            icerik += yaml_ek
            config_yolu.write_text(icerik, encoding="utf-8")
            return True
        else:
            config_yolu.write_text(
                "# ReYMeN Yapılandırma\n\nmcp_servers:\n" + yaml_ek,
                encoding="utf-8",
            )
            return True
    except Exception:
        return False


def kur(sunucu_adi: str) -> str:
    """MCP sunucusunu kur (config'e ekle)."""
    if sunucu_adi not in KATALOG:
        mevcut = ", ".join(KATALOG.keys())
        return f"[MCP_CATALOG] '{sunucu_adi}' bulunamadı. Mevcut: {mevcut}"

    bilgi = KATALOG[sunucu_adi]

    # Env kontrol
    env_eksik = []
    for env_key in bilgi.get("env", {}):
        if not os.environ.get(env_key):
            env_eksik.append(env_key)

    # Config'e ekle
    if _config_ekle(sunucu_adi):
        satirlar = [f"✅ {bilgi['adi']} config.yaml'a eklendi."]
        if env_eksik:
            satirlar.append(f"⚠️  Eksik env: {', '.join(env_eksik)}")
            satirlar.append(f"   .env dosyasına ekleyin.")
        satirlar.append(f"   Kullanmak için motor'u yeniden başlatın.")
        return "\n".join(satirlar)
    else:
        return f"[MCP_CATALOG] {bilgi['adi']} eklenemedi."


def run(islem: str, sunucu_adi: str = "") -> str:
    """MCP kataloğunu yönet.

    Args:
        islem: 'listele', 'kur', 'bilgi'
        sunucu_adi: İşlem yapılacak sunucu adı

    Returns:
        str: İşlem sonucu
    """
    islem = islem.strip().lower()

    if islem == "listele":
        _katalog_kaydet()
        return listele()
    elif islem == "bilgi":
        if not sunucu_adi:
            return "[MCP_CATALOG] 'bilgi' için 'sunucu_adi' gerekli."
        return bilgi(sunucu_adi)
    elif islem == "kur":
        if not sunucu_adi:
            return "[MCP_CATALOG] 'kur' için 'sunucu_adi' gerekli."
        return kur(sunucu_adi)
    else:
        return f"[MCP_CATALOG] Bilinmeyen işlem: '{islem}'. Şunlar: listele, kur, bilgi"


def check_fn(parametreler: dict) -> tuple:
    """Doğrulama: islem parametresi zorunlu."""
    if not parametreler.get("islem"):
        return False, "MCP_CATALOG: 'islem' parametresi zorunludur"
    return True, ""


# Kısa kullanım alias
MCP_CATALOG = run
