# -*- coding: utf-8 -*-
"""
voice_engine.py — Çok back-end'li ses motoru (ABC tabanlı).

VoiceEngine ABC:
  - Soyut seslendir(text, voice) → str (ses dosyası yolu)
  - Soyut yaziya_cevir(ses_dosyasi) → str (metin)

Engine'ler:
  - OpenAITTS    — OpenAI TTS API (OPENAI_API_KEY ortam değişkeni)
  - EdgeTTS      — edge-tts (yerel, ücretsiz, internet gerekli)
  - WhisperSTT   — OpenAI Whisper API (ses → yazı, OPENAI_API_KEY gerekli)
  - StubVoice    — local dummy (bağımlılık gerektirmez, simüle eder)

VoiceRegistry:
  - engine kaydet / seç (ad ile) / seslendir / yaziya_cevir
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Sabitler
# ═══════════════════════════════════════════════════════════════════════════════

_OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
_OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
_USER_AGENT = "ReYMeN-Ajan/1.0"

# OpenAI TTS'de desteklenen sesler
_OPENAI_SESLER = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

# Varsayılan çıktı dizini
_VOICE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "voice")


# ═══════════════════════════════════════════════════════════════════════════════
# Yardımcı fonksiyonlar
# ═══════════════════════════════════════════════════════════════════════════════

def _cikti_dizini() -> str:
    """Ses dosyaları için çıktı dizinini oluştur ve döndür."""
    out_dir = _VOICE_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _ses_dosyasi_adi(prefix: str = "ses", ext: str = ".mp3") -> str:
    """Benzersiz ses dosyası adı oluştur."""
    return os.path.join(_cikti_dizini(), f"{prefix}_{uuid.uuid4().hex[:8]}{ext}")


def _get_openai_api_key() -> str:
    """OPENAI_API_KEY ortam değişkenini döndür."""
    return os.environ.get("OPENAI_API_KEY", "").strip()


# ═══════════════════════════════════════════════════════════════════════════════
# Soyut Taban Sınıfı
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceEngine(ABC):
    """Tüm ses engine'leri için soyut taban sınıfı."""

    @property
    @abstractmethod
    def ad(self) -> str:
        """Engine'in benzersiz adı (küçük harf)."""
        ...

    @abstractmethod
    def seslendir(self, text: str, voice: str = "alloy") -> str:
        """Metni sese çevir, ses dosyası yolunu döndür."""
        ...

    @abstractmethod
    def yaziya_cevir(self, ses_dosyasi: str) -> str:
        """Ses dosyasını metne çevir, metni döndür."""
        ...

    def __init__(self) -> None:
        self._hazir = self._bagimliliklari_kontrol_et()

    def _bagimliliklari_kontrol_et(self) -> bool:
        return True

    @property
    def hazir(self) -> bool:
        return self._hazir


# ═══════════════════════════════════════════════════════════════════════════════
# OpenAI TTS Engine
# ═══════════════════════════════════════════════════════════════════════════════

class OpenAITTS(VoiceEngine):
    """OpenAI TTS API ile metni sese çevirir. OPENAI_API_KEY ortam değişkeni gerekli.

    Desteklenen sesler: alloy, echo, fable, onyx, nova, shimmer
    Model: tts-1 (varsayılan) veya tts-1-hd
    """

    def __init__(self, model: str = "tts-1") -> None:
        self._model = model
        super().__init__()

    @property
    def ad(self) -> str:
        return "openai"

    def _bagimliliklari_kontrol_et(self) -> bool:
        return bool(_get_openai_api_key())

    def seslendir(self, text: str, voice: str = "alloy") -> str:
        """Metni OpenAI TTS ile sese çevir.

        Args:
            text: Seslendirilecek metin.
            voice: Ses (alloy, echo, fable, onyx, nova, shimmer).

        Returns:
            Ses dosyasının yolu veya hata mesajı.
        """
        api_key = _get_openai_api_key()
        if not api_key:
            return "[SESLENDIR/OpenAI] Hata: OPENAI_API_KEY tanimli degil."

        if not text or not text.strip():
            return "[SESLENDIR/OpenAI] Hata: 'text' bos olamaz."

        ses = voice.strip().lower()
        if ses not in _OPENAI_SESLER:
            ses = "alloy"

        try:
            import urllib.request as _req

            payload = {
                "model": self._model,
                "input": text.strip(),
                "voice": ses,
                "response_format": "mp3",
            }

            data = json.dumps(payload).encode()
            req = _req.Request(
                _OPENAI_TTS_URL,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": _USER_AGENT,
                },
            )

            cikti = _ses_dosyasi_adi(prefix="openai_tts", ext=".mp3")
            with _req.urlopen(req, timeout=60) as r:
                with open(cikti, "wb") as f:
                    f.write(r.read())

            log.info("[OpenAITTS] Ses dosyasi olusturuldu: %s (voice=%s)", cikti, ses)
            return cikti

        except Exception as e:
            log.exception("[OpenAITTS] OpenAI TTS hatasi:")
            import urllib.error as _ue
            if hasattr(e, "read"):
                try:
                    govde = e.read().decode(errors="replace")[:300]
                    return f"[SESLENDIR/OpenAI] HTTP hatasi: {govde}"
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            return f"[SESLENDIR/OpenAI] Hata: {e}"

    def yaziya_cevir(self, ses_dosyasi: str) -> str:
        """Ses dosyasını OpenAI Whisper ile metne çevir.

        Not: OpenAITTS engine'i STT için değil TTS içindir.
        WhisperSTT engine'ini kullanın.
        """
        return "[SESLENDIR/OpenAI] Bu engine TTS icindir. STT icin WhisperSTT kullanin."


# ═══════════════════════════════════════════════════════════════════════════════
# Edge TTS Engine
# ═══════════════════════════════════════════════════════════════════════════════

class EdgeTTS(VoiceEngine):
    """Microsoft Edge TTS ile metni sese çevirir (yerel, ücretsiz, internet gerekli).

    edge-tts pip paketi veya edge-tts CLI kullanır.
    Desteklenen sesler Microsoft Edge tarafından belirlenir.
    Varsayılan ses: tr-TR-AhmetNeural (Türkçe erkek)
    """

    @property
    def ad(self) -> str:
        return "edge"

    def _bagimliliklari_kontrol_et(self) -> bool:
        """edge-tts kullanılabilir mi kontrol et."""
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            # CLI kontrolü
            import shutil
            return shutil.which("edge-tts") is not None

    def seslendir(self, text: str, voice: str = "tr-TR-AhmetNeural") -> str:
        """Metni Edge TTS ile sese çevir.

        Args:
            text: Seslendirilecek metin.
            voice: Edge TTS ses adı (örn. tr-TR-AhmetNeural, en-US-AriaNeural).

        Returns:
            Ses dosyasının yolu veya hata mesajı.
        """
        if not text or not text.strip():
            return "[SESLENDIR/Edge] Hata: 'text' bos olamaz."

        if not self._hazir:
            return "[SESLENDIR/Edge] Hata: edge-tts kurulu degil."

        ses = voice.strip() or "tr-TR-AhmetNeural"
        cikti = _ses_dosyasi_adi(prefix="edge_tts", ext=".mp3")

        try:
            # edge-tts kütüphane API'sini dene
            import edge_tts as _edge_tts
            import asyncio

            async def _tts():
                communicate = _edge_tts.Communicate(text.strip(), ses)
                await communicate.save(cikti)

            asyncio.run(_tts())
            log.info("[EdgeTTS] Ses dosyasi olusturuldu: %s (voice=%s)", cikti, ses)
            return cikti

        except ImportError:
            # CLI ile dene
            import subprocess
            try:
                subprocess.run(
                    ["edge-tts", "--text", text.strip(), "--voice", ses, "--write-media", cikti],
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
                log.info("[EdgeTTS] Ses dosyasi olusturuldu (CLI): %s (voice=%s)", cikti, ses)
                return cikti
            except subprocess.CalledProcessError as e:
                return f"[SESLENDIR/Edge] CLI hatasi: {e.stderr.decode(errors='replace')[:300]}"
            except FileNotFoundError:
                return "[SESLENDIR/Edge] Hata: edge-tts CLI bulunamadi."
            except Exception as e:
                return f"[SESLENDIR/Edge] CLI hatasi: {e}"

        except Exception as e:
            log.exception("[EdgeTTS] Edge TTS hatasi:")
            return f"[SESLENDIR/Edge] Hata: {e}"

    def yaziya_cevir(self, ses_dosyasi: str) -> str:
        """Edge TTS STT desteklemez."""
        return "[SESLENDIR/Edge] Bu engine TTS icindir, STT desteklemez."


# ═══════════════════════════════════════════════════════════════════════════════
# Whisper STT Engine
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperSTT(VoiceEngine):
    """OpenAI Whisper API ile ses dosyasını metne çevirir.

    OPENAI_API_KEY ortam değişkeni gerekli.
    Model: whisper-1 (varsayılan)
    Desteklenen formatlar: mp3, mp4, mpeg, mpga, m4a, wav, webm
    """

    def __init__(self, model: str = "whisper-1") -> None:
        self._model = model
        super().__init__()

    @property
    def ad(self) -> str:
        return "whisper"

    def _bagimliliklari_kontrol_et(self) -> bool:
        return bool(_get_openai_api_key())

    def seslendir(self, text: str, voice: str = "alloy") -> str:
        """Whisper STT metin üretir, ses üretmez."""
        return "[YAZIYA_CEVIR/Whisper] Bu engine STT icindir. TTS icin OpenAITTS veya EdgeTTS kullanin."

    def yaziya_cevir(self, ses_dosyasi: str) -> str:
        """Ses dosyasını OpenAI Whisper ile metne çevir.

        Args:
            ses_dosyasi: Ses dosyasının yolu (.mp3, .wav, .m4a, vb.).

        Returns:
            Çevrilen metin veya hata mesajı.
        """
        api_key = _get_openai_api_key()
        if not api_key:
            return "[YAZIYA_CEVIR/Whisper] Hata: OPENAI_API_KEY tanimli degil."

        if not ses_dosyasi or not os.path.isfile(ses_dosyasi):
            return f"[YAZIYA_CEVIR/Whisper] Hata: dosya bulunamadi: {ses_dosyasi}"

        try:
            import urllib.request as _req

            # Multipart form-data ile dosya gönder
            boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

            # Dosya içeriğini oku
            with open(ses_dosyasi, "rb") as f:
                file_data = f.read()

            dosya_adi = os.path.basename(ses_dosyasi)

            # Multipart body oluştur
            body_parts = []
            # model field
            body_parts.append(f"--{boundary}\r\n")
            body_parts.append('Content-Disposition: form-data; name="model"\r\n\r\n')
            body_parts.append(f"{self._model}\r\n")
            # file field
            body_parts.append(f"--{boundary}\r\n")
            body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{dosya_adi}"\r\n')
            body_parts.append("Content-Type: audio/mpeg\r\n\r\n")
            body_parts.append(file_data.decode("latin-1"))  # binary'yi latin-1 ile güvenli taşı
            body_parts.append(f"\r\n--{boundary}--\r\n")

            body = ""
            for p in body_parts:
                if isinstance(p, bytes):
                    body += p.decode("latin-1")
                else:
                    body += p

            data = body.encode("latin-1")

            req = _req.Request(
                _OPENAI_STT_URL,
                data=data,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": _USER_AGENT,
                },
            )

            with _req.urlopen(req, timeout=120) as r:
                response = json.loads(r.read().decode())

            metin = response.get("text", "").strip()
            if not metin:
                return "[YAZIYA_CEVIR/Whisper] Hata: metin bulunamadi."

            log.info("[WhisperSTT] Ses dosyasi cozuldu: %s (%d karakter)", ses_dosyasi, len(metin))
            return metin

        except ImportError:
            # openai kütüphanesini dene
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                with open(ses_dosyasi, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model=self._model,
                        file=f,
                    )
                metin = transcript.text.strip()
                if not metin:
                    return "[YAZIYA_CEVIR/Whisper] Hata: metin bulunamadi."
                log.info("[WhisperSTT] Ses dosyasi cozuldu (openai lib): %s (%d karakter)", ses_dosyasi, len(metin))
                return metin
            except Exception as e:
                log.exception("[WhisperSTT] openai kutuphanesi hatasi:")
                return f"[YAZIYA_CEVIR/Whisper] openai lib hatasi: {e}"

        except Exception as e:
            log.exception("[WhisperSTT] Whisper API hatasi:")
            import urllib.error as _ue
            if hasattr(e, "read"):
                try:
                    govde = e.read().decode(errors="replace")[:300]
                    return f"[YAZIYA_CEVIR/Whisper] HTTP hatasi: {govde}"
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            return f"[YAZIYA_CEVIR/Whisper] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stub Voice Engine (local dummy / simüle)
# ═══════════════════════════════════════════════════════════════════════════════

class StubVoice(VoiceEngine):
    """Local dummy engine. API key gerekmez. Ses üretmez, simüle eder."""

    @property
    def ad(self) -> str:
        return "stub"

    def seslendir(self, text: str, voice: str = "alloy") -> str:
        return (
            f"[SESLENDIR/Stub] Simule edilen seslendirme.\n"
            f"  Metin: {text.strip()}\n"
            f"  Ses: {voice}\n"
            f"  (Stub engine: gercek ses icin OPENAI_API_KEY ayarlayin veya EdgeTTS kullanin)"
        )

    def yaziya_cevir(self, ses_dosyasi: str) -> str:
        return (
            f"[YAZIYA_CEVIR/Stub] Simule edilen metin cevrimi.\n"
            f"  Dosya: {ses_dosyasi}\n"
            f"  (Stub engine: gercek cevrim icin OPENAI_API_KEY ayarlayin)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Voice Registry
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceRegistry:
    """Ses engine'lerini kaydet, seç ve çalıştır.

    Kullanım:
        vr = VoiceRegistry()
        vr.kaydet("openai", OpenAITTS())
        vr.kaydet("edge", EdgeTTS())
        engine = vr.sec("openai")
        engine.seslendir("Merhaba Dünya")
    """

    def __init__(self) -> None:
        self._engines: dict[str, VoiceEngine] = {}
        self._varsayilan: Optional[str] = None

    def kaydet(self, engine: VoiceEngine) -> None:
        """Bir engine kaydet."""
        adi = engine.ad
        self._engines[adi] = engine
        # Varsayılan: openai > whisper > edge > stub
        if self._varsayilan is None:
            self._varsayilan = adi
        elif adi == "openai" and engine.hazir:
            self._varsayilan = adi
        elif adi == "whisper" and engine.hazir and self._varsayilan not in ("openai",):
            self._varsayilan = adi
        elif adi == "edge" and engine.hazir and self._varsayilan not in ("openai", "whisper"):
            self._varsayilan = adi
        log.info("[VoiceRegistry] Engine kaydedildi: %s (varsayilan: %s)", adi, self._varsayilan)

    def sec(self, ad: str) -> Optional[VoiceEngine]:
        """Ada göre engine seç. Bulunamazsa varsayılanı döndür."""
        eng = self._engines.get(ad)
        if eng is None and self._varsayilan:
            log.warning("[VoiceRegistry] '%s' bulunamadi, varsayilana dusuluyor: %s", ad, self._varsayilan)
            return self._engines.get(self._varsayilan)
        return eng

    @property
    def varsayilan(self) -> Optional[VoiceEngine]:
        """Varsayılan engine'i döndür."""
        return self._engines.get(self._varsayilan) if self._varsayilan else None

    def seslendir(self, engine_adi: str, text: str, voice: str = "alloy") -> str:
        """Bir engine ile metni sese çevir."""
        if not text or not text.strip():
            return "[SESLENDIR] Hata: 'text' bos olamaz."
        eng = self.sec(engine_adi)
        if eng is None:
            return f"[SESLENDIR] '{engine_adi}' engine'i bulunamadi."
        if not eng.hazir:
            return f"[SESLENDIR] '{engine_adi}' hazir degil (API anahtari eksik)."
        try:
            return eng.seslendir(text.strip(), voice)
        except Exception as e:
            log.exception("[VoiceRegistry] '%s' seslendirme hatasi:", engine_adi)
            return f"[SESLENDIR] '{engine_adi}' hatasi: {e}"

    def yaziya_cevir(self, engine_adi: str, ses_dosyasi: str) -> str:
        """Bir engine ile ses dosyasını metne çevir."""
        if not ses_dosyasi:
            return "[YAZIYA_CEVIR] Hata: 'ses_dosyasi' bos olamaz."
        eng = self.sec(engine_adi)
        if eng is None:
            return f"[YAZIYA_CEVIR] '{engine_adi}' engine'i bulunamadi."
        if not eng.hazir:
            return f"[YAZIYA_CEVIR] '{engine_adi}' hazir degil (API anahtari eksik)."
        try:
            return eng.yaziya_cevir(ses_dosyasi)
        except Exception as e:
            log.exception("[VoiceRegistry] '%s' yaziya_cevirme hatasi:", engine_adi)
            return f"[YAZIYA_CEVIR] '{engine_adi}' hatasi: {e}"


# ── Global registry singleton ──────────────────────────────────────────────────

_registry: Optional[VoiceRegistry] = None


def _get_registry() -> VoiceRegistry:
    """Global VoiceRegistry singleton'ını oluştur/döndür."""
    global _registry
    if _registry is None:
        _registry = VoiceRegistry()
        # Stub her zaman çalışır
        _registry.kaydet(StubVoice())
        # OpenAI TTS
        try:
            _registry.kaydet(OpenAITTS())
        except Exception as e:
            log.warning("[VoiceRegistry] OpenAITTS yuklenemedi: %s", e)
        # OpenAI TTS HD
        try:
            _registry.kaydet(OpenAITTS(model="tts-1-hd"))
        except Exception as e:
            log.warning("[VoiceRegistry] OpenAITTS (hd) yuklenemedi: %s", e)
        # Edge TTS
        try:
            _registry.kaydet(EdgeTTS())
        except Exception as e:
            log.warning("[VoiceRegistry] EdgeTTS yuklenemedi: %s", e)
        # Whisper STT
        try:
            _registry.kaydet(WhisperSTT())
        except Exception as e:
            log.warning("[VoiceRegistry] WhisperSTT yuklenemedi: %s", e)
    return _registry


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Fonksiyonları
# ═══════════════════════════════════════════════════════════════════════════════

def seslendir(text: str, voice: str = "alloy", backend: str = "") -> str:
    """SESLENDIR tool'u — metni sese çevir.

    Args:
        text: Seslendirilecek metin.
        voice: Kullanilacak ses (openai: alloy/echo/fable/onyx/nova/shimmer,
               edge: tr-TR-AhmetNeural vb.).
        backend: Kullanilacak engine adi (openai, edge, stub).
                 Bos birakilirsa varsayilan kullanilir.

    Returns:
        Ses dosyasi yolu veya hata mesaji.
    """
    reg = _get_registry()
    engine_adi = backend.strip() if backend.strip() else ""
    if not engine_adi:
        eng = reg.varsayilan
        if eng is None:
            return "[SESLENDIR] Hata: hicbir engine kayitli degil."
        engine_adi = eng.ad
    return reg.seslendir(engine_adi, text, voice)


def yaziya_cevir(ses_dosyasi: str, backend: str = "whisper") -> str:
    """YAZIYA_CEVIR tool'u — ses dosyasını metne çevir.

    Args:
        ses_dosyasi: Ses dosyasinin yolu.
        backend: Kullanilacak engine adi (whisper, stub).

    Returns:
        Cozulen metin veya hata mesaji.
    """
    reg = _get_registry()
    engine_adi = backend.strip() if backend.strip() else "whisper"
    return reg.yaziya_cevir(engine_adi, ses_dosyasi)


def voice_engine_listele() -> str:
    """Kayitli engine'leri listele."""
    reg = _get_registry()
    satirlar = ["[SESLENDIR] Kayitli engine'ler:"]
    for ad, eng in reg._engines.items():
        durum = "hazir" if eng.hazir else "API anahtari eksik"
        isaret = " >" if ad == reg._varsayilan else "  "
        satirlar.append(f"  {isaret} {ad} ({durum})")
    return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# Motor Kayit
# ═══════════════════════════════════════════════════════════════════════════════

def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir. SESLENDIR ve YAZIYA_CEVIR tool'larini kaydeder."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "SESLENDIR",
            lambda ham="": _seslendir_ayristir_ve_calistir(ham),
            "Metni sese cevirir (coklu back-end).\n"
            " Kullanim: SESLENDIR(text=\"...\", voice=\"alloy\", backend=\"openai|edge|stub\")\n"
            "Varsayilan: OpenAI TTS > Edge TTS > stub\n"
            "OpenAI: OPENAI_API_KEY ortam degiskeni gerekli.\n"
            "  Sesler: alloy, echo, fable, onyx, nova, shimmer\n"
            "Edge: edge-tts pip paketi gerekli, internet baglantisi lazim.\n"
            "  Sesler: tr-TR-AhmetNeural, en-US-AriaNeural vb.\n"
            "Stub: API key gerekmez, simulasyon yapar.",
        )
        motor._plugin_arac_kaydet(
            "YAZIYA_CEVIR",
            lambda ham="": _yaziya_cevir_ayristir_ve_calistir(ham),
            "Ses dosyasini metne cevirir (Whisper STT).\n"
            " Kullanim: YAZIYA_CEVIR(ses_dosyasi=\"...\", backend=\"whisper|stub\")\n"
            "Whisper: OPENAI_API_KEY ortam degiskeni gerekli.\n"
            "Stub: API key gerekmez, simulasyon yapar.",
        )
        motor._plugin_arac_kaydet(
            "SESLENDIR_BACKEND_LISTELE",
            lambda: voice_engine_listele(),
            "Kullanilabilir ses engine'lerini listeler.",
        )
    except Exception as e:
        log.warning("[VoiceEngine] Motor kayit hatasi: %s", e)


def _seslendir_ayristir_ve_calistir(ham: str) -> str:
    """SESLENDIR(ham) -> parametre ayristir."""
    import re as _re
    text = ""
    voice = "alloy"
    backend = ""

    t_match = _re.search(r'text\s*=\s*"([^"]*)"', ham)
    if t_match:
        text = t_match.group(1)

    v_match = _re.search(r'voice\s*=\s*"([^"]*)"', ham)
    if v_match:
        voice = v_match.group(1)

    bk_match = _re.search(r'backend\s*=\s*"([^"]*)"', ham)
    if bk_match:
        backend = bk_match.group(1)

    if not text:
        text = ham.strip().strip('"').strip("'")

    return seslendir(text, voice, backend)


def _yaziya_cevir_ayristir_ve_calistir(ham: str) -> str:
    """YAZIYA_CEVIR(ham) -> parametre ayristir."""
    import re as _re
    ses_dosyasi = ""
    backend = "whisper"

    s_match = _re.search(r'ses_dosyasi\s*=\s*"([^"]*)"', ham)
    if s_match:
        ses_dosyasi = s_match.group(1)

    bk_match = _re.search(r'backend\s*=\s*"([^"]*)"', ham)
    if bk_match:
        backend = bk_match.group(1)

    if not ses_dosyasi:
        ses_dosyasi = ham.strip().strip('"').strip("'")

    return yaziya_cevir(ses_dosyasi, backend)


# ═══════════════════════════════════════════════════════════════════════════════
# Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(voice_engine_listele())
    print("\n--- Stub Test ---")
    print(seslendir("Merhaba Dünya", backend="stub"))
    print("\n--- Stub STT Test ---")
    print(yaziya_cevir("test.mp3", backend="stub"))
