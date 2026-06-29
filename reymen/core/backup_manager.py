# -*- coding: utf-8 -*-
"""
backup_manager.py — P2 Yedekleme Sistemi.

Zamanlanmis yedekleme: skills/, memory/, config/, .ReYMeN/
Git push (Watcher-Hermes/hermes-full-backup)
ZIP export (tum proje)

Motor Tools:
    YEDEK_AL(tip)       → Yedek al (git/zip/tam)
    YEDEK_LISTE()        → Yedek listesini goster
    GERI_YUKLE(kaynak)   → Yedekten geri yukle
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Proje dizini ────────────────────────────────────────────────────────────────
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
YEDEK_DIZINI = PROJE_KOK / ".ReYMeN" / "yedekler"
GIT_BACKUP_REPO = "Watcher-Hermes/hermes-full-backup"
_HARIC_TUT = {"yedekler", "__pycache__", ".git", "node_modules", ".venv", "venv"}
MAX_YEDEK = 10  # Maksimum yerel yedek sayisi


# ═══════════════════════════════════════════════════════════════════════════════
#  BackupManager
# ═══════════════════════════════════════════════════════════════════════════════


class BackupManager:
    """Yedekleme sistemi yoneticisi.

    Ozellikler:
        - Git push ile uzak repo'ya yedek
        - ZIP export ile komple proje yedegi
        - Kismi yedek (skills/, memory/, config/, .ReYMeN/)
        - Yedek listeleme ve geri yukleme
    """

    def __init__(self, yedek_dizini: Optional[Path] = None):
        self._yedek_dizini = yedek_dizini or YEDEK_DIZINI
        self._yedek_dizini.mkdir(parents=True, exist_ok=True)

    # ── YEDEK AL ───────────────────────────────────────────────────────────

    def yedek_al(self, tip: str = "kismi") -> Dict[str, Any]:
        """Yedek al.

        Args:
            tip: "kismi" (skills/memory/config/.ReYMeN),
                  "zip" (tum proje ZIP),
                  "git" (git push),
                  "tam" (kismi + zip)

        Returns:
            Yedek sonucu
        """
        baslangic = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if tip == "git":
            return self._git_yedek(baslangic)
        elif tip == "zip":
            return self._zip_yedek(timestamp, baslangic)
        elif tip == "tam":
            return self._tam_yedek(timestamp, baslangic)
        else:  # kismi
            return self._kismi_yedek(timestamp, baslangic)

    def _kismi_yedek(self, timestamp: str, baslangic: float) -> Dict[str, Any]:
        """Kismi yedek: skills/, memory/, config/, .ReYMeN/"""
        hedef = self._yedek_dizini / f"kismi_{timestamp}"
        hedef.mkdir(parents=True, exist_ok=True)

        yedeklenen = []

        # Yedeklenecek klasorler
        kaynaklar = {
            "skills": PROJE_KOK / "skills",
            "memory": PROJE_KOK / "memory",
            "config": PROJE_KOK / "config",
            "reymen_config": PROJE_KOK / ".ReYMeN",
            "config_yaml": PROJE_KOK / "config.yaml",
            "env": PROJE_KOK / ".env",
        }

        for ad, kaynak in kaynaklar.items():
            if kaynak.exists():
                try:
                    if kaynak.is_dir():
                        shutil.copytree(kaynak, hedef / ad, dirs_exist_ok=True)
                    else:
                        shutil.copy2(kaynak, hedef / ad)
                    yedeklenen.append(ad)
                except Exception as e:
                    logger.warning("[Backup] Kismi yedek hatasi (%s): %s", ad, e)

        # Metadata yaz
        self._metadata_yaz(hedef, "kismi", yedeklenen)

        sure = round(time.time() - baslangic, 2)
        self._temizle_eski("kismi")

        return {
            "tip": "kismi",
            "dizin": str(hedef),
            "yedeklenen": yedeklenen,
            "sure": sure,
            "durum": "basarili",
        }

    def _zip_yedek(self, timestamp: str, baslangic: float) -> Dict[str, Any]:
        """Tam proje ZIP yedegi (gitignore'dakileri haric)."""
        zip_adi = self._yedek_dizini / f"tam_{timestamp}.zip"

        try:
            with zipfile.ZipFile(zip_adi, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Gitignore oku
                gitignore = set()
                gitignore_path = PROJE_KOK / ".gitignore"
                if gitignore_path.exists():
                    for line in gitignore_path.read_text().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            gitignore.add(line.rstrip("/"))

                # Tum dosyalari tara
                for root, dirs, files in os.walk(PROJE_KOK):
                    # __pycache__ ve .git'i atla
                    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".venv", "node_modules", ".pytest_cache")]

                    for file in files:
                        dosya_yol = Path(root) / file
                        try:
                            rel_path = dosya_yol.relative_to(PROJE_KOK)
                            # Gitignore kontrol
                            if any(str(rel_path).startswith(ig) for ig in gitignore if ig):
                                continue
                            zf.write(dosya_yol, str(rel_path))
                        except (ValueError, OSError):
                            continue

            sure = round(time.time() - baslangic, 2)
            boyut = zip_adi.stat().st_size if zip_adi.exists() else 0

            self._temizle_eski("zip")

            return {
                "tip": "zip",
                "dosya": str(zip_adi),
                "boyut_mb": round(boyut / (1024 * 1024), 2),
                "sure": sure,
                "durum": "basarili",
            }

        except Exception as e:
            logger.error("[Backup] ZIP yedek hatasi: %s", e)
            return {"tip": "zip", "durum": "hata", "hata": str(e), "sure": round(time.time() - baslangic, 2)}

    def _git_yedek(self, baslangic: float) -> Dict[str, Any]:
        """Git push ile uzak repo'ya yedek.

        Hedef: Watcher-Hermes/hermes-full-backup
        """
        try:
            # Git komutlari
            commands = [
                ["git", "add", "-A"],
                ["git", "commit", "--allow-empty", "-m", f"Auto backup {datetime.now().isoformat()}"],
                ["git", "remote", "set-url", "origin", f"https://github.com/{GIT_BACKUP_REPO}.git"],
                ["git", "push", "origin", "main"],
            ]

            sonuc = []
            for cmd in commands:
                try:
                    r = subprocess.run(
                        cmd, cwd=str(PROJE_KOK),
                        capture_output=True, text=True, timeout=60,
                    )
                    sonuc.append({
                        "komut": " ".join(cmd[:2]),
                        "cikti": r.stdout[-200:] if r.stdout else "",
                        "hata": r.stderr[-200:] if r.stderr else "",
                        "kod": r.returncode,
                    })
                except subprocess.TimeoutExpired:
                    sonuc.append({"komut": " ".join(cmd[:2]), "cikti": "", "hata": "Zaman asimi", "kod": -1})

            sure = round(time.time() - baslangic, 2)

            # Basari kontrolu
            basarili = all(s.get("kod", -1) == 0 or "nothing to commit" in s.get("cikti", "") or "Everything up-to-date" in s.get("cikti", "") for s in sonuc)

            return {
                "tip": "git",
                "hedef": GIT_BACKUP_REPO,
                "adimlar": sonuc,
                "sure": sure,
                "durum": "basarili" if basarili else "kismi",
            }

        except Exception as e:
            logger.error("[Backup] Git yedek hatasi: %s", e)
            return {"tip": "git", "durum": "hata", "hata": str(e), "sure": round(time.time() - baslangic, 2)}

    def _tam_yedek(self, timestamp: str, baslangic: float) -> Dict[str, Any]:
        """Tam yedek: kismi + ZIP."""
        kismi = self._kismi_yedek(timestamp, baslangic)
        zip_result = self._zip_yedek(timestamp, baslangic)

        return {
            "tip": "tam",
            "kismi": kismi,
            "zip": zip_result,
            "sure": round(time.time() - baslangic, 2),
            "durum": "basarili",
        }

    def _metadata_yaz(self, hedef: Path, tip: str, yedeklenen: List[str]):
        """Metadata dosyasi yaz."""
        meta = {
            "tip": tip,
            "tarih": datetime.now().isoformat(),
            "proje": str(PROJE_KOK),
            "yedeklenen": yedeklenen,
            "python_version": sys.version,
        }
        try:
            (hedef / "yedek_metadata.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("[Backup] Metadata yazma hatasi: %s", e)

    def _temizle_eski(self, tip: str):
        """Eski yedekleri temizle (MAX_YEDEK'ten fazlasini sil)."""
        try:
            yedekler = self._yedekleri_listele(tip)
            if len(yedekler) > MAX_YEDEK:
                silinecek = yedekler[MAX_YEDEK:]
                for y in silinecek:
                    yol = Path(y["dizin"] if y.get("dizin") else y.get("dosya", ""))
                    if yol.exists():
                        if yol.is_dir():
                            shutil.rmtree(yol)
                        else:
                            yol.unlink()
                logger.info("[Backup] %d eski yedek temizlendi", len(silinecek))
        except Exception as e:
            logger.warning("[Backup] Temizleme hatasi: %s", e)

    # ── YEDEK LISTE ────────────────────────────────────────────────────────

    def yedek_listele(self, tip: Optional[str] = None) -> List[Dict[str, Any]]:
        """Yedek listesini goster.

        Args:
            tip: Opsiyonel filtre (kismi/zip/git)

        Returns:
            Yedek listesi
        """
        return self._yedekleri_listele(tip)

    def _yedekleri_listele(self, tip: Optional[str] = None) -> List[Dict[str, Any]]:
        """Yerel yedekleri tara ve listele."""
        yedekler = []

        if not self._yedek_dizini.exists():
            return yedekler

        # Kismi yedekler (klasor)
        for item in sorted(self._yedek_dizini.glob("kismi_*"), reverse=True):
            if item.is_dir():
                meta_dosya = item / "yedek_metadata.json"
                meta = {}
                if meta_dosya.exists():
                    try:
                        meta = json.loads(meta_dosya.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        pass

                yedek = {
                    "tip": "kismi",
                    "dizin": str(item),
                    "tarih": meta.get("tarih", datetime.fromtimestamp(item.stat().st_mtime).isoformat()),
                    "yedeklenen": meta.get("yedeklenen", []),
                    "boyut": sum(f.stat().st_size for f in item.rglob("*") if f.is_file()),
                }
                yedekler.append(yedek)

        # ZIP yedekler
        for item in sorted(self._yedek_dizini.glob("tam_*.zip"), reverse=True):
            if item.is_file():
                yedekler.append({
                    "tip": "zip",
                    "dosya": str(item),
                    "tarih": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "boyut": item.stat().st_size,
                    "boyut_mb": round(item.stat().st_size / (1024 * 1024), 2),
                })

        # Filtrele
        if tip:
            yedekler = [y for y in yedekler if y.get("tip") == tip]

        return yedekler

    # ── GERI YUKLE ─────────────────────────────────────────────────────────

    def geri_yukle(self, kaynak: str) -> Dict[str, Any]:
        """Yedekten geri yukle.

        Args:
            kaynak: Yedek dizini veya ZIP dosyasi yolu

        Returns:
            Geri yukleme sonucu
        """
        baslangic = time.time()
        kaynak_yol = Path(kaynak)

        if not kaynak_yol.exists():
            return {"durum": "hata", "hata": f"Kaynak bulunamadi: {kaynak}", "sure": 0}

        try:
            if kaynak_yol.is_dir():
                return self._kismi_geri_yukle(kaynak_yol, baslangic)
            elif kaynak_yol.suffix == ".zip":
                return self._zip_geri_yukle(kaynak_yol, baslangic)
            else:
                return {"durum": "hata", "hata": f"Bilinmeyen kaynak: {kaynak}", "sure": 0}
        except Exception as e:
            logger.error("[Backup] Geri yukleme hatasi: %s", e)
            return {"durum": "hata", "hata": str(e), "sure": round(time.time() - baslangic, 2)}

    def _kismi_geri_yukle(self, kaynak: Path, baslangic: float) -> Dict[str, Any]:
        """Kismi yedekten geri yukle."""
        geri_yuklenen = []

        # Hedef klasorler
        eslesmeler = {
            "skills": PROJE_KOK / "skills",
            "memory": PROJE_KOK / "memory",
            "config": PROJE_KOK / "config",
            "reymen_config": PROJE_KOK / ".ReYMeN",
        }

        for klasor, hedef in eslesmeler.items():
            kaynak_klasor = kaynak / klasor
            if kaynak_klasor.exists():
                try:
                    if hedef.exists():
                        shutil.rmtree(hedef)
                    shutil.copytree(kaynak_klasor, hedef)
                    geri_yuklenen.append(klasor)
                except Exception as e:
                    logger.warning("[Backup] Geri yukleme hatasi (%s): %s", klasor, e)

        # Tek dosyalar
        tek_dosyalar = ["config_yaml", "env"]
        for ad in tek_dosyalar:
            kaynak_dosya = kaynak / ad
            if kaynak_dosya.exists():
                try:
                    hedef = PROJE_KOK / (ad.replace("_yaml", ".yaml").replace("env", ".env"))
                    shutil.copy2(kaynak_dosya, hedef)
                    geri_yuklenen.append(ad)
                except Exception as e:
                    logger.warning("[Backup] Dosya geri yukleme hatasi (%s): %s", ad, e)

        sure = round(time.time() - baslangic, 2)
        return {
            "durum": "basarili",
            "kaynak": str(kaynak),
            "geri_yuklenen": geri_yuklenen,
            "sure": sure,
        }

    def _zip_geri_yukle(self, kaynak: Path, baslangic: float) -> Dict[str, Any]:
        """ZIP yedekten geri yukle (ayri dizine)."""
        cikti_dizini = PROJE_KOK / f"geri_yukleme_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cikti_dizini.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(kaynak, 'r') as zf:
                zf.extractall(str(cikti_dizini))

            sure = round(time.time() - baslangic, 2)
            return {
                "durum": "basarili",
                "kaynak": str(kaynak),
                "cikti": str(cikti_dizini),
                "sure": sure,
                "not": "ZIP geri yukleme ayri bir dizine yapildi. Elle tasimaniz gerekebilir.",
            }
        except Exception as e:
            return {"durum": "hata", "hata": str(e), "sure": round(time.time() - baslangic, 2)}

    # ── DURUM ──────────────────────────────────────────────────────────────

    def durum(self) -> Dict[str, Any]:
        """Yedekleme sistemi durumu."""
        yedekler = self.yedek_listele()
        toplam_boyut = sum(y.get("boyut", 0) for y in yedekler)

        return {
            "yedek_dizini": str(self._yedek_dizini),
            "toplam_yedek": len(yedekler),
            "kismi_yedek": len([y for y in yedekler if y.get("tip") == "kismi"]),
            "zip_yedek": len([y for y in yedekler if y.get("tip") == "zip"]),
            "toplam_boyut_mb": round(toplam_boyut / (1024 * 1024), 2),
            "max_yedek": MAX_YEDEK,
            "proje_dizini": str(PROJE_KOK),
            "git_repo": GIT_BACKUP_REPO,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_backup_manager_instance: Optional[BackupManager] = None


def backup_manager_al() -> BackupManager:
    """Varsayilan BackupManager singleton'ini al."""
    global _backup_manager_instance
    if _backup_manager_instance is None:
        _backup_manager_instance = BackupManager()
    return _backup_manager_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Motor Tools
# ═══════════════════════════════════════════════════════════════════════════════


def motor_kaydet(motor) -> None:
    """Motor'a yedekleme araclarini kaydeder.

    Kaydettigi araclar:
        - YEDEK_AL: Yedek al (kismi/zip/git/tam)
        - YEDEK_LISTE: Yedek listesini goster
        - GERI_YUKLE: Yedekten geri yukle
    """
    motor._plugin_arac_kaydet(
        "YEDEK_AL",
        _yedek_al_tool,
        "YEDEK_AL(tip) — Yedek al. "
        "Parametre: tip=kismi|zip|git|tam (varsayilan: kismi). "
        "Ornek: YEDEK_AL(tip='zip')"
    )
    motor._plugin_arac_kaydet(
        "YEDEK_LISTE",
        _yedek_liste_tool,
        "YEDEK_LISTE(tip) — Yedek listesini goster. "
        "Parametre: tip=kismi|zip (opsiyonel filtre). "
        "Ornek: YEDEK_LISTE()"
    )
    motor._plugin_arac_kaydet(
        "GERI_YUKLE",
        _geri_yukle_tool,
        "GERI_YUKLE(kaynak) — Yedekten geri yukle. "
        "Parametre: kaynak=yedek_dizini_veya_zip_yolu. "
        "Ornek: GERI_YUKLE(kaynak='/path/to/yedek')"
    )
    logger.info("[BackupManager] Motor'a 3 arac kaydedildi (YEDEK_AL, YEDEK_LISTE, GERI_YUKLE)")


def _yedek_al_tool(**kw) -> str:
    """YEDEK_AL aracı."""
    args = kw.get("args", [])
    tip = args[0] if args else kw.get("tip", "kismi")

    if tip not in ("kismi", "zip", "git", "tam"):
        return f"[HATA] YEDEK_AL: gecersiz tip '{tip}'. Secenekler: kismi, zip, git, tam"

    manager = backup_manager_al()
    sonuc = manager.yedek_al(tip=tip)

    if sonuc.get("durum") == "hata":
        return f"[HATA] Yedek alinamadi: {sonuc.get('hata', 'bilinmeyen hata')}"

    if tip == "kismi":
        return (
            f"[YEDEK] Kismi yedek alindi\n"
            f"  Dizin: {sonuc.get('dizin', '')}\n"
            f"  Yedeklenen: {', '.join(sonuc.get('yedeklenen', []))}\n"
            f"  Sure: {sonuc.get('sure', '?')}s"
        )
    elif tip == "zip":
        return (
            f"[YEDEK] ZIP yedek alindi\n"
            f"  Dosya: {sonuc.get('dosya', '')}\n"
            f"  Boyut: {sonuc.get('boyut_mb', 0)} MB\n"
            f"  Sure: {sonuc.get('sure', '?')}s"
        )
    elif tip == "git":
        return (
            f"[YEDEK] Git yedek: {sonuc.get('durum', '?')}\n"
            f"  Hedef: {sonuc.get('hedef', '')}\n"
            f"  Sure: {sonuc.get('sure', '?')}s"
        )
    else:  # tam
        return (
            f"[YEDEK] Tam yedek alindi\n"
            f"  Kismi: {sonuc.get('kismi', {}).get('durum', '?')}\n"
            f"  ZIP: {sonuc.get('zip', {}).get('durum', '?')}\n"
            f"  Sure: {sonuc.get('sure', '?')}s"
        )


def _yedek_liste_tool(**kw) -> str:
    """YEDEK_LISTE aracı."""
    args = kw.get("args", [])
    tip = args[0] if args else kw.get("tip", None)

    manager = backup_manager_al()
    yedekler = manager.yedek_listele(tip=tip)

    if not yedekler:
        return "[YEDEK] Henuz yedek bulunmuyor."

    satirlar = [f"[YEDEK] Toplam {len(yedekler)} yedek:"]
    for y in yedekler:
        tip_str = y.get("tip", "?")
        tarih = y.get("tarih", "?")[:19]
        boyut = y.get("boyut_mb", y.get("boyut", 0))
        if isinstance(boyut, int) and boyut > 1024 * 1024:
            boyut_str = f"{boyut / (1024 * 1024):.1f} MB"
        elif isinstance(boyut, int):
            boyut_str = f"{boyut / 1024:.1f} KB"
        else:
            boyut_str = f"{boyut} MB"

        if tip_str == "kismi":
            satirlar.append(f"  📁 {tip_str:6s} | {tarih} | {boyut_str:>10s} | {y.get('dizin', '')}")
        else:
            satirlar.append(f"  📦 {tip_str:6s} | {tarih} | {boyut_str:>10s} | {y.get('dosya', '')}")

    return "\n".join(satirlar)


def _geri_yukle_tool(**kw) -> str:
    """GERI_YUKLE aracı."""
    args = kw.get("args", [])
    kaynak = args[0] if args else kw.get("kaynak", "")

    if not kaynak:
        return "[HATA] GERI_YUKLE: kaynak parametresi zorunlu"

    manager = backup_manager_al()
    sonuc = manager.geri_yukle(kaynak)

    if sonuc.get("durum") == "hata":
        return f"[HATA] Geri yukleme basarisiz: {sonuc.get('hata', 'bilinmeyen hata')}"

    return (
        f"[GERI_YUKLE] Geri yukleme tamamlandi\n"
        f"  Kaynak: {sonuc.get('kaynak', '')}\n"
        f"  Geri yuklenen: {', '.join(sonuc.get('geri_yuklenen', []))}\n"
        f"  Cikti: {sonuc.get('cikti', '')}\n"
        f"  Sure: {sonuc.get('sure', '?')}s"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== BackupManager Test ===")

    manager = backup_manager_al()
    print(f"Durum: {json.dumps(manager.durum(), indent=2, ensure_ascii=False)}")

    # Kismi yedek al
    sonuc = manager.yedek_al(tip="kismi")
    print(f"\nKismi yedek: {sonuc.get('durum', '?')}")
    if sonuc.get("yedeklenen"):
        print(f"  Yedeklenen: {', '.join(sonuc['yedeklenen'])}")

    # Liste
    print(f"\nYedek listesi:")
    for y in manager.yedek_listele():
        print(f"  {y['tip']}: {y.get('dizin', y.get('dosya', ''))}")

    print("\n✓ Test tamamlandi")
