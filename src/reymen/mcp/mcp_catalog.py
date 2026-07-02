# -*- coding: utf-8 -*-
"""reymen/mcp/mcp_catalog.py — MCP Sunucu Kataloğu.

Önceden tanımlı MCP sunucularını listeler ve tek komutla kurulum sağlar.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Katalog: ad → kurulum bilgisi ────────────────────────────────
KATALOG = {
    "github": {
        "adi": "GitHub MCP",
        "aciklama": "GitHub API: issue, PR, repo, dosya yönetimi",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
    },
    "filesystem": {
        "adi": "Dosya Sistemi MCP",
        "aciklama": "Güvenli dosya okuma/yazma/dizin işlemleri",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    },
    "postgres": {
        "adi": "PostgreSQL MCP",
        "aciklama": "PostgreSQL veritabanı sorgulama ve şema okuma",
        "komut": "npx",
        "args": ["-y", "@anthropic/server-postgres"],
        "transport": "stdio",
        "dokuman": "https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp-server-postgres",
    },
    "sqlite": {
        "adi": "SQLite MCP",
        "aciklama": "SQLite veritabanı sorgulama ve yönetim",
        "komut": "uvx",
        "args": ["mcp-server-sqlite", "--db", "reymen.db"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
    },
    "memory": {
        "adi": "Bellek (Knowledge Graph) MCP",
        "aciklama": "JSON tabanlı bellek/knowledge graph depolama",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
    },
    "puppeteer": {
        "adi": "Puppeteer (Browser) MCP",
        "aciklama": "Headless Chrome ile web scraping ve ekran görüntüsü",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
    },
    "playwright": {
        "adi": "Playwright MCP",
        "aciklama": "Tarayıcı otomasyonu: sayfa yükleme, tıklama, form doldurma, ekran görüntüsü",
        "komut": "npx",
        "args": ["-y", "@playwright/mcp"],
        "transport": "stdio",
        "dokuman": "https://github.com/microsoft/playwright-mcp",
    },
    "brave-search": {
        "adi": "Brave Search MCP",
        "aciklama": "Brave Search API ile web arama",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
    },
    "sequential-thinking": {
        "adi": "Sequential Thinking MCP",
        "aciklama": "Adım adım düşünme ve problem çözme",
        "komut": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "transport": "stdio",
        "dokuman": "https://github.com/modelcontextprotocol/servers/tree/main/src/sequential-thinking",
    },
    "reymen-local": {
        "adi": "ReYMeN Local MCP",
        "aciklama": "ReYMeN'in kendi araçlarını MCP üzerinden sunar",
        "command": ["python", "-m", "reymen.mcp.server"],
        "transport": "stdio",
        "dokuman": "Yerleşik — reymen.mcp.server modülü",
    },
}


def listele() -> list[dict]:
    """Katalogdaki tüm sunucuları listele."""
    return [
        {
            "ad": ad,
            "adi": bilgi["adi"],
            "aciklama": bilgi["aciklama"],
            "transport": bilgi.get("transport", "stdio"),
            "komut": bilgi.get("komut", ""),
        }
        for ad, bilgi in KATALOG.items()
    ]


def bilgi(sunucu_adi: str) -> Optional[dict]:
    """Belirtilen sunucu hakkında detaylı bilgi."""
    if sunucu_adi not in KATALOG:
        return None
    return KATALOG[sunucu_adi]


def kur(sunucu_adi: str) -> dict:
    """MCP sunucusunu çalışma zamanına ekle (kurulum+yapılandırma).

    Not: Bu fonksiyon sadece yapılandırma bilgisini döndürür.
    Gerçek MCP sunucu başlatma config.yaml üzerinden veya
    mcp_manager().ekle() ile yapılır.
    """
    if sunucu_adi not in KATALOG:
        return {"durum": "hata", "hata": f"'{sunucu_adi}' katalogda yok"}

    bilgiler = KATALOG[sunucu_adi]
    cfg = {
        "command": bilgiler.get("command")
        or [bilgiler["komut"]] + bilgiler.get("args", []),
        "transport": bilgiler.get("transport", "stdio"),
    }

    # Async manager'a ekle
    try:
        from reymen.mcp.mcp_manager import mcp_manager
        import asyncio

        mgr = mcp_manager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            baglanti = mgr.ekle(sunucu_adi, cfg)
            sayi = loop.run_until_complete(baglanti.tools_kesfet())
            loop.close()
            return {
                "durum": "basarili",
                "sunucu": sunucu_adi,
                "tool_sayisi": sayi,
                "config": cfg,
            }
        except Exception:
            loop.close()
            return {
                "durum": "kaydedildi",
                "sunucu": sunucu_adi,
                "not": "Sunucu kaydedildi ama bağlantı kurulamadı (çalışmıyor olabilir)",
                "config": cfg,
            }
    except Exception as e:
        return {
            "durum": "kaydedildi",
            "sunucu": sunucu_adi,
            "config": cfg,
            "not": f"Yapılandırma hazır, manuel başlatma gerekebilir: {e}",
        }
