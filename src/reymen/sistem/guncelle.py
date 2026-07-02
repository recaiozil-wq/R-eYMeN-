# -*- coding: utf-8 -*-
"""
guncelle.py — ReYMeN Akıllı Güncelleme Modülü.

Kullanım (program içinde):
    /guncelle          → kontrol et ve güncelle
    /guncelle kapat    → otomatik kontrol bildirimini kapat
    /guncelle ac       → otomatik kontrol bildirimini aç
    /guncelle durum    → ayarı göster

Doğrudan çalıştırma:
    python guncelle.py
    python guncelle.py --kapat
    python guncelle.py --ac
"""

import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

PROJE_KOKU    = Path(__file__).parent.resolve()
GITHUB_BRANCH = "main"

# ── Buraya kendi GitHub kullanıcı adını ve repo adını yaz ──────────────────
GITHUB_REPO = "KULLANICI_ADI/ReYMeN"   # örn: "markopasa/ReYMeN"
# ───────────────────────────────────────────────────────────────────────────

# Güncelleme sırasında ASLA dokunulmayacak kişisel dosyalar
KORUNACAK = {
    ".env",
    ".ReYMeN/session.db",  # -> merkez_db/session_reymen.db
    ".ReYMeN/memories",
    ".ReYMeN/self_improvement.json",
    ".ReYMeN/cron/jobs.json",
    ".ReYMeN/session.db",  # -> merkez_db/session_reymen.db
    ".ReYMeN/memories",
}

AYAR_DOSYASI = PROJE_KOKU / ".ReYMeN" / "guncelleme.json"

_ARKA_PLAN_SONUC: dict = {}


# ── Ayar yönetimi ─────────────────────────────────────────────────────────

def ayar_oku() -> dict:
    varsayilan = {"otomatik_kontrol": True, "gosterilen_sha": ""}
    try:
        if AYAR_DOSYASI.exists():
            return {**varsayilan, **json.loads(AYAR_DOSYASI.read_text(encoding="utf-8"))}
    except Exception as _guncelle_e54:
        print(f"[UYARI] guncelle.py:55 - {_guncelle_e54}")
    return varsayilan


def ayar_kaydet(ayar: dict):
    AYAR_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    AYAR_DOSYASI.write_text(json.dumps(ayar, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Commit kontrol ────────────────────────────────────────────────────────

def _yerel_commit() -> str | None:
    try:
        ref = PROJE_KOKU / ".git" / "refs" / "heads" / GITHUB_BRANCH
        if ref.exists():
            return ref.read_text(encoding="utf-8").strip()[:7]
        head = PROJE_KOKU / ".git" / "HEAD"
        if head.exists():
            ic = head.read_text(encoding="utf-8").strip()
            if not ic.startswith("ref:"):
                return ic[:7]
    except OSError as _guncelle_e76:
        print(f"[UYARI] guncelle.py:77 - {_guncelle_e76}")
    return None


def _uzak_commit() -> str | None:
    if "KULLANICI_ADI" in GITHUB_REPO:
        return None
    try:
        import urllib.request
        url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
        istek = urllib.request.Request(url, headers={"User-Agent": "ReYMeN-updater"})
        with urllib.request.urlopen(istek, timeout=6) as r:
            return json.loads(r.read().decode())["sha"][:7]
    except Exception:
        return None


def guncelleme_var_mi() -> tuple[bool, str | None, str | None]:
    yerel = _yerel_commit()
    uzak  = _uzak_commit()
    if yerel and uzak:
        return yerel != uzak, uzak, yerel
    return False, uzak, yerel


# ── Değişen dosyaları listele ─────────────────────────────────────────────

def _degisen_dosyalar() -> dict:
    """git diff ile güncelleme öncesi nelerin değişeceğini göster."""
    sonuc = {"py": [], "skill": [], "diger": [], "korunan": []}
    try:
        # Uzak repo'dan fetch et
        subprocess.run(
            ["git", "fetch", "origin", GITHUB_BRANCH],
            capture_output=True, cwd=str(PROJE_KOKU), timeout=15,
        )
        r = subprocess.run(
            ["git", "diff", f"HEAD..origin/{GITHUB_BRANCH}", "--name-only"],
            capture_output=True, text=True, cwd=str(PROJE_KOKU), timeout=10,
        )
        for dosya in r.stdout.strip().splitlines():
            dosya = dosya.strip()
            if not dosya:
                continue
            # Korunacak mı?
            koruma = any(
                dosya == k or dosya.startswith(k + "/") or dosya.startswith(k)
                for k in KORUNACAK
            )
            if koruma:
                sonuc["korunan"].append(dosya)
            elif dosya.endswith(".py"):
                sonuc["py"].append(dosya)
            elif ".ReYMeN/skills" in dosya or "SKILL.md" in dosya:
                sonuc["skill"].append(dosya)
            else:
                sonuc["diger"].append(dosya)
    except Exception as _guncelle_e134:
        print(f"[UYARI] guncelle.py:135 - {_guncelle_e134}")
    return sonuc


# ── Güncelleme ────────────────────────────────────────────────────────────

def _git_pull() -> tuple[bool, str]:
    try:
        sonuc = subprocess.run(
            ["git", "pull", "origin", GITHUB_BRANCH],
            capture_output=True, text=True,
            cwd=str(PROJE_KOKU), timeout=60,
        )
        cikti = (sonuc.stdout + sonuc.stderr).strip()
        return sonuc.returncode == 0, cikti
    except FileNotFoundError:
        return False, "git bulunamadı"
    except subprocess.TimeoutExpired:
        return False, "Zaman aşımı"
    except Exception as e:
        return False, str(e)


def _zip_ile_guncelle() -> tuple[bool, str]:
    """Git olmayan kullanıcılar için — kişisel dosyaları atlar."""
    if "KULLANICI_ADI" in GITHUB_REPO:
        return False, "GITHUB_REPO ayarlanmamış."
    try:
        import urllib.request, zipfile, tempfile

        url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
        print("  Arşiv indiriliyor...")
        with urllib.request.urlopen(url, timeout=120) as r:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(r.read())
                tmp_yol = Path(tmp.name)

        repo_adi = f"{GITHUB_REPO.split('/')[-1]}-{GITHUB_BRANCH}"
        guncellenen = 0

        with zipfile.ZipFile(tmp_yol, "r") as zf:
            for uye in zf.namelist():
                if not uye.startswith(f"{repo_adi}/"):
                    continue
                hedef_yol = uye[len(repo_adi) + 1:]
                if not hedef_yol:
                    continue

                # Korunacak dosyaları atla
                koruma = any(
                    hedef_yol == k or hedef_yol.startswith(k + "/") or hedef_yol.startswith(k)
                    for k in KORUNACAK
                )
                if koruma:
                    continue

                # Sadece .py ve skill dosyaları
                if not (hedef_yol.endswith(".py") or "skills" in hedef_yol
                        or hedef_yol.endswith(".md") or hedef_yol.endswith(".json")):
                    if hedef_yol.endswith(".txt") or hedef_yol.endswith(".yaml"):
                        pass
                    else:
                        continue

                hedef = PROJE_KOKU / hedef_yol
                hedef.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(uye) as k, open(hedef, "wb") as h:
                    h.write(k.read())
                guncellenen += 1

        tmp_yol.unlink(missing_ok=True)
        return True, f"{guncellenen} dosya güncellendi (zip yöntemi)."
    except Exception as e:
        return False, f"Zip güncellemesi başarısız: {e}"


def guncelle(onaysiz: bool = False) -> bool:
    """
    Güncelleme yap. Önce değişenleri göster, sonra onay iste.

    Returns:
        True → güncellendi / False → iptal veya hata
    """
    print()
    var_mi, uzak, yerel = guncelleme_var_mi()

    if not var_mi and uzak is not None:
        print(f"  Zaten güncel ({yerel}).")
        return False

    if uzak:
        print(f"  Mevcut sürüm : {yerel or '(git yok)'}")
        print(f"  Yeni sürüm   : {uzak}")

    # Git varsa nelerin değişeceğini göster
    git_dir = PROJE_KOKU / ".git"
    if git_dir.exists():
        degisen = _degisen_dosyalar()
        print()
        if degisen["py"]:
            print(f"  Güncellenecek  : {len(degisen['py'])} Python dosyası")
        if degisen["skill"]:
            print(f"  Yeni/güncellen.: {len(degisen['skill'])} skill")
        if degisen["diger"]:
            print(f"  Diğer          : {len(degisen['diger'])} dosya")
        if degisen["korunan"]:
            print(f"  Korunacak      : {len(degisen['korunan'])} kişisel dosya (.env, hafıza vb.)")

    print()

    if not onaysiz:
        print("  [e] Güncelle    [h] Bu sefer atla    [kapat] Bir daha sorma")
        yanit = input("  Seçim: ").strip().lower()
        if yanit == "kapat":
            otomatik_kapat()
            return False
        if yanit != "e":
            print("  Atlandı.")
            return False

    if git_dir.exists():
        print("  git pull yapılıyor...")
        basari, cikti = _git_pull()
    else:
        print("  Zip yöntemiyle güncelleniyor...")
        basari, cikti = _zip_ile_guncelle()

    if basari:
        print(f"  ✓ {cikti}")
        print("\n  Güncelleme tamamlandı! Programı yeniden başlatın.")
        # SHA'yı "gösterildi" olarak kaydet
        ayar = ayar_oku()
        ayar["gosterilen_sha"] = uzak or ""
        ayar_kaydet(ayar)
    else:
        print(f"  ✗ Hata: {cikti}")
    return basari


# ── Açma / Kapatma ────────────────────────────────────────────────────────

def otomatik_ac():
    """Otomatik güncelleme bildirimini aç."""
    ayar = ayar_oku()
    ayar["otomatik_kontrol"] = True
    ayar["gosterilen_sha"] = ""   # Bildirimi sıfırla
    ayar_kaydet(ayar)
    print("  ✓ Otomatik güncelleme kontrolü açıldı.")


def otomatik_kapat():
    """Otomatik güncelleme bildirimini kapat."""
    ayar = ayar_oku()
    ayar["otomatik_kontrol"] = False
    ayar_kaydet(ayar)
    print("  Otomatik güncelleme kapatıldı.")
    print("  Tekrar açmak için: /guncelle ac")


def durum_goster():
    """Güncelleme ayarını ve son durumu göster."""
    ayar = ayar_oku()
    aktif = "Açık" if ayar.get("otomatik_kontrol", True) else "Kapalı"
    print(f"  Otomatik kontrol : {aktif}")
    print(f"  GitHub repo      : {GITHUB_REPO}")
    yerel = _yerel_commit()
    print(f"  Yerel sürüm      : {yerel or '(git repo değil)'}")


# ── Arka plan kontrolü ────────────────────────────────────────────────────

def _arka_plan_kontrol():
    try:
        ayar = ayar_oku()
        if not ayar.get("otomatik_kontrol", True):
            return
        var_mi, uzak, yerel = guncelleme_var_mi()
        _ARKA_PLAN_SONUC["var_mi"]  = var_mi
        _ARKA_PLAN_SONUC["uzak"]    = uzak
        _ARKA_PLAN_SONUC["yerel"]   = yerel
        _ARKA_PLAN_SONUC["gosterilen"] = ayar.get("gosterilen_sha", "")
    except Exception:
        _ARKA_PLAN_SONUC["var_mi"] = False


def arka_plan_baslat():
    """Startup'ta çağır — arka planda kontrol başlatır, kullanıcıyı bekletmez."""
    if "KULLANICI_ADI" in GITHUB_REPO:
        return
    t = threading.Thread(target=_arka_plan_kontrol, daemon=True)
    t.start()


def guncelleme_bildirimi() -> str | None:
    """
    Arka plan sonucu hazırsa ve yeni bir SHA ise bildirim döndür.
    main.py döngüsünde her turda çağrılır, bir kez gösterir.
    """
    if not _ARKA_PLAN_SONUC.get("var_mi"):
        return None
    uzak      = _ARKA_PLAN_SONUC.get("uzak", "?")
    yerel     = _ARKA_PLAN_SONUC.get("yerel", "?")
    gosterilen = _ARKA_PLAN_SONUC.get("gosterilen", "")

    # Aynı sürüm için tekrar gösterme
    if uzak == gosterilen:
        return None

    return (
        f"\n  ╔══════════════════════════════════════╗\n"
        f"  ║  Yeni sürüm mevcut: {yerel} → {uzak}  ║\n"
        f"  ║  Skill ve kod güncellemesi var.       ║\n"
        f"  ╚══════════════════════════════════════╝\n"
        f"  '/guncelle' → güncelle\n"
        f"  '/guncelle kapat' → bir daha sorma\n"
    )


# ── /guncelle komut yönlendirici ──────────────────────────────────────────

def komut_isle(args: str = "") -> bool:
    """
    main.py'den '/guncelle [args]' şeklinde çağrılır.

    Args:
        args: "kapat", "ac", "durum" veya "" (güncelle)

    Returns:
        True → program yeniden başlatılmalı
    """
    args = args.strip().lower()

    if args == "kapat":
        otomatik_kapat()
        return False

    if args == "ac":
        otomatik_ac()
        return False

    if args == "durum":
        durum_goster()
        return False

    # Varsayılan: güncelle
    return guncelle(onaysiz=False)


# ── Doğrudan çalıştırma ───────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--kapat" in args:
        otomatik_kapat()
        sys.exit(0)

    if "--ac" in args:
        otomatik_ac()
        sys.exit(0)

    if "--durum" in args:
        durum_goster()
        sys.exit(0)

    print("=== ReYMeN Güncelleme Aracı ===")
    print(f"Repo  : {GITHUB_REPO}")
    print(f"Yerel : {_yerel_commit() or '(git repo değil)'}")

    if "KULLANICI_ADI" in GITHUB_REPO:
        print("\n[!] guncelle.py içindeki GITHUB_REPO değişkenini ayarla.")
        print("    Örnek: GITHUB_REPO = \"markopasa/ReYMeN\"")
        sys.exit(1)

    guncelle(onaysiz=False)
