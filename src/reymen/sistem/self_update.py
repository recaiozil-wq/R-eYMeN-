# -*- coding: utf-8 -*-
"""
self_update.py — ReYMeN Otonom Self-Update Sistemi.

GitHub'dan son release tag'ini kontrol eder, mevcut versiyonla karsilastirir,
yeni versiyon varsa otomatik indirir ve kurar.

Kullanim:
    from reymen.sistem.self_update import (
        check_for_updates,
        perform_update,
        auto_update_check,
    )

    # Tek seferlik kontrol
    sonuc = check_for_updates()
    if sonuc["guncel_var"]:
        perform_update()

    # Otomatik (haftada 1 kontrol)
    auto_update_check()
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────

PROJE_KOK = Path(__file__).resolve().parent.parent.parent.parent
PYPROJECT_TOML = PROJE_KOK / "pyproject.toml"
UPDATE_MARKER_DIR = PROJE_KOK / ".ReYMeN"
UPDATE_MARKER_FILE = UPDATE_MARKER_DIR / "update_check.json"

# GitHub bilgileri — uzaktaki remoteden otomatik cikar
GITHUB_API_BASE = "https://api.github.com/repos"

# Haftada 1 kontrol (7 gun * 24 saat * 3600 saniye)
HAFTALIK_KONTROL_ARALIGI = 7 * 24 * 3600

# 1 gun (debug/test icin)
GUNLUK_KONTROL_ARALIGI = 24 * 3600


def _git_remote_parse() -> tuple[str, str]:
    """Git remote origin'den owner/repo bilgisini cikar.

    Returns:
        (owner, repo) tuple'i. Bulunamazsa ("recaiozil-wq", "reymen-agean") fallback.
    """
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=PROJE_KOK,
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            url = r.stdout.strip()
            # https://github.com/owner/repo.git
            # git@github.com:owner/repo.git
            for prefix in ("https://github.com/", "git@github.com:"):
                if url.startswith(prefix):
                    path = url[len(prefix):]
                    if path.endswith(".git"):
                        path = path[:-4]
                    parts = path.split("/", 1)
                    if len(parts) == 2:
                        return parts[0], parts[1]
    except Exception:
        pass
    return "recaiozil-wq", "reymen-agean"


def _mevcut_versiyon() -> str:
    """pyproject.toml'dan mevcut versiyonu oku.

    Returns:
        Versiyon stringi (ornek: "2026.07.01") veya "0.0.0" bulunamazsa.
    """
    if not PYPROJECT_TOML.exists():
        logger.warning("[SelfUpdate] pyproject.toml bulunamadi: %s", PYPROJECT_TOML)
        return "0.0.0"
    try:
        for line in PYPROJECT_TOML.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("version"):
                # version = "2026.07.01"
                if "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val
    except Exception as e:
        logger.warning("[SelfUpdate] Versiyon okuma hatasi: %s", e)
    return "0.0.0"


def _versiyon_karsilastir(v1: str, v2: str) -> int:
    """Iki versiyonu karsilastir.

    Args:
        v1: Mevcut versiyon
        v2: Yeni versiyon

    Returns:
        -1: v1 < v2 (guncelleme gerekli)
         0: v1 == v2
         1: v1 > v2 veya karsilastirilamaz
    """
    def _parcala(v: str) -> list:
        """Versiyon stringini rakam parcalarina ayir."""
        parcaciklar = []
        for p in v.replace("-", ".").split("."):
            try:
                parcaciklar.append(int(p))
            except ValueError:
                parcaciklar.append(0)
        return parcaciklar

    try:
        p1 = _parcala(v1)
        p2 = _parcala(v2)
        # Pad shorter list with zeros
        max_len = max(len(p1), len(p2))
        p1.extend([0] * (max_len - len(p1)))
        p2.extend([0] * (max_len - len(p2)))
        for a, b in zip(p1, p2):
            if a < b:
                return -1
            if a > b:
                return 1
        return 0
    except Exception:
        return 1  # Karsilastirilamazsa esit/guncel say


def _github_latest_release(owner: str, repo: str) -> Optional[dict]:
    """GitHub API'den en son release tag'ini al.

    Args:
        owner: GitHub owner/kullanici adi
        repo: GitHub repo adi

    Returns:
        {"tag_name": ..., "html_url": ..., "body": ...} veya None
    """
    import urllib.request as _ur
    import urllib.error as _ue

    url = f"{GITHUB_API_BASE}/{owner}/{repo}/releases/latest"
    logger.info("[SelfUpdate] GitHub API cagrisi: %s", url)

    try:
        req = _ur.Request(url, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ReYMeN-Agent/1.0",
        })
        with _ur.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                veri = json.loads(resp.read().decode("utf-8"))
                return {
                    "tag_name": veri.get("tag_name", ""),
                    "html_url": veri.get("html_url", ""),
                    "body": veri.get("body", ""),
                }
            else:
                logger.warning("[SelfUpdate] GitHub API yanit: %s", resp.status)
                return None
    except _ue.HTTPError as e:
        if e.code == 404:
            logger.info("[SelfUpdate] Henuz release yok (404)")
            return None
        logger.warning("[SelfUpdate] GitHub HTTP hatasi: %s", e.code)
        return None
    except Exception as e:
        logger.warning("[SelfUpdate] GitHub API hatasi: %s", e)
        return None


def _git_pull() -> dict:
    """git pull — ana branch'ten son degisiklikleri cek.

    Returns:
        {"basarili": bool, "cikti": str, "hata": str}
    """
    try:
        r = subprocess.run(
            ["git", "pull"],
            cwd=PROJE_KOK,
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return {"basarili": True, "cikti": r.stdout.strip(), "hata": ""}
        else:
            return {"basarili": False, "cikti": r.stdout.strip(), "hata": r.stderr.strip()[:500]}
    except Exception as e:
        return {"basarili": False, "cikti": "", "hata": str(e)}


def _pip_install_editable() -> dict:
    """pip install -e . — bagimliliklari guncelle.

    Returns:
        {"basarili": bool, "cikti": str, "hata": str}
    """
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(PROJE_KOK), "--quiet"],
            capture_output=True, text=True, timeout=180,
        )
        basarili = r.returncode == 0
        return {
            "basarili": basarili,
            "cikti": r.stdout.strip(),
            "hata": r.stderr.strip()[:500] if not basarili else "",
        }
    except Exception as e:
        return {"basarili": False, "cikti": "", "hata": str(e)}


def _pip_install_requirements() -> dict:
    """requirements.txt varsa pip install -r requirements.txt.

    Returns:
        {"basarili": bool, "cikti": str, "hata": str}
    """
    req_file = PROJE_KOK / "requirements.txt"
    if not req_file.exists():
        return {"basarili": True, "cikti": "requirements.txt yok, atlandi", "hata": ""}
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
            capture_output=True, text=True, timeout=180,
        )
        basarili = r.returncode == 0
        return {
            "basarili": basarili,
            "cikti": r.stdout.strip(),
            "hata": r.stderr.strip()[:500] if not basarili else "",
        }
    except Exception as e:
        return {"basarili": False, "cikti": "", "hata": str(e)}


def _son_kontrol_zamani() -> Optional[float]:
    """Son kontrol zamanini oku.

    Returns:
        Unix timestamp (float) veya None
    """
    if UPDATE_MARKER_FILE.exists():
        try:
            veri = json.loads(UPDATE_MARKER_FILE.read_text(encoding="utf-8"))
            return veri.get("son_kontrol")
        except Exception:
            pass
    return None


def _son_kontrol_kaydet() -> None:
    """Su anki zamani son kontrol olarak kaydet."""
    UPDATE_MARKER_DIR.mkdir(parents=True, exist_ok=True)
    UPDATE_MARKER_FILE.write_text(
        json.dumps({
            "son_kontrol": time.time(),
            "zaman": datetime.now(timezone.utc).isoformat(),
        }, indent=2),
        encoding="utf-8",
    )


# ── Ana Fonksiyonlar ──────────────────────────────────────────────────────


def check_for_updates() -> dict:
    """GitHub'dan son release'i kontrol et, mevcut versiyonla karsilastir.

    Returns:
        {
            "basarili": bool,
            "mevcut_versiyon": str,
            "son_versiyon": str | None,
            "son_tag": str | None,
            "release_url": str | None,
            "guncel_var": bool,  # True = yeni versiyon mevcut
            "aciklama": str,
            "hata": str | None,
            "release_body": str | None,
        }
    """
    mevcut = _mevcut_versiyon()
    sonuc = {
        "basarili": False,
        "mevcut_versiyon": mevcut,
        "son_versiyon": None,
        "son_tag": None,
        "release_url": None,
        "guncel_var": False,
        "aciklama": "",
        "hata": None,
        "release_body": None,
    }

    # GitHub remote bilgisi
    owner, repo = _git_remote_parse()

    # Son release'i sorgula
    release = _github_latest_release(owner, repo)
    if release is None:
        sonuc["aciklama"] = "GitHub release bilgisi alinamadi"
        sonuc["hata"] = "API yaniti yok veya henuz release yayinlanmamis"
        return sonuc

    son_tag = release.get("tag_name", "")
    # Tag'dan versiyon: "v2026.07.15" -> "2026.07.15"
    son_versiyon = son_tag.lstrip("v").lstrip("V")

    sonuc["son_tag"] = son_tag
    sonuc["son_versiyon"] = son_versiyon
    sonuc["release_url"] = release.get("html_url")
    sonuc["release_body"] = release.get("body")[:1000] if release.get("body") else None

    # Karsilastir
    karsilastirma = _versiyon_karsilastir(mevcut, son_versiyon)

    if karsilastirma < 0:
        sonuc["guncel_var"] = True
        sonuc["aciklama"] = f"Yeni surum mevcut: {son_tag} (mevcut: v{mevcut})"
        logger.info(
            "[SelfUpdate] Yeni surum: %s (mevcut: v%s)",
            son_tag, mevcut,
        )
    elif karsilastirma == 0:
        sonuc["aciklama"] = f"En son surum kullaniliyor: v{mevcut}"
        logger.info("[SelfUpdate] En son surum: v%s", mevcut)
    else:
        sonuc["aciklama"] = f"Mevcut surum (v{mevcut}) release'den ({son_tag}) daha yeni"
        logger.info(
            "[SelfUpdate] Mevcut surum daha yeni: v%s > %s",
            mevcut, son_tag,
        )

    sonuc["basarili"] = True
    return sonuc


def perform_update() -> dict:
    """Guncellemeyi gerceklestir: git pull + pip install.

    Returns:
        {
            "basarili": bool,
            "once": str,
            "sonra": str,
            "git": dict,
            "pip": dict,
            "req": dict,
            "aciklama": str,
            "hata": str | None,
        }
    """
    once = _mevcut_versiyon()
    sonuc = {
        "basarili": False,
        "once": once,
        "sonra": once,
        "git": {},
        "pip": {},
        "req": {},
        "aciklama": "",
        "hata": None,
    }

    logger.info("[SelfUpdate] Guncelleme baslatiliyor...")

    # 1. Git pull
    git_sonuc = _git_pull()
    sonuc["git"] = git_sonuc
    if not git_sonuc["basarili"]:
        hata = git_sonuc.get("hata", "Git pull basarisiz")
        sonuc["hata"] = hata
        sonuc["aciklama"] = f"Git pull basarisiz: {hata}"
        logger.warning("[SelfUpdate] %s", sonuc["aciklama"])
        return sonuc

    # 2. pip install -e .
    pip_sonuc = _pip_install_editable()
    sonuc["pip"] = pip_sonuc

    # 3. requirements.txt (varsa)
    req_sonuc = _pip_install_requirements()
    sonuc["req"] = req_sonuc

    # 4. Yeni versiyonu oku
    sonra = _mevcut_versiyon()
    sonuc["sonra"] = sonra

    degisti = once != sonra
    sonuc["basarili"] = True

    if degisti:
        sonuc["aciklama"] = f"Guncelleme tamam: v{once} -> v{sonra}"
        logger.info("[SelfUpdate] %s", sonuc["aciklama"])
    else:
        sonuc["aciklama"] = f"Guncelleme calisti ancak versiyon degismedi: v{once}"
        logger.info("[SelfUpdate] %s", sonuc["aciklama"])

    return sonuc


def auto_update_check(force: bool = False) -> dict:
    """Otomatik guncelleme kontrolu — haftada 1 kere calisir.

    Startup'ta cagrilir. Eger son kontrolden bu yana 7 gunden fazla
    gecmisse kontrol eder ve guncelleme varsa otomatik kurar.

    Args:
        force: True ise beklemeden kontrol et

    Returns:
        check_for_updates() sonucu veya atlama durumu
    """
    if not force:
        son_kontrol = _son_kontrol_zamani()
        if son_kontrol is not None:
            gecen = time.time() - son_kontrol
            kalan = HAFTALIK_KONTROL_ARALIGI - gecen
            if gecen < HAFTALIK_KONTROL_ARALIGI:
                logger.info(
                    "[SelfUpdate] Haftalik kontrol atlandi "
                    "(son: %ds once, kalan: %ds)",
                    int(gecen), int(kalan),
                )
                return {
                    "basarili": True,
                    "atlandi": True,
                    "aciklama": f"Haftalik kontrol atlandi "
                                f"(son kontrol: {int(gecen // 3600)}s once)",
                }

    # Kontrol yap
    _son_kontrol_kaydet()
    kontrol = check_for_updates()

    if kontrol and kontrol.get("guncel_var"):
        logger.info("[SelfUpdate] Yeni surum bulundu, otomatik guncelleniyor...")
        guncel = perform_update()
        kontrol["guncelleme"] = guncel
        kontrol["otomatik"] = True

    return kontrol


def auto_update_thread(interval: int = HAFTALIK_KONTROL_ARALIGI) -> None:
    """Background thread'te periyodik guncelleme kontrolu.

    Args:
        interval: Kac saniyede bir kontrol (varsayilan: 1 hafta)
    """
    while True:
        try:
            auto_update_check()
        except Exception as e:
            logger.warning("[SelfUpdate] Otomatik kontrol hatasi: %s", e)
        time.sleep(interval)


_auto_update_thread: Optional[threading.Thread] = None


def auto_update_baslat(interval: int = HAFTALIK_KONTROL_ARALIGI) -> None:
    """Arkaplan otomatik guncelleme thread'ini baslat.

    Args:
        interval: Kac saniyede bir kontrol (varsayilan: 1 hafta)
    """
    global _auto_update_thread
    if _auto_update_thread and _auto_update_thread.is_alive():
        return

    _auto_update_thread = threading.Thread(
        target=auto_update_thread,
        args=(interval,),
        daemon=True,
        name="reymen-self-update",
    )
    _auto_update_thread.start()
    logger.info("[SelfUpdate] ✅ Arkaplan kontrol baslatildi (her %ds)", interval)


# ── CLI Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ReYMeN Self-Update Sistemi")
    parser.add_argument("--check", action="store_true", help="GitHub'dan son release'i kontrol et")
    parser.add_argument("--auto", action="store_true", help="Otomatik guncelleme kontrolu (haftada 1)")
    parser.add_argument("--force", action="store_true", help="Auto kontrolu zorla (bekleme yapma)")
    parser.add_argument("--update", action="store_true", help="Guncellemeyi gerceklestir")
    args = parser.parse_args()

    if args.check:
        sonuc = check_for_updates()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))
    elif args.auto:
        sonuc = auto_update_check(force=args.force)
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))
    elif args.update:
        sonuc = perform_update()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
