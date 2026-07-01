# -*- coding: utf-8 -*-
"""
telegram_bot.py — ReYMeN Birlesik Telegram Botu.

Bu dosya Hermes Agent Gateway yapisindan esinlenilmistir.
Apache 2.0 Lisansi — github.com/NousResearch/hermes-agent
================================================

3 farkli bot dosyasinin TEK dosyada birlestirilmis hali:

  Kaynak 1: reymen/ag/telegram_bot.py   — Standalone HTTP API
  Kaynak 2: telegram_bot/bot.py         — PTB + Cron Yoneticisi
  Kaynak 3: telegram_bot/ai_bot.py      — AI + OnceHafiza + ConversationLoop

Ozellikler:
  - class UnifiedBot:  PTB Application + HTTP API destegi
  - class BotProcess:   AI + OnceHafiza + ConversationLoop
  - class CronManager:  Tam cron job yoneticisi (ekle/sil/calistir/listele)
  - _api(), gonder()    HTTP API yardimcilari
  - /start, /help, /run, /status, /logs command handler'lari
  - Gateway modu:      HERMES_GATEWAY env var ile kontrol
  - Async/await tabanli (PTB modunda)
  - Tum importlar graceful degrade (try/except)
  - Tum hatalar try/except ile yakalanir

Kullanim:
  python telegram_bot.py  (HTTP polling ile calisir)
  veya PTB modu icin: HERMES_GATEWAY=ptb python telegram_bot.py
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# ============================================================================
# PROJE KOKU & SYS.PATH
# ============================================================================
_PROJE_KOK = Path(__file__).resolve().parent.parent.parent  # reymen/ag/../../ = proje koku
if str(_PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(_PROJE_KOK))

# ============================================================================
# LOGGER
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_bot")

# ============================================================================
# GRACEFUL IMPORTLAR — Tum importlar try/except ile
# ============================================================================

# — Dotenv (.env yukleme) —
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# — python-telegram-bot (PTB) —
PTB_AVAILABLE = False
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    PTB_AVAILABLE = True
except ImportError:
    Update = None
    Application = None
    CommandHandler = None
    ContextTypes = None
    MessageHandler = None
    filters = None

# — Beyin (LLM) —
BEYIN_CLS = None
try:
    from reymen.cereyan.beyin import Beyin as _B
    BEYIN_CLS = _B
except ImportError as e:
    logger.warning("Beyin import edilemedi: %s", e)

# — OnceHafiza —
ONCE_HAFIZA_ARA = None
ONCE_HAFIZA_KAYDET = None
try:
    from reymen.cereyan.once_hafiza import hafizada_ara as _ara, kaydet as _kaydet
    ONCE_HAFIZA_ARA = _ara
    ONCE_HAFIZA_KAYDET = _kaydet
except ImportError as e:
    logger.warning("OnceHafiza import edilemedi: %s", e)

# — ConversationLoop —
CONVERSATION_LOOP_CLS = None
try:
    from reymen.cereyan.conversation_loop import ConversationLoop as _CL
    CONVERSATION_LOOP_CLS = _CL
except ImportError as e:
    logger.warning("ConversationLoop import edilemedi: %s", e)

# — Ortak komutlar —
try:
    from reymen.ag.ortak_komutlar import komut_isle as ortak_komut_isle, cmd_run as ortak_cmd_run
except ImportError:
    ortak_komut_isle = None
    ortak_cmd_run = None

# ============================================================================
# CEVRESEL DEGISKENLER
# ============================================================================
_ENV_YUKLENDI = False


def _env_yukle():
    """.env dosyasini yukle (sadece 1 kere).

    Oncelik sirasi:
      1. Ortam degiskeni (bot_supervisor.py ile gelen TELEGRAM_BOT_TOKEN)
      2. Proje kokundeki .env
      3. Hermes profil .env'si (HERMES_PROFILE'a gore)
    """
    global _ENV_YUKLENDI
    if _ENV_YUKLENDI:
        return
    _ENV_YUKLENDI = True
    if load_dotenv is None:
        return

    # 1. Proje kokundeki .env (fallback — override=False, profildeki degerleri ezmez)
    y = _PROJE_KOK / ".env"
    if y.exists():
        load_dotenv(str(y), override=False)
        logger.debug(".env fallback yuklendi: %s", y)

    # 2. Hermes profil .env (kazanan — override=True, profildeki degerler kesin gecerli)
    profil = os.environ.get("HERMES_PROFILE", "reymen")
    hermes_env = Path.home() / "AppData" / "Local" / "hermes" / "profiles" / profil / ".env"
    if hermes_env.exists():
        load_dotenv(str(hermes_env), override=True)
        logger.info("Hermes profil .env yuklendi: %s (override=True)", hermes_env)


_ = _env_yukle()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()  # "" = herkese acik
API_BASE = f"https://api.telegram.org/bot{TOKEN}"

# Gateway modu: "ptb" veya "http" (default: http)
GATEWAY_MOD = os.environ.get("HERMES_GATEWAY", "http").strip().lower()

# ── Reconnection ayarlari ─────────────────────────────────────────────────
_MAX_BACKOFF = 60  # maksimum bekleme saniyesi (exponential backoff)
_MAX_RETRY = 10    # maksimum ardışık hata sayisi -> bot restart sinyali

# ============================================================================
# OTOMATIK DURUM GUNCELLEME
# ============================================================================
try:
    from reymen.sistem.ortak_komut import guncelle as durum_otomatik_guncelle
    from reymen.sistem.ortak_watchdog import watchdog_baslat
    durum_otomatik_guncelle()
    watchdog_baslat(interval=30)
except Exception as e:
    logger.debug("OrtakKomut yukleme hatasi (opsiyonel): %s", e)

# ============================================================================
# AKTIF GOREV KILIDI
# ============================================================================
_gorev_kilidi = threading.Lock()
_aktif_gorev: Optional[dict] = None

# ============================================================================
# YARDIMCI FONKSIYONLAR — _api() ve gonder()
# ============================================================================

def _api(yontem: str, veri: dict = None, timeout: int = 30) -> dict:
    """Telegram HTTP API'sine istek gonder.

    Args:
        yontem: API metodu (ornek: "sendMessage", "getUpdates")
        veri: JSON body
        timeout: Istek zamani asimi

    Returns:
        Parsed JSON yaniti veya {"ok": False, "error": ...}
    """
    if not TOKEN:
        return {"ok": False, "error": "TOKEN ayarli degil"}
    url = f"{API_BASE}/{yontem}"
    body = json.dumps(veri or {}).encode()
    try:
        import urllib.request
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _api_requests(yontem: str, veri: dict = None, timeout: int = 30) -> dict:
    """Telegram HTTP API'sine requests kutuphanesi ile istek gonder.

    Fallback: _api() kullanir.
    """
    try:
        import requests
        url = f"{API_BASE}/{yontem}"
        r = requests.post(url, json=veri or {}, timeout=timeout)
        return r.json()
    except ImportError:
        return _api(yontem, veri, timeout)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def gonder(chat_id: int | str, metin: str, parse_mode: str = "") -> dict:
    """Telegram'a mesaj gonder — 4096 karakter sinirini otomatik boler.

    Args:
        chat_id: Hedef chat ID'si
        metin: Gonderilecek mesaj
        parse_mode: "Markdown" veya "HTML" (opsiyonel)

    Returns:
        API yaniti
    """
    sinir = 4000
    if len(metin) <= sinir:
        veri = {"chat_id": chat_id, "text": metin}
        if parse_mode:
            veri["parse_mode"] = parse_mode
        return _api("sendMessage", veri)
    # Cok uzunsa parcala
    for i in range(0, len(metin), sinir):
        parca = metin[i:i + sinir]
        veri = {"chat_id": chat_id, "text": parca}
        if parse_mode:
            veri["parse_mode"] = parse_mode
        _api("sendMessage", veri)
    return {"ok": True}


def gonder_requests(chat_id: int | str, metin: str) -> bool:
    """requests ile mesaj gonder (BotProcess icin)."""
    try:
        import requests
        r = requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": metin[:4096]},
            timeout=10,
        )
        return r.ok
    except Exception as e:
        logger.error("Mesaj gonderilemedi: %s", e)
        return False


def _izin_var(chat_id: int | str) -> bool:
    """TELEGRAM_CHAT_ID tanimlanmissa sadece o chat'e izin ver."""
    if not CHAT_ID:
        return True
    return str(chat_id) == str(CHAT_ID)


# ============================================================================
# CRON MANAGER — Tam cron job yoneticisi
# ============================================================================

class CronManager:
    """Cron job yoneticisi — job ekle, sil, calistir, listele.

    Job'lar JSON dosyasinda saklanir, arka planda thread'lerde calistirilir.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path(__file__).parent / "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.data_dir / "jobs.json"
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ── Job verisi ──────────────────────────────────────────────────────

    def load_jobs(self) -> dict:
        """JSON'dan job'lari yukle."""
        try:
            if self.jobs_file.exists():
                return json.loads(self.jobs_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Job yukleme hatasi: %s", e)
        return {}

    def save_jobs(self, jobs: dict):
        """Job'lari JSON'a kaydet."""
        try:
            self.jobs_file.write_text(
                json.dumps(jobs, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Job kaydetme hatasi: %s", e)

    # ── Job calistir ────────────────────────────────────────────────────

    def run_shell_job(self, job_id: str, command: str):
        """Shell komutunu calistir, log yaz, durumu guncelle."""
        jobs = self.load_jobs()
        job = jobs.get(job_id, {})
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc).isoformat()
        self.save_jobs(jobs)

        log_file = self.logs_dir / f"{job_id}.log"
        try:
            result = subprocess.run(
                command,
                shell=False if sys.platform != "win32" else True,
                capture_output=True,
                text=True,
                timeout=3600,
            )
            output = result.stdout + result.stderr
            log_file.write_text(output, encoding="utf-8")

            jobs = self.load_jobs()
            job = jobs.get(job_id, {})
            job["status"] = "success" if result.returncode == 0 else "failed"
            job["exit_code"] = result.returncode
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
            job["log"] = output
            self.save_jobs(jobs)
        except Exception as e:
            output = f"Error: {e}"
            log_file.write_text(output, encoding="utf-8")
            jobs = self.load_jobs()
            job = jobs.get(job_id, {})
            job["status"] = "failed"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
            job["log"] = output
            self.save_jobs(jobs)

    def add_job(self, name: str, command: str, schedule: str = "") -> str:
        """Job ekle ve arka planda calistir.

        Args:
            name: Job adi
            command: Shell komutu
            schedule: Cron schedule (opsiyonel, henuz uygulanmiyor)

        Returns:
            Job ID
        """
        jobs = self.load_jobs()
        job_id = str(uuid.uuid4())[:8]
        jobs[job_id] = {
            "id": job_id,
            "name": name,
            "command": command,
            "schedule": schedule,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save_jobs(jobs)

        thread = threading.Thread(
            target=self.run_shell_job, args=(job_id, command), daemon=True
        )
        thread.start()
        return job_id

    def delete_job(self, job_id: str) -> bool:
        """Job sil."""
        try:
            jobs = self.load_jobs()
            if job_id in jobs:
                del jobs[job_id]
                self.save_jobs(jobs)
                return True
        except Exception as e:
            logger.error("Job silme hatasi: %s", e)
        return False

    def list_jobs(self) -> list[dict]:
        """Tum job'lari listele."""
        jobs = self.load_jobs()
        return sorted(
            jobs.values(),
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

    def get_job_log(self, job_name: str) -> Optional[str]:
        """Job adina gore log bul."""
        jobs = self.load_jobs()
        # Tam eslesme
        matched = None
        for jid, job in jobs.items():
            if job.get("name", "").strip().lower() == job_name.strip().lower():
                matched = job
                break
        if not matched:
            # Kismi eslesme
            for jid, job in jobs.items():
                if job_name.strip().lower() in job.get("name", "").strip().lower():
                    matched = job
                    break
        if not matched:
            return None

        log = matched.get("log", "")
        if not log:
            log_file = self.logs_dir / f"{matched.get('id', '')}.log"
            if log_file.exists():
                log = log_file.read_text(encoding="utf-8")
        return log


# ============================================================================
# CRON MANAGER ORNEK (singleton)
# ============================================================================
_cron_manager = CronManager()


# ============================================================================
# BOTPROCESS — AI + OnceHafiza + ConversationLoop
# ============================================================================

_VARSAYILAN_AYARLAR = {
    "offset": 0,
    "model": "deepseek-v4-flash",
    "provider": "deepseek",
    "sistem_prompt": None,
    "bilinen_chatler": [],
    "konusma_gecmisi": [],
}


class BotProcess:
    """Tek bir Telegram botu icin AI Agent Orchestrator.

    - Beyin ile LLM yaniti uretir
    - OnceHafiza ile hafiza kontrolu (guven > 0.7 ise direkt don)
    - ConversationLoop ile tool kullanimi (opsiyonel)
    - Konusma gecmisi tutar (son 10 mesaj)
    - HTTP API polling dongusu ile mesaj dinler
    """

    def __init__(self, token: str, bot_ad: str = ""):
        _env_yukle()
        self.token = token
        self.bot_ad = bot_ad or self._bot_bilgisi_al()
        self.ayar_dosyasi = _PROJE_KOK / ".ReYMeN" / f"ai_bot_{self.bot_ad.replace('@', '')}.json"
        self.ayarlar: dict = dict(_VARSAYILAN_AYARLAR)
        self._beyin = None
        self._loop = None
        self._ayar_yukle()
        self._beyin_baslat()
        self._durum_guncelle()
        logger.info("[%s] BotProcess baslatildi", self.bot_ad)

    # ── Bot bilgisi ────────────────────────────────────────────────────

    def _bot_bilgisi_al(self) -> str:
        try:
            r = _api("getMe", timeout=5)
            if r.get("ok"):
                return f"@{r['result']['username']}"
        except Exception as _e:
            logger.warning("[TelegramBot] except Exception (L480): %s", Exception)
            pass
        try:
            import requests
            r = requests.get(
                f"https://api.telegram.org/bot{self.token}/getMe", timeout=5
            )
            return f"@{r.json()['result']['username']}"
        except Exception:
            return "@?"

    # ── Ayar yonetimi ──────────────────────────────────────────────────

    def _ayar_yukle(self):
        try:
            if self.ayar_dosyasi.exists():
                okunan = json.loads(self.ayar_dosyasi.read_text(encoding="utf-8"))
                self.ayarlar.update(okunan)
        except Exception as e:
            logger.warning("[%s] Ayar yukleme hatasi: %s", self.bot_ad, e)

    def _ayar_kaydet(self):
        try:
            self.ayar_dosyasi.parent.mkdir(parents=True, exist_ok=True)
            self.ayar_dosyasi.write_text(
                json.dumps(self.ayarlar, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("[%s] Ayar kaydedilemedi: %s", self.bot_ad, e)

    # ── ZORUNLU: Bot kendini durum.json'a kaydeder ─────────────────────────
    def _durum_guncelle(self):
        """KATI KURAL: Her bot baslangicinda kendini durum.json'a ekler/gunceller.
        Yeni bot veya yeni token geldiginde otomatik kaydedilir."""
        try:
            from reymen.sistem.durum import degisiklik_ekle
            durum_yolu = _PROJE_KOK / "durum.json"
            if durum_yolu.exists():
                veri = json.loads(durum_yolu.read_text(encoding="utf-8"))
                botlar = veri.get("botlar", {})
                bot_adi_str = self.bot_ad  # "@ReYMeN_ReYMeNbot"
                
                # Bot zaten var mi? (bot_adi alanina gore kontrol et)
                var = False
                for key, val in botlar.items():
                    if isinstance(val, dict) and val.get("bot_adi", "") == bot_adi_str:
                        var = True
                        break
                
                if not var:
                    anahtar = bot_adi_str.replace("@", "").lower()
                    botlar[anahtar] = {
                        "profil": os.environ.get("HERMES_PROFILE", "reymen"),
                        "bot_adi": self.bot_ad,
                        "gateway": "aktif",
                        "yetki": "tam",
                        "browser": "acik",
                        "terminal": "acik",
                        "web": "firecrawl",
                        "soul_boyut": 4799,
                        "tools": "tum"
                    }
                    veri["botlar"] = botlar
                    durum_yolu.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
                    logger.info("[%s] ✅ Yeni bot durum.json'a eklendi!", self.bot_ad)
                    degisiklik_ekle(self.bot_ad, f"Bot otomatik eklendi: {self.bot_ad}")
                else:
                    logger.debug("[%s] durum.json'da zaten kayitli", self.bot_ad)
            else:
                logger.warning("[%s] durum.json bulunamadi!", self.bot_ad)
        except Exception as _e:
            logger.warning("[%s] _durum_guncelle hatasi: %s", self.bot_ad, _e)

    def offset_guncelle(self, yeni_offset: int):
        if yeni_offset > self.ayarlar.get("offset", 0):
            self.ayarlar["offset"] = yeni_offset
            self._ayar_kaydet()

    def chat_ekle(self, chat_id: int):
        chatler = self.ayarlar.setdefault("bilinen_chatler", [])
        if chat_id not in chatler:
            chatler.append(chat_id)
            self.ayarlar["bilinen_chatler"] = chatler
            self._ayar_kaydet()

    def konusma_ekle(self, kullanici: str, asistan: str, maks: int = 10):
        gecmis = self.ayarlar.setdefault("konusma_gecmisi", [])
        gecmis.append({"kullanici": kullanici, "asistan": asistan})
        if len(gecmis) > maks:
            self.ayarlar["konusma_gecmisi"] = gecmis[-maks:]
        self._ayar_kaydet()

    # ── Beyin baslat ──────────────────────────────────────────────────

    def _beyin_baslat(self):
        """Beyin + ConversationLoop baslat. SADECE deepseek-v4-flash."""
        if BEYIN_CLS is None:
            logger.warning("[%s] Beyin modulu yuklu degil!", self.bot_ad)
            return

        provider = "deepseek"
        model = "deepseek-v4-flash"
        # ayarlar.json'daki eski değerleri override et
        self.ayarlar["provider"] = provider
        self.ayarlar["model"] = model

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

        cfg = {
            "default_provider": provider,
            "default_model": model,
            "providers": {
                "deepseek": {
                    "base_url": "https://api.deepseek.com",
                    "api_key": deepseek_key,
                },
                "openrouter": {
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key": openrouter_key,
                },
            },
        }
        try:
            self._beyin = BEYIN_CLS(cfg)
        except Exception as e:
            logger.error("[%s] Beyin baslatma hatasi: %s", self.bot_ad, e)
            return

        # ConversationLoop (opsiyonel)
        if CONVERSATION_LOOP_CLS is not None:
            try:
                self._loop = CONVERSATION_LOOP_CLS(beyin=self._beyin, motor=None, max_tur=5)
            except Exception as e:
                logger.warning("[%s] ConversationLoop baslatma hatasi: %s", self.bot_ad, e)

        logger.info("[%s] Beyin aktif: %s / %s", self.bot_ad, provider, model)

    # ── TOOL: Web Arama ────────────────────────────────────────────────

    def _tool_web_search(self, sorgu: str) -> str:
        """Web'de ara ve sonucu metin olarak dondur."""
        import urllib.parse as _up
        import requests as _req
        import re as _re

        # 1. BING (en stabil)
        try:
            url = f"https://www.bing.com/search?q={_up.quote(sorgu)}&mkt=tr-TR"
            headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"}
            r = _req.get(url, headers=headers, timeout=10)
            sonuc = " | ".join(_re.findall(r'<li[^>]*class="b_algo"[^>]*>.*?<h2[^>]*>(.*?)</h2>', r.text, _re.DOTALL)[:5])
            if sonuc:
                sonuc = _re.sub(r'<[^>]+>', '', sonuc)  # HTML tag temizligi
                sonuc = _re.sub(r'&#\d+;', '', sonuc)   # HTML entity temizligi
                return sonuc.strip()
        except Exception as _e:
            logger.warning("[%s] Bing hatasi: %s", self.bot_ad, _e)

        # 2. DUCKDUCKGO FALLBACK
        try:
            url = f"https://html.duckduckgo.com/html/?q={_up.quote(sorgu)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = _req.get(url, headers=headers, timeout=10)
            sonuc = " ".join(_re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', r.text)[:5])
            if sonuc:
                return sonuc
        except:
            pass

        return "(web arama su an kullanilamiyor)"

    # ── TOOL: Terminal ─────────────────────────────────────────────────

    def _tool_terminal(self, komut: str) -> str:
        """Komutu calistir ve ciktiyi dondur."""
        try:
            import subprocess as _sp
            r = _sp.run(komut, shell=True, capture_output=True, text=True, timeout=15)
            cikti = r.stdout.strip()[:500] if r.stdout.strip() else r.stderr.strip()[:500]
            return cikti if cikti else "(cikti yok)"
        except Exception as e:
            logger.warning("[%s] Terminal hatasi: %s", self.bot_ad, e)
            return f"(terminal hatasi: {e})"

    # ── AI yanit uret ──────────────────────────────────────────────────

    def ai_yanit_uret(self, mesaj: str) -> str:
        """OnceHafiza + Beyin ile yanit uret (30sn timeout).

        Args:
            mesaj: Kullanici mesaji

        Returns:
            AI yaniti (en fazla 2000 karakter)
        """
        # 1. OnceHafiza kontrolu
        if ONCE_HAFIZA_ARA is not None:
            try:
                h = ONCE_HAFIZA_ARA(mesaj, kategori="")
                if h and len(h) > 0:
                    kayit = h[0] if isinstance(h[0], dict) else {}
                    guven = kayit.get("guven", 0) if isinstance(kayit, dict) else 0
                    if guven > 0.7:
                        cozum = kayit.get("cozum", "") if isinstance(kayit, dict) else (
                            kayit[3] if len(kayit) > 3 else ""
                        )
                        if cozum:
                            return cozum[:2000]
            except Exception as _e:
                logger.warning("[TelegramBot] except Exception (L640): %s", Exception)
                pass

        # 2. Dogrudan Beyin (30sn timeout ile)
        if self._beyin is not None:
            sonuc = {"cevap": None}

            def _cagir():
                try:
                    self._ayar_yukle()
                    sistem = self.ayarlar.get("sistem_prompt", None)
                    if not sistem:
                        try:
                            _soul = _PROJE_KOK / "SOUL.md"
                            if _soul.exists():
                                sistem = _soul.read_text(encoding="utf-8")
                            else:
                                sistem = (
                                    "Sen ReYMeN adinda yardimsever bir AI asistanisin. "
                                    "Kisa ve oz cevap ver. Turkce konus."
                                )
                        except Exception:
                            sistem = (
                                "Sen ReYMeN adinda yardimsever bir AI asistanisin. "
                                "Kisa ve oz cevap ver. Turkce konus."
                            )
                    # ── TARIH VE TEMEL KURAL ───────────────────────────
                    from datetime import date as _date
                    sistem += f"\n\n[TEMEL KURAL: ÖNCE BAK, SONRA KONUŞ]\n"
                    sistem += f"BUGUNUN TARIHI: {_date.today()}\n"
                    sistem += "1. Önce web'den araştır. Web sonucu varsa SADECE onu kullan, kendi ezberinden ASLA tahmin etme.\n"
                    sistem += "2. Web sonucu yoksa 'güncel veri alınamadı' de, kendi bilginle tahmin etme.\n"
                    sistem += "3. Sorunu analiz et, adım adım çözüm sun, alternatifleri belirt.\n"
                    sistem += "4. Selam/teşekkür gibi basit mesajlarda kısa cevap ver.\n"

                    # ── TOOL OTOMATIK CALISTIRMA ─────────────────────
                    _tool_cikti = ""
                    _mesaj_lower = mesaj.lower()

                    # Web arama: soru/sikayet iceren her mesajda tetiklenir
                    _soru_mi = ("?" in mesaj or "nedir" in _mesaj_lower or "nasıl" in _mesaj_lower
                                or "ne" in _mesaj_lower or "mi" in _mesaj_lower
                                or "kaç" in _mesaj_lower or "neden" in _mesaj_lower
                                or len(mesaj.split()) >= 4)
                    _selam_mi = _mesaj_lower.strip() in ["merhaba", "selam", "hey", "sa", "hi", "hello", "iyi günler"]
                    if _soru_mi and not _selam_mi:
                        logger.info("[%s] 🔍 Web arama tetiklendi: %s", self.bot_ad, mesaj[:60])
                        _tool_cikti = self._tool_web_search(mesaj)
                        logger.info("[%s] 🔍 Web sonucu (%d karakter): %s", self.bot_ad, len(_tool_cikti), _tool_cikti[:200])
                        sistem += f"\n\n🔍 WEB ARAMA SONUCU:\n{_tool_cikti}\n"

                    # Terminal tetikleyicisi ($ ile baslayan komut)
                    if mesaj.strip().startswith("$") and len(mesaj.strip()) > 1:
                        _komut = mesaj.strip()[1:].strip()
                        logger.info("[%s] 💻 Terminal tetiklendi: %s", self.bot_ad, _komut)
                        _term_cikti = self._tool_terminal(_komut)
                        sistem += f"\n\n💻 TERMINAL CIKTISI:\n{_term_cikti}\n"

                    # ── /run komutu ────────────────────────────────────
                    if mesaj.strip().startswith("/run") and len(mesaj.strip()) > 4:
                        _gorev = mesaj.strip()[4:].strip()
                        logger.info("[%s] 🚀 /run tetiklendi: %s", self.bot_ad, _gorev)
                        _web_cikti = self._tool_web_search(_gorev)
                        sistem += f"\n\n🚀 GOREV BILGISI:\n{_web_cikti}\n"

                    gecmis = self.ayarlar.get("konusma_gecmisi", [])
                    msg_list = []
                    for kayit in gecmis[-5:]:
                        if isinstance(kayit, dict):
                            if kayit.get("kullanici"):
                                msg_list.append({"role": "user", "content": kayit["kullanici"]})
                            if kayit.get("asistan"):
                                msg_list.append({"role": "assistant", "content": kayit["asistan"]})
                    msg_list.append({"role": "user", "content": mesaj})
                    yanit = self._beyin.uret(sistem, msg_list)
                    sonuc["cevap"] = yanit.strip() if yanit else "Anlayamadim."
                except Exception as e:
                    sonuc["cevap"] = "Bir hata olustu: " + str(e)[:60]

            t = threading.Thread(target=_cagir, daemon=True)
            t.start()
            t.join(timeout=30)

            if sonuc["cevap"] is None:
                logger.warning("[%s] Beyin 30sn timeout!", self.bot_ad)
                sonuc["cevap"] = "Uzgunum, yanit uretilemedi. (timeout)"
            else:
                if ONCE_HAFIZA_KAYDET is not None:
                    try:
                        ONCE_HAFIZA_KAYDET(mesaj, "bot_sohbet", sonuc["cevap"], basari=True)
                    except Exception as _e:
                        logger.warning("[TelegramBot] except Exception (L700): %s", Exception)
                        pass
                self.konusma_ekle(mesaj, sonuc["cevap"])

            return sonuc["cevap"][:2000]

        return "AI modulu aktif degil."

    # ── Telegram mesaj islemleri ───────────────────────────────────────

    def mesaj_gonder(self, chat_id: int, metin: str) -> bool:
        """Telegram'a mesaj gonder."""
        return gonder_requests(chat_id, metin)

    def mesaj_sil(self, chat_id: int, msg_id: int):
        """Mesaj sil."""
        try:
            _api("deleteMessage", {"chat_id": chat_id, "message_id": msg_id}, timeout=5)
        except Exception as _e:
            logger.warning("[TelegramBot] except Exception (L718): %s", Exception)
            pass

    # ── Komut isleyici ────────────────────────────────────────────────

    def komut_isle(self, chat_id: int, text: str) -> bool:
        """Slash komutlarini isle — once kendi komutlari, sonra ortak komut modulu.

        Desteklenen komutlar:
          /start, /help, /run, /status, /logs
          /model, /provider, /sistem, /ayarlar, /sifirla
        """
        if not text.startswith("/"):
            return False

        parts = text.strip().split(None, 1)
        komut = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        # — Kendi AI ayar komutlari (SADECE deepseek-v4-flash) —
        if komut == "/model":
            if not arg:
                self.mesaj_gonder(chat_id, f"Model: {self.ayarlar.get('model')} (kilitli)")
            else:
                self.mesaj_gonder(chat_id, "❌ Model degistirme devre disi. Sadece deepseek-v4-flash kullanilir.")
            return True
        elif komut == "/provider":
            if not arg:
                self.mesaj_gonder(chat_id, f"Provider: {self.ayarlar.get('provider')} (kilitli)")
            else:
                self.mesaj_gonder(chat_id, "❌ Provider degistirme devre disi. Sadece deepseek kullanilir.")
            return True
        elif komut == "/sistem":
            if not arg:
                sp = self.ayarlar.get("sistem_prompt", "")
                self.mesaj_gonder(chat_id, f"Sistem prompt:\n{sp[:200]}")
            else:
                self.ayarlar["sistem_prompt"] = arg
                self._ayar_kaydet()
                self.mesaj_gonder(chat_id, "Sistem prompt guncellendi.")
            return True
        elif komut == "/ayarlar":
            o = self.ayarlar
            self.mesaj_gonder(
                chat_id,
                f"Model: {o.get('model')}\n"
                f"Provider: {o.get('provider')}\n"
                f"Chatler: {len(o.get('bilinen_chatler', []))}\n"
                f"Konusma: {len(o.get('konusma_gecmisi', []))} mesaj",
            )
            return True
        elif komut == "/sifirla":
            offset = self.ayarlar.get("offset", 0)
            self.ayarlar = dict(_VARSAYILAN_AYARLAR)
            self.ayarlar["offset"] = offset
            self._ayar_kaydet()
            self._beyin_baslat()
            self.mesaj_gonder(chat_id, "Ayarlar sifirlandi.")
            return True

        # — Ortak komut modulune yonlendir —
        if ortak_komut_isle is not None:
            try:
                return ortak_komut_isle(text, self.mesaj_gonder, chat_id)
            except Exception as _e:
                logger.warning("[TelegramBot] except Exception (L788): %s", Exception)
                pass

        return False

    # ── Polling dongusu ──────────────────────────────────────────────

    def poll(self, durma_events: Optional[list] = None):
        """Ana polling dongusu — exponential backoff supervisor ile.

        Args:
            durma_events: Event listesi — herhangi biri set edilirse dongu durur.
        """
        if durma_events is None:
            durma_events = []

        # Webhook temizle
        try:
            _api("deleteWebhook", {"drop_pending_updates": True}, timeout=5)
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        offset = self.ayarlar.get("offset", 0)
        logger.info("[%s] Polling basliyor, offset=%s", self.bot_ad, offset)

        # Startup bildirimi
        for cid in self.ayarlar.get("bilinen_chatler", []):
            self.mesaj_gonder(cid, f"{self.bot_ad} Gateway Starting")

        def _tur():
            nonlocal offset
            for evt in durma_events:
                if evt and evt.is_set():
                    logger.info("[%s] Durma istegi alindi.", self.bot_ad)
                    raise SystemExit(0)

            r = _api(
                "getUpdates",
                {"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=45,
            )
            if not r.get("ok"):
                if "409" in str(r.get("error", "")):
                    logger.warning("[%s] 409 Conflict — offset sifirlaniyor.", self.bot_ad)
                    offset = 0
                raise RuntimeError(f"[{self.bot_ad}] API hatasi: {r}")

            for update in r.get("result", []):
                yeni_offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id", 0)
                from_user = msg.get("from", {}).get("first_name", "?")

                offset = yeni_offset
                self.offset_guncelle(yeni_offset)

                if chat_id:
                    self.chat_ekle(chat_id)
                if not text:
                    continue

                logger.info("[%s] [%s] %s: %.60s", self.bot_ad, chat_id, from_user, text)

                if self.komut_isle(chat_id, text):
                    continue

                cevap = self.ai_yanit_uret(text)
                self.mesaj_gonder(chat_id, cevap)

        _polling_yonetici(self.bot_ad, _tur)

    # ── Context manager ──────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ============================================================================
# KOMUT HANDLERLARI (HTTP API modu icin)
# ============================================================================

def _cmd_start(msg: dict):
    """/start komutu."""
    gonder(msg["chat"]["id"],
           "ReYMeN ajan botuna hosgeldin!\n/help ile komutlari gor.")


def _cmd_help(msg: dict):
    """/help komutu."""
    yardim = (
        "Komutlar:\n"
        "/run <hedef>    — Ajana gorev ver\n"
        "/status         — Sistem durumu\n"
        "/logs           — Gateway logu (son 15 satir)\n"
        "/cancel         — Aktif gorevi iptal et\n"
        "/clarify <soru> — Talebi netlestir (secenekler icin | kullan)\n"
        "/exec <kod>     — Python kodu calistir\n"
        "/beceriler      — Kristallesmis beceriler\n"
        "/cron add <ad> <komut> — Cron job ekle\n"
        "/cron list      — Cron job listele\n"
        "/cron logs <ad> — Cron job logu\n"
        "/help           — Bu liste"
    )
    gonder(msg["chat"]["id"], yardim)


def _cmd_run(msg: dict, hedef: str):
    """/run komutu — ajana gorev gonder."""
    global _aktif_gorev
    cid = msg["chat"]["id"]

    if not hedef.strip():
        gonder(cid, "Kullanim: /run <hedef>\nOrnek: /run Python dosyasi olustur")
        return

    if not _gorev_kilidi.acquire(blocking=False):
        gonder(cid, "Simdi baska bir gorev calisiyor. /cancel ile iptal et.")
        return

    gonder(cid, f"Basladi: {hedef[:100]}")

    def _calistir():
        global _aktif_gorev
        iptal = threading.Event()
        _aktif_gorev = {"hedef": hedef, "iptal": iptal, "chat_id": cid}
        try:
            from reymen.sistem.main import AIAgentOrchestrator, CONFIG
            agent = AIAgentOrchestrator(config=CONFIG, max_tur=20, onay_iste=False)

            sonuc_listesi = [None]
            hata_listesi = [None]

            def _run_thread():
                try:
                    sonuc_listesi[0] = agent.run_conversation(hedef)
                except Exception as e:
                    hata_listesi[0] = str(e)

            t = threading.Thread(target=_run_thread, daemon=True)
            t.start()

            while t.is_alive():
                if iptal.is_set():
                    gonder(cid, "Gorev iptal edildi.")
                    return
                time.sleep(5)

            if hata_listesi[0]:
                gonder(cid, f"HATA:\n{hata_listesi[0][:500]}")
                try:
                    from reymen.sistem.ortak_komut import reasoning_loop as _rl, guncelle as _og
                    _rl(hata_listesi[0], str(_og())[:2000], "telegram_bot", [])
                except Exception:
                    pass
            else:
                sonuc = sonuc_listesi[0] or "(tamamlandi, cikti yok)"
                gonder(cid, f"Sonuc:\n{str(sonuc)[:2000]}")

        except Exception as e:
            gonder(cid, f"Ajan baslatilamadi: {e}")
        finally:
            _aktif_gorev = None
            _gorev_kilidi.release()

    threading.Thread(target=_calistir, daemon=True).start()


def _cmd_cancel(msg: dict):
    """/cancel komutu — aktif gorevi iptal et."""
    cid = msg["chat"]["id"]
    global _aktif_gorev
    if _aktif_gorev:
        _aktif_gorev["iptal"].set()
        gonder(cid, f"Iptal istegi gonderildi: {_aktif_gorev['hedef'][:80]}")
    else:
        gonder(cid, "Aktif gorev yok.")


def _cmd_status(msg: dict):
    """/status komutu — sistem durumu."""
    cid = msg["chat"]["id"]
    satirlar = ["ReYMeN DURUM\n"]

    try:
        durum_json_yolu = Path(__file__).parent / "durum.json"
        if not durum_json_yolu.exists():
            durum_json_yolu = _PROJE_KOK / "durum.json"
        if durum_json_yolu.exists():
            with open(durum_json_yolu, encoding="utf-8") as _f:
                durum = json.load(_f)

            ajanlar = durum.get("aktif_ajanlar", {})
            if ajanlar:
                satirlar.append(f"Ajanlar ({len(ajanlar)}):")
                for ad, bilgi in ajanlar.items():
                    satirlar.append(f"  {ad}: {bilgi.get('durum', '?')} ({bilgi.get('platform', '?')})")
            else:
                satirlar.append("Ajanlar: (liste bos)")

            surum = durum.get("surum", "?")
            satirlar.append(f"Surum: {surum}")

            si = durum.get("tohum_self_improve", {})
            trend = si.get("trend_7gun", {})
            if trend:
                satirlar.append(f"Self-improve: {trend.get('ortalama_skor', '?')} skor ({trend.get('gecme_orani', '?')} gecme)")

            kk = si.get("kod_kalitesi", {})
            if kk:
                satirlar.append(f"Kod: {kk.get('toplam_dosya', '?')} dosya, {kk.get('toplam_satir', '?')} satir")

            # Cron jobs
            cron_jobs = _cron_manager.list_jobs()
            if cron_jobs:
                satirlar.append(f"\nCron Jobs ({len(cron_jobs)}):")
                for j in cron_jobs[:5]:
                    satirlar.append(f"  {j.get('name')}: {j.get('status')}")
            else:
                satirlar.append("\nCron Jobs: yok")
        else:
            satirlar.append("durum.json bulunamadi")
            raise FileNotFoundError
    except Exception:
        # Fallback: hardcoded kontroller
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:1234/v1/models", timeout=2)
            satirlar.append("LM Studio: AKTIF")
        except Exception:
            satirlar.append("LM Studio: KAPALI")

        if _aktif_gorev:
            satirlar.append(f"Aktif gorev: {_aktif_gorev['hedef'][:60]}")
        else:
            satirlar.append("Aktif gorev: yok")

        try:
            from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
            n = ClosedLearningLoop().toplam_beceri_sayisi()
            satirlar.append(f"Beceriler: {n}")
        except Exception:
            satirlar.append("Beceriler: ?")

        try:
            from reymen.arac.kanban_orchestrator import AdvancedKanbanOrchestrator
            ozet = AdvancedKanbanOrchestrator().ozet()
            toplam = ozet.get("toplam", 0)
            satirlar.append(f"Kanban: {toplam} gorev")
        except Exception as _e:
            logger.warning("[TelegramBot] except Exception (L1035): %s", Exception)
            pass

        pid_dosyasi = Path(__file__).parent / ".ReYMeN" / "gateway.pid"
        if pid_dosyasi.exists():
            satirlar.append(f"Gateway PID: {pid_dosyasi.read_text().strip()}")
        else:
            satirlar.append("Gateway: kapali")

        # Cron jobs
        cron_jobs = _cron_manager.list_jobs()
        if cron_jobs:
            satirlar.append(f"Cron Jobs ({len(cron_jobs)}):")
            for j in cron_jobs[:5]:
                satirlar.append(f"  {j.get('name')}: {j.get('status')}")
        else:
            satirlar.append("Cron Jobs: yok")

    gonder(cid, "\n".join(satirlar))


def _cmd_logs(msg: dict):
    """/logs komutu — gateway loglari."""
    cid = msg["chat"]["id"]
    log_dosyasi = Path(__file__).parent / "logs" / "gateway.jsonl"
    if not log_dosyasi.exists():
        gonder(cid, "Log dosyasi henuz olusturulmamis.")
        return
    try:
        with open(log_dosyasi, encoding="utf-8") as f:
            satirlar = f.readlines()
        son = satirlar[-15:]
        cikti_satirlari = []
        for s in son:
            try:
                e = json.loads(s)
                ts = e.get("timestamp", "")[:16]
                tip = e.get("type", "")
                msg_ = e.get("message", "")[:80]
                cikti_satirlari.append(f"[{ts}] {tip}: {msg_}")
            except Exception:
                cikti_satirlari.append(s.strip()[:100])
        gonder(cid, "GATEWAY LOG (son 15):\n" + "\n".join(cikti_satirlari))
    except Exception as e:
        gonder(cid, f"Log okuma hatasi: {e}")


def _cmd_clarify(msg: dict, hedef: str):
    """/clarify komutu — net olmayan talebi netlestir."""
    cid = msg["chat"]["id"]
    if not hedef.strip():
        gonder(
            cid,
            "Kullanim: /clarify <soru> | <secenek1,secenek2> | <varsayilan>\n"
            "Ornek: /clarify Hangi ortam? | local,docker | local\n"
            "Sadece soru: /clarify Bu islemi onayliyor musun?",
        )
        return
    try:
        from tools.clarify_tool import run as clarify_run
        parcalar = hedef.split("|")
        soru = parcalar[0].strip()
        secenekler = [s.strip() for s in parcalar[1].split(",")] if len(parcalar) > 1 and parcalar[1].strip() else None
        varsayilan = parcalar[2].strip() if len(parcalar) > 2 and parcalar[2].strip() else ""
        sonuc = clarify_run(soru=soru, secenekler=secenekler, varsayilan=varsayilan)
        gonder(cid, sonuc)
    except Exception as e:
        gonder(cid, f"[CLARIFY HATASI] {e}")


def _cmd_exec(msg: dict, kod: str):
    """/exec komutu — Python kodunu calistir."""
    cid = msg["chat"]["id"]
    if not kod.strip():
        gonder(
            cid,
            "Kullanim: /exec <python_kodu>\n"
            "Ornek: /exec print(sum(range(100)))\n"
            "Cok satirli: noktali virgul ile ayirin.",
        )
        return
    try:
        from tools.execute_code_tool import run as exec_run
        sonuc = exec_run(kod=kod)
        cikti = sonuc[:3000]
        gonder(cid, cikti)
    except Exception as e:
        gonder(cid, f"[EXEC HATASI] {e}")


def _cmd_beceriler(msg: dict):
    """/beceriler komutu — beceri listesi."""
    cid = msg["chat"]["id"]
    try:
        from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
        beceriler = ClosedLearningLoop().tum_beceriler()
        if not beceriler:
            gonder(cid, "Hic beceri yok.")
            return
        satirlar = [f"Beceriler ({len(beceriler)}):"]
        for b in beceriler[:20]:
            satirlar.append(f"  {b['ad']}: {b['aciklama'][:60]}")
        if len(beceriler) > 20:
            satirlar.append(f"  ... ve {len(beceriler) - 20} tane daha")
        gonder(cid, "\n".join(satirlar))
    except Exception as e:
        gonder(cid, f"Beceri hatasi: {e}")


def _cmd_cron(msg: dict, args: str):
    """/cron komutu — cron job yonetimi.

    Kullanim:
      /cron add <ad> <komut>  — Yeni job ekle
      /cron list              — Job'lari listele
      /cron logs <ad>         — Job logunu goster
      /cron delete <id>       — Job sil
    """
    cid = msg["chat"]["id"]
    parts = args.strip().split(None, 2)
    if not parts:
        gonder(
            cid,
            "Kullanim:\n"
            "/cron add <ad> <komut>\n"
            "/cron list\n"
            "/cron logs <ad>\n"
            "/cron delete <id>",
        )
        return

    alt_komut = parts[0].lower()

    if alt_komut == "add" and len(parts) >= 2:
        name = parts[1] if len(parts) > 1 else "job"
        command = parts[2] if len(parts) > 2 else name
        job_id = _cron_manager.add_job(name, command)
        gonder(cid, f"Cron job eklendi:\n  Ad: {name}\n  ID: {job_id}\n  Komut: {command[:100]}")

    elif alt_komut == "list":
        jobs = _cron_manager.list_jobs()
        if not jobs:
            gonder(cid, "Hic job yok.")
            return
        lines = ["📊 Cron Jobs:\n"]
        for j in jobs[:10]:
            status = j.get("status", "?")
            emoji = {"running": "🟢", "success": "✅", "failed": "❌", "pending": "⏳"}.get(status, "⚪")
            lines.append(f"{emoji} {j.get('name')} ({j.get('id', '')}) — {status}")
        gonder(cid, "\n".join(lines))

    elif alt_komut == "logs" and len(parts) >= 2:
        name = parts[1]
        log = _cron_manager.get_job_log(name)
        if log:
            if len(log) > 3900:
                log = log[:3900] + "\n\n... (kesildi)"
            gonder(cid, f"📋 Log: {name}\n```\n{log}\n```")
        else:
            gonder(cid, f"Job bulunamadi: {name}")

    elif alt_komut == "delete" and len(parts) >= 2:
        job_id = parts[1]
        if _cron_manager.delete_job(job_id):
            gonder(cid, f"Job silindi: {job_id}")
        else:
            gonder(cid, f"Job silinemedi: {job_id}")

    else:
        gonder(cid, "Gecersiz /cron alt komutu. Kullanim: add, list, logs, delete")


# ============================================================================
# MESAJ YONLENDIRICI (HTTP API modu)
# ============================================================================

def _isle(msg: dict):
    """Gelen mesaji komutlara yonlendir — once kendi handlerlar, sonra ortak komut modulu."""
    cid = msg.get("chat", {}).get("id")
    if not cid:
        return
    if not _izin_var(cid):
        gonder(cid, "Bu bota erisim izniniz yok.")
        return

    metin = (msg.get("text") or "").strip()
    if not metin:
        return

    # ── Kendi komut handler'larimiz ──────────────────────────────────
    if metin.startswith("/"):
        parts = metin.split(None, 1)
        komut = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if komut == "/start":
            _cmd_start(msg)
            return
        elif komut == "/help":
            _cmd_help(msg)
            return
        elif komut == "/run":
            _cmd_run(msg, arg)
            return
        elif komut == "/status":
            _cmd_status(msg)
            return
        elif komut == "/logs":
            _cmd_logs(msg)
            return
        elif komut == "/cancel":
            _cmd_cancel(msg)
            return
        elif komut == "/clarify":
            _cmd_clarify(msg, arg)
            return
        elif komut == "/exec":
            _cmd_exec(msg, arg)
            return
        elif komut == "/beceriler":
            _cmd_beceriler(msg)
            return
        elif komut == "/cron":
            _cmd_cron(msg, arg)
            return

    # ── Ortak komut modulune yonlendir ───────────────────────────────
    if ortak_komut_isle is not None:
        try:
            if ortak_komut_isle(metin, gonder, cid):
                return
        except Exception as _e:
            logger.warning("[TelegramBot] except Exception (L1266): %s", Exception)
            pass

    # ── Komut degilse /run olarak isle ───────────────────────────────
    if ortak_cmd_run is not None:
        try:
            ortak_cmd_run(gonder, cid, metin)
            return
        except Exception as _e:
            logger.warning("[TelegramBot] except Exception (L1274): %s", Exception)
            pass

    # ── Hicbiri eslesmezse AI yaniti ─────────────────────────────────
    # BotProcess kullanilmiyorsa direkt mesaj
    gonder(cid, f"Anlasilamadi. /help yazin.")


# ============================================================================
# POLLING (HTTP API modu)
# ============================================================================

def _polling_yonetici(ad: str, poll_fn, durma_events: Optional[list] = None):
    """Polling supervisor — exponential backoff + maksimum deneme + restart.

    Args:
        ad: Bot adi (loglama icin)
        poll_fn: Polling fonksiyonu (tek tur)
        durma_events: Event listesi
    """
    if durma_events is None:
        durma_events = []
    ardisik_hata = 0
    while True:
        for evt in durma_events:
            if evt and evt.is_set():
                logger.info("[%s] Supervisor: durma istegi alindi.", ad)
                return
        try:
            poll_fn()
            # Basarili tur — hatayi sifirla
            ardisik_hata = 0
        except KeyboardInterrupt:
            logger.info("[%s] Supervisor: KeyboardInterrupt", ad)
            return
        except Exception as e:
            ardisik_hata += 1
            backoff = min(2 ** ardisik_hata, _MAX_BACKOFF)
            logger.error(
                "[%s] Polling hatasi (%d/%d): %s — %ds bekleniyor...",
                ad, ardisik_hata, _MAX_RETRY, e, backoff,
            )
            if ardisik_hata >= _MAX_RETRY:
                logger.critical(
                    "[%s] %d ardısık hata — bot yeniden baslatiliyor...",
                    ad, _MAX_RETRY,
                )
                time.sleep(5)
                ardisik_hata = 0  # restart dongusu
                continue
            time.sleep(backoff)


def polling():
    """Uzun polling ile Telegram'dan mesaj al — HTTP API modu."""
    if not TOKEN or TOKEN.startswith("***"):
        logger.error("TELEGRAM_BOT_TOKEN ayarli degil — cikiliyor.")
        return

    logger.info("Polling basliyor... (chat_id filtresi: %s)", CHAT_ID or "yok")
    offset_ = [0]  # mutable box

    if CHAT_ID:
        gonder(CHAT_ID, "ReYMeN botu aktif. /help yazin.")

    def _tur():
        nonlocal offset_
        sonuc = _api("getUpdates", {"offset": offset_[0], "timeout": 30}, timeout=45)
        if not sonuc.get("ok"):
            hata = sonuc.get("error", "")
            if "409" in str(hata):
                logger.warning("Polling: 409 Conflict — offset sifirlaniyor.")
                offset_[0] = 0
            raise RuntimeError(f"API hatasi: {sonuc}")
        for upd in sonuc.get("result", []):
            offset_[0] = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("edited_message")
            if msg:
                threading.Thread(target=_isle, args=(msg,), daemon=True).start()
        return True

    _polling_yonetici("HTTP", _tur)


# ============================================================================
# PTB MODE — UNIFIEDBOT (python-telegram-bot)
# ============================================================================

if PTB_AVAILABLE:

    class UnifiedBot:
        """PTB Application + HTTP API destegi ile birlesik bot.

        - PTB Application ile polling
        - Tum komut handler'lari async/await
        - Gerektiginde _api()/gonder() ile HTTP API'ye de erisebilir
        """

        def __init__(self, token: str):
            _env_yukle()
            self.token = token
            self.app = Application.builder().token(token).build() if Application else None
            self.cron = _cron_manager
            self._register_handlers()

        def _register_handlers(self):
            """PTB command handler'larini kaydet."""
            if self.app is None:
                return

            self.app.add_handler(CommandHandler("start", self._ptb_start))
            self.app.add_handler(CommandHandler("help", self._ptb_help))
            self.app.add_handler(CommandHandler("run", self._ptb_run))
            self.app.add_handler(CommandHandler("status", self._ptb_status))
            self.app.add_handler(CommandHandler("logs", self._ptb_logs))
            self.app.add_handler(CommandHandler("cancel", self._ptb_cancel))
            self.app.add_handler(CommandHandler("clarify", self._ptb_clarify))
            self.app.add_handler(CommandHandler("exec", self._ptb_exec))
            self.app.add_handler(CommandHandler("beceriler", self._ptb_beceriler))
            self.app.add_handler(CommandHandler("cron", self._ptb_cron))

            # Normal mesaj handler (komut disi)
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._ptb_mesaj_handler))

            # Fotograf handler
            self.app.add_handler(MessageHandler(filters.PHOTO, self._ptb_foto_handler))

            # Error handler
            self.app.add_error_handler(self._ptb_error_handler)

            # Komut listesini kaydet
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._bot_komutlarini_ayarla())
                loop.close()
            except Exception as _e:
                logger.warning("[TelegramBot] except Exception (L1411): %s", Exception)
                pass

        async def _bot_komutlarini_ayarla(self):
            """BotFather'a komut listesini kaydet."""
            try:
                await self.app.bot.set_my_commands([
                    ("start", "Botu baslat / menu"),
                    ("run", "Job calistir: /run <hedef>"),
                    ("status", "Sistem durumu"),
                    ("logs", "Gateway loglari"),
                    ("cancel", "Aktif gorevi iptal et"),
                    ("clarify", "Talebi netlestir"),
                    ("exec", "Python kodu calistir"),
                    ("beceriler", "Beceri listesi"),
                    ("cron", "Cron job yonetimi"),
                    ("help", "Yardim"),
                ])
                logger.info("Komut listesi Telegram'a kaydedildi")
            except Exception as e:
                logger.warning("Komut listesi kaydedilemedi: %s", e)

        # ── PTB Handler'lar ─────────────────────────────────────────

        async def _ptb_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "🤖 *ReYMeN Birlesik Bot*\n\n"
                "Komutlar:\n"
                "`/run <hedef>` — Ajana gorev ver\n"
                "`/status` — Sistem durumu\n"
                "`/logs` — Gateway loglari\n"
                "`/cancel` — Gorev iptal\n"
                "`/clarify` — Netlestirme\n"
                "`/exec <kod>` — Kod calistir\n"
                "`/beceriler` — Beceri listesi\n"
                "`/cron` — Cron yonetimi\n"
                "`/help` — Yardim\n\n"
                "_ReYMeN AI Agent_",
                parse_mode="Markdown",
            )

        async def _ptb_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            await self._ptb_start(update, context)

        async def _ptb_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            hedef = " ".join(context.args) if context.args else ""
            if not hedef:
                await update.message.reply_text("Kullanim: /run <hedef>\nOrnek: /run Python dosyasi olustur")
                return

            await update.message.reply_text(f"Gorev baslatiliyor: {hedef[:100]}...")
            # PTB modunda HTTP API uzerinden async olmayan thread'de calistir
            # (orijinal _cmd_run'u kullan)

            # Gecici msg dict olustur
            mock_msg = {"chat": {"id": cid}}
            _cmd_run(mock_msg, hedef)

        async def _ptb_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            # Gecici msg dict
            mock_msg = {"chat": {"id": cid}}
            _cmd_status(mock_msg)

        async def _ptb_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            if context.args:
                # Cron job logu
                job_name = " ".join(context.args).strip()
                log = _cron_manager.get_job_log(job_name)
                if log:
                    if len(log) > 3900:
                        log = log[:3900] + "\n\n... (kesildi)"
                    await update.message.reply_text(
                        f"📋 *Log: `{job_name}`*\n```\n{log}\n```",
                        parse_mode="Markdown",
                    )
                else:
                    await update.message.reply_text(f"Job bulunamadi: {job_name}")
            else:
                # Gateway logu
                mock_msg = {"chat": {"id": cid}}
                _cmd_logs(mock_msg)

        async def _ptb_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            mock_msg = {"chat": {"id": cid}}
            _cmd_cancel(mock_msg)

        async def _ptb_clarify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            hedef = " ".join(context.args) if context.args else ""
            mock_msg = {"chat": {"id": cid}}
            _cmd_clarify(mock_msg, hedef)

        async def _ptb_exec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            kod = " ".join(context.args) if context.args else ""
            mock_msg = {"chat": {"id": cid}}
            _cmd_exec(mock_msg, kod)

        async def _ptb_beceriler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            mock_msg = {"chat": {"id": cid}}
            _cmd_beceriler(mock_msg)

        async def _ptb_cron(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            cid = update.message.chat_id
            args = " ".join(context.args) if context.args else ""
            mock_msg = {"chat": {"id": cid}}
            _cmd_cron(mock_msg, args)

        async def _ptb_mesaj_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Normal mesajlara AI ile yanit ver."""
            if not update.message or not update.message.text:
                return
            metin = update.message.text.strip()
            if metin.startswith("/"):
                return

            # ── OnceHafiza kontrolu ─────────────────────────────────
            if ONCE_HAFIZA_ARA is not None:
                try:
                    _hafiza = ONCE_HAFIZA_ARA(metin, kategori="")
                    if _hafiza and _hafiza[0].get("guven", 0) > 0.7:
                        _cevap = _hafiza[0].get("cozum", "")[:2000]
                        if _cevap:
                            await update.message.reply_text(f"🧠 {_cevap}")
                            return
                except Exception as _e:
                    logger.warning("[TelegramBot] except Exception (L1541): %s", Exception)
                    pass

            bekleme = await update.message.reply_text("Dusunuyorum...")

            try:
                # Beyin yapilandirmasi
                deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
                openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
                cfg = {
                    "default_provider": os.environ.get("ReYMeN_DEFAULT_PROVIDER", "deepseek"),
                    "default_model": os.environ.get("ReYMeN_DEFAULT_MODEL", "deepseek-chat"),
                    "providers": {
                        "deepseek": {
                            "base_url": "https://api.deepseek.com",
                            "api_key": deepseek_key,
                        },
                        "openrouter": {
                            "base_url": "https://openrouter.ai/api/v1",
                            "api_key": openrouter_key,
                        },
                    },
                }

                if BEYIN_CLS is not None:
                    _beyin = BEYIN_CLS(cfg)
                    _sistem = "Sen ReYMeN adinda yardimsever bir AI asistanisin. Kisa ve oz cevap ver. Turkce konus."
                    _yanit = _beyin.uret(_sistem, [{"role": "user", "content": metin}])
                    _cevap = _yanit.strip() if _yanit else "Anlayamadim, tekrar dener misin?"

                    # Cevabi hafizaya kaydet
                    if ONCE_HAFIZA_KAYDET is not None:
                        try:
                            ONCE_HAFIZA_KAYDET(metin, "bot_sohbet", _cevap, basari=True)
                        except Exception as _e:
                            logger.warning("[TelegramBot] except Exception (L1575): %s", Exception)
                            pass
                else:
                    _cevap = "AI modulu aktif degil."

            except Exception as e:
                _cevap = f"Ufak bir aksaklik oldu: {str(e)[:100]}"
                logger.error("AI yanit hatasi: %s", e)

            try:
                await bekleme.delete()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            await update.message.reply_text(_cevap[:2000])

        async def _ptb_foto_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Telegram'a gonderilen fotografi analiz et."""
            if not update.message or not update.message.photo:
                return
            foto = update.message.photo[-1]
            dosya = await foto.get_file()

            import tempfile
            tmp = Path(tempfile.gettempdir()) / f"reymen_vision_{foto.file_id[:10]}.jpg"

            bekleme = await update.message.reply_text("🖼️ Gorsel analiz ediliyor...")
            try:
                await dosya.download_to_drive(tmp)
                from reymen.arac.araclar_goruntu import vision_analiz
                sonuc = vision_analiz(
                    kaynak=str(tmp),
                    soru="Bu gorselde ne var? Detayli Turkce acikla.",
                )
                await bekleme.edit_text(
                    f"🖼️ **Gorsel Analiz**\n\n{sonuc[:1500]}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                await bekleme.edit_text(f"❌ Gorsel analiz hatasi: {e}")
            finally:
                if tmp.exists():
                    tmp.unlink()

        async def _ptb_error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Hata handler."""
            logger.error("PTB Hatasi: %s | Update: %s", context.error, update)

        # ── Calistir ────────────────────────────────────────────────

        def run(self):
            """PTB polling baslat."""
            if self.app is None:
                logger.error("PTB Application baslatilamadi.")
                return
            logger.info("UnifiedBot (PTB) baslatiliyor...")
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)


# ============================================================================
# MOTOR ENTEGRASYON FONKSIYONLARI
# ============================================================================

def motor_bildirim_gonder(mesaj: str) -> str:
    """motor.py'den dogrudan Telegram bildirimi gonder.

    Args:
        mesaj: Gonderilecek mesaj

    Returns:
        Durum bilgisi
    """
    if not TOKEN or not CHAT_ID:
        return "[Telegram] Token/chat_id ayarli degil."
    sonuc = gonder(CHAT_ID, mesaj)
    return "[Telegram] Gonderildi." if sonuc.get("ok") else f"[Telegram] Hata: {sonuc}"


def telegram_araclari_kaydet(motor) -> None:
    """Motor'a TELEGRAM_GONDER aracini ekle."""
    try:
        from plugins.kanban import _plugin_arac_kaydet
    except Exception:
        return

    def _telegram_gonder(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        mesaj = params[0] if params else ham.strip('"')
        return motor_bildirim_gonder(mesaj)

    _plugin_arac_kaydet(motor, "TELEGRAM_GONDER", _telegram_gonder)
    logger.info("TELEGRAM_GONDER araci kayit edildi.")


def motor_kaydet(motor):
    """Motor'a TELEGRAM_BOT_GONDER aracini ekle."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    motor._plugin_arac_kaydet(
        "TELEGRAM_BOT_GONDER",
        lambda metin="", chat_id="": motor_bildirim_gonder(metin) if not chat_id
        else (gonder(chat_id, metin).get("ok") and "[Telegram] Gonderildi." or "[Telegram] Hata."),
        "Telegram bot ile mesaj gonder (metin, chat_id: opsiyonel — bos=env'den)",
    )


# ============================================================================
# ANA GIRIS
# ============================================================================

def main():
    """Ana giris noktasi.

    HERMES_GATEWAY ortam degiskenine gore mod secimi:
      - "ptb"  → python-telegram-bot ile (UnifiedBot)
      - "http" → HTTP API polling ile (varsayilan)
      - "ai"   → BotProcess AI modu ile
    """
    global GATEWAY_MOD

    if not TOKEN or TOKEN.startswith("***"):
        logger.error("TELEGRAM_BOT_TOKEN ayarli degil! .env dosyasini kontrol edin.")
        sys.exit(1)

    mod = GATEWAY_MOD
    logger.info("Gateway modu: %s", mod)

    if mod == "ptb":
        # python-telegram-bot modu
        if not PTB_AVAILABLE:
            logger.warning("python-telegram-bot kurulu degil! HTTP moduna geciyor.")
            mod = "http"
        else:
            bot = UnifiedBot(TOKEN)
            bot.run()
            return

    if mod == "ai":
        # BotProcess AI modu
        logger.info("BotProcess AI modu baslatiliyor...")
        bot = BotProcess(TOKEN)
        bot.poll()
        return

    # Varsayilan: HTTP API polling
    polling()


if __name__ == "__main__":
    main()
