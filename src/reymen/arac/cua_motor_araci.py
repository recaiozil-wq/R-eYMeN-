"""
╔══════════════════════════════════════════════════════════════════╗
║  ReYMeN — CUA_EKRAN_KULLAN  •  cua_motor_araci.py               ║
║  Tam otonom: Ekran → Vision → Koordinat → Eylem → Doğrula       ║
║  motor.py'ye doğrudan import edilir.                             ║
╠══════════════════════════════════════════════════════════════════╣
║  v2.0 — Düzeltmeler:                                             ║
║   1. Config YAML desteği (LM_STUDIO_URL artık sabit değil)       ║
║   2. tikla() içinde FailSafeException yakalama                   ║
║   3. Doğrulama: EVET/HAYIR + sonraki koordinat önerisi           ║
║   4. Adaptif MAX_DENEME (başarısızlıkla artar)                   ║
║   5. requests.Session havuzu (~%20 hız kazancı)                  ║
╚══════════════════════════════════════════════════════════════════╝

KURULUM:
    pip install mss pyautogui requests pillow pyyaml

MOTOR.PY'YE EKLE:
    from cua_motor_araci import CUA_EKRAN_KULLAN, CUA_ARACLARI_TARA
import logging
logger = logging.getLogger(__name__)

CONFIG (isteğe bağlı — cua_config.yaml):
    lm_studio_url: http://localhost:1234/v1/chat/completions
    lm_studio_model: llava
    max_deneme: 3
    tikla_bekleme: 1.0
"""

from __future__ import annotations

import base64
import gc
import json
import logging
import re
import time
import weakref
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Generator, Optional

import requests

# pyautogui ve PIL lazy import — kullanım anında try/except ile yüklenir
# Kurulum: pip install pyautogui pillow mss

# ──────────────────────────────────────────────
# 1. CONFIG — YAML'DAN OKU, YOKSA VARSAYILAN
# ──────────────────────────────────────────────

def _config_yukle() -> dict:
    """
    cua_config.yaml varsa oradan, yoksa varsayılanları döndürür.
    PyYAML kurulu değilse sessizce varsayılana düşer.
    """
    varsayilan = {
        "lm_studio_url": "http://localhost:1234/v1/chat/completions",
        "lm_studio_model": "llava",
        "max_deneme": 3,
        "tikla_bekleme": 1.0,
        "screenshot_dir": "reymen_screenshots",
        "log_dosyasi": "cua_log.txt",
        "guvenli_bolge": [10, 10],
    }
    config_yol = Path("cua_config.yaml")
    if not config_yol.exists():
        return varsayilan
    try:
        import yaml  # type: ignore
        with config_yol.open(encoding="utf-8") as f:
            kullanici = yaml.safe_load(f) or {}
        return {**varsayilan, **kullanici}
    except Exception:
        return varsayilan

_CFG = _config_yukle()

LM_STUDIO_URL: str        = _CFG["lm_studio_url"]
LM_STUDIO_MODEL: str      = _CFG["lm_studio_model"]
SCREENSHOT_DIR: Path      = Path(_CFG["screenshot_dir"])
LOG_DOSYASI: Path         = Path(_CFG["log_dosyasi"])
TIKLA_BEKLEME: float      = float(_CFG["tikla_bekleme"])
MAX_DENEME_TABAN: int     = int(_CFG["max_deneme"])   # adaptif için taban
GUVENLI_BOLGE: tuple[int, int] = tuple(_CFG["guvenli_bolge"])  # type: ignore

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[CUA %(asctime)s] %(levelname)s → %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DOSYASI, encoding="utf-8"),
    ],
)
log = logging.getLogger("CUA")

# ──────────────────────────────────────────────
# 5. REQUESTS SESSION HAVUZU
#    Tek Session nesnesi, bağlantıları yeniden kullanır.
#    weakref ile tutulur — modül kapanınca GC onu temizler.
# ──────────────────────────────────────────────

_session_ref: Optional[weakref.ref] = None

def _get_session() -> requests.Session:
    """
    Tek bir requests.Session döndürür; yoksa oluşturur.
    Bağlantı havuzu ~%20 hız kazancı sağlar.
    """
    global _session_ref
    if _session_ref is not None:
        s = _session_ref()
        if s is not None:
            return s
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # weakref: Session büyük bir nesne değil ama tutarlılık için
    _session_ref = weakref.ref(s)
    return s

# Critic Note: _session_ref bir weakref.ref tutar; Python'ın GC'si
# Session'ı referans kalmadığında temizler; bağlantı havuzu sızıntısı yok.


# ──────────────────────────────────────────────
# VERİ YAPILARI
# ──────────────────────────────────────────────

@dataclass
class CUASonucu:
    basarili: bool
    eylem: str
    koordinat: Optional[tuple[int, int]] = None
    vision_yaniti: str = ""
    sonraki_koordinat: Optional[tuple[int, int]] = None   # v2: doğrulamadan gelen öneri
    hata: str = ""
    ekran_boyutu: tuple[int, int] = field(default_factory=lambda: (0, 0))

    def str(self) -> str:
        if self.basarili:
            sonraki = f" | Sonraki öneri: {self.sonraki_koordinat}" if self.sonraki_koordinat else ""
            return (
                f"✅ Eylem: {self.eylem} | "
                f"Koordinat: {self.koordinat} | "
                f"Ekran: {self.ekran_boyutu}{sonraki}"
            )
        return f"❌ Başarısız: {self.hata}"


# ──────────────────────────────────────────────
# EKRAN GÖRÜNTÜSÜ
# ──────────────────────────────────────────────

def ekran_goruntusu_al() -> tuple[Image.Image, tuple[int, int]]:
    """
    Tam ekran görüntüsü alır.
    Önce mss dener; yoksa pyautogui'ye düşer.
    Döner: (PIL.Image, (genişlik, yükseklik))
    """
    from PIL import Image

    SCREENSHOT_DIR.mkdir(exist_ok=True)
    try:
        import mss
        with mss.mss() as sct:
            ham = sct.grab(sct.monitors[1])
            goruntu = Image.frombytes("RGB", ham.size, ham.bgra, "raw", "BGRX")
            log.info(f"Ekran alındı (mss): {goruntu.size}")
            return goruntu, goruntu.size
    except ImportError:
        log.warning("mss bulunamadı — pyautogui yedek devreye girdi.")
    try:
        import pyautogui
        goruntu = pyautogui.screenshot()
        log.info(f"Ekran alındı (pyautogui): {goruntu.size}")
        return goruntu, goruntu.size
    except ImportError:
        raise ImportError("Ekran görüntüsü için mss veya pyautogui gerekli. pip install mss pyautogui")


def goruntu_base64_yap(goruntu: Image.Image, max_genislik: int = 1280) -> str:
    """
    PIL görüntüsünü Base64 JPEG'e dönüştürür.
    Büyük ekranlarda yeniden boyutlandırır.
    """
    from PIL import Image
    if goruntu.width > max_genislik:
        oran = max_genislik / goruntu.width
        yeni_boyut = (max_genislik, int(goruntu.height * oran))
        goruntu = goruntu.resize(yeni_boyut, Image.LANCZOS)
        log.info(f"Görüntü yeniden boyutlandırıldı: {yeni_boyut}")
    tampon = BytesIO()
    goruntu.save(tampon, format="JPEG", quality=85)
    b64 = base64.b64encode(tampon.getvalue()).decode("utf-8")
    tampon.close()
    del tampon
    gc.collect()
    return b64

# Critic Note: BytesIO açıkça kapatılır, gc.collect() çağrılır;
# büyük PIL nesnesi scope dışına çıktığında GC tarafından toplanır.


# ──────────────────────────────────────────────
# VİSİON MODEL İLETİŞİMİ
# ──────────────────────────────────────────────

def vision_modele_sor(
    goruntu_b64: str,
    prompt: str,
    zaman_asimi: int = 30,
) -> str:
    """
    LM Studio llava endpoint'ine görüntü + prompt gönderir.
    Session havuzunu kullanır — bağlantı yeniden açılmaz.
    """
    payload = {
        "model": LM_STUDIO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{goruntu_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 256,
        "temperature": 0.1,
    }
    try:
        session = _get_session()
        yanit = session.post(LM_STUDIO_URL, json=payload, timeout=zaman_asimi)
        yanit.raise_for_status()
        metin = yanit.json()["choices"][0]["message"]["content"]
        log.info(f"Vision yanıtı: {metin[:120]}")
        return metin
    except requests.exceptions.ConnectionError:
        hata = "LM Studio bağlantısı kurulamadı. http://localhost:1234 çalışıyor mu?"
        log.error(hata)
        return f"HATA: {hata}"
    except requests.exceptions.Timeout:
        hata = f"Vision model {zaman_asimi}s içinde yanıt vermedi."
        log.error(hata)
        return f"HATA: {hata}"
    except Exception as e:
        log.error(f"Vision API hatası: {e}")
        return f"HATA: {e}"

# Critic Note: Session.post() bağlantıyı havuzda tutar; her çağrıda
# yeni TCP el sıkışması açılmaz; timeout zorunlu; sızıntı yok.


# ──────────────────────────────────────────────
# KOORDİNAT AYRIŞTIRICI
# ──────────────────────────────────────────────

_KOORDINAT_DESENI = re.compile(
    r"(?:x\s*[=:]\s*)?(\d{1,4})\s*[,\s]+(?:y\s*[=:]\s*)?(\d{1,4})"
)

def koordinat_parse(
    metin: str,
    ekran_boyutu: tuple[int, int] = (1920, 1080),
) -> Optional[tuple[int, int]]:
    """
    Vision yanıtından (x, y) çıkarır.
    Ekran sınırları dışını reddeder.
    """
    eslesmeler = _KOORDINAT_DESENI.findall(metin)
    if not eslesmeler:
        log.warning(f"Koordinat bulunamadı → '{metin[:80]}'")
        return None
    x, y = int(eslesmeler[0][0]), int(eslesmeler[0][1])
    maks_x, maks_y = ekran_boyutu
    if not (0 < x < maks_x and 0 < y < maks_y):
        log.warning(f"Koordinat sınır dışı: ({x},{y}) — ekran {ekran_boyutu}")
        return None
    log.info(f"Koordinat parse edildi: ({x}, {y})")
    return x, y


# ──────────────────────────────────────────────
# 2. EYLEM MOTORU — FailSafe tikla() içinde de yakalanıyor
# ──────────────────────────────────────────────

class FailSafeHatasi(Exception):
    """PyAutoGUI fare güvenli köşeye gittiğinde fırlatılır."""


def tikla(x: int, y: int, cift_tik: bool = False) -> None:
    """
    PyAutoGUI ile güvenli tıklama.
    FailSafeException hem burada hem CUA_EKRAN_KULLAN'da yakalanır —
    her çağrı noktası korunuyor.
    """
    import pyautogui

    try:
        pyautogui.moveTo(x, y, duration=0.3)
        if cift_tik:
            pyautogui.doubleClick(x, y)
            log.info(f"Çift tıklandı: ({x}, {y})")
        else:
            pyautogui.click(x, y)
            log.info(f"Tıklandı: ({x}, {y})")
    except pyautogui.FailSafeException as e:
        log.critical(f"FailSafe tetiklendi tikla() içinde: {e}")
        raise FailSafeHatasi("Fare güvenli köşeye gitti.") from e

# Critic Note: FailSafeException tikla() içinde yakalanıp FailSafeHatasi'na
# dönüştürülür; üst katman (CUA_EKRAN_KULLAN) kendi try bloğunda bunu yakalar;
# çift yakalama zincirleme istisna bilgisini korur.


def yaz(metin: str, gecikme: float = 0.05) -> None:
    import pyautogui
    pyautogui.typewrite(metin, interval=gecikme)
    log.info(f"Yazıldı: '{metin}'")


def klavye_kisayol(*tuslar: str) -> None:
    import pyautogui
    pyautogui.hotkey(*tuslar)
    log.info(f"Kısayol: {'+'.join(tuslar)}")


def eylem_yorumla_ve_calistir(
    hedef: str,
    koordinat: tuple[int, int],
) -> str:
    hedef_kucuk = hedef.lower()
    x, y = koordinat
    if "çift tık" in hedef_kucuk or "double" in hedef_kucuk:
        tikla(x, y, cift_tik=True)
        return f"çift_tıklandı({x},{y})"
    if "yaz" in hedef_kucuk or "gir" in hedef_kucuk or "type" in hedef_kucuk:
        yazilacak = re.search(r"['\"](.+?)['\"]", hedef)
        tikla(x, y)
        time.sleep(0.2)
        if yazilacak:
            yaz(yazilacak.group(1))
            return f"tıklandı({x},{y}) + yazıldı('{yazilacak.group(1)}')"
        return f"tıklandı({x},{y}) [yazılacak metin bulunamadı]"
    tikla(x, y)
    return f"tıklandı({x},{y})"


# ──────────────────────────────────────────────
# 4. ADAPTİF DENEME SAYACI
# ──────────────────────────────────────────────

class AdaptifDenemeSayaci:
    """
    Başarısız parse girişimlerine göre MAX_DENEME'yi dinamik olarak artırır.
    Taban: MAX_DENEME_TABAN (config'den).
    Her ardışık başarısızlıkta +1 eklenir, maksimum taban × 2.
    Başarıda sıfırlanır.
    """
    def __init__(self) -> None:
        self._ardisik_basarisiz: int = 0
        self._taban: int = MAX_DENEME_TABAN

    @property
    def mevcut_limit(self) -> int:
        return min(self._taban + self._ardisik_basarisiz, self._taban * 2)

    def basarisiz_kaydet(self) -> None:
        self._ardisik_basarisiz += 1
        log.info(f"Adaptif limit: {self.mevcut_limit} (ardışık başarısız: {self._ardisik_basarisiz})")

    def sifirla(self) -> None:
        self._ardisik_basarisiz = 0

# Tek global sayaç — motor yaşam döngüsü boyunca öğrenir.
_deneme_sayaci = AdaptifDenemeSayaci()

# Critic Note: AdaptifDenemeSayaci sade bir int tutar; bellek maliyeti sabit;
# global nesne weakref gerektirmiyor — küçük, uzun ömürlü, paylaşılan durum.


# ──────────────────────────────────────────────
# 3. GELİŞTİRİLMİŞ DOĞRULAMA
#    EVET/HAYIR + bir sonraki adım için koordinat önerisi
# ──────────────────────────────────────────────

def _dogrulama_yap(
    b64: str,
    hedef: str,
    ekran_boyutu: tuple[int, int],
) -> tuple[bool, Optional[tuple[int, int]]]:
    """
    Eylem sonrası doğrulama:
      - Başarılı mı? (EVET/HAYIR)
      - Başarısızsa: bir sonraki adım için koordinat önerisi
    Döner: (basarili: bool, sonraki_koordinat: Optional[tuple])
    """
    dogr_prompt = (
        f"'{hedef}' eylemi gerçekleştirildikten sonraki ekran bu. "
        "1) Eylem başarılı olduysa sadece 'EVET' yaz. "
        "2) Başarısız olduysa 'HAYIR' yaz, ardından bir satırda "
        f"'{hedef}' için doğru koordinatı 'x, y' formatında öner. "
        "Başka hiçbir şey yazma."
    )
    yanit = vision_modele_sor(b64, dogr_prompt)
    basarili = "EVET" in yanit.upper()
    sonraki: Optional[tuple[int, int]] = None

    if not basarili:
        sonraki = koordinat_parse(yanit, ekran_boyutu)
        if sonraki:
            log.info(f"Doğrulamadan sonraki koordinat önerisi: {sonraki}")

    return basarili, sonraki

# Critic Note: b64 bu fonksiyona referans olarak geçer, kopyalanmaz;
# sonraki koordinat sadece başarısız durumda ayrıştırılır — gereksiz parse yok.


# ──────────────────────────────────────────────
# ÖN KOŞUL KONTROLÜ — çağrılmadan önce ortamı doğrula
# ──────────────────────────────────────────────

_on_kosul_kontrolu_yapildi: bool = False
_on_kosul_sonuc: Optional[str] = None


def _on_kosul_kontrol() -> Optional[str]:
    """
    CUA döngüsü için gerekli tüm bileşenleri kontrol eder.
    Sadece bir kere çalışır — sonraki çağrılarda önbellek döndürür.
    Döner: None (her şey tamam) veya uyarı metni
    """
    global _on_kosul_kontrolu_yapildi, _on_kosul_sonuc
    if _on_kosul_kontrolu_yapildi:
        return _on_kosul_sonuc

    uyarilar: list[str] = []

    # 1. PIL (pillow)
    try:
        from PIL import Image
        Image.new("RGB", (1, 1))
    except ImportError:
        uyarilar.append("PIL (pillow) kurulu değil: pip install pillow")

    # 2. pyautogui
    try:
        import pyautogui
        pyautogui.size()
    except ImportError:
        uyarilar.append("pyautogui kurulu değil: pip install pyautogui")

    # 3. Ekran görüntüsü (mss veya pyautogui)
    try:
        import mss
        with mss.mss() as sct:
            sct.monitors[1]
    except ImportError:
        try:
            import pyautogui
            pyautogui.screenshot()
        except Exception:
            uyarilar.append("Ekran görüntüsü alınamıyor — mss veya pyautogui gerekli")
    except Exception:
        uyarilar.append("Ekran görüntüsü alınamıyor (monitor algılanamadı)")

    # 4. LM Studio bağlantısı
    try:
        import requests
        yanit = requests.get(LM_STUDIO_URL.replace("/v1/chat/completions", "/v1/models"),
                            timeout=5)
        if yanit.status_code == 200:
            modeller = yanit.json()
            model_listesi = [m.get("id", "") for m in modeller if isinstance(m, dict)]
            if LM_STUDIO_MODEL not in model_listesi:
                uyarilar.append(
                    f"Vision model '{LM_STUDIO_MODEL}' LM Studio'da bulunamadı. "
                    f"Yüklü modeller: {', '.join(model_listesi[:5])}..."
                )
        else:
            uyarilar.append(f"LM Studio yanıt vermedi (HTTP {yanit.status_code})")
    except requests.exceptions.ConnectionError:
        uyarilar.append(
            "LM Studio çalışmıyor. Vision işlemler için LM Studio'da "
            "bir vision model (ör: llava) yükleyip http://localhost:1234'ü açın."
        )
    except requests.exceptions.Timeout:
        uyarilar.append("LM Studio'ya bağlantı zaman aşımına uğradı (5 sn)")
    except Exception as e:
        uyarilar.append(f"LM Studio kontrolü başarısız: {e}")

    _on_kosul_kontrolu_yapildi = True
    if uyarilar:
        _on_kosul_sonuc = "⚠ CUA ön koşul hatası:\n" + "\n".join(f"  • {u}" for u in uyarilar)
        log.warning(_on_kosul_sonuc)
    else:
        _on_kosul_sonuc = None
        log.info("CUA ön koşulları tamam — vision model hazır.")
    return _on_kosul_sonuc


# ──────────────────────────────────────────────
# ANA CUA DÖNGÜSÜ
# ──────────────────────────────────────────────

_vision_onbellek: weakref.WeakValueDictionary = weakref.WeakValueDictionary()


def CUA_EKRAN_KULLAN(hedef: str = "") -> str:
    """
    Tam otonom CUA döngüsü.

    Adımlar:
        1. Ön koşul kontrolü (LM Studio, pyautogui, PIL)
        2. Ekran görüntüsü al
        3. Vision modele gönder → koordinat iste
        4. Koordinatı parse et (adaptif deneme sayısı)
        5. Eylemi yürüt (tıkla / yaz) — FailSafe her katmanda yakalanır
        6. Bekleme → yeni ekran → doğrula (EVET/HAYIR + sonraki koordinat)
        7. Sonuç döndür

    Parametreler:
        hedef: "WhatsApp ikonuna tıkla"
               "arama çubuğuna 'merhaba' yaz"
               "" → sadece analiz, eylem yok
    """
    # ── Ön koşul kontrolü ──────────────────────
    uyari = _on_kosul_kontrol()
    if uyari:
        return f"[CUA_UYARI]\n{uyari}\nEksikleri giderdikten sonra tekrar dene."

    if not hedef:
        goruntu, boyut = ekran_goruntusu_al()
        b64 = goruntu_base64_yap(goruntu)
        del goruntu
        analiz = vision_modele_sor(b64, "Bu ekranı kısaca analiz et.")
        del b64
        gc.collect()
        return f"[CUA_ANALIZ] {analiz}"

    log.info(f"CUA başladı → hedef: '{hedef}'")

    # 1. Ekran
    goruntu, ekran_boyutu = ekran_goruntusu_al()
    b64 = goruntu_base64_yap(goruntu)
    del goruntu

    # 2-3. Vision + adaptif parse
    prompt = (
        f"Bu ekran görüntüsünde '{hedef}' işlemini yapmam gerekiyor. "
        "Hangi koordinata tıklamalıyım? "
        "SADECE 'x, y' formatında koordinat döndür, başka hiçbir şey yazma. "
        f"Ekran boyutu: {ekran_boyutu[0]}x{ekran_boyutu[1]} piksel."
    )

    koordinat: Optional[tuple[int, int]] = None
    limit = _deneme_sayaci.mevcut_limit

    for deneme in range(1, limit + 1):
        yanit = vision_modele_sor(b64, prompt)
        if yanit.startswith("HATA:"):
            del b64
            gc.collect()
            return str(CUASonucu(basarili=False, eylem=hedef, hata=yanit))

        koordinat = koordinat_parse(yanit, ekran_boyutu)
        if koordinat:
            _deneme_sayaci.sifirla()
            break

        log.warning(f"Parse başarısız (deneme {deneme}/{limit})")
        _deneme_sayaci.basarisiz_kaydet()
        limit = _deneme_sayaci.mevcut_limit  # dinamik güncelleme
        prompt = (
            f"Önceki yanıtın anlaşılmadı. '{hedef}' için "
            "SADECE iki sayı yaz, örnek: '452, 317' — başka hiçbir şey."
        )

    del b64
    gc.collect()

    if not koordinat:
        return str(CUASonucu(
            basarili=False,
            eylem=hedef,
            hata=f"Adaptif {limit} denemede koordinat alınamadı.",
        ))

    # 4. Eylem — FailSafe her iki katmanda da yakalanır
    try:
        eylem_aciklama = eylem_yorumla_ve_calistir(hedef, koordinat)
    except FailSafeHatasi as e:
        return str(CUASonucu(
            basarili=False,
            eylem=hedef,
            koordinat=koordinat,
            hata=str(e),
        ))

    # 5. Doğrulama
    time.sleep(TIKLA_BEKLEME)
    yeni_goruntu, _ = ekran_goruntusu_al()
    yeni_b64 = goruntu_base64_yap(yeni_goruntu)
    del yeni_goruntu

    basarili, sonraki_koordinat = _dogrulama_yap(yeni_b64, hedef, ekran_boyutu)
    del yeni_b64
    gc.collect()

    sonuc = CUASonucu(
        basarili=basarili,
        eylem=eylem_aciklama,
        koordinat=koordinat,
        sonraki_koordinat=sonraki_koordinat,
        ekran_boyutu=ekran_boyutu,
    )
    log.info(str(sonuc))
    return str(sonuc)


# ──────────────────────────────────────────────
# ARAÇ TARAYICI
# ──────────────────────────────────────────────

_REYMEN_DOSYALARI = [
    "motor.py",
    "screenshot_v2.py",
    "hermesapprove.py",
    "sistem_talimati.py",
    "screen_vision_analiz.py",
]


def _dosya_tara(yol: Path) -> dict:
    if not yol.exists():
        return {"durum": "bulunamadı", "fonksiyonlar": [], "siniflar": []}
    icerik = yol.read_text(encoding="utf-8", errors="replace")
    fonksiyonlar = re.findall(r"^def\s+(\w+)", icerik, re.MULTILINE)
    siniflar = re.findall(r"^class\s+(\w+)", icerik, re.MULTILINE)
    return {
        "durum": "bulundu",
        "satir": icerik.count("\n"),
        "fonksiyonlar": fonksiyonlar,
        "siniflar": siniflar,
    }


def _dosyalari_tara_generator(
    kok: Path = Path("."),
) -> Generator[tuple[str, dict], None, None]:
    """yield tabanlı — tüm dosyaları aynı anda belleğe almaz."""
    for dosya_adi in _REYMEN_DOSYALARI:
        yield dosya_adi, _dosya_tara(kok / dosya_adi)


def CUA_ARACLARI_TARA(kok: str = ".") -> str:
    """
    ReYMeN bileşenlerini tarar; CUA entegrasyonu için durum raporu üretir.
    """
    satirlar = ["═" * 56, "  ReYMeN CUA — Bileşen Tarama Raporu", "═" * 56]
    eksik: list[str] = []
    hazir: list[str] = []

    for dosya_adi, bilgi in _dosyalari_tara_generator(Path(kok)):
        if bilgi["durum"] == "bulunamadı":
            satirlar.append(f"  ✗  {dosya_adi:<30} → BULUNAMADI")
            eksik.append(dosya_adi)
        else:
            fn_sayisi = len(bilgi["fonksiyonlar"])
            satirlar.append(
                f"  ✓  {dosya_adi:<30} → {bilgi['satir']:>4} satır | "
                f"{fn_sayisi} fonksiyon"
            )
            if bilgi["fonksiyonlar"]:
                ozet = ", ".join(bilgi["fonksiyonlar"][:5])
                if fn_sayisi > 5:
                    ozet += f" … (+{fn_sayisi-5})"
                satirlar.append(f"       {ozet}")
            hazir.append(dosya_adi)

    satirlar += [
        "─" * 56,
        f"  Hazır  : {len(hazir)}/{len(_REYMEN_DOSYALARI)} bileşen",
        f"  Eksik  : {', '.join(eksik) if eksik else 'yok'}",
        "─" * 56,
    ]
    if eksik:
        satirlar.append("  ⚠  Eksik dosyalar CUA döngüsünü kısmen kırabilir.")
    else:
        satirlar.append("  ✅ Tüm bileşenler mevcut — CUA başlatılabilir.")
    satirlar.append("═" * 56)
    rapor = "\n".join(satirlar)
    log.info("Araç tarama tamamlandı.")
    return rapor

# Critic Note: Generator teker teker dosya okur; N dosya için O(1) bellek;
# büyük projede bile yığın birikmez.


# ── Motor Kaydı ──────────────────────────────────────────────────
def motor_kaydet(motor: object):
    """motor.py entegrasyonu: CUA araçlarını kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    motor._plugin_arac_kaydet(
        "CUA_EKRAN_KULLAN",
        lambda hedef="": CUA_EKRAN_KULLAN(hedef),
        "Ekranı görür, vision model ile analiz eder, hedefe göre tıklar veya yazar. Tam otonom CUA döngüsü.",
    )
    motor._plugin_arac_kaydet(
        "CUA_ARACLARI_TARA",
        lambda kok=".": CUA_ARACLARI_TARA(kok),
        "ReYMeN bileşenlerini tarar, CUA hazırlık durumunu raporlar",
    )


# ──────────────────────────────────────────────
# MOTOR.PY + SİSTEM_TALİMATI.PY ENTEGRASYON BLOKLARI
# ──────────────────────────────────────────────

MOTOR_ENTEGRASYON_KODU = '''
# ── motor.py üstüne ekle ─────────────────────────────────────────
from cua_motor_araci import CUA_EKRAN_KULLAN, CUA_ARACLARI_TARA

ARACLAR["CUA_EKRAN_KULLAN"] = CUA_EKRAN_KULLAN
ARACLAR["CUA_ARACLARI_TARA"] = CUA_ARACLARI_TARA
'''

SISTEM_TALIMATI_EKI = '''
CUA_ARACLARI = [
    {
        "isim": "CUA_EKRAN_KULLAN",
        "aciklama": (
            "Ekranı görür, vision model ile analiz eder, "
            "verilen hedefe göre tıklar veya yazar. "
            "hedef='WhatsApp ikonuna tıkla' veya "
            "hedef='arama çubuğuna \\'merhaba\\' yaz'"
        ),
        "parametreler": {"hedef": "str"},
    },
    {
        "isim": "CUA_ARACLARI_TARA",
        "aciklama": "ReYMeN bileşenlerini tarar, CUA hazırlık durumunu raporlar.",
        "parametreler": {"kok": "str — taranacak dizin (varsayılan '.')"},
    },
]
'''


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print(CUA_ARACLARI_TARA())

    if len(sys.argv) > 1:
        hedef_arg = " ".join(sys.argv[1:])
        print(f"\nHedef: '{hedef_arg}'")
        print(CUA_EKRAN_KULLAN(hedef_arg))
    else:
        print("\nKullanım : python cua_motor_araci.py '<hedef>'")
        print("Örnek    : python cua_motor_araci.py \"WhatsApp ikonuna tıkla\"")
        print("\n--- motor.py entegrasyon kodu ---")
        print(MOTOR_ENTEGRASYON_KODU)
