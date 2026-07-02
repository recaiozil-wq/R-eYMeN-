# -*- coding: utf-8 -*-
"""
voice_mode.py — Sesli (Push-to-Talk) arayüz modülü.

Mikrofondan ses kaydeder, faster-whisper ile metne çevirir,
Beyin (LLM) ile yanıt üretir, edge-tts ile seslendirir
ve hoparlörden oynatır.

Kullanım:
    from reymen.cereyan.voice_mode import VoiceMode

    vm = VoiceMode(beyin=benim_beyin)
    vm.baslat()         # REPL: dinle / konus / cik
    vm.dinle_ve_cevapla()  # tek seferlik kaydet->STT->LLM->TTS döngüsü

Bağımlılıklar (opsiyonel — eksik olanlar graceful degrade yapar):
    - sounddevice       : mikrofon kaydı + hoparlör oynatma
    - numpy             : ses buffer işlemleri
    - faster-whisper    : yerel STT (CPU/GPU)
    - edge-tts          : Microsoft Edge TTS (ücretsiz, çevrimiçi)
    - pygame            : alternatif ses oynatıcı
"""

from __future__ import annotations

import io
import json
import logging
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generator, Optional

logger = logging.getLogger(__name__)

# ── Opsiyonel bağımlılıklar ────────────────────────────────────────────────

# sounddevice — mikrofon kaydı ve hoparlör oynatma
try:
    import sounddevice as sd
    import numpy as np
    SD_MEVCUT = True
except ImportError:
    sd = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    SD_MEVCUT = False

# faster-whisper — yerel STT motoru
try:
    from faster_whisper import WhisperModel
    _FASTER_WHISPER_MEVCUT = True
except ImportError:
    WhisperModel = None  # type: ignore[assignment]
    _FASTER_WHISPER_MEVCUT = False

# openai — Whisper API (alternatif STT)
try:
    from openai import OpenAI
    _OPENAI_MEVCUT = True
except ImportError:
    OpenAI = None  # type: ignore[assignment]
    _OPENAI_MEVCUT = False

# edge-tts — Microsoft Edge TTS motoru
try:
    import edge_tts
    _EDGE_TTS_MEVCUT = True
except ImportError:
    edge_tts = None  # type: ignore[assignment]
    _EDGE_TTS_MEVCUT = False

# pygame — alternatif ses oynatıcı
try:
    import pygame
    PYGAME_MEVCUT = True
except ImportError:
    pygame = None  # type: ignore[assignment]
    PYGAME_MEVCUT = False

# ffmpeg/ffplay — ses oynatma için sistem aracı
_FFPLAY_BULUNDU: Optional[str] = None
for _exe in ("ffplay", "ffplay.exe"):
    try:
        _r = subprocess.run(
            ["where" if os.name == "nt" else "which", _exe],
            capture_output=True, text=True, timeout=3,
        )
        if _r.returncode == 0 and _r.stdout.strip():
            _FFPLAY_BULUNDU = _r.stdout.strip().splitlines()[0]
            break
    except Exception:
        pass


# ── Beyin import (opsiyonel) ───────────────────────────────────────────────

def _beyin_al() -> Any:
    """Beyin sınıfını döndürür; yoksa None."""
    try:
        from reymen.cereyan.beyin import Beyin
        return Beyin
    except ImportError:
        return None


# ── Varsayılan sabitler ────────────────────────────────────────────────────

_VARSAYILAN_SES_KAYNAGI: int = 0          # varsayılan mikrofon
_VARSAYILAN_ORNEKLEME_HIZI: int = 16000  # Whisper için ideal
_VARSAYILAN_KANAL_SAYISI: int = 1        # mono
_VARSAYILAN_KAYIT_SURESI: float = 5.0    # saniye (push-to-talk değilse)
_VARSAYILAN_DINLEME_ESIĞI: float = 0.02  # ses seviyesi eşiği (VAD basit)
_VARSAYILAN_SESSIZLIK_SURESI: float = 1.5  # VAD için sessizlik timeout
_VARSAYILAN_DIL: str = "tr"              # STT dili
_VARSAYILAN_TTS_SESI: str = "tr-TR-AhmetNeural"  # edge-tts Türkçe erkek sesi

# VAD (Voice Activity Detection) parametreleri
_VAD_PENCERE_BOYUTU: int = 1024  # RMS penceresi
_VAD_SESSIZ_EN_COK: int = 15     # kaç sessiz pencereden sonra dur


# ── Ses verisi taşıyıcısı ──────────────────────────────────────────────────

@dataclass
class SesKaydi:
    """Kaydedilmiş ses verisini ve üstverisini taşır."""
    veri: Optional[Any] = None          # numpy array
    ornekleme_hizi: int = _VARSAYILAN_ORNEKLEME_HIZI
    sure_sn: float = 0.0
    dosya_yolu: Optional[str] = None   # temp wav dosya yolu
    metin: str = ""                    # STT çıktısı


# ── Durum kodları ─────────────────────────────────────────────────────────

class VoiceModeDurum:
    """VoiceMode çalışma durumları."""
    DURDU = "durdu"
    DİNLİYOR = "dinliyor"
    KONUSUYOR = "konusuyor"
    İŞLİYOR = "isliyor"
    HATA = "hata"


# ═══════════════════════════════════════════════════════════════════════════
# VoiceMode Ana Sınıfı
# ═══════════════════════════════════════════════════════════════════════════

class VoiceMode:
    """Sesli arayüz yöneticisi.

    Push-to-talk ve otomatik VAD ile ses kaydı, STT, LLM yanıtı
    ve TTS çıktısını tek bir döngüde birleştirir.

    Args:
        beyin: Beyin instance'ı (LLM bağlantısı). Yoksa sadece
               kayıt + STT + TTS test edilebilir.
        config: Yapılandırma sözlüğü (opsiyonel).
            Anahtarlar:
                - kaynak_id: mikrofon cihaz indeksi (int)
                - ornekleme_hizi: örnekleme hızı (int)
                - kayit_suresi: maksimum kayıt süresi (float)
                - dil: STT dil kodu (str)
                - tts_sesi: edge-tts ses adı (str)
                - stt_backend: "faster_whisper" veya "openai"
                - tts_backend: "edge_tts" (tek seçenek)
                - ses_esiği: VAD ses eşiği (float)
                - sessizlik_suresi: VAD timeout (float)
    """

    def __init__(
        self,
        beyin: Optional[Any] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        self.beyin = beyin
        self._cfg = config or {}

        # ── Cihaz yapılandırması ──────────────────────────────────────
        self.kaynak_id: int = self._cfg.get("kaynak_id", _VARSAYILAN_SES_KAYNAGI)
        self.ornekleme_hizi: int = self._cfg.get(
            "ornekleme_hizi", _VARSAYILAN_ORNEKLEME_HIZI
        )
        self.kanal_sayisi: int = self._cfg.get("kanal_sayisi", _VARSAYILAN_KANAL_SAYISI)
        self.kayit_suresi: float = self._cfg.get(
            "kayit_suresi", _VARSAYILAN_KAYIT_SURESI
        )

        # ── STT yapılandırması ────────────────────────────────────────
        self.dil: str = self._cfg.get("dil", _VARSAYILAN_DIL)
        self.stt_backend: str = self._cfg.get("stt_backend", "faster_whisper")
        self._whisper_model: Optional[Any] = None
        self._openai_client: Optional[Any] = None

        # ── TTS yapılandırması ────────────────────────────────────────
        self.tts_sesi: str = self._cfg.get("tts_sesi", _VARSAYILAN_TTS_SESI)
        self.tts_backend: str = self._cfg.get("tts_backend", "edge_tts")

        # ── VAD yapılandırması ────────────────────────────────────────
        self.ses_esiği: float = self._cfg.get("ses_esiği", _VARSAYILAN_DINLEME_ESIĞI)
        self.sessizlik_suresi: float = self._cfg.get(
            "sessizlik_suresi", _VARSAYILAN_SESSIZLIK_SURESI
        )

        # ── Çalışma durumu ────────────────────────────────────────────
        self.durum: str = VoiceModeDurum.DURDU
        self._durdurma_olayi = threading.Event()
        self._kilit = threading.Lock()

        # ── Ses oynatma ───────────────────────────────────────────────
        self._pygame_ilk = False

        # ── İstatistik ────────────────────────────────────────────────
        self.istatistik: dict[str, Any] = {
            "kayit_sayisi": 0,
            "stt_sayisi": 0,
            "tts_sayisi": 0,
            "hata_sayisi": 0,
            "toplam_konusma_suresi": 0.0,
        }

        # Başlangıçta kullanılabilirliği kontrol et
        self._kullanilabilirlik_kontrol()

    # ────────────────────────────────────────────────────────────────────
    # Kontrol
    # ────────────────────────────────────────────────────────────────────

    def _kullanilabilirlik_kontrol(self) -> None:
        """Mevcut bağımlılıkları raporla."""
        eksik: list[str] = []
        if not SD_MEVCUT:
            eksik.append("sounddevice")
        if self.stt_backend == "faster_whisper" and not _FASTER_WHISPER_MEVCUT:
            eksik.append("faster-whisper")
        if self.stt_backend == "openai" and not _OPENAI_MEVCUT:
            eksik.append("openai")
        if not _EDGE_TTS_MEVCUT:
            eksik.append("edge-tts")
        if not PYGAME_MEVCUT and _FFPLAY_BULUNDU is None:
            eksik.append("pygame/ffplay (ses oynatma)")

        if eksik:
            logger.warning(
                "[VoiceMode] Eksik bağımlılıklar: %s",
                ", ".join(eksik),
            )

    def kullanilabilir_mi(self) -> dict[str, bool]:
        """Kullanılabilirlik durumunu sözlük olarak döndürür.

        Returns:
            {
                "mikrofon": bool,
                "hoparlor": bool,
                "stt": bool,
                "tts": bool,
                "beyin": bool,
            }
        """
        return {
            "mikrofon": SD_MEVCUT,
            "hoparlor": SD_MEVCUT or PYGAME_MEVCUT or _FFPLAY_BULUNDU is not None,
            "stt": _FASTER_WHISPER_MEVCUT or _OPENAI_MEVCUT,
            "tts": _EDGE_TTS_MEVCUT,
            "beyin": self.beyin is not None,
        }

    # ────────────────────────────────────────────────────────────────────
    # Mikrofon — Ses Kaydı
    # ────────────────────────────────────────────────────────────────────

    def cihazlari_listele(self) -> list[dict[str, Any]]:
        """Kullanılabilir ses cihazlarını listeler.

        Returns:
            Her cihaz için {'id': int, 'adi': str, 'kanal': int, 'ornek': int}
            listesi. sounddevice yoksa boş liste.
        """
        if not SD_MEVCUT:
            logger.warning("[VoiceMode] sounddevice yok, cihaz listelenemez.")
            return []
        try:
            cihazlar = []
            for i, c in enumerate(sd.query_devices()):  # type: ignore[arg-type]
                cihazlar.append({
                    "id": i,
                    "adi": c["name"],
                    "kanal": c["max_input_channels"],
                    "ornek": int(c["default_samplerate"]),
                })
            return cihazlar
        except Exception as e:
            logger.error("[VoiceMode] Cihaz listeleme hatası: %s", e)
            return []

    def _vad_ile_kaydet(
        self,
        maks_sure: float = 30.0,
    ) -> Optional[SesKaydi]:
        """Voice Activity Detection ile konuşma algılayarak kaydeder.

        Sessizlik algılandığında veya maksimum süre aşıldığında durur.

        Args:
            maks_sure: Maksimum kayıt süresi (saniye).

        Returns:
            SesKaydi nesnesi veya başarısızsa None.
        """
        if not SD_MEVCUT:
            logger.error("[VoiceMode] sounddevice gerekli — VAD kaydı yapılamaz.")
            return None

        self.durum = VoiceModeDurum.DİNLİYOR
        print("🎤 Dinliyor (konuşmayı bırakınca otomatik durur)...")

        buffer: list = []
        sessiz_sayac = 0
        baslangic = time.monotonic()

        def _callback(indata: Any, frames: int, _time_info: Any, status: Any) -> None:
            nonlocal sessiz_sayac
            if status:
                logger.debug("[VoiceMode] Ses akışı status: %s", status)
            # RMS ses seviyesi
            rms = np.sqrt(np.mean(indata ** 2))  # type: ignore[operator]
            buffer.append(indata.copy())
            if rms < self.ses_esiği:
                sessiz_sayac += 1
            else:
                sessiz_sayac = 0

        try:
            with sd.InputStream(
                device=self.kaynak_id,
                samplerate=self.ornekleme_hizi,
                channels=self.kanal_sayisi,
                callback=_callback,
                blocksize=_VAD_PENCERE_BOYUTU,
            ):
                while True:
                    if self._durdurma_olayi.is_set():
                        print("\n⏹ Durduruldu.")
                        return None
                    if sessiz_sayac > _VAD_SESSIZ_EN_COK:
                        print()  # yeni satır
                        break
                    if time.monotonic() - baslangic > maks_sure:
                        print("\n⏱ Maksimum süre aşıldı.")
                        break
                    time.sleep(0.05)
        except Exception as e:
            logger.error("[VoiceMode] Kayıt hatası: %s", e)
            self.durum = VoiceModeDurum.HATA
            self.istatistik["hata_sayisi"] += 1
            return None

        if not buffer:
            logger.warning("[VoiceMode] Ses verisi alınamadı.")
            return None

        # Buffer'ı numpy array'e çevir
        ses_verisi = np.concatenate(buffer, axis=0)  # type: ignore[arg-type]
        sure = time.monotonic() - baslangic
        self.istatistik["kayit_sayisi"] += 1
        self.istatistik["toplam_konusma_suresi"] += sure

        return SesKaydi(
            veri=ses_verisi,
            ornekleme_hizi=self.ornekleme_hizi,
            sure_sn=sure,
        )

    def _sureli_kaydet(self, sure: float = 0.0) -> Optional[SesKaydi]:
        """Belirtilen süre boyunca ses kaydeder.

        Args:
            sure: Kayıt süresi (saniye). 0 ise varsayılan kullanılır.

        Returns:
            SesKaydi nesnesi veya başarısızsa None.
        """
        if not SD_MEVCUT:
            logger.error("[VoiceMode] sounddevice gerekli — kayıt yapılamaz.")
            return None

        sure = sure or self.kayit_suresi
        self.durum = VoiceModeDurum.DİNLİYOR
        print(f"🎤 {sure:.0f} saniye kaydediliyor...")

        try:
            ses_verisi = sd.rec(
                int(sure * self.ornekleme_hizi),
                samplerate=self.ornekleme_hizi,
                channels=self.kanal_sayisi,
                device=self.kaynak_id,
            )
            sd.wait()
        except Exception as e:
            logger.error("[VoiceMode] Kayıt hatası: %s", e)
            self.durum = VoiceModeDurum.HATA
            self.istatistik["hata_sayisi"] += 1
            return None

        self.istatistik["kayit_sayisi"] += 1
        self.istatistik["toplam_konusma_suresi"] += sure

        return SesKaydi(
            veri=ses_verisi,
            ornekleme_hizi=self.ornekleme_hizi,
            sure_sn=sure,
        )

    def kaydet(
        self,
        sure: float = 0.0,
        vad: bool = True,
        maks_sure: float = 30.0,
    ) -> Optional[SesKaydi]:
        """Ses kaydeder.

        VAD (Voice Activity Detection) ile otomatik kesme veya
        sabit süreli kayıt yapar.

        Args:
            sure: Sabit süre (saniye). 0 ise VAD veya varsayılan süre kullanılır.
            vad: VAD kullanılsın mı? (varsayılan: True)
            maks_sure: VAD modunda maksimum kayıt süresi.

        Returns:
            SesKaydi nesnesi veya başarısızsa None.
        """
        if vad and sure <= 0:
            return self._vad_ile_kaydet(maks_sure=maks_sure)
        return self._sureli_kaydet(sure=sure or self.kayit_suresi)

    # ────────────────────────────────────────────────────────────────────
    # STT — Konuşmadan Metne
    # ────────────────────────────────────────────────────────────────────

    def _ses_verisini_wav_yap(self, kayit: SesKaydi) -> Optional[str]:
        """NumPy ses verisini geçici WAV dosyasına yazar.

        scipy.io.wavfile veya soundfile kullanır; yoksa elle yazar.

        Args:
            kayit: SesKaydi nesnesi (veri ve ornekleme_hizi ile).

        Returns:
            WAV dosya yolu veya başarısızsa None.
        """
        if kayit.dosya_yolu and os.path.exists(kayit.dosya_yolu):
            return kayit.dosya_yolu

        try:
            # soundfile ile yaz
            import soundfile as sf
            fd, yol = tempfile.mkstemp(suffix=".wav", prefix="reymen_voice_")
            os.close(fd)
            sf.write(yol, kayit.veri, kayit.ornekleme_hizi)
            kayit.dosya_yolu = yol
            return yol
        except ImportError:
            pass

        try:
            # scipy.io.wavfile ile yaz
            from scipy.io import wavfile
            fd, yol = tempfile.mkstemp(suffix=".wav", prefix="reymen_voice_")
            os.close(fd)
            wavfile.write(yol, kayit.ornekleme_hizi, kayit.veri)
            kayit.dosya_yolu = yol
            return yol
        except ImportError:
            pass

        logger.error("[VoiceMode] WAV yazmak için soundfile veya scipy gerekli.")
        return None

    def _faster_whisper_stt(self, ses_yolu: str) -> str:
        """faster-whisper ile yerel STT çevirisi.

        Args:
            ses_yolu: WAV dosya yolu.

        Returns:
            Çözümlenen metin.
        """
        if not _FASTER_WHISPER_MEVCUT:
            raise RuntimeError("faster-whisper yüklü değil.")

        # Modeli ilk çağrıda yükle
        if self._whisper_model is None:
            model_boyutu = self._cfg.get("whisper_model", "tiny")
            device = self._cfg.get("whisper_device", "cpu")
            compute_type = self._cfg.get("whisper_compute", "int8")
            logger.info(
                "[VoiceMode] faster-whisper model yükleniyor: %s (%s, %s)...",
                model_boyutu, device, compute_type,
            )
            self._whisper_model = WhisperModel(
                model_boyutu,
                device=device,
                compute_type=compute_type,
            )

        segmentler, _bilgi = self._whisper_model.transcribe(
            ses_yolu,
            language=self.dil,
            beam_size=5,
        )
        metin = " ".join(seg.text for seg in segmentler).strip()
        return metin

    def _openai_stt(self, ses_yolu: str) -> str:
        """OpenAI Whisper API ile STT çevirisi.

        Args:
            ses_yolu: WAV dosya yolu.

        Returns:
            Çözümlenen metin.
        """
        if not _OPENAI_MEVCUT:
            raise RuntimeError("openai (OpenAI SDK) yüklü değil.")

        if self._openai_client is None:
            api_key = self._cfg.get(
                "openai_api_key",
                os.environ.get("OPENAI_API_KEY", ""),
            )
            self._openai_client = OpenAI(api_key=api_key)

        with open(ses_yolu, "rb") as f:
            yanit = self._openai_client.audio.transcriptions.create(
                model=self._cfg.get("openai_stt_model", "whisper-1"),
                file=f,
                language=self.dil,
            )
        return yanit.text.strip()

    def metne_cevir(self, kayit: SesKaydi) -> str:
        """Kaydedilmiş sesi metne çevirir (STT).

        Sırasıyla dener:
            1. Seçili STT backend (faster-whisper veya openai)
            2. Varsa diğer backend

        Args:
            kayit: SesKaydi nesnesi.

        Returns:
            Çözümlenen metin veya hata durumunda "[STT Hatası] ...".
        """
        self.durum = VoiceModeDurum.İŞLİYOR
        print("📝 Ses metne çevriliyor...")

        # WAV dosyasına yaz
        ses_yolu = self._ses_verisini_wav_yap(kayit)
        if not ses_yolu:
            self.durum = VoiceModeDurum.HATA
            self.istatistik["hata_sayisi"] += 1
            return "[STT Hatası] WAV dosyası oluşturulamadı."

        # STT backend'leri dene
        hatalar: list[str] = []
        backends = [self.stt_backend]
        if self.stt_backend == "faster_whisper":
            backends.append("openai")
        else:
            backends.append("faster_whisper")

        for backend in backends:
            try:
                if backend == "faster_whisper" and _FASTER_WHISPER_MEVCUT:
                    metin = self._faster_whisper_stt(ses_yolu)
                elif backend == "openai" and _OPENAI_MEVCUT:
                    metin = self._openai_stt(ses_yolu)
                else:
                    continue

                if metin:
                    kayit.metin = metin
                    self.istatistik["stt_sayisi"] += 1
                    self.durum = VoiceModeDurum.DURDU
                    # Temp dosyayı temizle
                    self._temizle(ses_yolu)
                    return metin
            except Exception as e:
                hatalar.append(f"{backend}: {e}")
                logger.warning("[VoiceMode] STT backend hatası (%s): %s", backend, e)
                continue

        self._temizle(ses_yolu)
        self.durum = VoiceModeDurum.HATA
        self.istatistik["hata_sayisi"] += 1
        hata_msg = f"[STT Hatası] Tüm backend'ler başarısız: {'; '.join(hatalar)}"
        logger.error(hata_msg)
        return hata_msg

    # ────────────────────────────────────────────────────────────────────
    # TTS — Metinden Sese (edge-tts)
    # ────────────────────────────────────────────────────────────────────

    def seslendir(self, metin: str) -> Optional[bytes]:
        """Metni edge-tts ile seslendirir.

        Args:
            metin: Seslendirilecek metin.

        Returns:
            MP3 ses verisi (bytes) veya başarısızsa None.
        """
        if not _EDGE_TTS_MEVCUT:
            logger.error("[VoiceMode] edge-tts gerekli — seslendirme yapılamaz.")
            return None

        if not metin or not metin.strip():
            logger.warning("[VoiceMode] Seslendirilecek metin boş.")
            return None

        self.durum = VoiceModeDurum.KONUSUYOR
        print(f"🗣 Seslendiriliyor ({len(metin)} karakter)...")

        try:
            ses = edge_tts.Communicate(metin.strip(), voice=self.tts_sesi)
            # BytesIO'ya yaz
            buf = io.BytesIO()
            asyncio_loop(self._edge_tts_stream(ses, buf))
            ses_verisi = buf.getvalue()
            self.istatistik["tts_sayisi"] += 1
            return ses_verisi
        except Exception as e:
            logger.error("[VoiceMode] TTS hatası: %s", e)
            self.durum = VoiceModeDurum.HATA
            self.istatistik["hata_sayisi"] += 1
            return None

    async def _edge_tts_stream(
        self,
        ses: Any,
        buffer: io.BytesIO,
    ) -> None:
        """edge-tts üretimini BytesIO buffer'a yazar."""
        async for chunk in ses.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

    # ────────────────────────────────────────────────────────────────────
    # Ses Oynatma
    # ────────────────────────────────────────────────────────────────────

    def _pygame_baslat(self) -> bool:
        """Pygame mixer'ı başlatır (ilk çağrıda)."""
        if not PYGAME_MEVCUT:
            return False
        if not self._pygame_ilk:
            try:
                pygame.mixer.init(frequency=self.ornekleme_hizi)
                self._pygame_ilk = True
            except Exception as e:
                logger.warning("[VoiceMode] Pygame mixer başlatılamadı: %s", e)
                return False
        return True

    def _sounddevice_oynat(self, ses_verisi: bytes, format_hint: str = "mp3") -> None:
        """sounddevice ile ses oynatır (WAV formatında).

        Args:
            ses_verisi: Ses verisi (bytes).
            format_hint: Ses formatı ("mp3" veya "wav").
        """
        if not SD_MEVCUT:
            raise RuntimeError("sounddevice gerekli.")

        # MP3'ü WAV'a çevir
        if format_hint == "mp3":
            try:
                import pydub
                from pydub import AudioSegment
                ses = AudioSegment.from_mp3(io.BytesIO(ses_verisi))
                wav_buf = io.BytesIO()
                ses.export(wav_buf, format="wav")
                wav_buf.seek(0)
                import soundfile as sf
                data, sr = sf.read(wav_buf)
            except ImportError:
                # pydub yoksa geçici dosyaya yaz, ffmpeg ile çevir
                fd, temp_in = tempfile.mkstemp(suffix=".mp3", prefix="reymen_tts_")
                os.close(fd)
                with open(temp_in, "wb") as f:
                    f.write(ses_verisi)
                fd, temp_wav = tempfile.mkstemp(suffix=".wav", prefix="reymen_tts_")
                os.close(fd)
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", temp_in, temp_wav],
                        capture_output=True, timeout=30,
                    )
                    import soundfile as sf
                    data, sr = sf.read(temp_wav)
                except Exception:
                    self._temizle(temp_in)
                    self._temizle(temp_wav)
                    raise
                self._temizle(temp_in)
                self._temizle(temp_wav)
            sound_device_data = data
            sample_rate = sr
        else:
            # WAV direkt
            import soundfile as sf
            data, sr = sf.read(io.BytesIO(ses_verisi))
            sound_device_data = data
            sample_rate = sr

        sd.play(sound_device_data, samplerate=sample_rate)
        sd.wait()

    def _pygame_oynat(self, ses_verisi: bytes) -> None:
        """Pygame ile ses oynatır.

        Args:
            ses_verisi: MP3 ses verisi (bytes).
        """
        if not self._pygame_baslat():
            raise RuntimeError("Pygame kullanılamaz.")

        # BytesIO üzerinden geçici dosyaya yazmadan oynat
        try:
            # pygame.mixer.music load from file object
            fd, temp = tempfile.mkstemp(suffix=".mp3", prefix="reymen_tts_")
            os.close(fd)
            with open(temp, "wb") as f:
                f.write(ses_verisi)
            pygame.mixer.music.load(temp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self._durdurma_olayi.is_set():
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.1)
            self._temizle(temp)
        except Exception as e:
            logger.warning("[VoiceMode] Pygame oynatma hatası: %s", e)
            # Fallback: ffplay ile dene
            self._ffplay_oynat(ses_verisi)

    def _ffplay_oynat(self, ses_verisi: bytes) -> None:
        """ffplay (FFmpeg) ile ses oynatır.

        Args:
            ses_verisi: Ses verisi (bytes).
        """
        if _FFPLAY_BULUNDU is None:
            raise RuntimeError("ffplay bulunamadı.")

        try:
            proc = subprocess.Popen(
                [_FFPLAY_BULUNDU, "-nodisp", "-autoexit", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.stdin.write(ses_verisi)
            proc.stdin.close()
            proc.wait()
        except Exception as e:
            logger.error("[VoiceMode] ffplay oynatma hatası: %s", e)
            raise

    def oynat(self, ses_verisi: bytes) -> bool:
        """Ses verisini hoparlörden oynatır.

        Sırasıyla dener:
            1. sounddevice (WAV'a çevirerek)
            2. pygame
            3. ffplay

        Args:
            ses_verisi: Ses verisi (bytes, edge-tts'den MP3).

        Returns:
            Başarılıysa True, değilse False.
        """
        if not ses_verisi:
            return False

        self.durum = VoiceModeDurum.KONUSUYOR
        print("🔊 Oynatılıyor...")

        hatalar: list[str] = []

        # 1. sounddevice
        if SD_MEVCUT:
            try:
                self._sounddevice_oynat(ses_verisi)
                self.durum = VoiceModeDurum.DURDU
                return True
            except Exception as e:
                hatalar.append(f"sounddevice: {e}")
                logger.debug("[VoiceMode] sounddevice oynatma başarısız, pygame deneniyor...")

        # 2. pygame
        if PYGAME_MEVCUT:
            try:
                self._pygame_oynat(ses_verisi)
                self.durum = VoiceModeDurum.DURDU
                return True
            except Exception as e:
                hatalar.append(f"pygame: {e}")

        # 3. ffplay
        if _FFPLAY_BULUNDU is not None:
            try:
                self._ffplay_oynat(ses_verisi)
                self.durum = VoiceModeDurum.DURDU
                return True
            except Exception as e:
                hatalar.append(f"ffplay: {e}")

        self.durum = VoiceModeDurum.HATA
        self.istatistik["hata_sayisi"] += 1
        logger.error("[VoiceMode] Tüm oynatma backend'leri başarısız: %s", "; ".join(hatalar))
        return False

    # ────────────────────────────────────────────────────────────────────
    # Beyin (LLM) Entegrasyonu
    # ────────────────────────────────────────────────────────────────────

    def _beyin_yanit(self, metin: str) -> str:
        """Kullanıcı metnini Beyin'e gönderir, yanıt alır.

        Args:
            metin: Kullanıcının söylediği metin.

        Returns:
            Beyin yanıtı metni.
        """
        if self.beyin is None:
            logger.warning("[VoiceMode] Beyin bağlı değil — yanıt üretilemez.")
            return "[Beyin yok — sesli test modu]"

        print("🧠 Beyin düşünüyor...")
        try:
            # Varsayılan sistem prompt
            sistem = self._cfg.get(
                "sistem_prompt",
                "Sen yardımsever bir asistansın. Kullanıcıyla sesli olarak "
                "Türkçe konuşuyorsun. Kısa ve net cevaplar ver.",
            )
            mesajlar = [
                {"role": "user", "content": metin},
            ]
            yanit = self.beyin.dusun(
                sistem_prompt=sistem,
                mesajlar=mesajlar,
            )
            return yanit
        except Exception as e:
            logger.error("[VoiceMode] Beyin hatası: %s", e)
            self.istatistik["hata_sayisi"] += 1
            return f"[Beyin Hatası] {e}"

    # ────────────────────────────────────────────────────────────────────
    # Ana Döngü: Kaydet → STT → LLM → TTS → Oynat
    # ────────────────────────────────────────────────────────────────────

    def dinle_ve_cevapla(
        self,
        sure: float = 0.0,
        vad: bool = True,
        maks_sure: float = 30.0,
    ) -> bool:
        """Tam sesli döngü: kaydet → STT → LLM → TTS → oynat.

        Args:
            sure: Sabit kayıt süresi (0 = VAD veya varsayılan).
            vad: Voice Activity Detection kullanılsın mı?
            maks_sure: VAD'de maksimum kayıt süresi.

        Returns:
            Döngü başarıyla tamamlandıysa True.
        """
        if self._durdurma_olayi.is_set():
            return False

        # 1. Kaydet
        kayit = self.kaydet(sure=sure, vad=vad, maks_sure=maks_sure)
        if kayit is None:
            return False

        # 2. STT
        metin = self.metne_cevir(kayit)
        if not metin or metin.startswith("[STT"):
            print(f"❌ {metin}")
            return False

        print(f"\n📝 Söylediğiniz: {metin}")

        # 3. LLM yanıtı
        yanit = self._beyin_yanit(metin)
        if yanit.startswith("[Beyin"):
            print(f"❌ {yanit}")
            return False

        print(f"🤖 Yanıt: {yanit}")

        # 4. TTS
        ses_verisi = self.seslendir(yanit)
        if ses_verisi is None:
            return False

        # 5. Oynat
        return self.oynat(ses_verisi)

    # ────────────────────────────────────────────────────────────────────
    # REPL (Read-Eval-Print-Loop) Arayüzü
    # ────────────────────────────────────────────────────────────────────

    def baslat(self) -> None:
        """Etkileşimli sesli REPL başlatır.

        Komutlar:
            dinle   — konuşmayı dinle ve cevapla (VAD)
            kaydet  — sabit süre kaydet ve cevapla
            test    — ses testi (kaydet → oynat, LLM'siz)
            durum   — mevcut durumu göster
            cihaz   — ses cihazlarını listele
            yardım  — komut listesini göster
            cik     — REPL'den çık
        """
        self._durdurma_olayi.clear()
        print("╔══════════════════════════════════════════╗")
        print("║   🎙  ReYMeN Voice Mode — Sesli Asistan   ║")
        print("╚══════════════════════════════════════════╝")
        print("Komutlar: dinle | kaydet | test | durum | cihaz | yardım | cik")
        print()

        komut_handler: dict[str, Callable[[], bool]] = {
            "dinle": lambda: self.dinle_ve_cevapla(vad=True),
            "kaydet": self._repl_kaydet_ve_cevapla,
            "test": self._repl_ses_testi,
            "durum": self._repl_durum_goster,
            "cihaz": self._repl_cihaz_listele,
            "yardım": self._repl_yardim,
        }

        try:
            while not self._durdurma_olayi.is_set():
                try:
                    komut = input("\n🎙> ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n")
                    break

                if not komut:
                    continue

                if komut == "cik":
                    print("👋 Görüşmek üzere!")
                    break

                handler = komut_handler.get(komut)
                if handler:
                    try:
                        handler()
                    except Exception as e:
                        logger.error("[VoiceMode] Komut hatası: %s", e)
                        print(f"❌ Hata: {e}")
                else:
                    print(f"❌ Bilinmeyen komut: '{komut}'. 'yardım' yazın.")
        finally:
            self.durum = VoiceModeDurum.DURDU

    def _repl_kaydet_ve_cevapla(self) -> bool:
        """Sabit süreli kayıt + cevaplama (REPL komutu)."""
        try:
            sure_str = input("⏱ Kayıt süresi (saniye, varsayılan 5): ").strip()
            sure = float(sure_str) if sure_str else 5.0
        except (ValueError, EOFError):
            sure = 5.0
        return self.dinle_ve_cevapla(sure=sure, vad=False)

    def _repl_ses_testi(self) -> bool:
        """Ses testi: kaydet → STT → oynat (LLM'siz)."""
        print("🔊 Ses testi başlatılıyor...")
        kayit = self.kaydet(vad=True, maks_sure=10.0)
        if kayit is None:
            print("❌ Kayıt başarısız.")
            return False
        metin = self.metne_cevir(kayit)
        print(f"📝 Algılanan: {metin}")
        # Kaydı oynat
        ses_yolu = self._ses_verisini_wav_yap(kayit)
        if ses_yolu:
            with open(ses_yolu, "rb") as f:
                wav_data = f.read()
            self.oynat(wav_data)
            self._temizle(ses_yolu)
        return True

    def _repl_durum_goster(self) -> bool:
        """Mevcut durumu göster (REPL komutu)."""
        durum = self.kullanilabilir_mi()
        print("╔═══ VoiceMode Durumu ═══╗")
        print(f"  Durum     : {self.durum}")
        print(f"  Mikrofon  : {'✅' if durum['mikrofon'] else '❌'}")
        print(f"  Hoparlör  : {'✅' if durum['hoparlor'] else '❌'}")
        print(f"  STT       : {'✅' if durum['stt'] else '❌'}")
        print(f"  TTS       : {'✅' if durum['tts'] else '❌'}")
        print(f"  Beyin     : {'✅' if durum['beyin'] else '❌'}")
        print(f"  STT Motor : {self.stt_backend}")
        print(f"  TTS Ses   : {self.tts_sesi}")
        print(f"  Kayıtlar  : {self.istatistik['kayit_sayisi']}")
        print(f"  STT Sayı  : {self.istatistik['stt_sayisi']}")
        print(f"  TTS Sayı  : {self.istatistik['tts_sayisi']}")
        print(f"  Hata      : {self.istatistik['hata_sayisi']}")
        print("╚══════════════════════════╝")
        return True

    def _repl_cihaz_listele(self) -> bool:
        """Ses cihazlarını listele (REPL komutu)."""
        cihazlar = self.cihazlari_listele()
        if not cihazlar:
            print("❌ Cihaz bulunamadı veya sounddevice yok.")
            return False
        print("╔═══ Ses Cihazları ═══╗")
        for c in cihazlar:
            print(f"  [{c['id']}] {c['adi']}")
            print(f"       Kanal: {c['kanal']}, Örnek: {c['ornek']} Hz")
        print("╚══════════════════════╝")
        return True

    def _repl_yardim(self) -> bool:
        """Yardım mesajı göster (REPL komutu)."""
        print("╔═══ Komutlar ═══╗")
        print("  dinle  — Konuşmayı dinle (VAD) ve Beyin ile cevapla")
        print("  kaydet — Sabit süre belirleyip kaydet ve cevapla")
        print("  test   — Ses testi (kaydet → çöz → oynat, LLM'siz)")
        print("  durum  — Mevcut yapılandırma ve kullanım istatistikleri")
        print("  cihaz  — Ses giriş/çıkış cihazlarını listele")
        print("  cik    — Çıkış")
        print("  yardım — Bu mesaj")
        print("╚══════════════════╝")
        return True

    # ────────────────────────────────────────────────────────────────────
    # Kontrol / Temizlik
    # ────────────────────────────────────────────────────────────────────

    def durdur(self) -> None:
        """Tüm ses işlemlerini durdurur."""
        self._durdurma_olayi.set()

        # Pygame oynatma varsa durdur
        if PYGAME_MEVCUT and self._pygame_ilk:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

        # sounddevice oynatma varsa durdur
        if SD_MEVCUT:
            try:
                sd.stop()
            except Exception:
                pass

        self.durum = VoiceModeDurum.DURDU
        logger.info("[VoiceMode] Durduruldu.")

    def temizle(self) -> None:
        """Kaynakları serbest bırak."""
        self.durdur()

        # Whisper modelini temizle
        if self._whisper_model is not None:
            try:
                del self._whisper_model
            except Exception:
                pass
            self._whisper_model = None

        # OpenAI client
        self._openai_client = None

        # Pygame mixer
        if PYGAME_MEVCUT and self._pygame_ilk:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
            self._pygame_ilk = False

    @staticmethod
    def _temizle(dosya_yolu: str) -> None:
        """Geçici dosyayı güvenle siler."""
        try:
            if dosya_yolu and os.path.exists(dosya_yolu):
                os.unlink(dosya_yolu)
        except Exception as e:
            logger.debug("[VoiceMode] Temp dosya silinemedi: %s — %s", dosya_yolu, e)


# ── Asenkron yardımcı ────────────────────────────────────────────────────

def asyncio_loop(koroutin: Any) -> None:
    """Async fonksiyonu senkron context'te çalıştırır.

    Mevcut event loop varsa onu kullanır, yoksa yeni loop oluşturur.

    Args:
        koroutin: Çalıştırılacak coroutine.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Zaten çalışan bir loop var — yeni loop aç
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(koroutin)
            finally:
                loop.close()
        else:
            loop.run_until_complete(koroutin)
    except RuntimeError:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(koroutin)
        finally:
            loop.close()


# ── Dışa aktarılan isimler ─────────────────────────────────────────────────

__all__ = [
    "VoiceMode",
    "VoiceModeDurum",
    "SesKaydi",
]


# ── Test / Demo ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("VoiceMode Demo")
    print("==============")
    print()

    vm = VoiceMode()
    durum = vm.kullanilabilir_mi()
    print(f"Mikrofon: {'✅' if durum['mikrofon'] else '❌'}")
    print(f"Hoparlör: {'✅' if durum['hoparlor'] else '❌'}")
    print(f"STT:      {'✅' if durum['stt'] else '❌'}")
    print(f"TTS:      {'✅' if durum['tts'] else '❌'}")
    print(f"Beyin:    {'✅' if durum['beyin'] else '❌'}")
    print()

    if all(durum.values()):
        print("Tüm bileşenler hazır. REPL başlatılıyor...")
        vm.baslat()
    else:
        print("Demo modu: sadece cihaz listeleme yapılabilir.")
        cihazlar = vm.cihazlari_listele()
        if cihazlar:
            print(f"\n{len(cihazlar)} cihaz bulundu.")
            for c in cihazlar[:5]:
                print(f"  [{c['id']}] {c['adi']}")
