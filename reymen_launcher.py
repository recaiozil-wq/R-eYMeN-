# -*- coding: utf-8 -*-
"""reymen_launcher.py — ReYMeN özel REPL. Hermes UI açılmaz, sadece motor kullanılır."""

import os
import sys
import time
import shutil
import threading
import itertools
from pathlib import Path
from datetime import datetime
import re as _re

import logging
# Tum loglari ERROR'a cek - kullaniciya hicbir log gosterme
logging.basicConfig(level=logging.ERROR, force=True)
for _l in ['CUA', 'Motor', 'motor', 'hermes', 'reymen', 'conversation_loop',
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

# Hermes agent path — banner import icin
_HERMES_AGENT = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "hermes-agent"
if _HERMES_AGENT.exists():
    sys.path.insert(0, str(_HERMES_AGENT))

_HERMES_HOME  = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
_PROFILE_CFG  = _HERMES_HOME / "profiles" / "reymen" / "config.yaml"

try:
    from dotenv import load_dotenv
    load_dotenv(_KOK / ".env", override=True)
    load_dotenv(_HERMES_HOME / ".env", override=True)
    load_dotenv(_HERMES_HOME / "profiles" / "reymen" / ".env", override=True)
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
def _b(t):   return f"{_B}{t}{_R}"
def _d(t):   return f"{_D}{t}{_R}"
def _r(t):   return f"{_RED}{t}{_R}"
def _gb(t):  return f"{_G}{_B}{t}{_R}"
def _cb(t):  return f"{_C}{_B}{t}{_R}"

# ── API Cache ──────────────────────────────────────────────────────────────────
_API_CACHE: dict = {}
_KAYNAK_RE = None

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

def _model_guncelle(provider, model):
    """Provider+model'i .env'ye yaz."""
    os.environ["REYMEN_PROVIDER"] = provider
    os.environ["REYMEN_MODEL"] = model
    _REYMEN_CONFIG["provider"] = provider
    _REYMEN_CONFIG["model"] = model
    try:
        env_path = _KOK / ".env"
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nREYMEN_PROVIDER={provider}\n")
            f.write(f"\nREYMEN_MODEL={model}\n")
    except Exception:
        pass

# ── API kontrol ────────────────────────────────────────────────────────────────
def _api_kontrol(yenile=False):
    """Provider'larin API key'lerini test et."""
    import http.client as _hc
    import json as _js

    if not yenile and _API_CACHE:
        return _API_CACHE

    import threading as _th

    sonuclar = {}
    kilid = _th.Lock()

    def _tek_kontrol(prov, url, env_var, sonuclar, kilid):
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
            conn = _hc.HTTPSConnection(host, timeout=5)
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
        t = _th.Thread(target=_tek_kontrol, args=(p, info["url"], info["env"], sonuclar, kilid), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=6)

    for p in _MODEL_DB:
        if p not in sonuclar:
            sonuclar[p] = "zaman_asimi"
    _API_CACHE.clear()
    _API_CACHE.update(sonuclar)
    return sonuclar

# ── REYMEN-AGENT Logo (Hermes'teki HERMES-AGENT logosunun yerine) ──────────────
_REYMEN_AGENT_LOGO = """[bold #FFD700]██████  ███████ ██    ██ ███    ███ ███████ ███    ██   █████   ██████  ███████ ███    ██ ████████[/]
[bold #FFD700]██   ██ ██       ██  ██  ████  ████ ██      ████   ██   ██   ██ ██       ██      ████   ██    ██[/]
[#FFBF00]██████  █████     ████   ██ ████ ██ █████   ██ ██  ██   ███████ ██   ███ █████   ██ ██  ██    ██[/]
[#FFBF00]██   ██ ██         ██    ██  ██  ██ ██      ██  ██ ██   ██   ██ ██    ██ ██      ██  ██ ██    ██[/]
[#CD7F32]██   ██ ███████    ██    ██      ██ ███████ ██   ████   ██   ██  ██████  ███████ ██   ████    ██[/]"""

# ── Hermes-style welcome banner ────────────────────────────────────────────────
def _hermes_welcome(model: str, session_id: str = ""):
    """Hermes'in build_welcome_banner fonksiyonunu cagirir (birebir ayni goruntu).
    REYMEN-AGENT logosu ile."""
    try:
        # Monkey-patch: Hermes'in banner modulundeki tum marka bilgilerini REYMEN yap
        import hermes_cli.banner as _hb
        _hb.HERMES_AGENT_LOGO = _REYMEN_AGENT_LOGO
        _hb.HERMES_CADUCEUS = ""
        _hb.format_banner_version_label = lambda: "R>eYMeN Ajan v0.1.0 (2026.6.29)"
        # Patch "Nous Research" string in build_welcome_banner
        _src = _hb.build_welcome_banner.__code__
        # Replace the hardcoded "Nous Research" label
        _hb._NOUS_LABEL = "ReYMeN Agent"

        from hermes_cli.banner import build_welcome_banner
        from rich.console import Console

        # Patch the banner function's source to replace "Nous Research"
        import hermes_cli.banner as _banner_mod
        import types

        # Create a wrapper that patches left_lines
        _orig_bwb = _banner_mod.build_welcome_banner

        def _rey_welcome_banner(*args, **kwargs):
            """Call original build_welcome_banner and fix branding."""
            # Save originals
            _orig_logo = _banner_mod.HERMES_AGENT_LOGO
            _orig_cad = _banner_mod.HERMES_CADUCEUS
            _orig_ver = _banner_mod.format_banner_version_label

            # Set ReYMeN branding
            _banner_mod.HERMES_AGENT_LOGO = _REYMEN_AGENT_LOGO
            _banner_mod.HERMES_CADUCEUS = ""
            _banner_mod.format_banner_version_label = lambda: "ReYMeN Agent v0.1.0 (2026.6.29)"

            result = _orig_bwb(*args, **kwargs)

            # Restore originals (in case another call is made)
            _banner_mod.HERMES_AGENT_LOGO = _orig_logo
            _banner_mod.HERMES_CADUCEUS = _orig_cad
            _banner_mod.format_banner_version_label = _orig_ver

            return result

        console = Console()
        _rey_welcome_banner(
            console=console,
            model=model,
            cwd=str(_KOK),
            tools=[],
            enabled_toolsets=[],
            session_id=session_id,
            context_length=1048576,  # 1M token
        )
    except Exception:
        # Fallback: basit acilis
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {_b('ReYMeN Agent')}  {_d('v0.1.0')}")
        print(f"  {_d('─'*50)}")
        print(f"  {_d('Model:')} {model}  {_d('Session:')} {session_id}")
        print(f"  {_d('─'*50)}\n")

# ── Model secim ekrani (Hermes tarzi basit liste) ──────────────────────────────
def _model_sec(api_sonuc=None):
    """Etkilesimli model secim ekrani."""
    cur_m, cur_p = _mevcut_model()
    print(f"\n  {_gb('ReYMeN — Model Seçimi')}")
    print(f"  {_d('─'*50)}")
    if api_sonuc:
        for ad, durum in api_sonuc.items():
            ikon = _g("✓") if durum is True else (_r("✗") if durum == "401" else _y("?"))
            print(f"  {ikon} {_b(ad):<16} {_d(str(durum))}")
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
_HERMES = shutil.which("hermes") or shutil.which("hermes") or "hermes"
_ilk_tur = True

# ── SOUL.md oku ───────────────────────────────────────────────────────────────
def _sistem_prompu_al() -> str:
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

        beyin = Beyin(config=_REYMEN_CONFIG)
        motor = Motor()
        motor._plugin_moduller_yukle()
        cl = ConversationLoop(
            motor=motor,
            beyin=beyin,
            max_tur=15,
        )
        sonuc = cl.run_conversation(
            hedef=soru,
            provider="deepseek",
        )

        if sonuc.get("basarili"):
            yanit = sonuc.get("yanit") or sonuc.get("sonuc", "")
            return yanit, ""
        else:
            hata = sonuc.get("hata") or "Bilinmeyen hata"
            return f"HATA: {hata}", ""

    except Exception as e:
        return f"HATA: {e}", ""
    finally:
        stop.set()
        t.join(timeout=1)


def _sor_direkt_api(soru: str) -> tuple[str, str]:
    """Fallback: direkt API cagrisi."""
    try:
        from reymen.cereyan.beyin import Beyin as _Beyin
        _b = _Beyin(config=_REYMEN_CONFIG)
        _s = "Sen ReYMeN adinda yardimsever bir AI asistanisin. Kisa ve oz cevap ver. Turkce konus."
        _c = _b.uret(_s, [{"role": "user", "content": soru}])
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

        t0 = time.time()
        cevap, kaynak = _sor(girdi)
        dt = time.time() - t0
        # Hermes tarzi cevap
        print(f"\n  {'─'*50}")
        print(f"  {cevap}")
        print(f"  {'─'*50}")
        # Hermes tarzi status line
        t_in = len(girdi.split())
        t_out = len(cevap.split())
        print(f"  {_y('deepseek-v4-flash')} {_d('|')} {_c(f'{t_in*2}K/1M')} {_d('|')} [{_g('█'*int(min(20, t_in*2//5000)))}{_d('▒'*max(0,20-int(min(20, t_in*2//5000))))}] {_g(f'{min(99, t_in*2//10000)}%')} {_d('|')} {_y(f'{dt:.0f}s')}", flush=True)

# ── Giriş noktası ────────────────────────────────────────────────────────────
def main():
    import uuid as _uid
    session_id = _uid.uuid4().hex[:8]

    # 1. Model sec
    cur_m, cur_p = _mevcut_model()

    # API kontrol
    _api_sonuc = _api_kontrol(yenile=True)
    durum = _api_sonuc.get(cur_p)
    if durum is not True:
        # Model secim goster
        _model_sec(_api_sonuc)
        # 5 saniye bekle, sonra varsayilanla devam et
        print(f"  {_d('Varsayılan model ile devam ediliyor...')}\n")
        time.sleep(2)

    # 2. HERMES ILE AYNI WELCOME BANNER
    _hermes_welcome(cur_m, session_id)

    # 3. Welcome mesaji
    try:
        from hermes_cli.skin_engine import get_active_skin
        _skin = get_active_skin()
        _welcome_text = _skin.get_branding("welcome", "R>eYMeN Ajan'a hoş geldiniz! Mesajınızı yazın veya /yardım yazın.")
        _welcome_color = _skin.get_color("banner_text", "#FFF8DC")
    except Exception:
        _welcome_text = "R>eYMeN Ajan'a hoş geldiniz! Mesajınızı yazın veya /yardım yazın."
        _welcome_color = "#FFF8DC"

    from rich.console import Console
    Console().print(f"[{_welcome_color}]{_welcome_text}[/]")
    print()

    # 4. REPL
    _repl(session_id)

if __name__ == "__main__":
    main()
