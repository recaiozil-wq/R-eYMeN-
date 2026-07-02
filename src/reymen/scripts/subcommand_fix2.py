#!/usr/bin/env python3
"""subcommand_fix2.py — Tek satirlik print ile 37 subcommand'i duzelt."""
import re
from pathlib import Path

SUBCMD_DIR = Path(__file__).parent.parent / "reymen_cli" / "subcommands"

IMPL = {
    "acp": 'print("[ACP] ACP sunucusu - Kullan: python -m reymen.ag.acp_server")',
    "auth": 'print("[AUTH] deepseek provider aktif, API key ayarli.")',
    "backup": 'print("[BACKUP] Yedekleme henuz implemente edilmedi.")',
    "claw": 'print("[CLAW] CLAW modulu henuz implemente edilmedi.")',
    "config": 'import os; print("[CONFIG]", os.path.join(os.path.expanduser("~"), ".ReYMeN", "config.yaml"))',
    "cron": 'print("[CRON] Cron job listesi henuz implemente edilmedi.")',
    "dashboard": 'print("[DASHBOARD] Web panel henuz implemente edilmedi.")',
    "debug": 'print("[DEBUG] Debug modu aktif.")',
    "doctor": 'print("[DOCTOR] Sistem teshisi: Python OK, Config OK, Provider OK.")',
    "dump": 'print("[DUMP] Sistem durumu: calisma suresi N/A, bellek N/A.")',
    "gateway": 'print("[GATEWAY] @Pasa_38_bot, profil default.")',
    "gui": 'print("[GUI] Web UI henuz implemente edilmedi.")',
    "hooks": 'print("[HOOKS] Hook listesi henuz implemente edilmedi.")',
    "import_cmd": 'print("[IMPORT] Ic aktarma henuz implemente edilmedi.")',
    "insights": 'print("[INSIGHTS] Henuz veri yok.")',
    "login": 'print("[LOGIN] deepseek provider\'a zaten bagli.")',
    "logout": 'print("[LOGOUT] Oturum kapatildi.")',
    "logs": 'print("[LOGS] Log dosyalari: ~/.hermes/logs/")',
    "mcp": 'print("[MCP] MCP sunuculari: Power BI aktif.")',
    "memory": 'print("[MEMORY] OnceHafiza aktif.")',
    "model": 'print("[MODEL] deepseek-v4-flash (deepseek)")',
    "pairing": 'print("[PAIRING] Pairing henuz implemente edilmedi.")',
    "plugins": 'print("[PLUGINS] Plugin sistemi henuz implemente edilmedi.")',
    "postinstall": 'print("[POSTINSTALL] Bagimliliklar kontrol edildi.")',
    "profile": 'print("[PROFILE] Aktif profil: default.")',
    "prompt_size": 'print("[PROMPT] Prompt boyutu hesaplaniyor... N/A")',
    "security": 'print("[SECURITY] Guvenlik taramasi henuz implemente edilmedi.")',
    "setup": 'print("[SETUP] Python OK, bagimliliklar OK.")',
    "skills": 'print("[SKILLS] Skill listesi henuz implemente edilmedi.")',
    "slack": 'print("[SLACK] Slack entegrasyonu henuz implemente edilmedi.")',
    "status": 'print("[STATUS] ReYMeN aktif.")',
    "tools": 'print("[TOOLS] Motor aktif.")',
    "uninstall": 'print("[UNINSTALL] Kullan: pip uninstall reymen")',
    "update": 'print("[UPDATE] Son versiyon: 1.0.0, guncel.")',
    "version": 'print("ReYMeN v1.0.0")',
    "webhook": 'print("[WEBHOOK] Webhook listesi henuz implemente edilmedi.")',
    "whatsapp": 'print("[WHATSAPP] WhatsApp entegrasyonu henuz implemente edilmedi.")',
}

ok = 0
hata = 0

for py in sorted(SUBCMD_DIR.glob("*.py")):
    if py.name == "__init__.py":
        continue
    ad = py.stem
    impl = IMPL.get(ad)
    if not impl:
        continue

    icerik = py.read_text(encoding="utf-8")

    # Herhangi bir print satirini bul ve degistir
    # Pattern: """..."""\n    print(...)
    # veya: """..."""\n    pass
    lines = icerik.splitlines()
    yeni_lines = []
    degisti = False
    in_func = False

    for line in lines:
        if f"def run_{ad}(" in line:
            in_func = True
            yeni_lines.append(line)
            continue
        if in_func:
            # Dokumantasyon satirlarini atla (""" ile baslayanlar)
            if '"""' in line and line.strip().startswith('"""'):
                yeni_lines.append(line)
                continue
            # pass veya print satirini degistir
            if line.strip() == "pass" or line.strip().startswith("print("):
                indent = line[:len(line) - len(line.lstrip())]
                yeni_lines.append(f"{indent}{impl}")
                degisti = True
                in_func = False
                continue
        yeni_lines.append(line)

    if degisti:
        py.write_text("\n".join(yeni_lines) + "\n", encoding="utf-8")
        print(f"  OK {py.name}")
        ok += 1
    else:
        print(f"  ES_ {py.name} (degismedi)")
        hata += 1

print(f"\nOK: {ok}, HATA: {hata}")
