# -*- coding: utf-8 -*-
"""
alt_ajan.py — Ana ajandan bağımsız, kendi ReAct döngüsüne sahip
izole alt ajan modülü.

LLM çağrıları I/O-bound olduğu için threading yeterli.
Ana ajanı ASLA bloklamaz — görevlendirme anında task_id döner.
"""

import os
import re
import threading
import time
import traceback
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

# ReYMeN arayüzleri
from src.reymen.cereyan.beyin import Beyin
import yaml
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()

# .env dosyasını yükle (API anahtarları için)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError as _alt_ajan_e30:
    print(f"[UYARI] alt_ajan.py:31 - {_alt_ajan_e30}")

# Alt ajan için ayrı Beyin instance'ı
try:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f) or {}
except (FileNotFoundError, OSError) as _alt_ajan_e35:
    print(f"[UYARI] alt_ajan.py:35 - config.yaml bulunamadi, bos config kullaniliyor - {_alt_ajan_e35}")
    _CONFIG = {}
_ALT_BEYIN = Beyin(_CONFIG)

# Thread-local: alt ajan içinde olup olmadığımızı işaretler
_alt_ajan_tls = threading.local()


def _alt_ajan_icinde_mi() -> bool:
    """Motor.py'nin ALT_AJAN_GOREVLENDIR handler'ı bu fonksiyonu
    çağırarak mevcut thread'in bir alt ajana ait olup olmadığını kontrol eder."""
    return getattr(_alt_ajan_tls, "aktif", False)


# Alt ajanların kullanabileceği araç seti (tehlikeli/alt-ajan araçları HARİÇ)
_ALT_AJAN_IZINLI_ARACLAR = frozenset({
    "KOMUT_CALISTIR", "PYTHON_CALISTIR", "DOSYA_YAZ", "DOSYA_OKU",
    "HAFIZA_ARA", "IC_GOZLEM", "GOREV_BITTI",
    "WEB_ARA", "TARAYICI_AC",
    "PDF_OKU", "EXCEL_OKU", "CSV_OKU", "GORUNTU_ANALIZ", "DOSYA_ANALIZ",
    "PROJE_TARA", "SKILL_ARA",
    # ALT_AJAN_GOREVLENDIR BURADA YOK → zincir koruması
})


@dataclass
class AltAjanSonuc:
    task_id: str
    durum: str = "calisiyor"          # calisiyor | tamamlandi | hata
    sonuc: Optional[str] = None
    hata: Optional[str] = None
    adim_sayisi: int = 0
    baslangic: float = field(default_factory=time.time)
    bitis: Optional[float] = None
    # Retry icin orijinal gorev ve baglam
    gorev: str = ""
    baglam: str = ""
    # Callback sistemi
    _callback_fn: Optional[callable] = field(default=None, repr=False)


class AltAjan:
    """Tek bir izole alt ajan oturumu. Kendi mesaj geçmişini tutar,
    ana ajanın context'ine asla dokunmaz.

    Motor.calistir() çağrılarını thread-safe bir kilit ile yönetir.
    """

    def __init__(self, gorev: str, baglam: str = "", max_adim: int = None,
                 derinlik: int = 1, izinli_araclar: Optional[set] = None) -> None:
        self.task_id = str(uuid.uuid4())[:8]
        self.gorev = gorev
        self.baglam = baglam
        # .env'den varsayılan max_adim, yoksa 15
        self.max_adim = max_adim or int(os.environ.get("ALT_AJAN_MAX_ADIM", "15"))
        self.derinlik = derinlik
        self.izinli_araclar = izinli_araclar or _ALT_AJAN_IZINLI_ARACLAR
        self.mesajlar: list[dict] = []
        self.sonuc = AltAjanSonuc(
            task_id=self.task_id,
            gorev=gorev,
            baglam=baglam,
        )
        self._motor = None  # lazy import
        # Döngü dedektörü
        self._onceki_gozlemler = []       # son 5 gözlemi tutar
        self._onceki_eylemler: list[str] = []  # son 5 eylemi tutar
        self._onceki_hata_sayaci: int = 0  # ardisik hata sayaci (circuit breaker)
        self._baslangic_zamani = time.time()
        self._zaman_asimi = float(os.environ.get("ALT_AJAN_ZAMAN_ASIMI", "120"))

    def _motor_al(self):
        """Lazy Motor instance — thread-safe."""
        if self._motor is None:
            from reymen.cereyan.motor import Motor
            try:
                self._motor = Motor(
                    backend_mode="local",
                    config=_CONFIG
                )
            except Exception:
                self._motor = Motor(backend_mode="local")
        return self._motor

    def _baslangic_promptu(self) -> str:
        arac_liste = "\n".join(f"  - {a}" for a in sorted(self.izinli_araclar))
        return (
            f"Sen {self.task_id} ID'li bir ALT AJANSIN. Ana ajan tarafından görevlendirildin.\n"
            f"\nGÖREV: {self.gorev}"
            f"\nBAĞLAM: {self.baglam or '(verilmedi)'}"
            f"\n\nKULLANABILECEĞİN ARAÇLAR:\n{arac_liste}"
            f"\n\n== KATIKSIZ KURALLAR =="
            f"\n- Her turda MUTLAKA su formati kullan:"
            f"\n    Dusunce: [ne yapacagini ve neden acikla]"
            f"\n    Eylem: ARAC_ADI(\"parametre\")"
            f"\n- Basit bilgi sorusu ise: Eylem: GOREV_BITTI(\"cevap\")  → hemen bitir"
            f"\n- ALT_AJAN_GOREVLENDIR aracini KULLANAMAZSIN (engellendi)"
            f"\n- Asla birden fazla eylem yazma"
            f"\n- Cevabini Turkce yaz"
            f"\n- En fazla {self.max_adim} adimin var"
        )

    def _eylem_coz(self, cevap: str):
        """LLM çıktısından 'Eylem: ARAÇ("param")' yakalar."""
        m = re.search(r'Eylem:\s*([A-Z_]+)\s*\((.*)\)', cevap, re.DOTALL)
        if not m:
            return None, None
        arac = m.group(1).strip()
        ham_param = m.group(2).strip()
        return arac, ham_param

    def calistir(self) -> AltAjanSonuc:
        """Senkron çalışır — AltAjanYoneticisi bunu thread'de çağırır.
        
        ReAct döngüsü: Düşünce → Eylem → Gözlem → Tekrar
        Motor üzerinden gerçek araçları kullanır.
        
        Döngü dedektörü: Aynı gözlem/eylem 3x tekrarlanırsa GOREV_BITTI'yi zorlar.
        Zaman aşımı: ALT_AJAN_ZAMAN_ASIMI saniye sonra force bitirir.
        """
        try:
            self.mesajlar.append({"role": "system", "content": self._baslangic_promptu()})

            for adim in range(1, self.max_adim + 1):
                self.sonuc.adim_sayisi = adim

                # Zaman aşımı kontrolü
                gecen_sure = time.time() - self._baslangic_zamani
                if gecen_sure > self._zaman_asimi:
                    self.sonuc.sonuc = f"(zaman_asimi={self._zaman_asimi}s doldu) Son durum: {self.mesajlar[-1]['content'][:200]}"
                    self.sonuc.durum = "tamamlandi"
                    return self.sonuc

                cevap = _ALT_BEYIN.uret(
                    "ReAct formatina UY: Dusunce: ... Eylem: ARAC(\"param\"). "
                    "Arac gerekmiyorsa Eylem: GOREV_BITTI(\"cevap\") yaz.",
                    self.mesajlar
                )
                self.mesajlar.append({"role": "assistant", "content": cevap})

                # BITTI veya GOREV_BITTI kontrolü
                if cevap.strip().startswith("BITTI:"):
                    self.sonuc.sonuc = cevap.split("BITTI:", 1)[1].strip()
                    self.sonuc.durum = "tamamlandi"
                    return self.sonuc
                if "GOREV_BITTI" in cevap:
                    # GOREV_BITTI("...") içindeki metni çıkar
                    import re as _re
                    m = _re.search(r'GOREV_BITTI\s*\(\s*"([^"]*)"\s*\)', cevap)
                    if m:
                        self.sonuc.sonuc = m.group(1)
                        self.sonuc.durum = "tamamlandi"
                        return self.sonuc

                # Eylem çözümle ve çalıştır
                arac, ham_param = self._eylem_coz(cevap)
                if arac and arac in self.izinli_araclar:
                    try:
                        motor = self._motor_al()
                        gozlem = motor.calistir(arac, ham_param)
                        self._onceki_hata_sayaci = 0  # basarili arac → sayaci sifirla
                    except Exception as e:
                        gozlem = f"[HATA] {arac} çalıştırılırken hata: {e}"
                        self._onceki_hata_sayaci += 1
                elif arac:
                    gozlem = f"[ENGELLENDI] '{arac}' aracı alt ajanlar için izinli değil."
                    self._onceki_hata_sayaci += 1
                else:
                    # Eylem yok, düşünmeye devam et
                    gozlem = "Devam et. Hedefe ulaştıysan BITTI: yaz."

                # Circuit Breaker: ardisik hata esigi asildi mi?
                _HATA_ESIK = 5  # circuit_breaker.CircuitBreaker.ESIK ile uyumlu
                if self._onceki_hata_sayaci >= _HATA_ESIK:
                    self.sonuc.sonuc = (
                        f"[REACT_LOOP_DETECTOR] {self._onceki_hata_sayaci} ardisik hata — "
                        f"circuit open, gorev zorla sonlandirildi: {self.gorev[:100]}"
                    )
                    self.sonuc.durum = "tamamlandi"
                    return self.sonuc

                self.mesajlar.append({"role": "user", "content": f"GÖZLEM: {gozlem}"})

                # === DÖNGÜ DEDEKTÖRÜ ===
                # Son 5 gözlemi takip et
                self._onceki_gozlemler.append(gozlem)
                if len(self._onceki_gozlemler) > 5:
                    self._onceki_gozlemler.pop(0)

                # Son 5 eylemi takip et
                if arac:
                    self._onceki_eylemler.append(arac)
                    if len(self._onceki_eylemler) > 5:
                        self._onceki_eylemler.pop(0)

                # Aynı gözlem 3x tekrarlandı mı? → ReAct Loop Detector, force GOREV_BITTI
                if len(self._onceki_gozlemler) >= 3:
                    son_3 = self._onceki_gozlemler[-3:]
                    if len(set(son_3)) == 1:
                        self.sonuc.sonuc = (
                            f"[REACT_LOOP_DETECTOR] Ayni gozlem 3x tekrarlandi "
                            f"({repr(son_3[0][:80])}) — GOREV_BITTI zorlandirildi. "
                            f"Gorev: {self.gorev[:100]}"
                        )
                        self.sonuc.durum = "tamamlandi"
                        return self.sonuc

                # Aynı eylem 3x tekrarlandı mı? → ReAct Loop Detector
                if len(self._onceki_eylemler) >= 3:
                    son_3_eylem = self._onceki_eylemler[-3:]
                    if len(set(son_3_eylem)) == 1:
                        self.sonuc.sonuc = (
                            f"[REACT_LOOP_DETECTOR] Ayni eylem 3x tekrarlandi "
                            f"({son_3_eylem[0]}) — GOREV_BITTI zorlandirildi. "
                            f"Gorev: {self.gorev[:100]}"
                        )
                        self.sonuc.durum = "tamamlandi"
                        return self.sonuc

            # max_adim doldu
            self.sonuc.sonuc = (
                f"(max_adim={self.max_adim} doldu) "
                f"Son durum: {self.mesajlar[-1]['content'][:200]}"
            )
            self.sonuc.durum = "tamamlandi"

        except Exception as e:
            self.sonuc.durum = "hata"
            self.sonuc.hata = f"{e}\n{traceback.format_exc()}"
        finally:
            self.sonuc.bitis = time.time()

        return self.sonuc


class AltAjanYoneticisi:
    """Alt ajanları thread'de başlatır, sonuçları task_id ile saklar.
    Ana ajanı ASLA bloklamaz.

    Background notification: callback fonksiyonu atanırsa ajan bitince
    callback(task_id, sonuc) çağrılır. (ReYMeN delegate_task pattern'i)
    """

    def __init__(self, sonuc_zaman_asimi: float = 1800.0,
                 callback=None) -> None:
        self._gorevler: dict[str, AltAjanSonuc] = {}
        self._kilit = threading.Lock()
        self._sonuc_zaman_asimi = sonuc_zaman_asimi
        self._callback = callback  # background notification

    def gorevlendir(self, gorev: str, baglam: str = "", max_adim: int = 8,
                    izinli_araclar: Optional[set] = None) -> str:
        """Alt ajan başlatır, hemen task_id döner. Ana ajan bloklanmaz.
        
        izinli_araclar: Alt ajanın kullanabileceği araç seti.
                        None = varsayılan kısıtlı set.
        """
        self._eski_sonuclari_temizle()
        alt = AltAjan(gorev, baglam, max_adim, izinli_araclar=izinli_araclar)
        with self._kilit:
            self._gorevler[alt.task_id] = alt.sonuc

        def _calistir() -> None:
            # Thread-local işareti koy → motor.py bu işareti görüp
            # ALT_AJAN_GOREVLENDIR'i bloklar
            _alt_ajan_tls.aktif = True
            try:
                sonuc = alt.calistir()
            finally:
                _alt_ajan_tls.aktif = False
            with self._kilit:
                self._gorevler[alt.task_id] = sonuc
                # Per-task callback (alt_ajan_sonuc_callback ile atanir)
                try:
                    if sonuc._callback_fn:
                        sonuc._callback_fn(alt.task_id, sonuc)
                except Exception as _alt_ajan_e310:
                    print(f"[UYARI] alt_ajan.py:311 - {_alt_ajan_e310}")
            # Background notification callback
            if self._callback:
                try:
                    self._callback(alt.task_id, sonuc)
                except Exception as _alt_ajan_e316:
                    print(f"[UYARI] alt_ajan.py:317 - {_alt_ajan_e316}")

        threading.Thread(
            target=_calistir, daemon=True,
            name=f"alt-ajan-{alt.task_id}"
        ).start()
        return alt.task_id

    def durum_sorgula(self, task_id: str) -> Optional[AltAjanSonuc]:
        with self._kilit:
            return self._gorevler.get(task_id)

    def sonuc_bekle(self, task_id: str, timeout: float = 60.0) -> Optional[AltAjanSonuc]:
        """Gerekirse senkron bekleme (polling tercih edilir)."""
        baslangic = time.time()
        while time.time() - baslangic < timeout:
            sonuc = self.durum_sorgula(task_id)
            if sonuc and sonuc.durum != "calisiyor":
                return sonuc
            time.sleep(0.5)
        return self.durum_sorgula(task_id)

    def _eski_sonuclari_temizle(self):
        """30dk'dan eski tamamlanmış görevleri temizle (bellek sızıntısı önleme)."""
        simdi = time.time()
        with self._kilit:
            self._gorevler = {
                tid: s for tid, s in self._gorevler.items()
                if s.durum == "calisiyor"
                or (s.bitis and simdi - s.bitis < self._sonuc_zaman_asimi)
            }


# ── 1) ALT AJAN RETRY ────────────────────────────────────────────────

def alt_ajan_retry(task_id: str, max_retry: int = 2) -> Optional[str]:
    """Başarısız bir alt ajan görevini tekrar dene.

    Orijinal goal + context ile yeni bir AltAjan oluşturup çalıştırır.
    Eski sonucun durumu 'hata' ise retry yapar, aksi halde None döner.

    Args:
        task_id: Tekrar denenmek istenen görevin ID'si.
        max_retry: Kaç kere tekrar deneneceği (varsayılan: 2).

    Returns:
        Yeni task_id (başarılı başlatıldıysa) veya None.
    """
    try:
        eski_sonuc = alt_ajan_yoneticisi.durum_sorgula(task_id)
        if eski_sonuc is None:
            print(f"[alt_ajan_retry] '{task_id}' bulunamadi.")
            return None
        if eski_sonuc.durum != "hata":
            print(f"[alt_ajan_retry] '{task_id}' durumu '{eski_sonuc.durum}', retry gerekmiyor.")
            return None

        orijinal_gorev = eski_sonuc.gorev or "(bilinmiyor)"
        orijinal_baglam = eski_sonuc.baglam or ""
        print(f"[alt_ajan_retry] '{task_id}' tekrar deneniyor (max_retry={max_retry})...")
        print(f"  Gorev: {orijinal_gorev[:80]}")

        yeni_task_id = None
        for deneme in range(1, max_retry + 1):
            print(f"  Retry {deneme}/{max_retry}...")
            try:
                yeni_task_id = alt_ajan_yoneticisi.gorevlendir(
                    gorev=orijinal_gorev,
                    baglam=orijinal_baglam,
                    max_adim=12,
                )
                # Retry baslatildi, bekle ve sonucu kontrol et
                yeni_sonuc = alt_ajan_yoneticisi.sonuc_bekle(yeni_task_id, timeout=120.0)
                if yeni_sonuc and yeni_sonuc.durum == "tamamlandi":
                    print(f"[alt_ajan_retry] '{task_id}' -> '{yeni_task_id}' basarili!")
                    return yeni_task_id
                elif yeni_sonuc and yeni_sonuc.durum == "hata":
                    print(f"[alt_ajan_retry] Retry {deneme} basarisiz: {yeni_sonuc.hata[:100]}")
                else:
                    print(f"[alt_ajan_retry] Retry {deneme} sonuc: {yeni_sonuc.durum if yeni_sonuc else 'None'}")
            except Exception as e:
                print(f"[alt_ajan_retry] Retry {deneme} hata: {e}")

        print(f"[alt_ajan_retry] '{task_id}' icin tum {max_retry} deneme basarisiz.")
        return yeni_task_id

    except Exception as e:
        print(f"[alt_ajan_retry] Beklenmeyen hata: {e}")
        traceback.print_exc()
        return None


# ── 2) ALT AJAN SONUC CALLBACK ────────────────────────────────────────

def _alt_ajan_varsayilan_callback(task_id: str, sonuc: "AltAjanSonuc") -> None:
    """Varsayılan callback: sonucu log'a yaz."""
    try:
        sure = round(sonuc.bitis - sonuc.baslangic, 2) if sonuc.bitis else "?"
        print(
            f"[alt_ajan_callback] task_id={task_id} "
            f"durum={sonuc.durum} "
            f"sure={sure}s "
            f"adim={sonuc.adim_sayisi} "
            f"sonuc={str(sonuc.sonuc)[:80] if sonuc.sonuc else '-'} "
            f"hata={str(sonuc.hata)[:80] if sonuc.hata else '-'}"
        )
    except Exception as e:
        print(f"[alt_ajan_callback] Log hatasi: {e}")


def alt_ajan_sonuc_callback(task_id: str, callback_url: Optional[str] = None) -> bool:
    """Bir alt ajan görevi tamamlanınca çağrılacak callback fonksiyonu ata.

    callback_url=None ise varsayılan log callback'i kullanılır.
    callback_url bir dosya yolu ise sonuc o dosyaya yazılır.
    callback_url bir HTTP/HTTPS URL ise POST isteği gönderilir (ileriye dönük).

    Args:
        task_id: Hedef görevin ID'si.
        callback_url: Callback hedefi (None=varsayılan log, dosya yolu, URL).

    Returns:
        True başarılı, False başarısız.
    """
    try:
        sonuc = alt_ajan_yoneticisi.durum_sorgula(task_id)
        if sonuc is None:
            print(f"[alt_ajan_sonuc_callback] '{task_id}' bulunamadi.")
            return False

        if callback_url is None:
            # Varsayılan: log callback
            sonuc._callback_fn = _alt_ajan_varsayilan_callback
            print(f"[alt_ajan_sonuc_callback] '{task_id}' -> varsayilan log callback atandi.")
            return True

        # Dosya yolu callback
        if callback_url.startswith("/") or callback_url.startswith("~") or ":" in callback_url:
            from pathlib import Path as _Path
            callback_path = _Path(callback_url).expanduser().resolve()

            def _dosya_callback(tid: str, s: "AltAjanSonuc") -> None:
                try:
                    import json as _json
                    import datetime as _dt
                    veri = {
                        "task_id": tid,
                        "durum": s.durum,
                        "sonuc": s.sonuc,
                        "hata": s.hata,
                        "adim_sayisi": s.adim_sayisi,
                        "baslangic": s.baslangic,
                        "bitis": s.bitis,
                        "timestamp": _dt.datetime.now().isoformat(),
                    }
                    callback_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(callback_path, "w", encoding="utf-8") as f:
                        _json.dump(veri, f, ensure_ascii=False, indent=2)
                    print(f"[alt_ajan_callback] '{tid}' -> {callback_path} yazildi.")
                except Exception as e:
                    print(f"[alt_ajan_callback] Dosya yazma hatasi: {e}")

            sonuc._callback_fn = _dosya_callback
            print(f"[alt_ajan_sonuc_callback] '{task_id}' -> dosya callback: {callback_path}")
            return True

        # HTTP/HTTPS URL callback (ileriye donuk)
        if callback_url.startswith("http://") or callback_url.startswith("https://"):
            def _http_callback(tid: str, s: "AltAjanSonuc") -> None:
                try:
                    import urllib.request as _req
                    import json as _json
                    veri = _json.dumps({
                        "task_id": tid,
                        "durum": s.durum,
                        "sonuc": s.sonuc,
                        "hata": s.hata,
                        "adim_sayisi": s.adim_sayisi,
                    }).encode("utf-8")
                    _req.urlopen(_req.Request(callback_url, data=veri,
                                  headers={"Content-Type": "application/json"}),
                                  timeout=10)
                except Exception as e:
                    print(f"[alt_ajan_callback] HTTP callback hatasi: {e}")

            sonuc._callback_fn = _http_callback
            print(f"[alt_ajan_sonuc_callback] '{task_id}' -> HTTP callback: {callback_url}")
            return True

        print(f"[alt_ajan_sonuc_callback] Bilinmeyen callback_url: {callback_url}")
        return False

    except Exception as e:
        print(f"[alt_ajan_sonuc_callback] Hata: {e}")
        traceback.print_exc()
        return False


# ── 3) GOREV HAVUZU (TASK POOL) ──────────────────────────────────────

class AltAjanHavuzu:
    """Alt ajan gorev havuzu.

    Beklemedeki gorevleri kuyruga ekler, max 5 ayni anda calissin.
    Kuyruktaki gorevler sirasiyla baslatilir.
    """

    def __init__(self, max_es_zamanli: int = 5) -> None:
        self._kuyruk: list[dict] = []                # Bekleyen gorevler
        self._aktif_gorevler: dict[str, AltAjanSonuc] = {}  # Su an calisanlar
        self._tamamlananlar: dict[str, AltAjanSonuc] = {}   # Bitenler
        self._max_es_zamanli = max_es_zamanli
        self._kilit = threading.Lock()
        self._kuyruk_thread = None
        self._calisiyor = False

    def _kuyruk_islemcisi(self) -> None:
        """Arka planda calisir, kuyruktaki gorevleri sirayla baslatir."""
        while self._calisiyor:
            try:
                time.sleep(0.3)
                with self._kilit:
                    # Aktif gorev sayisini kontrol et
                    # Tamamlananlari aktiften cikar
                    for tid in list(self._aktif_gorevler.keys()):
                        s = self._aktif_gorevler[tid]
                        if s.durum != "calisiyor":
                            self._tamamlananlar[tid] = self._aktif_gorevler.pop(tid)

                    # Kuyruk bos veya maksimum kapasiteye ulasildi
                    if not self._kuyruk:
                        continue
                    if len(self._aktif_gorevler) >= self._max_es_zamanli:
                        continue

                    # Siradaki gorevi al
                    gorev_bilgisi = self._kuyruk.pop(0)

                # Kilit disinda baslat (olabildigince az kilitte kal)
                yeni_task_id = alt_ajan_yoneticisi.gorevlendir(
                    gorev=gorev_bilgisi.get("gorev", ""),
                    baglam=gorev_bilgisi.get("baglam", ""),
                    max_adim=gorev_bilgisi.get("max_adim", 8),
                    izinli_araclar=gorev_bilgisi.get("izinli_araclar", None),
                )
                with self._kilit:
                    yeni_sonuc = alt_ajan_yoneticisi.durum_sorgula(yeni_task_id)
                    if yeni_sonuc:
                        self._aktif_gorevler[yeni_task_id] = yeni_sonuc

            except Exception as e:
                print(f"[AltAjanHavuzu] Kuyruk islemcisi hatasi: {e}")
                time.sleep(1)

    def baslat(self) -> None:
        """Havuzu baslat (arka plan islemcisini devreye al)."""
        try:
            if self._calisiyor:
                return
            self._calisiyor = True
            self._kuyruk_thread = threading.Thread(
                target=self._kuyruk_islemcisi,
                daemon=True,
                name="alt-ajan-havuzu",
            )
            self._kuyruk_thread.start()
            print(f"[AltAjanHavuzu] Baslatildi (max_es_zamanli={self._max_es_zamanli})")
        except Exception as e:
            print(f"[AltAjanHavuzu] Baslatma hatasi: {e}")
            self._calisiyor = False

    def durdur(self) -> None:
        """Havuzu durdur."""
        try:
            self._calisiyor = False
            print(f"[AltAjanHavuzu] Durduruldu. Kuyrukta {len(self._kuyruk)}, "
                  f"aktif {len(self._aktif_gorevler)}, "
                  f"tamamlanan {len(self._tamamlananlar)} gorev.")
        except Exception as e:
            print(f"[AltAjanHavuzu] Durdurma hatasi: {e}")

    def alt_ajan_kuyruk_ekle(self, gorev: str, baglam: str = "",
                              max_adim: int = 8,
                              izinli_araclar: Optional[set] = None) -> bool:
        """Bir gorevi kuyruga ekle.

        Args:
            gorev: Gorev tanimi.
            baglam: Baglam metni.
            max_adim: Maksimum adim sayisi.
            izinli_araclar: Izinli araclar (None=varsayilan).

        Returns:
            True basarili, False basarisiz.
        """
        try:
            if not gorev or not gorev.strip():
                print("[AltAjanHavuzu] Gorev metni bos, eklenemedi.")
                return False
            with self._kilit:
                self._kuyruk.append({
                    "gorev": gorev,
                    "baglam": baglam,
                    "max_adim": max_adim,
                    "izinli_araclar": izinli_araclar,
                })
            # Havuz calismiyorsa otomatik baslat
            if not self._calisiyor:
                self.baslat()
            print(f"[AltAjanHavuzu] Gorev kuyruga eklendi. Sira: {len(self._kuyruk)}")
            return True
        except Exception as e:
            print(f"[AltAjanHavuzu] Kuyruk ekleme hatasi: {e}")
            return False

    def alt_ajan_kuyruk_durum(self) -> dict:
        """Kuyruk durumunu dondur.

        Returns:
            {
                "kuyruk_uzunlugu": int,
                "aktif_sayisi": int,
                "tamamlanan_sayisi": int,
                "aktif_gorevler": list[str],
                "tamamlananlar": list[dict],
                "max_es_zamanli": int,
            }
        """
        try:
            with self._kilit:
                # Tamamlananlari guncelle (aktiften cikmis olanlari da al)
                for tid in list(self._aktif_gorevler.keys()):
                    s = self._aktif_gorevler[tid]
                    if s.durum != "calisiyor":
                        self._tamamlananlar[tid] = self._aktif_gorevler.pop(tid)

                aktif_liste = [
                    {"task_id": tid, "durum": s.durum, "adim": s.adim_sayisi}
                    for tid, s in self._aktif_gorevler.items()
                ]
                tamam_liste = [
                    {"task_id": tid, "durum": s.durum, "sonuc": str(s.sonuc)[:60] if s.sonuc else None}
                    for tid, s in list(self._tamamlananlar.items())[-20:]  # son 20
                ]
                return {
                    "kuyruk_uzunlugu": len(self._kuyruk),
                    "aktif_sayisi": len(self._aktif_gorevler),
                    "tamamlanan_sayisi": len(self._tamamlananlar),
                    "aktif_gorevler": aktif_liste,
                    "tamamlananlar": tamam_liste,
                    "max_es_zamanli": self._max_es_zamanli,
                }
        except Exception as e:
            print(f"[AltAjanHavuzu] Durum sorgulama hatasi: {e}")
            return {
                "hata": str(e),
                "kuyruk_uzunlugu": 0,
                "aktif_sayisi": 0,
                "tamamlanan_sayisi": 0,
                "aktif_gorevler": [],
                "tamamlananlar": [],
                "max_es_zamanli": self._max_es_zamanli,
            }


# Singleton'lar — motor.py buradan import eder
alt_ajan_yoneticisi = AltAjanYoneticisi()
alt_ajan_havuzu = AltAjanHavuzu()


# ── Kolaylik fonksiyonlari (dogrudan modul seviyesinde) ──────────────

def alt_ajan_kuyruk_ekle(gorev: str, baglam: str = "",
                           max_adim: int = 8,
                           izinli_araclar: Optional[set] = None) -> bool:
    """Bir gorevi kuyruga ekle (AltAjanHavuzu.alt_ajan_kuyruk_ekle wrapper).

    Args:
        gorev: Gorev tanimi.
        baglam: Baglam metni.
        max_adim: Maksimum adim sayisi.
        izinli_araclar: Izinli araclar (None=varsayilan).

    Returns:
        True basarili, False basarisiz.
    """
    try:
        return alt_ajan_havuzu.alt_ajan_kuyruk_ekle(
            gorev=gorev,
            baglam=baglam,
            max_adim=max_adim,
            izinli_araclar=izinli_araclar,
        )
    except Exception as e:
        print(f"[alt_ajan_kuyruk_ekle] Hata: {e}")
        return False


def alt_ajan_kuyruk_durum() -> dict:
    """Kuyruk durumunu dondur (AltAjanHavuzu.alt_ajan_kuyruk_durum wrapper).

    Returns:
        {
            "kuyruk_uzunlugu": int,
            "aktif_sayisi": int,
            "tamamlanan_sayisi": int,
            "aktif_gorevler": list[dict],
            "tamamlananlar": list[dict],
            "max_es_zamanli": int,
        }
    """
    try:
        return alt_ajan_havuzu.alt_ajan_kuyruk_durum()
    except Exception as e:
        print(f"[alt_ajan_kuyruk_durum] Hata: {e}")
        return {"hata": str(e)}
