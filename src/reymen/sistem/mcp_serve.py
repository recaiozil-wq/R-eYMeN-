# -*- coding: utf-8 -*-
"""
mcp_serve.py — ReYMeN MCP (Model Context Protocol) Sunucusu.

ReYMeN'i Claude Code, Cursor, Windsurf vb. MCP istemcilerine expose eder.
Stdio uzerinden JSON-RPC 2.0 protokolu kullanir.

Calistirmak icin:
    python mcp_serve.py

Claude Code entegrasyonu (.claude/settings.json):
    "mcpServers": {
      "ReYMeN": {
        "command": "python",
        "args": ["C:/path/to/ReYMeN_projesi/mcp_serve.py"]
      }
    }

Sunulan araclar:
  - ReYMeN_run(hedef)         — Ajani belirtilen hedefle calistir
  - ReYMeN_status()           — Ajan durumu
  - ReYMeN_memory_search(sorgu) — Anlamsal hafizada ara
  - ReYMeN_file_read(dosya)   — Dosya oku
  - ReYMeN_file_write(dosya, icerik) — Dosya yaz
  - ReYMeN_shell(komut)       — Kabuk komutu calistir
  - ReYMeN_skills_list()      — Kristal becerileri listele
  - ReYMeN_providers_list()   — Kullanilabilir LLM providerlari
"""
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

# ── MCP Protokol Sabitleri ───────────────────────────────────────────
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "ReYMeN", "version": "1.0.0"}

# ── Ajan Durum Tamponu ───────────────────────────────────────────────
_durum = {"calisiyor": False, "son_sonuc": "", "son_hedef": ""}
_durum_kilit = threading.Lock()


# ── Araç Tanimlamalari ───────────────────────────────────────────────

TOOLS = [
    {
        "name": "ReYMeN_run",
        "description": "ReYMeN ajanini belirtilen hedefle calistir ve sonucu dondur.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hedef": {"type": "string", "description": "Ajanin gerceklestirecegi gorev"}
            },
            "required": ["hedef"],
        },
    },
    {
        "name": "ReYMeN_status",
        "description": "ReYMeN ajaninin mevcut durumunu sorgula.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ReYMeN_memory_search",
        "description": "ReYMeN anlamsal hafizasinda arama yap.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sorgu": {"type": "string", "description": "Arama sorgusu"}
            },
            "required": ["sorgu"],
        },
    },
    {
        "name": "ReYMeN_file_read",
        "description": "Proje dizininde bir dosyayi oku.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dosya": {"type": "string", "description": "Dosya yolu (mutlak veya goreceli)"}
            },
            "required": ["dosya"],
        },
    },
    {
        "name": "ReYMeN_file_write",
        "description": "Proje dizininde bir dosyaya yaz.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dosya": {"type": "string"},
                "icerik": {"type": "string"},
            },
            "required": ["dosya", "icerik"],
        },
    },
    {
        "name": "ReYMeN_shell",
        "description": "Proje dizininde kabuk komutu calistir.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "komut": {"type": "string", "description": "Shell komutu"}
            },
            "required": ["komut"],
        },
    },
    {
        "name": "ReYMeN_skills_list",
        "description": "ReYMeN'in kristallesmis beceri kartlarini listele.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ReYMeN_providers_list",
        "description": "Kullanilabilir LLM provider listesini dondur.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# ── Araç Uygulayicilari ──────────────────────────────────────────────

def _arac_calistir(name: str, args: dict) -> str:
    try:
        if name == "ReYMeN_run":
            return _run_ajan(args.get("hedef", ""))
        if name == "ReYMeN_status":
            return _get_durum()
        if name == "ReYMeN_memory_search":
            return _hafiza_ara(args.get("sorgu", ""))
        if name == "ReYMeN_file_read":
            return _dosya_oku(args.get("dosya", ""))
        if name == "ReYMeN_file_write":
            return _dosya_yaz(args.get("dosya", ""), args.get("icerik", ""))
        if name == "ReYMeN_shell":
            return _shell_calistir(args.get("komut", ""))
        if name == "ReYMeN_skills_list":
            return _beceri_listele()
        if name == "ReYMeN_providers_list":
            return _provider_listele()
        return f"Bilinmeyen arac: {name}"
    except Exception as e:
        return f"[Hata] {name}: {e}"


def _run_ajan(hedef: str) -> str:
    with _durum_kilit:
        if _durum["calisiyor"]:
            return "Ajan zaten calisiyor. Lutfen bekleyin."
        _durum["calisiyor"] = True
        _durum["son_hedef"] = hedef

    def _worker():
        try:
            from reymen.sistem.main import AIAgentOrchestrator, CONFIG
            agent = AIAgentOrchestrator(config=CONFIG, max_tur=15)
            sonuc = agent.run_conversation(hedef)
            with _durum_kilit:
                _durum["son_sonuc"] = sonuc or "Tamamlanamadi"
                _durum["calisiyor"] = False
        except Exception as e:
            with _durum_kilit:
                _durum["son_sonuc"] = f"Hata: {e}"
                _durum["calisiyor"] = False

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return f"Ajan baslatildi: '{hedef[:60]}'. ReYMeN_status() ile durumu kontrol edin."


def _get_durum() -> str:
    with _durum_kilit:
        d = dict(_durum)
    return json.dumps({
        "calisiyor": d["calisiyor"],
        "son_hedef": d["son_hedef"],
        "son_sonuc": d["son_sonuc"],
    }, ensure_ascii=False)


def _hafiza_ara(sorgu: str) -> str:
    try:
        from reymen.hafiza.vektorel_hafiza import vektorel_hafiza_sistemini_kur, anlamsal_hafiza_ara
        hafiza = vektorel_hafiza_sistemini_kur()
        return anlamsal_hafiza_ara(hafiza, sorgu)
    except Exception as e:
        return f"Hafiza arasi basarisiz: {e}"


def _dosya_oku(dosya: str) -> str:
    yol = Path(dosya) if Path(dosya).is_absolute() else ROOT / dosya
    if not yol.exists():
        return f"Dosya bulunamadi: {dosya}"
    return yol.read_text(encoding="utf-8")[:8000]


def _dosya_yaz(dosya: str, icerik: str) -> str:
    yol = Path(dosya) if Path(dosya).is_absolute() else ROOT / dosya
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(icerik, encoding="utf-8")
    return f"Yazildi: {dosya} ({len(icerik)} karakter)"


def _shell_calistir(komut: str) -> str:
    """MCP uzerinden calistirilan shell komutu. shlex.split ile güvenli."""
    import subprocess
    import shlex
    try:
        args_list = shlex.split(komut, posix=(sys.platform != "win32"))
        if not args_list:
            return "Geçersiz komut"
        r = subprocess.run(  # nosec B603
            args_list, shell=False, capture_output=True, text=True,
            cwd=str(ROOT), timeout=60
        )
        return (r.stdout + r.stderr)[:4000]
    except subprocess.TimeoutExpired:
        return "Zaman asimi (60s)"
    except (ValueError, OSError) as e:
        return f"Komut ayrıştırma hatası: {e}"
    except Exception as e:
        return f"Hata: {e}"


def _beceri_listele() -> str:
    beceriler = []
    for klasor in [ROOT / "skills", ROOT / ".ReYMeN" / "skills"]:
        if klasor.exists():
            beceriler.extend(f.stem for f in klasor.glob("*.md"))
    return json.dumps(sorted(beceriler), ensure_ascii=False)


def _provider_listele() -> str:
    try:
        from providers import list_providers, mevcut_providerlar
        return json.dumps({
            "tum": list_providers(),
            "mevcut": mevcut_providerlar(),
        }, ensure_ascii=False)
    except Exception:
        return '{"tum":[],"mevcut":[]}'


# ── JSON-RPC Isleyici ────────────────────────────────────────────────

def _yanit(req_id, sonuc):
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": sonuc})


def _hata_yaniti(req_id, code, mesaj):
    return json.dumps({
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": code, "message": mesaj},
    })


def _istek_isle(istek: dict) -> str:
    method = istek.get("method", "")
    req_id = istek.get("id")
    params = istek.get("params", {})

    if method == "initialize":
        return _yanit(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": {"tools": {}},
        })

    if method == "tools/list":
        return _yanit(req_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        sonuc = _arac_calistir(name, args)
        return _yanit(req_id, {
            "content": [{"type": "text", "text": sonuc}]
        })

    if method == "ping":
        return _yanit(req_id, {})

    # Bildirim mesajları (id yoktur, yanıt beklenmez)
    if method.startswith("notifications/"):
        return None

    return _hata_yaniti(req_id, -32601, f"Method not found: {method}")


# ── Stdio Dongusu ────────────────────────────────────────────────────

def stdio_dongu():
    """MCP stdio protokolu: her satir bir JSON-RPC istegi."""
    for satir in sys.stdin:
        satir = satir.strip()
        if not satir:
            continue
        try:
            istek = json.loads(satir)
        except json.JSONDecodeError as e:
            yanit = _hata_yaniti(None, -32700, f"Parse error: {e}")
            print(yanit, flush=True)
            continue
        try:
            yanit = _istek_isle(istek)
        except Exception as e:
            yanit = _hata_yaniti(istek.get("id"), -32603, str(e))
        if yanit is not None:
            print(yanit, flush=True)


if __name__ == "__main__":
    stdio_dongu()
