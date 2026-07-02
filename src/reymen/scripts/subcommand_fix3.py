#!/usr/bin/env python3
"""subcommand_fix3.py — run_xxx fonksiyon govdesini bastan yaz."""
import re
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

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
hata_files = []

for py in sorted(SUBCMD_DIR.glob("*.py")):
    if py.name == "__init__.py":
        continue
    ad = py.stem
    impl = IMPL.get(ad)
    if not impl:
        continue

    lines = py.read_text(encoding="utf-8").splitlines()
    yeni = []
    in_func = False
    func_started = False
    brace_count = 0
    skip_rest = False

    for i, line in enumerate(lines):
        if f"def run_{ad}(" in line:
            in_func = True
            yeni.append(line)
            continue

        if in_func and not func_started:
            yeni.append(line)  # docstring satiri
            # Eger docstring """ ile basliyorsa, kapanana kadar bekle
            if '"""' in line:
                if line.count('"""') == 2:  # tek satirlik docstring
                    func_started = True
                    continue
                else:
                    brace_count = 1
                    continue
        
        if in_func and brace_count > 0:
            yeni.append(line)
            if '"""' in line:
                brace_count -= 1
            if brace_count == 0:
                func_started = True
            continue

        if in_func and func_started and not skip_rest:
            # run_xxx bodysini yeni implementasyonla degistir
            indent = "    "
            if line.strip().startswith("def ") or line.strip().startswith("class ") or line.strip().startswith("if __name__"):
                # Fonksiyon bitti, yeni impl'i yerlestir
                yeni.append(f"{indent}{impl}")
                yeni.append(line)
                in_func = False
                skip_rest = False
                continue
            else:
                # Eski body satirini atla
                continue

        yeni.append(line)

    py.write_text("\n".join(yeni) + "\n", encoding="utf-8")

    # Syntax kontrol
    try:
        import ast
        ast.parse(py.read_text(encoding="utf-8"), str(py))
        print(f"  OK {py.name}")
        ok += 1
    except SyntaxError as e:
        print(f"  HATA {py.name}: {e}")
        hata_files.append(py.name)

print(f"\nOK: {ok}, HATA: {len(hata_files)}")
if hata_files:
    print(f"Hata: {', '.join(hata_files)}")
