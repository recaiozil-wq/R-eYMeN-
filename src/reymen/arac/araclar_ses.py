# -*- coding: utf-8 -*-
"""
araclar_ses.py — Sesli komut girişi + STT/TTS araçları.

  SES_DINLE   — Mikrofonu dinler, konuşmayı metne çevirir (mevcut, korunur).
  SES_TANIMA  — Bir ses dosyasını (wav/mp3/...) metne çevirir (Whisper).
  SESLENDIR   — Metni sese çevirir, dosya yolu MEDIA formatında döner.
  OPENAI_TTS  — OpenAI TTS API ile metni sese çevirir (yeni).
  OPENAI_STT  — OpenAI Whisper API ile sesi metne çevirir (yeni).

Bağımlılıklar (hepsi opsiyonel, eksikse araç sessizce/açıklayarak degrade eder):
    pip install SpeechRecognition pyaudio   # SES_DINLE (mikrofon)
    pip install faster-whisper              # SES_TANIMA (öncelikli, hızlı)
    pip install openai-whisper              # SES_TANIMA (fallback)
    pip install edge-tts                    # SESLENDIR (öncelikli, online, kaliteli)
    pip install pyttsx3                     # SESLENDIR (fallback, offline)

OpenAI API (yeni):
    OPENAI_API_KEY env var gerekli
    POST https://api.openai.com/v1/audio/speech      → TTS
    POST https://api.openai.com/v1/audio/transcriptions → STT

MEDIA format sözleşmesi (köprü/telegram_bot tarafından ayrıştırılması beklenir):

    [MEDIA type="audio" src="<dosya-yolu>"]
    <açıklama>
    [/MEDIA]

Projenizdeki köprü farklı bir biçim bekliyorsa _media() fonksiyonunu güncelleyin.
"""
import asyncio
import logging
import os
import tempfile
import threading
import uuid

logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
    SR_OK = True
except Exception:
    SR_OK = False


def _media(tip: str, kaynak: str, aciklama: str = "") -> str:
    blok = f'[MEDIA type="{tip}" src="{kaynak}"]'
    if aciklama:
        blok += f"\n{aciklama}"
    blok += "\n[/MEDIA]"
    return blok


class SesliKomut:
    def __init__(self, dil="tr-TR"):
        self.dil = dil
        self._recognizer = sr.Recognizer() if SR_OK else None

    def dinle(self, zaman_asimi=5):
        """Mikrofondan tek bir komut dinler, metne çevirir."""
        if not SR_OK:
            return "[Ses]: SpeechRecognition kurulu değil (pip install SpeechRecognition pyaudio)."
        try:
            with sr.Microphone() as kaynak:
                self._recognizer.adjust_for_ambient_noise(kaynak, duration=0.5)
                print("[Ses]: Dinliyorum...")
                ses = self._recognizer.listen(kaynak, timeout=zaman_asimi)
            metin = self._recognizer.recognize_google(ses, language=self.dil)
            return metin
        except sr.WaitTimeoutError:
            return "[Ses]: Zaman aşımı, ses algılanmadı."
        except sr.UnknownValueError:
            return "[Ses]: Ne dediğiniz anlaşılamadı."
        except Exception as e:
            return f"[Ses Hatası]: {e}"

    def seslendir(self, metin):
        """Metni doğrudan hoparlörden seslendirir (pyttsx3, dosya üretmez).

        Not: Dosya üretip MEDIA olarak göndermek için modül seviyesindeki
        seslendir() fonksiyonunu (SESLENDIR aracı) kullanın.
        """
        try:
            import pyttsx3
            motor = pyttsx3.init()
            motor.say(metin)
            motor.runAndWait()
            return "[Ses]: Seslendirildi."
        except ImportError:
            return "[Ses]: TTS kurulu değil (pip install pyttsx3)."
        except Exception as e:
            return f"[Ses Hatasi]: {e}"

    def komut_bekle(self, tetikleyici="yeni proje"):
        """Belirli bir tetikleyici cümle duyana kadar dinler (basit eşleşme)."""
        metin = self.dinle()
        if isinstance(metin, str) and tetikleyici.lower() in metin.lower():
            return {"tetiklendi": True, "metin": metin}
        return {"tetiklendi": False, "metin": metin}


# ── SES_TANIMA (STT) ─────────────────────────────────────────────────

_fw_model = None
_ow_model = None
_model_lock = threading.Lock()


def _faster_whisper_model(model_adi: str = "small"):
    global _fw_model
    if _fw_model is None:
        with _model_lock:
            if _fw_model is None:
                from faster_whisper import WhisperModel
                _fw_model = WhisperModel(model_adi, device="cpu", compute_type="int8")
    return _fw_model


def _openai_whisper_model(model_adi: str = "base"):
    global _ow_model
    if _ow_model is None:
        with _model_lock:
            if _ow_model is None:
                import whisper
                _ow_model = whisper.load_model(model_adi)
    return _ow_model


def ses_tanima(dosya_yolu: str, dil: str = "tr") -> str:
    """Ses dosyasını (wav/mp3/m4a/...) metne çevirir. faster-whisper > openai-whisper."""
    if not dosya_yolu or not dosya_yolu.strip():
        return "[SES_TANIMA] Hata: 'dosya_yolu' boş olamaz."
    if not os.path.exists(dosya_yolu):
        return f"[SES_TANIMA] Hata: dosya bulunamadı: {dosya_yolu}"

    dil_param = dil.strip() if dil and dil.strip() else None

    try:
        model = _faster_whisper_model()
        segments, _bilgi = model.transcribe(dosya_yolu, language=dil_param)
        metin = " ".join(s.text.strip() for s in segments).strip()
        return f"[SES_TANIMA] (faster-whisper)\n{metin or '(boş)'}"
    except ImportError:
        logger.warning("[fix_01_sessiz_except] ImportError")
    except Exception as e:
        logger.warning("[SES_TANIMA] faster-whisper hatası, openai-whisper deneniyor: %s", e)

    try:
        model = _openai_whisper_model()
        sonuc = model.transcribe(dosya_yolu, language=dil_param)
        metin = (sonuc.get("text") or "").strip()
        return f"[SES_TANIMA] (openai-whisper)\n{metin or '(boş)'}"
    except ImportError:
        return ("[SES_TANIMA] Hata: whisper kurulu değil. "
                "pip install faster-whisper  (veya)  pip install openai-whisper")
    except Exception as e:
        logger.error("[SES_TANIMA] hata: %s", e)
        return f"[SES_TANIMA] Hata: {e}"


# ── SESLENDIR (TTS) ──────────────────────────────────────────────────

def seslendir(metin: str, ses: str = "tr-TR-AhmetNeural", dosya_yolu: str = "") -> str:
    """Metni sese çevirir; dosya yolunu MEDIA formatında döner. edge-tts > pyttsx3."""
    if not metin or not metin.strip():
        return "[SESLENDIR] Hata: 'metin' boş olamaz."

    if not dosya_yolu or not dosya_yolu.strip():
        dosya_yolu = os.path.join(tempfile.gettempdir(), f"reymen_tts_{uuid.uuid4().hex[:8]}.mp3")

    try:
        import edge_tts

        async def _uret():
            iletisimci = edge_tts.Communicate(metin.strip(), ses)
            await iletisimci.save(dosya_yolu)

        asyncio.run(_uret())
        return _media("audio", dosya_yolu, f"Seslendirme (edge-tts, ses={ses})")
    except ImportError:
        logger.warning("[fix_01_sessiz_except] ImportError")
    except Exception as e:
        logger.warning("[SESLENDIR] edge-tts hatası, pyttsx3'e düşülüyor: %s", e)

    try:
        import pyttsx3
        wav_yolu = dosya_yolu.rsplit(".", 1)[0] + ".wav"
        motor = pyttsx3.init()
        motor.save_to_file(metin.strip(), wav_yolu)
        motor.runAndWait()
        return _media("audio", wav_yolu, "Seslendirme (pyttsx3, offline)")
    except ImportError:
        return "[SESLENDIR] Hata: edge-tts veya pyttsx3 kurulu değil. pip install edge-tts"
    except Exception as e:
        logger.error("[SESLENDIR] hata: %s", e)
        return f"[SESLENDIR] Hata: {e}"


# ── OPENAI TTS (Text-to-Speech) ───────────────────────────────────────

def openai_tts(metin: str, ses: str = "alloy", model: str = "tts-1",
               dosya_yolu: str = "", format: str = "mp3") -> str:
    """OpenAI TTS API ile metni sese çevirir.

    https://api.openai.com/v1/audio/speech endpoint'ini çağırır.

    Args:
        metin: Sese çevrilecek metin
        ses: OpenAI sesi ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer')
        model: TTS modeli ('tts-1' hızlı, 'tts-1-hd' kaliteli)
        dosya_yolu: Çıktı dosyası yolu (boşsa temp dosya)
        format: Çıktı formatı ('mp3', 'opus', 'aac', 'flac')

    Returns:
        str: MEDIA formatında dosya yolu veya hata mesajı
    """
    if not metin or not metin.strip():
        return "[OPENAI_TTS] Hata: 'metin' boş olamaz."

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "[OPENAI_TTS] Hata: OPENAI_API_KEY env var gerekli."

    if not dosya_yolu or not dosya_yolu.strip():
        dosya_yolu = os.path.join(
            tempfile.gettempdir(), f"reymen_openai_tts_{uuid.uuid4().hex[:8]}.{format}"
        )

    import urllib.request
    import urllib.error
    import json as _json

    body = _json.dumps({
        "model": model,
        "input": metin.strip(),
        "voice": ses,
        "response_format": format,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            ses_verisi = resp.read()

        with open(dosya_yolu, "wb") as f:
            f.write(ses_verisi)

        return _media(
            "audio", dosya_yolu,
            f"Seslendirme (OpenAI TTS, ses={ses}, model={model})"
        )
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "[OPENAI_TTS] Kimlik doğrulama hatası. OPENAI_API_KEY kontrol edin."
        elif e.code == 429:
            return "[OPENAI_TTS] Rate limit aşıldı. Daha sonra tekrar deneyin."
        return f"[OPENAI_TTS] HTTP {e.code}: {e.reason}"
    except Exception as e:
        logger.error("[OPENAI_TTS] hata: %s", e)
        return f"[OPENAI_TTS] Hata: {e}"


# ── OPENAI STT (Speech-to-Text / Whisper API) ────────────────────────

def openai_stt(dosya_yolu: str, model: str = "whisper-1", dil: str = "tr") -> str:
    """OpenAI Whisper API ile ses dosyasını metne çevirir.

    https://api.openai.com/v1/audio/transcriptions endpoint'ini çağırır.

    Args:
        dosya_yolu: Ses dosyası yolu (wav/mp3/m4a/...)
        model: STT modeli ('whisper-1')
        dil: Dil kodu ('tr', 'en', ...)

    Returns:
        str: Transkripsiyon metni veya hata mesajı
    """
    if not dosya_yolu or not dosya_yolu.strip():
        return "[OPENAI_STT] Hata: 'dosya_yolu' boş olamaz."
    if not os.path.exists(dosya_yolu):
        return f"[OPENAI_STT] Hata: dosya bulunamadı: {dosya_yolu}"

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "[OPENAI_STT] Hata: OPENAI_API_KEY env var gerekli."

    import urllib.request
    import urllib.error
    import json as _json
    import mimetypes

    # multipart/form-data manuel oluştur
    boundary = f"----ReYMeN{uuid.uuid4().hex}"
    dosya_adi = os.path.basename(dosya_yolu)
    mime_tip = mimetypes.guess_type(dosya_yolu)[0] or "audio/mpeg"

    with open(dosya_yolu, "rb") as f:
        ses_verisi = f.read()

    body_parts = []
    # model field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\n')
    body_parts.append(f"{model}\r\n".encode())
    # language field
    if dil and dil.strip():
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="language"\r\n\r\n')
        body_parts.append(f"{dil.strip()}\r\n".encode())
    # file field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{dosya_adi}"\r\n'.encode()
    )
    body_parts.append(f"Content-Type: {mime_tip}\r\n\r\n".encode())
    body_parts.append(ses_verisi)
    body_parts.append(f"\r\n--{boundary}--\r\n".encode())

    body = b"".join(body_parts)

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            sonuc = _json.loads(resp.read().decode("utf-8"))

        metin = sonuc.get("text", "").strip()
        return f"[OPENAI_STT] (Whisper API)\n{metin or '(boş)'}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "[OPENAI_STT] Kimlik doğrulama hatası. OPENAI_API_KEY kontrol edin."
        elif e.code == 429:
            return "[OPENAI_STT] Rate limit aşıldı. Daha sonra tekrar deneyin."
        return f"[OPENAI_STT] HTTP {e.code}: {e.reason}"
    except Exception as e:
        logger.error("[OPENAI_STT] hata: %s", e)
        return f"[OPENAI_STT] Hata: {e}"


def motor_kaydet(motor):
    """Ses araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    _sk = SesliKomut()
    try:
        motor._plugin_arac_kaydet(
            "SES_DINLE",
            lambda: _sk.dinle(),
            "Mikrofondan sesli komut dinle ve metne çevir",
        )
        motor._plugin_arac_kaydet(
            "SES_TANIMA",
            ses_tanima,
            "Bir ses dosyasını metne çevirir (Whisper). Parametreler: dosya_yolu, dil.",
        )
        motor._plugin_arac_kaydet(
            "SESLENDIR",
            seslendir,
            "Metni sese çevirir, dosya yolunu MEDIA olarak döner (edge-tts/pyttsx3). "
            "Parametreler: metin, ses, dosya_yolu.",
        )
        motor._plugin_arac_kaydet(
            "OPENAI_TTS",
            openai_tts,
            "OpenAI TTS API ile metni sese çevirir (yüksek kalite). "
            "Parametreler: metin, ses (alloy/echo/fable/onyx/nova/shimmer), "
            "model (tts-1/tts-1-hd), dosya_yolu, format.",
        )
        motor._plugin_arac_kaydet(
            "OPENAI_STT",
            openai_stt,
            "OpenAI Whisper API ile ses dosyasını metne çevirir. "
            "Parametreler: dosya_yolu, model (whisper-1), dil.",
        )
    except Exception as e:
        print(f"[AraclarSes] Motor kayıt hatası: {e}")


if __name__ == "__main__":
    print("SesliKomut hazir (SpeechRecognition:%s)" % SR_OK)

