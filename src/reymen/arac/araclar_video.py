# -*- coding: utf-8 -*-
"""
araclar_video.py — Video bilgi ve analiz araçları.

  VIDEO_BILGI   — Video metadata (başlık, süre, çözünürlük, yükleyen).
                  Uzak (YouTube vb.) için yt-dlp, yerel dosya için ffprobe kullanır.
  VIDEO_ANALIZ  — Altyazı varsa onu, yoksa sesi Whisper ile metne çevirir,
                  basit bir hızlı özet + transkript döner. Asıl derin özet
                  ReAct ajanının kendi LLM'i tarafından bu metin üzerinden
                  yapılması beklenir (araç burada ham/yarı-işlenmiş veri sağlar).

Bağımlılıklar (opsiyonel — eksikse araç açıklayarak degrade eder):
    pip install yt-dlp                       # uzak video bilgisi + indirme
    pip install faster-whisper                # ses → metin (öncelikli)
    pip install openai-whisper                 # ses → metin (fallback)
    ffmpeg / ffprobe sistemde kurulu olmalı   # yerel video metadata + ses çıkarma

MEDIA bu modülde kullanılmaz (video dosyasının kendisi gönderilmiyor, sadece
metin/metadata döndürülüyor); biçim diğer araçlarla tutarlı kalsın diye
ileride video MEDIA'sı eklenmek istenirse aynı sözleşme izlenebilir:

    [MEDIA type="video" src="<url-veya-yol>"]
"""
import glob
import logging
import os
import re
import subprocess
import tempfile
import threading

logger = logging.getLogger(__name__)

_whisper_lock = threading.Lock()
_fw_model = None
_ow_model = None


# ── Whisper (bağımsız kopya — diğer modüllere bağımlı olmamak için) ──

def _faster_whisper_model(model_adi: str = "small"):
    global _fw_model
    if _fw_model is None:
        with _whisper_lock:
            if _fw_model is None:
                from faster_whisper import WhisperModel
                _fw_model = WhisperModel(model_adi, device="cpu", compute_type="int8")
    return _fw_model


def _openai_whisper_model(model_adi: str = "base"):
    global _ow_model
    if _ow_model is None:
        with _whisper_lock:
            if _ow_model is None:
                import whisper
                _ow_model = whisper.load_model(model_adi)
    return _ow_model


def _whisper_transcribe(dosya_yolu: str, dil: str = "tr") -> str:
    dil_param = dil.strip() if dil and dil.strip() else None
    try:
        model = _faster_whisper_model()
        segments, _bilgi = model.transcribe(dosya_yolu, language=dil_param)
        return " ".join(s.text.strip() for s in segments).strip()
    except ImportError:
        logger.warning("[fix_01_sessiz_except] ImportError")
    except Exception as e:
        logger.warning("[VIDEO_ANALIZ] faster-whisper hatası, openai-whisper deneniyor: %s", e)
    try:
        model = _openai_whisper_model()
        sonuc = model.transcribe(dosya_yolu, language=dil_param)
        return (sonuc.get("text") or "").strip()
    except ImportError:
        return ""
    except Exception as e:
        logger.warning("[VIDEO_ANALIZ] openai-whisper hatası: %s", e)
        return ""


# ── Altyazı dosyası ayrıştırma (vtt/srt → düz metin) ─────────────────

def _altyazi_dosya_oku(yol: str) -> str:
    with open(yol, encoding="utf-8", errors="replace") as f:
        ham = f.read()
    satirlar = []
    for satir in ham.splitlines():
        s = satir.strip()
        if not s or s.upper().startswith(("WEBVTT", "NOTE", "KIND:", "LANGUAGE:")):
            continue
        if re.match(r"^\d+$", s):           # srt sıra numarası
            continue
        if "-->" in s:                       # zaman damgası
            continue
        s = re.sub(r"<[^>]+>", "", s)        # vtt etiketleri
        if s:
            satirlar.append(s)
    # otomatik altyazılarda sık görülen ardışık tekrarları sil
    temiz = []
    for s in satirlar:
        if not temiz or temiz[-1] != s:
            temiz.append(s)
    return " ".join(temiz)


def _basit_ozet(metin: str, n_cumle: int = 3, maks_uzunluk: int = 400) -> str:
    cumleler = re.split(r"(?<=[.!?])\s+", metin.strip())
    secim = " ".join(c for c in cumleler[:n_cumle] if c)
    if len(secim) > maks_uzunluk:
        secim = secim[:maks_uzunluk] + "…"
    return secim or "(özet çıkarılamadı)"


# ── Uzak video (YouTube vb.) ──────────────────────────────────────────

def _video_bilgi_uzak(url: str) -> str:
    try:
        import yt_dlp
    except ImportError:
        return "[VIDEO_BILGI] Hata: yt-dlp kurulu değil (pip install yt-dlp)."
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        baslik = info.get("title", "?")
        sure = info.get("duration", "?")
        genislik, yukseklik = info.get("width", "?"), info.get("height", "?")
        yukleyen = info.get("uploader", "?")
        return (f"[VIDEO_BILGI]\nBaşlık: {baslik}\nSüre: {sure}s\n"
                f"Çözünürlük: {genislik}x{yukseklik}\nYükleyen: {yukleyen}\nURL: {url}")
    except Exception as e:
        return f"[VIDEO_BILGI] Hata: {e}"


def _altyazi_veya_ses_metni_uzak(url: str, dil: str) -> tuple:
    """Önce altyazı indirmeyi dener; yoksa sesi indirip Whisper ile çevirir."""
    import yt_dlp

    with tempfile.TemporaryDirectory() as tmp:
        # 1) Altyazı dene (manuel + otomatik)
        try:
            with yt_dlp.YoutubeDL({
                "quiet": True, "no_warnings": True, "skip_download": True,
                "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": [dil or "tr", "en"],
                "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
            }) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.warning("[VIDEO_ANALIZ] altyazı indirme hatası: %s", e)

        altyazilar = glob.glob(os.path.join(tmp, "*.vtt")) + glob.glob(os.path.join(tmp, "*.srt"))
        if altyazilar:
            return _altyazi_dosya_oku(altyazilar[0]), "altyazı"

        # 2) Ses indir + Whisper
        try:
            with yt_dlp.YoutubeDL({
                "quiet": True, "no_warnings": True,
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmp, "ses.%(ext)s"),
            }) as ydl:
                ydl.download([url])
        except Exception as e:
            return "", f"ses_indirme_hatasi:{e}"

        ses_dosyalari = glob.glob(os.path.join(tmp, "ses.*"))
        if not ses_dosyalari:
            return "", "ses_bulunamadi"
        return _whisper_transcribe(ses_dosyalari[0], dil), "whisper(ses)"


# ── Yerel video ───────────────────────────────────────────────────────

def _video_bilgi_yerel(yol: str) -> str:
    if not os.path.exists(yol):
        return f"[VIDEO_BILGI] Hata: dosya bulunamadı: {yol}"
    try:
        cikti = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", yol],
            capture_output=True, text=True, timeout=20,
        )
        import json as _json
        veri = _json.loads(cikti.stdout)
        video_akisi = next((s for s in veri.get("streams", []) if s.get("codec_type") == "video"), {})
        sure = veri.get("format", {}).get("duration", "?")
        return (f"[VIDEO_BILGI]\nDosya: {yol}\nSüre: {sure}s\n"
                f"Çözünürlük: {video_akisi.get('width', '?')}x{video_akisi.get('height', '?')}\n"
                f"Codec: {video_akisi.get('codec_name', '?')}")
    except FileNotFoundError:
        boyut_mb = os.path.getsize(yol) / 1_048_576
        return (f"[VIDEO_BILGI] (ffprobe kurulu değil, sınırlı bilgi)\n"
                f"Dosya: {yol}\nBoyut: {boyut_mb:.1f} MB")
    except Exception as e:
        return f"[VIDEO_BILGI] Hata: {e}"


def _yerel_video_ses_metni(yol: str, dil: str) -> tuple:
    with tempfile.TemporaryDirectory() as tmp:
        ses_yolu = os.path.join(tmp, "ses.wav")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", yol, "-vn", "-ac", "1", "-ar", "16000", ses_yolu],
                capture_output=True, timeout=180, check=True,
            )
        except FileNotFoundError:
            return "", "ffmpeg_kurulu_degil"
        except subprocess.CalledProcessError as e:
            return "", f"ffmpeg_hatasi:{e}"
        return _whisper_transcribe(ses_yolu, dil), "whisper(yerel)"


# ── Ana araçlar ───────────────────────────────────────────────────────

def video_bilgi(kaynak: str) -> str:
    """Video metadata döner (başlık, süre, çözünürlük). URL veya yerel dosya yolu kabul eder."""
    if not kaynak or not kaynak.strip():
        return "[VIDEO_BILGI] Hata: kaynak boş olamaz."
    kaynak = kaynak.strip()
    if kaynak.startswith(("http://", "https://")):
        return _video_bilgi_uzak(kaynak)
    return _video_bilgi_yerel(kaynak)


def video_analiz(kaynak: str, dil: str = "tr", max_karakter: str = "4000") -> str:
    """Videodan (altyazı veya Whisper ile) metin çıkarır, hızlı özet + transkript döner."""
    if not kaynak or not kaynak.strip():
        return "[VIDEO_ANALIZ] Hata: kaynak boş olamaz."
    kaynak = kaynak.strip()
    try:
        maks = int(max_karakter)
    except (TypeError, ValueError):
        maks = 4000

    try:
        if kaynak.startswith(("http://", "https://")):
            metin, kaynak_tip = _altyazi_veya_ses_metni_uzak(kaynak, dil)
        else:
            if not os.path.exists(kaynak):
                return f"[VIDEO_ANALIZ] Hata: dosya bulunamadı: {kaynak}"
            metin, kaynak_tip = _yerel_video_ses_metni(kaynak, dil)
    except ImportError as e:
        return f"[VIDEO_ANALIZ] Hata: gerekli kütüphane kurulu değil ({e})."
    except Exception as e:
        logger.error("[VIDEO_ANALIZ] hata: %s", e)
        return f"[VIDEO_ANALIZ] Hata: {e}"

    if not metin or not metin.strip():
        return (f"[VIDEO_ANALIZ] Hata: metin çıkarılamadı (kaynak_tip={kaynak_tip}). "
                "Altyazı yok ve Whisper başarısız olmuş olabilir (ffmpeg/yt-dlp/whisper kontrol edin).")

    metin = metin.strip()
    hizli_ozet = _basit_ozet(metin)
    kisaltilmis = metin[:maks] + ("…" if len(metin) > maks else "")
    return (f"[VIDEO_ANALIZ] (kaynak: {kaynak_tip})\n"
            f"Hızlı özet: {hizli_ozet}\n\n"
            f"Transkript/Altyazı ({len(metin)} karakter, {len(kisaltilmis)} gösteriliyor):\n{kisaltilmis}")


# ── Motor kayıt ───────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "VIDEO_BILGI",
            video_bilgi,
            "Video metadata (başlık, süre, çözünürlük) döner. Parametreler: kaynak (url/yol).",
        )
        motor._plugin_arac_kaydet(
            "VIDEO_ANALIZ",
            video_analiz,
            "YouTube/yerel videodan altyazı veya Whisper ile metin çıkarır, hızlı özet "
            "+ transkript döner. Parametreler: kaynak (url/yol), dil, max_karakter.",
        )
    except Exception as e:
        print(f"[AraclarVideo] Motor kayıt hatası: {e}")


if __name__ == "__main__":
    print("araclar_video hazır.")
