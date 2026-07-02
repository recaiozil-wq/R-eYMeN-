# -*- coding: utf-8 -*-
"""reymen_launcher.py — ReYMeN özel REPL. ReYMeN UI açılmaz, sadece motor kullanılır."""

import os
import sys
import time
import threading
import itertools
from pathlib import Path
import re as _re

import logging
logging.basicConfig(level=logging.ERROR, force=True)
for _l in ['CUA', 'Motor', 'motor', 'ReYMeN', 'reymen', 'conversation_loop',
           'beyin', 'plugin', 'cron', 'skill', 'root', '__main__']:
    logging.getLogger(_l).setLevel(logging.ERROR)
logger = logging.getLogger("reymen_launcher")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_KOK = Path(__file__).parent.resolve()
os.chdir(_KOK)
sys.path.insert(0, str(_KOK))

# src/ altindaki reymen paketi icin
_src = _KOK / "src"
if _src.exists():
    sys.path.insert(0, str(_src))

try:
    from dotenv import load_dotenv
    load_dotenv(_KOK / ".env", override=True)
except Exception:
    pass

# ── Otomatik durum/komut guncelleme (her CLI baslangicinda) ────────────
try:
    sys.path.insert(0, str(_KOK))
    from reymen.sistem.ortak_komut import guncelle as durum_otomatik_guncelle
    from reymen.sistem.ortak_watchdog import watchdog_baslat
    durum_otomatik_guncelle()
    watchdog_baslat(interval=30)
except Exception:
    pass

# ── Renkler ────────────────────────────────────────────────────────────────────
_R   = "\033[0m"
_C   = "\033[96m"   # cyan
_G   = "\033[92m"   # green
_Y   = "\033[93m"   # yellow
_B   = "\033[94m"   # blue
_M   = "\033[95m"   # magenta
_W   = "\033[97m"   # white
_D   = "\033[2m"    # dim
_RED = "\033[91m"   # kirmizi

def _c(t):   return f"{_C}{t}{_R}"
def _g(t):   return f"{_G}{t}{_R}"
def _y(t):   return f"{_Y}{t}{_R}"
def _mavi(t): return f"{_B}{t}{_R}"  # fix #6: _b -> _mavi
def _d(t):   return f"{_D}{t}{_R}"
def _r(t):   return f"{_RED}{t}{_R}"
def _gb(t):  return f"{_G}{_B}{t}{_R}"
def _cb(t):  return f"{_C}{_B}{t}{_R}"

# ── API Cache ──────────────────────────────────────────────────────────────────
_API_CACHE: dict = {}

# ── ReYMeN config (sabit) ──────────────────────────────────────────────────────
_REYMEN_CONFIG = {
    "provider": os.environ.get("REYMEN_PROVIDER", "deepseek"),
    "model": os.environ.get("REYMEN_MODEL", "deepseek-v4-flash"),
    "temperature": 0.7,
    "max_tokens": 4096,
    "frequency_penalty": 0.8,
}

# ── Model yardimcilari ─────────────────────────────────────────────────────────
_MODEL_DB = {
    "deepseek": {
        "ad": "DeepSeek",
        "modeller": ["deepseek-v4-flash", "deepseek-chat"],
        "env": "DEEPSEEK_API_KEY",
        "url": "https://api.deepseek.com/v1/models",
    },
    "openrouter": {
        "ad": "OpenRouter",
        "modeller": ["openrouter/auto", "anthropic/claude-sonnet-4"],
        "env": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/api/v1/models",
    },
    "groq": {
        "ad": "Groq",
        "modeller": ["groq/llama-3.3-70b-versatile", "groq/llama-3.1-8b-instant"],
        "env": "GROQ_API_KEY",
        "url": "https://api.groq.com/openai/v1/models",
    },
    "xiaomi": {
        "ad": "Xiaomi",
        "modeller": ["xiaomi/mimo-v2.5-pro"],
        "env": "XIAOMI_API_KEY",
        "url": "https://api.minimax.chat/v1/models",
    },
    "xai": {
        "ad": "xAI",
        "modeller": ["xai/grok-2-latest"],
        "env": "XAI_API_KEY",
        "url": "https://api.x.ai/v1/models",
    },
}

def _mevcut_model():
    m = os.environ.get("REYMEN_MODEL", "deepseek-v4-flash")
    p = os.environ.get("REYMEN_PROVIDER", "deepseek")
    return m, p

def _env_replace(key, value):
    """.env'deki bir satiri replace et (fix #3: append yerine in-place)."""
    env_path = _KOK / ".env"
    if not env_path.exists():
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
        return
    lines = []
    found = False
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith(f"{key}=") or line.strip().startswith(f"#{key}="):
                lines.append(f"{key}={value}\n")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"\n{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def _model_guncelle(provider, model):
    """Provider+model'i .env'ye yaz (fix #3: in-place replace)."""
    os.environ["REYMEN_PROVIDER"] = provider
    os.environ["REYMEN_MODEL"] = model
    _REYMEN_CONFIG["provider"] = provider
    _REYMEN_CONFIG["model"] = model
    try:
        _env_replace("REYMEN_PROVIDER", provider)
        _env_replace("REYMEN_MODEL", model)
    except Exception:
        pass

# ── API kontrol (fix #4: background + timeout) ─────────────────────────────────
_API_KONTROL_SONUC = {}
_API_KONTROL_KILIT = threading.Lock()
_API_KONTROL_BITTI = threading.Event()

def _api_kontrol_arkaplan():
    """Provider API key'lerini background thread'te test et."""
    global _API_KONTROL_SONUC
    import http.client as _hc

    sonuclar = {}
    kilid = threading.Lock()

    def _tek(prov, url, env_var):
        key = os.environ.get(env_var, "")
        if not key:
            with kilid:
                sonuclar[prov] = "401"
            return
        try:
            parsed = _re.match(r"https?://([^/]+)(/.*)", url)
            if not parsed:
                with kilid:
                    sonuclar[prov] = False
                return
            host = parsed.group(1)
            path = parsed.group(2) or "/"
            conn = _hc.HTTPSConnection(host, timeout=3)
            conn.request("GET", path, headers={"Authorization": f"Bearer {key}"})
            resp = conn.getresponse()
            ok = resp.status == 200
            conn.close()
            with kilid:
                sonuclar[prov] = ok
        except Exception:
            with kilid:
                sonuclar[prov] = False

    threads = []
    for p, info in _MODEL_DB.items():
        t = threading.Thread(target=_tek, args=(p, info["url"], info["env"]), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=4)

    for p in _MODEL_DB:
        if p not in sonuclar:
            sonuclar[p] = "zaman_asimi"
    with _API_KONTROL_KILIT:
        _API_KONTROL_SONUC = sonuclar
    _API_KONTROL_BITTI.set()

def _api_kontrol_bekle(timeout=4):
    """Background API kontrol sonucunu bekle (en fazla timeout saniye)."""
    _API_KONTROL_BITTI.wait(timeout=timeout)
    with _API_KONTROL_KILIT:
        return dict(_API_KONTROL_SONUC)

# Arka planda baslat
_API_KONTROL_BITTI.clear()
threading.Thread(target=_api_kontrol_arkaplan, daemon=True).start()

# ── REYMEN-AGENT Logo (ReYMeN'teki ReYMeN-AGENT logosuyla birebir ayni font/punta) ─
_REYMEN_AGENT_LOGO = """[bold #FFD700]██████╗ ███████╗██╗   ██╗███╗   ███╗███████╗███╗   ██╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #FFD700]██╔══██╗██╔════╝╚██╗ ██╔╝████╗ ████║██╔════╝████╗  ██║    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#FFBF00]██████╔╝█████╗   ╚████╔╝ ██╔████╔██║█████╗  ██╔██╗ ██║    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#FFBF00]██╔══██╗██╔══╝    ╚██╔╝  ██║╚██╔╝██║██╔══╝  ██║╚██╗██║    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#CD7F32]██║  ██║███████╗   ██║   ██║ ╚═╝ ██║███████╗██║ ╚████║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#CD7F32]╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]"""

# ── ReYMeN-style welcome banner (bağımsız, ReYMeN bağımlılığı yok) ────────────
def _hermes_welcome(model: str, session_id: str = ""):
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table

        console = Console()

        # Logo
        logo_lines = [
            "[bold #FFD700]██████╗ ███████╗██╗   ██╗███╗   ███╗███████╗███╗   ██╗[/]",
            "[bold #FFD700]██╔══██╗██╔════╝╚██╗ ██╔╝████╗ ████║██╔════╝████╗  ██║[/]",
            "[#FFBF00]██████╔╝█████╗   ╚████╔╝ ██╔████╔██║█████╗  ██╔██╗ ██║[/]",
            "[#FFBF00]██╔══██╗██╔══╝    ╚██╔╝  ██║╚██╔╝██║██╔══╝  ██║╚██╗██║[/]",
            "[#CD7F32]██║  ██║███████╗   ██║   ██║ ╚═╝ ██║███████╗██║ ╚████║[/]",
            "[#CD7F32]╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝[/]",
        ]
        for line in logo_lines:
            console.print(line)

        # Info panel
        info = Table.grid(padding=(0, 1))
        info.add_column(style="dim", width=14)
        info.add_column(style="white")
        info.add_row("Model", model)
        info.add_row("Oturum", session_id)
        info.add_row("cd:", os.getcwd())
        info.add_row("exe:", sys.executable)
        info.add_row("Context", "1,048,576")
        console.print(Panel(info, border_style="dim"))

        # Yönlendirici tablosu (ReYMeN'teki gibi)
        ep_table = Table.grid(padding=(0, 2))
        ep_table.add_column(style="dim", width=38)
        ep_table.add_column(style="white")
        ep_table.add_row("reymen/bin/reymen.cmd", ".cmd -> python reymen_launcher.py")
        ep_table.add_row("venv/Scripts/reymen.cmd", ".cmd -> python reymen_launcher.py")
        ep_table.add_row("venv/Scripts/reymen.exe", ".exe direkt (PyInstaller)")
        ep_table.add_row("~/.local/bin/reymen.exe", ".exe -> python reymen_launcher.py (zipapp)")
        console.print(f"\n  [dim]ReYMeN'de 4 tane:[/]")
        console.print(Panel(ep_table, border_style="dim"))

        welcome = "[#FFF8DC]R>eYMeN Ajan'a hoş geldiniz! Mesajınızı yazın veya /yardım yazın.[/]"
        console.print(f"\n{welcome}\n")

    except ImportError:
        # Fallback: rich yoksa ANSI ile
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {_mavi('R>eYMeN Ajan')}  {_d('v0.1.0')}")
        print(f"  {_d('─'*50)}")
        print(f"  {_d('Model:')} {model}  {_d('Oturum:')} {session_id}")
        print(f"  {_d('Dizin:')} {_KOK}")
        print(f"  {_d('─'*50)}\n")
        print(f"  R>eYMeN Ajan'a hoş geldiniz!\n")

# ── Model secim ekrani ─────────────────────────────────────────────────────────
def _model_sec(api_sonuc=None):
    cur_m, cur_p = _mevcut_model()
    print(f"\n  {_gb('ReYMeN — Model Seçimi')}")
    print(f"  {_d('─'*50)}")
    if api_sonuc:
        for ad, durum in api_sonuc.items():
            ikon = _g("✓") if durum is True else (_r("✗") if durum == "401" else _y("?"))
            print(f"  {ikon} {_mavi(ad):<16} {_d(str(durum))}")
    print(f"  {_d('─'*50)}")
    print(f"  {_d('Aktif:')} {_g(cur_m)}")
    print()

# ── Spinner ───────────────────────────────────────────────────────────────────
def _spinner(stop_evt):
    frames = ["◈", "◉", "◎", "⊙", "○"]
    cyc_f = itertools.cycle(frames)
    while not stop_evt.is_set():
        frame = next(cyc_f)
        print(f"\r  {frame} ", end="", flush=True)
        time.sleep(0.12)
    print(f"\r{' '*30}\r", end="", flush=True)

# ── ReYMeN cagrisi ────────────────────────────────────────────────────────────
_ilk_tur = True

def _sistem_prompu_al() -> str:
    """SOUL.md + DURUM_OKU talimati ile sistem promptu olustur."""
    try:
        soul_path = Path(__file__).parent / "reymen" / "arac" / ".ReYMeN" / "SOUL.md"
        if soul_path.exists():
            soul = soul_path.read_text(encoding="utf-8")
        else:
            soul = ""
    except Exception:
        soul = ""
    return (
        "Sen ReYMeN adinda yardimsever bir AI asistanisin. "
        "Kisa ve oz cevap ver. Turkce konus.\\n\\n"
        "## \\u26a0\\ufe0f DURUM_OKU() ZORUNLU TALIMAT\\n"
        "ReYMeN durumu/projesi/eksikleri/kapasitesi hakkinda soru gelince "
        "KESINLIKLE ONCE DOGRUDAN DURUM_OKU() tool'unu cagir. "
        "Kendi bilginle asla liste olusturma. durum.json TEK KAYNAK.\\n"
        "Karsilastirma/eksik/liste/sayi sorularinda ONCE DURUM_OKU().\\n"
        + (f"\\n## SOUL.md\\n{soul[:2000]}\\n" if soul else "")
    )

def _sor(soru: str) -> tuple[str, str]:
    """ReYMeN'e soru sor — Telegram bot ile AYNI full pipeline."""
    global _ilk_tur
    _ilk_tur = False

    stop = threading.Event()
    t = threading.Thread(target=_spinner, args=(stop,), daemon=True)
    t.start()

    try:
        from reymen.cereyan.beyin import Beyin
        from reymen.cereyan.motor import Motor
        from reymen.cereyan.conversation_loop import ConversationLoop

        # fix #2: SOUL.md entegrasyonu
        system_prompt = _sistem_prompu_al()
        config = dict(_REYMEN_CONFIG)
        config["system_prompt"] = system_prompt

        beyin = Beyin(config=config)
        motor = Motor()
        motor._plugin_moduller_yukle()
        cl = ConversationLoop(
            motor=motor,
            beyin=beyin,
            max_tur=15,
        )
        # fix #1: provider hardcode kaldirildi
        sonuc = cl.run_conversation(
            hedef=soru,
            provider=_REYMEN_CONFIG["provider"],
        )

        if sonuc.get("basarili"):
            yanit = sonuc.get("yanit") or sonuc.get("sonuc", "")
            return yanit, ""
        else:
            hata = sonuc.get("hata") or "Bilinmeyen hata"
            # fix #8: fallback dene
            return _sor_direkt_api(soru)

    except Exception as e:
        # fix #8: fallback dene
        return _sor_direkt_api(soru)
    finally:
        stop.set()
        t.join(timeout=5)  # fix #5: 1s -> 5s


def _sor_direkt_api(soru: str) -> tuple[str, str]:
    """Fallback: direkt API cagrisi (Beyin.uret ile)."""
    try:
        from reymen.cereyan.beyin import Beyin as _BeyinMod
        _beyin_inst = _BeyinMod(config=_REYMEN_CONFIG)
        _s = _sistem_prompu_al()
        _c = _beyin_inst.uret(_s, [{"role": "user", "content": soru}])
        return _c or "Cevap alinamadi", ""
    except Exception as e:
        return f"HATA: {e}", ""


_YARDIM = f"""
  {_cb('ReYMeN Komutlar')}

  {_c('/yardim')}        Bu menüyü göster
  {_c('/model')}         Model değiştir
  {_c('/temizle')}       Ekranı temizle
  {_c('/cik')}           Çıkış

  {_d('Herhangi bir metin yaz → ReYMeN cevaplar.')}
"""

# ── Ana REPL ──────────────────────────────────────────────────────────────────
def _repl(session_id=""):
    cur_m, cur_p = _mevcut_model()
    print(f"  {_gb('ReYMeN')} hazır. /yardim /model /temizle /cik")
    print()

    def _repl_gonder(cid, metin):
        """REPL icin mesaj gonder — Telegram yerine print yapar."""
        print(f"\n  {metin}\n")

    while True:
        try:
            girdi = input(f"  {_gb('ReYMeN')}{_R} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {_d('ReYMeN kapanıyor.')}")
            break

        if not girdi:
            continue

        if girdi.lower() in ("/cik", "/çık", "exit", "quit", "q"):
            print(f"  {_d('ReYMeN kapanıyor.')}")
            break
        if girdi.lower() in ("/yardim", "/help", "/?"):
            print(_YARDIM)
            continue
        if girdi.lower() in ("/temizle", "/cls", "/clear"):
            _hermes_welcome(cur_m, session_id)
            continue
        if girdi.lower().startswith("/model"):
            _model_sec()
            continue

        # Ortak komut modulune yonlendir
        try:
            from reymen.ag.ortak_komutlar import komut_isle
            if komut_isle(girdi, _repl_gonder, 0):
                continue  # Komut islendi, normal akisa gecme
        except ImportError:
            pass
        except Exception:
            pass

        t0 = time.time()
        cevap, kaynak = _sor(girdi)
        dt = time.time() - t0
        print(f"\n  {'─'*50}")
        print(f"  {cevap}")
        print(f"  {'─'*50}")
        t_in = len(girdi.split())
        t_out = len(cevap.split())
        print(f"  {_y(cur_m)} {_d('|')} {_c(f'{t_in*2}K/1M')} {_d('|')} [{_g('█'*int(min(20, t_in*2//5000)))}{_d('▒'*max(0,20-int(min(20, t_in*2//5000))))}] {_g(f'{min(99, t_in*2//10000)}%')} {_d('|')} {_y(f'{dt:.0f}s')}", flush=True)

# ── Versiyon ─────────────────────────────────────────────────────────────────
_REYMEN_VERSION = "0.1.0"
_REYMEN_BUILD = "2026.6.29"

def _show_version():
    print(f"ReYMeN Agent v{_REYMEN_VERSION} ({_REYMEN_BUILD})")
    print(f"Proje: {_KOK}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Model: {_REYMEN_CONFIG['model']} ({_REYMEN_CONFIG['provider']})")
    return 0


# ── Argüman ayrıştırıcı (ReYMeN uyumlu) ─────────────────────────────────────
def _build_parser():
    """Parser'ı reymen.console.build_parser() üzerinden kur, launcher'a özel handler'ları ekle."""
    from reymen.console import build_parser as _bp

    p = _bp()

    # required=True'i kaldır — command olmadan da -z/-V/m/provider çalışabilmeli
    for action in p._actions:
        if hasattr(action, 'required') and hasattr(action, 'choices'):
            action.required = False

    # Launcher'a özel: model komutu handler'ı
    for action in p._actions:
        if hasattr(action, 'choices') and action.choices is not None:
            if 'status' in action.choices or 'cost' in action.choices:
                if 'model' not in action.choices:
                    p_model = action.add_parser("model", help="Model seçimi")
                    p_model.set_defaults(func=lambda a: _model_sec_interactive())
                break

    # start komutu (eski .bat/.vbs dosyalarinin yerine)
    _sub = None
    for action in p._actions:
        if hasattr(action, 'choices') and action.choices is not None:
            _sub = action
            break

    if _sub is not None:
        p_start = _sub.add_parser("start", help="ReYMeN bileşenlerini başlat")
        p_start.add_argument("--mode", choices=["bot", "gateway", "tray", "web", "doctor"],
                             default="bot", help="Başlatılacak modül")
        p_start.add_argument("--bot-name", default="all",
                             help="Bot adı (pasa, reymen, kiral38, all)")
        p_start.set_defaults(func=_cmd_start)

    # Update komutu
    if _sub is not None:
        p_update = _sub.add_parser("update", help="ReYMeN'i güncelle (git pull + pip install)")
        p_update.set_defaults(func=_cmd_update)

    # Cost handler override (launcher'daki _cmd_cost_alt console.py'ye yönlendirir)
    for action in p._actions:
        if hasattr(action, 'choices') and action.choices:
            if 'cost' in action.choices:
                action.choices['cost'].set_defaults(
                    func=lambda a: _cmd_cost_alt(a)
                )

    # Status handler override
    for action in p._actions:
        if hasattr(action, 'choices') and action.choices:
            if 'status' in action.choices:
                action.choices['status'].set_defaults(
                    func=lambda a: _cmd_status()
                )

    return p


# ── CLI yonlendirme ve alt komut proxy'leri ──────────────────────────────────
from reymen.arac.cli_commands import (
    cmd_gateway as _cmd_gateway,
    cmd_config as _cmd_config,
    cmd_session as _cmd_session,
    cmd_doctor as _cmd_doctor,
    cmd_backup as _cmd_backup,
)

# ── start komutu (eski .bat/.vbs dosyalari yerine) ──────────────────────────
def _cmd_start(args):
    """reymen start --mode bot --bot-name all (veya gateway/tray/web/doctor)"""
    mode = args.mode
    bot_name = args.bot_name

    if mode == "doctor":
        return _cmd_doctor(args)

    if mode == "gateway":
        print(f"  Gateway başlatılıyor...")
        return _cmd_gateway(args)

    if mode == "tray":
        print(f"  Sistem tepsisi başlatılıyor...")
        import subprocess as _sp
        _pyw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.isfile(_pyw):
            _pyw = sys.executable
        _sp.Popen([_pyw, str(_KOK / "reymen" / "desktop" / "tray.py")],
                  creationflags=_sp.CREATE_NO_WINDOW if os.name == "nt" else 0)
        print(f"  {_g('✓')} Tray arkaplanda başlatıldı")
        return 0

    if mode == "web":
        print(f"  Web UI başlatılıyor...")
        from reymen.arac.cli_commands import cmd_web as _cmd_web
        return _cmd_web(args)

    # mode == "bot" (varsayilan)
    print(f"  Telegram Bot ({bot_name}) başlatılıyor...")
    if bot_name == "all":
        print(f"  Tüm botlar başlatılıyor...")
        _bat = _KOK / "baslat_reymen_bot.bat"
        if _bat.exists():
            import subprocess as _sp
            _sp.Popen(["cmd", "/c", "start", str(_bat)], shell=True)
    else:
        _token_map = {
            "pasa": "TELEGRAM_BOT_TOKEN",
            "reymen": "TELEGRAM_BOT_TOKEN",
            "kiral38": "TELEGRAM_BOT_TOKEN",
        }
        token_var = _token_map.get(bot_name, "TELEGRAM_BOT_TOKEN")
        token = os.environ.get(token_var, "")
        if token:
            from reymen.ag.telegram_bot import BotProcess
            bot = BotProcess(token)
            bot.poll()
        else:
            print(f"  {_r('✗')} {bot_name} için token bulunamadi (.env kontrol et)")
    return 0
# ── Cron komutu — reymen.cli._cmd_cron kullanılır (build_parser üzerinden)
# ── Cost komutu proxy (console.py'ye) ──────────────────────────────────────
def _cmd_cost_alt(args):
    from reymen.console import cmd_cost as _cc
    return _cc(args)


# ── Status komutu (console.py'ye proxy) ─────────────────────────────────────
def _cmd_status():
    """Genel durum bilgisi."""
    from reymen.console import cmd_status as _cs
    import argparse as _ap
    return _cs(_ap.Namespace())


# ── update komutu ──────────────────────────────────────────────────────────
def _cmd_update(args=None):
    """ReYMeN'i güncelle: git pull + pip install -e ."""
    import subprocess as _sp
    import sys as _sys

    print(f"\n  {_c('╔══════════════════════════════════════╗')}")
    print(f"  {_c('║')}   ReYMeN Güncelleme Başlatılıyor...  {_c('║')}")
    print(f"  {_c('╚══════════════════════════════════════╝')}\n")

    # 1. Mevcut versiyon — versiyon bilgisini yakalamak için stdout'u yönlendir
    import io as _io
    _buf = _io.StringIO()
    _old_stdout = sys.stdout
    sys.stdout = _buf
    _show_version()
    sys.stdout = _old_stdout
    _versiyon_once = _buf.getvalue().strip()
    print(f"  {_d('Mevcut:')} {_versiyon_once}")

    # 2. Git pull
    print(f"\n  {_y('⟳')} Git çekiliyor...")
    try:
        r = _sp.run(["git", "pull"], cwd=_KOK, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            print(f"  {_g('✓')} Git pull başarılı")
            if r.stdout.strip():
                for line in r.stdout.strip().splitlines()[-5:]:
                    print(f"    {_d(line)}")
        else:
            print(f"  {_r('✗')} Git pull hatası:")
            print(f"    {r.stderr[:200]}")
            return 1
    except Exception as e:
        print(f"  {_r('✗')} Git pull başarısız: {e}")
        return 1

    # 3. pip install -e .
    print(f"\n  {_y('⟳')} Bağımlılıklar güncelleniyor...")
    _pip = _sys.executable.replace("python.exe", "pythonw.exe") if os.name == "nt" else _sys.executable
    _pip = _sys.executable  # pythonw.exe pip calismaz, normal python kullan
    try:
        r = _sp.run(
            [_sys.executable, "-m", "pip", "install", "-e", str(_KOK), "--quiet"],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            print(f"  {_g('✓')} Bağımlılıklar güncellendi")
        else:
            print(f"  {_y('⚠')} pip uyarısı: {r.stderr[:200]}")
    except Exception as e:
        print(f"  {_r('✗')} pip hatası: {e}")

    # 4. Yeni versiyon — versiyon bilgisini yakala
    _buf2 = _io.StringIO()
    _old_stdout2 = sys.stdout
    sys.stdout = _buf2
    _show_version()
    sys.stdout = _old_stdout2
    _versiyon_sonra = _buf2.getvalue().strip()
    print(f"\n  {_d('Güncel:')} {_versiyon_sonra}")

    # 5. Özet
    print(f"\n  {_g('✓')} Güncelleme tamamlandı!")
    print(f"  {_d('Önce:')} {_versiyon_once}")
    print(f"  {_d('Sonra:')} {_versiyon_sonra}")
    if _versiyon_once != _versiyon_sonra:
        print(f"  {_y('⟳')} Sürüm değişti — gateway'leri yeniden başlatmayı unutma!")
    return 0


def _model_sec_interactive():
    """Etkileşimli model seçim ekranı (eski _model_sec ile aynı)."""
    _api_sonuc = _api_kontrol_bekle(timeout=3)
    _model_sec(_api_sonuc)
    return 0


# ── One-shot mod ─────────────────────────────────────────────────────────────
def _oneshot(prompt: str):
    """-z/--oneshot: direkt API çağrısı, banner yok, REPL yok."""
    from reymen.cereyan.beyin import Beyin
    from reymen.cereyan.motor import Motor
    from reymen.cereyan.conversation_loop import ConversationLoop

    model = os.environ.get("REYMEN_MODEL", "deepseek-v4-flash")
    provider = os.environ.get("REYMEN_PROVIDER", "deepseek")

    config = dict(_REYMEN_CONFIG)
    config["system_prompt"] = _sistem_prompu_al()
    config["model"] = model
    config["provider"] = provider

    beyin = Beyin(config=config)
    motor = Motor()
    motor._plugin_moduller_yukle()
    cl = ConversationLoop(motor=motor, beyin=beyin, max_tur=5)

    sonuc = cl.run_conversation(hedef=prompt, provider=provider)
    if sonuc.get("basarili"):
        yanit = sonuc.get("yanit") or sonuc.get("sonuc", "")
        print(yanit)
    else:
        # fallback: direkt API
        print(_sor_direkt_api(prompt)[0])
    return 0


# ── Giriş noktası ────────────────────────────────────────────────────────────
def main():
    import sys as _sys
    import uuid as _uid

    # CLI komutlarini tanı: reymen/cli.py build_parser + launcher özel komutlar
    # Tek kaynak: reymen.cli.build_parser + launcher ekleri (model)
    _LAUNCHER_CMD = {"model", "status", "cost", "gateway", "config",
                         "session", "doctor", "backup", "cron", "skills",
                         "plugins", "tools", "setup", "profile", "logs",
                         "mcp", "update"}

    # Argümanları parse et
    parser = _build_parser()
    args = parser.parse_args()

    # -V / --version
    if getattr(args, 'version', False):
        return _show_version()

    # -m / --model override
    if getattr(args, 'model', False):
        _model_guncelle(
            args.provider or os.environ.get("REYMEN_PROVIDER", "deepseek"),
            args.model,
        )

    # --provider override (model yoksa da çalışır)
    if getattr(args, 'provider', None) and not getattr(args, 'model', None):
        cur_m = os.environ.get("REYMEN_MODEL", "deepseek-v4-flash")
        _model_guncelle(args.provider, cur_m)

    # -z / --oneshot: banner yok, direkt cevap
    if getattr(args, 'oneshot', None):
        return _oneshot(args.oneshot)

    # Alt komutlar
    if getattr(args, 'command', None):
        if args.command == "model":
            return _model_sec_interactive()
        if args.command == "status":
            return _cmd_status()
        if hasattr(args, "func"):
            return args.func(args)
        parser.print_help()
        return 1

    # ── TUI modu ──────────────────────────────────────────────────────────
    if "--tui" in sys.argv or getattr(args, "tui", False):
        from reymen.cli.tui import tui_baslat
        cur_m, cur_p = _mevcut_model()
        session_id = _uid.uuid4().hex[:8]

        def _tui_soru(soru: str) -> str:
            """TUI callback: soruyu ReYMeN'e ilet ve cevabi don."""
            cevap, _ = _sor(soru)
            return cevap

        return tui_baslat(
            soru_callback=_tui_soru,
            model=cur_m,
            provider=cur_p,
            session_id=session_id,
        )

    # Varsayılan: REPL başlat
    session_id = _uid.uuid4().hex[:8]
    cur_m, cur_p = _mevcut_model()

    # Yeni moduller: --voice, --api-server, --credential-pool
    if "--voice" in sys.argv:
        try:
            from reymen.cereyan.voice_mode import VoiceMode
            vm = VoiceMode()
            print("🎤 Voice Mode baslatiliyor...")
            vm.baslat()
            return 0
        except Exception as e:
            print(f"❌ Voice Mode hatasi: {e}")
            return 1

    if "--api-server" in sys.argv:
        try:
            port = 8000
            for i, a in enumerate(sys.argv):
                if a == "--port" and i + 1 < len(sys.argv):
                    port = int(sys.argv[i + 1])
            from reymen.api_server import APIServer
            import uvicorn
            print(f"🌐 API Server baslatiliyor (port {port})...")
            uvicorn.run("reymen.api_server:app", host="0.0.0.0", port=port)
            return 0
        except Exception as e:
            print(f"❌ API Server hatasi: {e}")
            return 1

    if "--credential-pool" in sys.argv:
        try:
            from reymen.core.credential_pool import get_credential_pool
            pool = get_credential_pool()
            print("🔑 Credential Pool durumu:")
            print(pool.durum())
            return 0
        except Exception as e:
            print(f"❌ Credential Pool hatasi: {e}")
            return 1

    # fix #4: background API kontrol — bekleme yok
    _api_sonuc = _api_kontrol_bekle(timeout=3)
    durum = _api_sonuc.get(cur_p)
    if durum is not True:
        _model_sec(_api_sonuc)
        print(f"  {_d('Varsayılan model ile devam ediliyor...')}\n")

    _hermes_welcome(cur_m, session_id)
    _repl(session_id)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
