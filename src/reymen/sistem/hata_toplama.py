# -*- coding: utf-8 -*-
"""hata_toplama.py — Merkezi Hata Toplama + Bildirim Sistemi

Tum motor/plugin/tool hatalarini merkezi olarak toplar, kategorize eder,
frekans analizi yapar ve bildirim gonderir.

Ozellikler:
  - SQLite ile kalici depolama
  - Hata kategorizasyonu (tip, modul, seviye)
  - Frekans analizi (son 1s/5dk/1sa/24sa)
  - Telegram bildirimi
  - Motor hook entegrasyonu
"""

import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Varsayilan yollar ──────────────────────────────────────────────────────
PROJE_KOK = Path(__file__).parent.parent
DEFAULT_DB_PATH = PROJE_KOK / "merkez_db" / "hata_toplama.db"
DEFAULT_CONFIG_PATH = PROJE_KOK / ".ReYMeN" / "hata_toplama.json"


@dataclass
class HataKaydi:
    """Tek bir hata kaydi."""
    id: Optional[int] = None
    zaman: str = ""
    modul: str = ""
    arac: str = ""
    hata_tipi: str = ""
    hata_mesaji: str = ""
    seviye: str = "UYARI"         # BILGI | UYARI | HATA | KRITIK
    frekans_imzasi: str = ""      # Ayni hatalari gruplamak icin
    ek_bilgi: str = ""            # JSON string
    cozuldu_mu: bool = False
    bildirim_gonderildi_mi: bool = False

    def as_dict(self) -> dict:
        d = asdict(self)
        d["zaman"] = self.zaman or datetime.now().isoformat()
        return d


class HataVeritabani:
    """SQLite tabanli hata depolama."""

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._local = threading.local()
        self._ac()

    def _baglan(self) -> sqlite3.Connection:
        """Thread-safe baglanti."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=10)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ac(self):
        """Veritabanini olustur/tablo var mi kontrol et."""
        conn = self._baglan()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS hata_kayitlari (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman       TEXT NOT NULL,
                modul       TEXT NOT NULL DEFAULT '',
                arac        TEXT NOT NULL DEFAULT '',
                hata_tipi   TEXT NOT NULL DEFAULT '',
                hata_mesaji TEXT NOT NULL DEFAULT '',
                seviye      TEXT NOT NULL DEFAULT 'UYARI',
                frekans_imzasi TEXT NOT NULL DEFAULT '',
                ek_bilgi    TEXT NOT NULL DEFAULT '{}',
                cozuldu_mu  INTEGER NOT NULL DEFAULT 0,
                bildirim_gonderildi_mi INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_hata_zaman ON hata_kayitlari(zaman);
            CREATE INDEX IF NOT EXISTS idx_hata_imza ON hata_kayitlari(frekans_imzasi);
            CREATE INDEX IF NOT EXISTS idx_hata_seviye ON hata_kayitlari(seviye);
        """)
        conn.commit()

    def kaydet(self, kayit: HataKaydi) -> int:
        """Yeni hata kaydi ekle. Doner: kayit id."""
        conn = self._baglan()
        imza = kayit.frekans_imzasi or f"{kayit.modul}:{kayit.hata_tipi}:{kayit.hata_mesaji[:100]}"
        cur = conn.execute("""
            INSERT INTO hata_kayitlari
                (zaman, modul, arac, hata_tipi, hata_mesaji, seviye,
                 frekans_imzasi, ek_bilgi, cozuldu_mu, bildirim_gonderildi_mi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kayit.zaman or datetime.now().isoformat(),
            kayit.modul[:100],
            kayit.arac[:100],
            kayit.hata_tipi[:100],
            kayit.hata_mesaji[:1000],
            kayit.seviye,
            imza[:200],
            kayit.ek_bilgi or "{}",
            1 if kayit.cozuldu_mu else 0,
            1 if kayit.bildirim_gonderildi_mi else 0,
        ))
        conn.commit()
        return cur.lastrowid or 0

    def frekans_analizi(self, zaman_araligi_s: int = 3600) -> list[dict]:
        """Son N saniyedeki hata frekanslari."""
        conn = self._baglan()
        sinir = (datetime.now() - timedelta(seconds=zaman_araligi_s)).isoformat()
        cur = conn.execute("""
            SELECT frekans_imzasi, modul, hata_tipi, seviye,
                   COUNT(*) as sayi,
                   MAX(zaman) as son_zaman
            FROM hata_kayitlari
            WHERE zaman > ?
            GROUP BY frekans_imzasi
            ORDER BY sayi DESC
            LIMIT 20
        """, (sinir,))
        return [dict(row) for row in cur.fetchall()]

    def seviye_istatistik(self, zaman_araligi_s: int = 86400) -> dict[str, int]:
        """Son N saniyedeki seviye bazli hata sayilari."""
        conn = self._baglan()
        sinir = (datetime.now() - timedelta(seconds=zaman_araligi_s)).isoformat()
        cur = conn.execute("""
            SELECT seviye, COUNT(*) as sayi
            FROM hata_kayitlari
            WHERE zaman > ?
            GROUP BY seviye
        """, (sinir,))
        return {row["seviye"]: row["sayi"] for row in cur.fetchall()}

    def son_hatalar(self, limit: int = 20) -> list[dict]:
        """En son hata kayitlari."""
        conn = self._baglan()
        cur = conn.execute("""
            SELECT * FROM hata_kayitlari
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

    def cozuldu_isaretle(self, kayit_id: int) -> bool:
        """Bir hatayi cozuldu olarak isaretle."""
        conn = self._baglan()
        cur = conn.execute(
            "UPDATE hata_kayitlari SET cozuldu_mu = 1 WHERE id = ?",
            (kayit_id,)
        )
        conn.commit()
        return cur.rowcount > 0

    def bildirim_gonderildi_isaretle(self, kayit_id: int) -> bool:
        """Bildirim gonderildi olarak isaretle."""
        conn = self._baglan()
        cur = conn.execute(
            "UPDATE hata_kayitlari SET bildirim_gonderildi_mi = 1 WHERE id = ?",
            (kayit_id,)
        )
        conn.commit()
        return cur.rowcount > 0

    def toplam_sayi(self) -> int:
        conn = self._baglan()
        cur = conn.execute("SELECT COUNT(*) as sayi FROM hata_kayitlari")
        return cur.fetchone()["sayi"]

    def kapat(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class HataToplayici:
    """Merkezi hata toplama ve bildirim yoneticisi."""

    def __init__(self, db_path: str = "", config_path: str = ""):
        self.db = HataVeritabani(db_path)
        self.config = self._config_yukle(config_path)
        self._bildirim_fonksiyonu: Any = None
        self._kilit = threading.Lock()
        self._istatistik_ornekleyici: Optional[threading.Thread] = None
        self._calisiyor = False
        # Seviye esikleri: bu esigin uzerindeki hatalar bildirim gonderir
        self._bildirim_esigi = self.config.get("bildirim_esigi", "UYARI")
        self._bildirim_interval_s = self.config.get("bildirim_interval_s", 300)  # 5dk

    def _config_yukle(self, config_path: str) -> dict:
        """JSON config dosyasindan ayarlari yukle."""
        yol = Path(config_path or DEFAULT_CONFIG_PATH)
        if yol.exists():
            try:
                return json.loads(yol.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("[HataToplama] Config yukleme hatasi: %s", e)
        return {}

    def bildirim_fonksiyonu_ayarla(self, fn: Any):
        """Bildirim gonderecek fonksiyonu ayarla (ornek: telegram_gonder)."""
        self._bildirim_fonksiyonu = fn

    def hata_kaydet(self, modul: str = "", arac: str = "",
                    hata_tipi: str = "", hata_mesaji: str = "",
                    seviye: str = "UYARI", ek_bilgi: str = "") -> int:
        """Bir hatayi kaydet ve gerekirse bildirim gonder.

        Args:
            modul: Hatanin kaynak modulu (ornek: motor, plugin, web_ui)
            arac: Hatanin kaynak araci (ornek: PYTHON_CALISTIR, WEB_ARA)
            hata_tipi: Hata tipi sinifi (ornek: ImportError, TimeoutError)
            hata_mesaji: Hata mesaji
            seviye: BILGI | UYARI | HATA | KRITIK
            ek_bilgi: Opsiyonel JSON string

        Returns:
            int: Kayit ID
        """
        with self._kilit:
            kayit = HataKaydi(
                zaman=datetime.now().isoformat(),
                modul=modul,
                arac=arac,
                hata_tipi=hata_tipi[:100],
                hata_mesaji=hata_mesaji[:1000],
                seviye=seviye,
                ek_bilgi=ek_bilgi or "{}",
            )
            kayit_id = self.db.kaydet(kayit)

            # Bildirim gonderimi
            if self._bildirim_gerekli_mi(seviye, kayit.frekans_imzasi):
                self._bildirim_gonder(kayit_id, kayit)

            return kayit_id

    def _bildirim_gerekli_mi(self, seviye: str, imza: str) -> bool:
        """Bildirim gonderilmeli mi?"""
        if not self._bildirim_fonksiyonu:
            return False

        # Seviye kontrolu
        seviye_sirasi = {"BILGI": 0, "UYARI": 1, "HATA": 2, "KRITIK": 3}
        esik = seviye_sirasi.get(self._bildirim_esigi, 1)
        mevcut = seviye_sirasi.get(seviye, 1)
        if mevcut < esik:
            return False

        # Son N saniyede ayni imzali hata varsa atla (spam korumasi)
        sinir = (datetime.now() - timedelta(seconds=self._bildirim_interval_s)).isoformat()
        conn = self.db._baglan()
        cur = conn.execute("""
            SELECT COUNT(*) as sayi
            FROM hata_kayitlari
            WHERE frekans_imzasi = ? AND zaman > ? AND bildirim_gonderildi_mi = 1
        """, (imza, sinir))
        row = cur.fetchone()
        if row and row["sayi"] > 0:
            return False

        return True

    def _bildirim_gonder(self, kayit_id: int, kayit: HataKaydi):
        """Bildirim gonder ve isaretle."""
        try:
            if self._bildirim_fonksiyonu:
                mesaj = (
                    f"⚠️ *Hata Bildirimi* [{kayit.seviye}]\n"
                    f"Modul: `{kayit.modul}`\n"
                    f"Arac: `{kayit.arac}`\n"
                    f"Tip: `{kayit.hata_tipi}`\n"
                    f"Mesaj: `{kayit.hata_mesaji[:200]}`\n"
                    f"ID: #{kayit_id}"
                )
                self._bildirim_fonksiyonu(mesaj)
                self.db.bildirim_gonderildi_isaretle(kayit_id)
        except Exception as e:
            logger.error("[HataToplama] Bildirim hatasi: %s", e)

    # ── Motor Integration ─────────────────────────────────────────────────

    def motor_hook_handler(self, olay: str, **kwargs) -> None:
        """Motor hook'larindan gelen hatalari topla.

        Motor._hook_tetikle'den cagrilmak uzere:
          - TOOL_CALLED: basarili cagri (BILGI)
          - TOOL_ERROR: hatali cagri (HATA)
        """
        if olay == "TOOL_ERROR":
            arac = kwargs.get("arac", "")
            params = kwargs.get("params", [])
            sonuc = kwargs.get("sonuc", "")
            hata_mesaji = sonuc[:500] if sonuc else str(params)[:200]
            self.hata_kaydet(
                modul="motor",
                arac=arac,
                hata_tipi="ToolError",
                hata_mesaji=hata_mesaji,
                seviye="HATA",
                ek_bilgi=json.dumps({"params": str(params)[:200]}, ensure_ascii=False),
            )

    def motor_baslangic_kancasi(self, motor: Any) -> None:
        """Motor baslatilirken hooklari kaydet."""
        try:
            if hasattr(motor, "hook_kaydet"):
                motor.hook_kaydet("TOOL_ERROR", self.motor_hook_handler)
            logger.info("[HataToplama] Motor hook'lari kaydedildi")
        except Exception as e:
            logger.warning("[HataToplama] Hook kayit hatasi: %s", e)

    # ── Periyodik Istatistik ──────────────────────────────────────────────

    def periyodik_istatistik_baslat(self, interval_s: int = 3600):
        """Periyodik hata istatistigi olustur (arkaplan thread)."""
        if self._calisiyor:
            return
        self._calisiyor = True
        self._istatistik_ornekleyici = threading.Thread(
            target=self._periyodik_dongu,
            args=(interval_s,),
            daemon=True,
            name="hata-istatistik",
        )
        self._istatistik_ornekleyici.start()
        logger.info("[HataToplama] Periyodik istatistik baslatildi (%ds)", interval_s)

    def _periyodik_dongu(self, interval_s: int):
        """Periyodik istatistik dongusu."""
        while self._calisiyor:
            time.sleep(interval_s)
            try:
                ozet = self.ozet_raporu()
                if ozet["toplam_hata"] > 0:
                    logger.info("[HataToplama] Periyodik rapor:\n%s", ozet["ozet_text"])
            except Exception as e:
                logger.warning("[HataToplama] Istatistik hatasi: %s", e)

    def periyodik_istatistik_durdur(self):
        self._calisiyor = False

    # ── Raporlama ─────────────────────────────────────────────────────────

    def ozet_raporu(self, saat: int = 24) -> dict:
        """N saatlik hata ozet raporu."""
        aralik = saat * 3600
        frekans = self.db.frekans_analizi(aralik)
        seviye = self.db.seviye_istatistik(aralik)
        toplam = sum(seviye.values())

        satirlar = [
            f"[HataToplama] Son {saat} saat ozeti:",
            f"  Toplam: {toplam} hata",
            f"  Seviye: {', '.join(f'{s}: {a}' for s, a in sorted(seviye.items()))}",
        ]
        if frekans:
            satirlar.append("  En sik (ilk 5):")
            for f in frekans[:5]:
                satirlar.append(f"    {f['sayi']}x [{f['seviye']}] {f['modul']}/{f['hata_tipi']}")

        return {
            "toplam_hata": toplam,
            "seviye_dagilim": seviye,
            "en_sik": frekans[:10],
            "ozet_text": "\n".join(satirlar),
            "db_kayit_sayisi": self.db.toplam_sayi(),
        }

    def son_hatalar_text(self, limit: int = 10) -> str:
        """Son hatalari metin olarak goster."""
        hatalar = self.db.son_hatalar(limit)
        if not hatalar:
            return "[HataToplama] Kayitli hata yok"

        satirlar = ["[HataToplama] Son Hatalar:", "=" * 50]
        for h in hatalar:
            cozuldu = "✅" if h["cozuldu_mu"] else "❌"
            satirlar.append(
                f"#{h['id']} [{h['seviye']}] {cozuldu} "
                f"{h['modul']}/{h['arac']}: {h['hata_mesaji'][:100]}"
            )
        return "\n".join(satirlar)


# ── Singleton ──────────────────────────────────────────────────────────────

_TOPLAYICI: Optional[HataToplayici] = None


def hata_toplayici() -> HataToplayici:
    """Singleton erisim."""
    global _TOPLAYICI
    if _TOPLAYICI is None:
        _TOPLAYICI = HataToplayici()
    return _TOPLAYICI


# ── Motor Plugin API ───────────────────────────────────────────────────────

def motor_kaydet(motor):
    """Motor'a hata toplama araclarini kaydet."""
    toplayici = hata_toplayici()

    # Hook'lari kaydet
    toplayici.motor_baslangic_kancasi(motor)

    # Periyodik istatistik baslat (6 saatte bir)
    toplayici.periyodik_istatistik_baslat(interval_s=21600)

    # Arac olarak kaydet
    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet(
            "HATA_RAPOR",
            lambda saat=24: hata_toplayici().ozet_raporu(saat)["ozet_text"],
            "Son N saatlik hata ozet raporu. Parametre: saat (varsayilan 24)",
        )
        motor._plugin_arac_kaydet(
            "HATA_SON",
            lambda limit=10: hata_toplayici().son_hatalar_text(limit),
            "Son hata kayitlarini listele. Parametre: limit (varsayilan 10)",
        )
        motor._plugin_arac_kaydet(
            "HATA_COZ",
            lambda kayit_id=0: "✅ Cozuldu" if hata_toplayici().db.cozuldu_isaretle(int(kayit_id)) else "❌ Bulunamadi",
            "Bir hatayi cozuldu olarak isaretle. Parametre: kayit_id (int)",
        )

    logger.info("[HataToplama] Motor'a kaydedildi")


# ── CLI Test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    t = hata_toplayici()

    # Test kayitlari
    t.hata_kaydet(modul="test", arac="CALISTIR", hata_tipi="ImportError",
                   hata_mesaji="modul bulunamadi", seviye="HATA")
    t.hata_kaydet(modul="test", arac="BAGLAN", hata_tipi="TimeoutError",
                   hata_mesaji="zaman asimi", seviye="KRITIK")

    time.sleep(0.5)
    print(t.ozet_raporu(24)["ozet_text"])
    print()
    print(t.son_hatalar_text())
