# -*- coding: utf-8 -*-
"""skill_utils.py — Skill Yardimci Fonksiyonlar v4.

v4 yenilikleri (agentskills.io derin analiz):
- .agents/skills/ dizin destegi (resmi standart dizin yolu)
- uv run / PEP 723 inline dep destegi (skill scriptleri icin)
- skill_script_yardim(): script --help ciktisi
- Eval sistemi: skill_eval_al(), skill_eval_ekle() (evals/evals.json)
- skill_aktivat() evals/ dizinini de gosterir
- skill_dogrula(): "Use when" imperatif kontrol, aciklama kalite skoru
- skill_olustur(): otomatik "kullan" ipucu ve eval dizin iskeleti

v3 yenilikleri (agentskills.io spec ile uyumlu):
- FTS5 SQLite index: 1041+ skill'de hizli arama (O(1) vs O(n*file))
- allowed-tools destegi
- skill_dogrula(): spec dogrulama
- Agirlikli arama: description match (3x) > name (2x) > body (1x)
"""

import json
import logging
import os
import re
import shutil
import sqlite3

logger = logging.getLogger(__name__)
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.resolve()

# Tum skill kaynak klasorleri (oncelik sirasinda)
# NOT: .agents/skills/ resmi agentskills.io standart dizini (VS Code, Copilot, vb. burada arar)
SKILLS_KLASORLERI = [
    ROOT / "skills",              # Ana ReYMeN skill deposu (1041+)
    ROOT / ".ReYMeN" / "skills", # Kullanici kristallestirilen skilllar
    ROOT / ".agents" / "skills", # Resmi agentskills.io standart dizini
]

# Geriye donuk uyumluluk
SKILLS_KLASOR = SKILLS_KLASORLERI[1]

# FTS5 index dosyasi
_INDEX_DB = ROOT / ".ReYMeN" / "skill_index.db"

# Spec limitleri (agentskills.io)
_MAKS_AD_UZUNLUGU = 64
_MAKS_ACIKLAMA_UZUNLUGU = 1024
_MAKS_UYUMLULUK_UZUNLUGU = 500
_ONERI_MAKS_SATIR = 500
_ONERI_MAKS_TOKEN = 5000


# ── YAML frontmatter parser (PyYAML gerekmez) ────────────────────────────────

def _frontmatter_parse(icerik: str) -> dict:
    """SKILL.md'nin YAML frontmatter'ini sozluge cevir.

    Sadece stdlib ile calisir. Desteklenen: string, liste ([a, b, c]).
    """
    meta = {}
    icerik_norm = icerik.replace("\r\n", "\n")
    if not icerik_norm.startswith("---"):
        return meta
    bitis = icerik_norm.find("\n---", 3)
    if bitis == -1:
        return meta
    blok = icerik_norm[3:bitis].strip()
    for satir in blok.split("\n"):
        if ":" not in satir or satir.startswith(" ") or satir.startswith("\t"):
            continue
        anahtar, deger = satir.split(":", 1)
        anahtar = anahtar.strip()
        deger = deger.strip().strip('"\'')
        if deger.startswith("[") and deger.endswith("]"):
            ic = deger[1:-1]
            deger = [x.strip().strip('"\'') for x in ic.split(",") if x.strip()]
        meta[anahtar] = deger
    return meta


def _tum_skill_dosyalari():
    """Tum klasorlerden SKILL.md dosyalarini yield et (tekrar olmadan)."""
    goruldu = set()
    for klasor in SKILLS_KLASORLERI:
        if not klasor.exists():
            continue
        for dosya in sorted(klasor.rglob("SKILL.md")):
            anahtar = dosya.parent.name
            if anahtar not in goruldu:
                goruldu.add(anahtar)
                yield dosya


# ── FTS5 SQLite Index ─────────────────────────────────────────────────────────

def _index_db_ac() -> sqlite3.Connection:
    """FTS5 index veritabanini ac (yoksa olustur)."""
    _INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_INDEX_DB))
    con.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS skill_fts
        USING fts5(
            ad, kategori, baslik, aciklama, etiketler,
            uyumluluk, izin_araclar, govde,
            content='', tokenize='unicode61 remove_diacritics 1'
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS skill_meta (
            ad TEXT PRIMARY KEY,
            yol TEXT,
            satir_sayisi INTEGER,
            guncelleme INTEGER
        )
    """)
    con.commit()
    return con


def skill_index_yenile(zorla: bool = False) -> int:
    """FTS5 indexi tum skill'lerden yeniden olustur.

    Args:
        zorla: True ise degisiklik kontrolu yapmadan tum skill'leri yeniden ekle.

    Returns:
        Eklenen/guncellenen skill sayisi.
    """
    con = _index_db_ac()
    try:
        guncellenen = 0
        for dosya in _tum_skill_dosyalari():
            ad = dosya.parent.name
            mtime = int(dosya.stat().st_mtime)
            # Degismemisse atla
            if not zorla:
                row = con.execute(
                    "SELECT guncelleme FROM skill_meta WHERE ad=?", (ad,)
                ).fetchone()
                if row and row[0] == mtime:
                    continue
            try:
                icerik = dosya.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            meta = _frontmatter_parse(icerik)
            ust = dosya.parent.parent
            kat = "genel"
            for klas in SKILLS_KLASORLERI:
                if ust != klas:
                    kat = ust.name
                    break
            baslik = str(meta.get("title") or meta.get("name") or ad).strip('"\'')
            aciklama = str(meta.get("description", "")).strip('"\'')[:_MAKS_ACIKLAMA_UZUNLUGU]
            etiketler_ham = meta.get("tags", [])
            if isinstance(etiketler_ham, list):
                etiketler = " ".join(etiketler_ham)
            else:
                etiketler = str(etiketler_ham)
            uyumluluk = str(meta.get("compatibility", "")).strip()
            izin_araclar = str(meta.get("allowed-tools", "")).strip()
            # Govde: frontmatter sonrasi markdown icerigi (token tasarrufu icin kisalt)
            govde = icerik[icerik.find("\n---\n", 3) + 5:] if "\n---\n" in icerik else icerik
            govde = govde[:3000]
            satir_sayisi = icerik.count("\n")
            # Var olani sil, yenisini ekle
            con.execute("DELETE FROM skill_fts WHERE ad=?", (ad,))
            con.execute(
                "INSERT INTO skill_fts(ad, kategori, baslik, aciklama, etiketler, "
                "uyumluluk, izin_araclar, govde) VALUES(?,?,?,?,?,?,?,?)",
                (ad, kat, baslik, aciklama, etiketler, uyumluluk, izin_araclar, govde),
            )
            con.execute(
                "INSERT OR REPLACE INTO skill_meta(ad, yol, satir_sayisi, guncelleme) "
                "VALUES(?,?,?,?)",
                (ad, str(dosya), satir_sayisi, mtime),
            )
            guncellenen += 1
        con.commit()
        return guncellenen
    finally:
        con.close()


def _index_gecerli_mi() -> bool:
    """Index DB'nin var olup olmadigini kontrol et."""
    return _INDEX_DB.exists() and _INDEX_DB.stat().st_size > 0


def skill_fts_ara(sorgu: str, limit: int = 10) -> list:
    """FTS5 ile hizli skill ara. Index yoksa dosya taramaya dusar.

    Agirlikli puan: aciklama/baslik match > ad match > govde match.

    Returns:
        [{ad, kategori, aciklama, yol, puan}, ...] listesi (puanla sirali)
    """
    if not _index_gecerli_mi():
        skill_index_yenile()

    sorgu_kucuk = sorgu.lower().strip()
    if not sorgu_kucuk:
        return []

    # FTS5 sorgusu: tirmnak isaretleri ve ozel karakterleri temizle
    fts_sorgu = re.sub(r'[^a-z0-9 _-]', '', sorgu_kucuk).strip()
    if not fts_sorgu:
        fts_sorgu = sorgu_kucuk

    con = _index_db_ac()
    try:
        sonuclar = []
        # Tam eslesen sorgular + prefix search
        for q in [f'"{fts_sorgu}"', fts_sorgu + "*", fts_sorgu]:
            try:
                rows = con.execute(
                    "SELECT ad, kategori, aciklama, rank FROM skill_fts(?) "
                    "ORDER BY rank LIMIT ?",
                    (q, limit * 3),
                ).fetchall()
                if rows:
                    break
            except sqlite3.OperationalError:
                rows = []

        goruldu = set()
        for ad, kat, aciklama, rank in rows:
            if ad in goruldu:
                continue
            goruldu.add(ad)
            # Agirlikli manuel puan (FTS rank negatif, dusuk = iyi)
            puan = abs(rank)
            # Ek agirlik: aciklama veya adi icinde sorgu varsa daha yukari
            if sorgu_kucuk in (aciklama or "").lower():
                puan += 3.0
            if sorgu_kucuk in ad.lower():
                puan += 2.0
            # yol bul
            row2 = con.execute(
                "SELECT yol FROM skill_meta WHERE ad=?", (ad,)
            ).fetchone()
            yol = row2[0] if row2 else ""
            sonuclar.append({
                "ad": ad, "kategori": kat,
                "aciklama": (aciklama or "")[:120],
                "yol": yol, "puan": puan,
            })
        # Puanla sirala (yuksek puan = daha iyi)
        sonuclar.sort(key=lambda x: x["puan"], reverse=True)
        return sonuclar[:limit]
    finally:
        con.close()


# ── Temel okuma / bulma ───────────────────────────────────────────────────────

def skill_bul(ad: str) -> Optional[Path]:
    """Skill adina gore SKILL.md yolunu bul (her iki klasorde arar)."""
    for klasor in SKILLS_KLASORLERI:
        if not klasor.exists():
            continue
        dogrudan = klasor / ad / "SKILL.md"
        if dogrudan.exists():
            return dogrudan
        for dosya in klasor.rglob(f"{ad}/SKILL.md"):
            return dosya
    return None


def skill_oku(ad: str) -> Optional[str]:
    """SKILL.md icerigini ham metin olarak dondur."""
    dosya = skill_bul(ad)
    if dosya:
        try:
            return dosya.read_text(encoding="utf-8", errors="replace")
        except Exception as _e:
            logger.warning("[Skill oku] %s: %s", dosya.name, _e)
    return None


def skill_meta(ad: str) -> dict:
    """Skill'in YAML frontmatter metadata sozlugunu dondur."""
    icerik = skill_oku(ad)
    if not icerik:
        return {}
    return _frontmatter_parse(icerik)


def skill_baslik_al(ad: str) -> str:
    """Skill basligini dondur (title -> name -> klasor adi)."""
    meta = skill_meta(ad)
    return (meta.get("title") or meta.get("name") or ad).strip('"\'')


def skill_aciklama_al(ad: str) -> str:
    """Skill'in description alanini dondur."""
    meta = skill_meta(ad)
    return str(meta.get("description", "")).strip('"\'')


def skill_etiketleri_al(ad: str) -> list:
    """Skill'in tags listesini dondur."""
    meta = skill_meta(ad)
    etiketler = meta.get("tags", [])
    if isinstance(etiketler, str):
        etiketler = [e.strip() for e in etiketler.strip("[]").split(",") if e.strip()]
    return etiketler


def skill_kategori_al(ad: str) -> str:
    """Skill'in kategorisini dondur (frontmatter veya ust klasor adi)."""
    meta = skill_meta(ad)
    if meta.get("category"):
        return str(meta["category"])
    dosya = skill_bul(ad)
    if dosya and dosya.parent.parent.name not in ("skills", ".ReYMeN"):
        return dosya.parent.parent.name
    return "genel"


def skill_izin_verilen_araclar(ad: str) -> list:
    """Skill'in allowed-tools alanini liste olarak dondur.

    Ornek SKILL.md: allowed-tools: Bash(git:*) WEB_ARA DOSYA_OKU
    Dondurulen liste: ['Bash(git:*)', 'WEB_ARA', 'DOSYA_OKU']
    """
    meta = skill_meta(ad)
    val = meta.get("allowed-tools", "")
    if isinstance(val, list):
        return val
    return [t.strip() for t in str(val).split() if t.strip()]


def skill_uyumluluk_al(ad: str) -> str:
    """Skill'in compatibility alanini dondur."""
    meta = skill_meta(ad)
    return str(meta.get("compatibility", "")).strip()


def skill_guncelle(ad: str, yeni_icerik: str) -> bool:
    """Skill icerigini guncelle (sadece .ReYMeN/skills/ yazilabilir)."""
    dosya = skill_bul(ad)
    if not dosya:
        return False
    try:
        dosya.write_text(yeni_icerik, encoding="utf-8")
        return True
    except Exception:
        return False


# ── Sayim ve listeleme ────────────────────────────────────────────────────────

def skill_sayisi() -> int:
    """Tum klasorlerdeki toplam benzersiz SKILL.md sayisi."""
    return sum(1 for _ in _tum_skill_dosyalari())


def kategorileri_listele() -> list:
    """Tum benzersiz kategorileri alfabetik sirali dondur."""
    kategoriler = set()
    for dosya in _tum_skill_dosyalari():
        ust = dosya.parent.parent
        for klas in SKILLS_KLASORLERI:
            if ust == klas:
                kategoriler.add("genel")
                break
        else:
            kategoriler.add(ust.name)
    return sorted(kategoriler)


def kategori_skill_listele(kategori: str, limit: int = 20) -> list:
    """Belirli kategorideki skill adlarini dondur."""
    sonuclar = []
    for klasor in SKILLS_KLASORLERI:
        kat_yol = klasor / kategori
        if not kat_yol.exists():
            continue
        for skill_klas in sorted(kat_yol.iterdir()):
            if len(sonuclar) >= limit:
                break
            skill_md = skill_klas / "SKILL.md"
            if skill_md.exists():
                try:
                    icerik = skill_md.read_text(encoding="utf-8", errors="replace")
                    meta = _frontmatter_parse(icerik)
                    sonuclar.append({
                        "ad": skill_klas.name,
                        "aciklama": str(meta.get("description", ""))[:120],
                        "yol": str(skill_md),
                    })
                except Exception as _e:
                    logger.warning("[Skill liste] %s: %s", skill_md.name if skill_md else "?", _e)
    return sonuclar


# ── Arama ────────────────────────────────────────────────────────────────────

def skill_ara(sorgu: str, limit: int = 10) -> list:
    """Skill ara — FTS5 ile hizli, yoksa dosya taramasi.

    Returns:
        [{ad, kategori, aciklama, yol}, ...] listesi
    """
    # FTS5 dene
    if _index_gecerli_mi():
        try:
            return skill_fts_ara(sorgu, limit)
        except Exception as _e:
            logger.warning("[Skill FTS5] %s: %s", sorgu[:30], _e)

    # Fallback: dosya taramasi (agirlikli puan)
    sorgu_kucuk = sorgu.lower()
    eslesen = []
    for dosya in _tum_skill_dosyalari():
        if len(eslesen) >= limit:
            break
        try:
            icerik = dosya.read_text(encoding="utf-8", errors="replace")
            if sorgu_kucuk not in icerik.lower():
                continue
            meta = _frontmatter_parse(icerik)
            ust = dosya.parent.parent
            kat = "genel"
            for klas in SKILLS_KLASORLERI:
                if ust != klas:
                    kat = ust.name
                    break
            aciklama = str(meta.get("description", ""))[:120]
            ad = dosya.parent.name
            puan = 0.0
            if sorgu_kucuk in aciklama.lower():
                puan += 3.0
            if sorgu_kucuk in ad.lower():
                puan += 2.0
            puan += 1.0  # govde match
            eslesen.append({
                "ad": ad, "kategori": kat,
                "aciklama": aciklama, "yol": str(dosya), "puan": puan,
            })
        except Exception as _e:
            logger.warning("[Skill dosya tara] %s: %s", dosya.name if dosya else "?", _e)
    eslesen.sort(key=lambda x: x.get("puan", 0), reverse=True)
    return eslesen


# ── Progressive Disclosure: Aktivasyon ───────────────────────────────────────

def skill_aktivat(ad: str) -> str:
    """Skill'i aktive et — tam SKILL.md + scripts/references listesi + uyumluluk uyarisi.

    Returns:
        Formatlı skill icerigi veya hata mesaji.
    """
    dosya = skill_bul(ad)
    if not dosya:
        # Fuzzy: adi kismi eslestirme
        olasılar = skill_ara(ad, limit=3)
        if olasılar:
            oneriler = ", ".join(s["ad"] for s in olasılar)
            return f"[Skill]: '{ad}' bulunamadi. Benzer: {oneriler}"
        return f"[Skill]: '{ad}' bulunamadi. SKILL_ARA ile ara."

    try:
        icerik = dosya.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[Skill Hata]: {e}"

    meta = _frontmatter_parse(icerik)
    baslik = str(meta.get("title") or meta.get("name") or ad).strip('"\'')

    # Uyumluluk uyarisi
    uyumluluk = str(meta.get("compatibility", "")).strip()
    uyum_blogu = ""
    if uyumluluk:
        uyum_blogu = f"\n[Uyumluluk]: {uyumluluk}"

    # allowed-tools bildirimi
    izin_araclar = skill_izin_verilen_araclar(ad)
    arac_blogu = ""
    if izin_araclar:
        arac_blogu = f"\n[Izin verilen araclar]: {', '.join(izin_araclar)}"

    # scripts/ listesi
    scripts_dizin = dosya.parent / "scripts"
    scripts_listesi = ""
    if scripts_dizin.exists():
        scriptler = sorted(scripts_dizin.iterdir())
        if scriptler:
            script_adlari = ", ".join(s.name for s in scriptler[:10])
            scripts_listesi = f"\n[Skill Scripts]: {script_adlari}"

    # references/ listesi
    ref_dizin = dosya.parent / "references"
    ref_listesi = ""
    if ref_dizin.exists():
        refler = sorted(ref_dizin.iterdir())
        if refler:
            ref_adlari = ", ".join(r.name for r in refler[:10])
            ref_listesi = f"\n[Skill References]: {ref_adlari}"

    # evals/ bilgisi (agentskills.io eval standardı)
    eval_bilgisi = ""
    eval_dizin = dosya.parent / "evals"
    if eval_dizin.exists():
        eval_dosya = eval_dizin / "evals.json"
        if eval_dosya.exists():
            try:
                veri = json.loads(eval_dosya.read_text(encoding="utf-8"))
                eval_sayisi = len(veri.get("evals", []))
                eval_bilgisi = f"\n[Skill Evals]: {eval_sayisi} test case — SKILL_EVAL_LISTELE ile goru"
            except Exception:
                eval_bilgisi = "\n[Skill Evals]: evals/ dizini mevcut"

    # Boyut uyarisi
    satir_sayisi = icerik.count("\n")
    boyut_uyan = ""
    if satir_sayisi > _ONERI_MAKS_SATIR:
        boyut_uyan = f"\n[Uyari]: Bu skill {satir_sayisi} satir (onerilenden fazla). references/ dosyalarina bakin."

    return (
        f"=== SKILL: {baslik} ==={uyum_blogu}{arac_blogu}\n"
        f"{icerik[:4000]}"
        + (f"\n...[{len(icerik)} karakter, ilk 4000 gosterildi]" if len(icerik) > 4000 else "")
        + scripts_listesi
        + ref_listesi
        + eval_bilgisi
        + boyut_uyan
    )


# ── Skill Dogrulama (agentskills.io spec) ────────────────────────────────────

def skill_dogrula(ad: str) -> str:
    """Skill'i agentskills.io spec kurallarina gore dogrula.

    Kontroller:
    - name: max 64 karakter, kucuk harf + rakam + tire, bas/son tire yok,
            ardisik tire yok, klasor adiyla eslesme
    - description: bos olmamali, max 1024 karakter,
                   'ne zaman kullanilacagi' ipucu var mi
    - compatibility: max 500 karakter
    - Dosya boyutu: 500 satirdan az olmali (tavsiye)
    - allowed-tools: eger varsa bos olmamali

    Returns:
        Dogrulama raporu (gecti/uyari/hata).
    """
    hatalar = []
    uyarilar = []
    dosya = skill_bul(ad)

    if not dosya:
        return f"[Skill Dogrula]: '{ad}' bulunamadi."

    icerik = dosya.read_text(encoding="utf-8", errors="replace")
    meta = _frontmatter_parse(icerik)
    klasor_adi = dosya.parent.name

    # name kurallari
    name_val = str(meta.get("name", "")).strip('"\'')
    if not name_val:
        hatalar.append("'name' alani eksik.")
    else:
        if len(name_val) > _MAKS_AD_UZUNLUGU:
            hatalar.append(f"'name' {len(name_val)} karakter (max {_MAKS_AD_UZUNLUGU}).")
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]', name_val):
            hatalar.append(f"'name' gecersiz karakter iceriyor: '{name_val}'. Sadece a-z, 0-9, - izinli.")
        if "--" in name_val:
            hatalar.append("'name' ardisik tire iceriyor (--).")
        if name_val != klasor_adi:
            uyarilar.append(f"'name' ({name_val}) klasor adiyla ({klasor_adi}) uyusmuyor.")

    # description kurallari
    desc_val = str(meta.get("description", "")).strip('"\'')
    if not desc_val:
        hatalar.append("'description' alani eksik veya bos.")
    else:
        if len(desc_val) > _MAKS_ACIKLAMA_UZUNLUGU:
            hatalar.append(f"'description' {len(desc_val)} karakter (max {_MAKS_ACIKLAMA_UZUNLUGU}).")
        # "Ne zaman kullanilacagi" kontrol — imperatif yapı (Use when / ne zaman / kullan)
        zaman_ipuclari = [
            "use when", "use this when", "when ", "ne zaman", "kullan",
            "icin kullan", "uygulanir", "gerektiginde", "durumunda",
            "use for", "kullanici", "istendiginde",
        ]
        if not any(ipucu in desc_val.lower() for ipucu in zaman_ipuclari):
            uyarilar.append(
                "'description' tetikleyici ifade icermiyor. "
                "Agentskills.io onerir: 'Use when ...' veya '... icin kullan.' "
                "Ornek: 'PDF analizi yapar. Kullanici PDF islemek istediginde kullan.'"
            )
        # Cok kisa aciklama
        if len(desc_val) < 30:
            uyarilar.append(
                f"'description' cok kisa ({len(desc_val)} karakter). "
                "Ne yaptigini VE ne zaman kullanilacagini aciklayan bir paragraf ekle."
            )
        # Generik/anlamsiz aciklama tespiti
        generik_kaliplar = [
            r"^helps? with\b", r"^a skill (that|for)\b", r"^this skill\b",
            r"^provides?\b", r"^handles?\b",
        ]
        if any(re.match(p, desc_val.lower().strip()) for p in generik_kaliplar):
            uyarilar.append(
                "'description' generik bir giris ile basliyor ('helps with', 'a skill that', vb.). "
                "Dogrudan ne yaptigini belirtin."
            )

    # compatibility kontrol
    uyum = str(meta.get("compatibility", "")).strip()
    if uyum and len(uyum) > _MAKS_UYUMLULUK_UZUNLUGU:
        hatalar.append(f"'compatibility' {len(uyum)} karakter (max {_MAKS_UYUMLULUK_UZUNLUGU}).")

    # Dosya boyutu
    satir_sayisi = icerik.count("\n")
    if satir_sayisi > _ONERI_MAKS_SATIR:
        uyarilar.append(
            f"Skill {satir_sayisi} satir (tavsiye: {_ONERI_MAKS_SATIR} alti). "
            "Uzun referans materyali references/ klasorune tasinin."
        )

    # Sonuc raporu
    satirlar = [f"=== SKILL DOGRULAMA: {klasor_adi} ==="]
    if hatalar:
        satirlar.append(f"HATA ({len(hatalar)}):")
        for h in hatalar:
            satirlar.append(f"  [X] {h}")
    if uyarilar:
        satirlar.append(f"UYARI ({len(uyarilar)}):")
        for u in uyarilar:
            satirlar.append(f"  [!] {u}")
    if not hatalar and not uyarilar:
        satirlar.append("[OK] Tum kontroller gecildi. Skill spec uyumlu.")
    elif not hatalar:
        satirlar.append("[OK] Kritik hata yok. Uyarilari gidermeniz onerilir.")

    return "\n".join(satirlar)


# ── Skill Olusturma (spec uyumlu) ─────────────────────────────────────────────

def _ad_dogrula(ad: str) -> tuple:
    """Skill adinin spec kurallarina uyup uymadigini kontrol et.

    Returns:
        (gecerli: bool, hata_mesaji: str)
    """
    if not ad:
        return False, "Ad bos olamaz."
    if len(ad) > _MAKS_AD_UZUNLUGU:
        return False, f"Ad max {_MAKS_AD_UZUNLUGU} karakter olabilir."
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]', ad):
        return False, "Sadece kucuk harf (a-z), rakam (0-9) ve tire (-) kullanilabilir."
    if "--" in ad:
        return False, "Ardisik tire (--) kullanilamaz."
    return True, ""


def skill_olustur(
    ad: str,
    aciklama: str,
    talimatlar: str,
    kategori: str = "",
    lisans: str = "MIT",
    uyumluluk: str = "",
    izin_araclar: str = "",
) -> str:
    """Spec uyumlu yeni skill olustur .ReYMeN/skills/ altinda.

    Args:
        ad:           Skill adi (kucuk harf, tire, rakam — spec kurallari uygulanir)
        aciklama:     Ne yaptigini VE ne zaman kullanilacagini acikla (max 1024 karakter)
        talimatlar:   SKILL.md govde icerigi (Markdown)
        kategori:     Opsiyonel alt klasor (ornegin 'python', 'devops')
        lisans:       Lisans adi (varsayilan: MIT)
        uyumluluk:    Ortam gereksinimleri (opsiyonel)
        izin_araclar: Boslukla ayrili arac listesi (opsiyonel)

    Returns:
        Basari/hata mesaji.
    """
    # Ad dogrulama
    gecerli, hata = _ad_dogrula(ad)
    if not gecerli:
        return f"[Skill Olustur Hata]: Gecersiz ad '{ad}': {hata}"

    # Aciklama dogrulama
    if not aciklama.strip():
        return "[Skill Olustur Hata]: 'aciklama' bos olamaz."
    if len(aciklama) > _MAKS_ACIKLAMA_UZUNLUGU:
        aciklama = aciklama[:_MAKS_ACIKLAMA_UZUNLUGU]

    # Hedef klasor
    temel = SKILLS_KLASORLERI[1]  # .ReYMeN/skills/
    if kategori:
        hedef = temel / kategori / ad
    else:
        hedef = temel / ad

    if hedef.exists():
        return f"[Skill Olustur]: '{ad}' zaten mevcut: {hedef}"

    hedef.mkdir(parents=True, exist_ok=True)

    # SKILL.md icerigi
    frontmatter_satirlar = [
        "---",
        f"name: {ad}",
        f'description: "{aciklama}"',
    ]
    if lisans:
        frontmatter_satirlar.append(f"license: {lisans}")
    if uyumluluk:
        frontmatter_satirlar.append(f"compatibility: {uyumluluk}")
    if izin_araclar:
        frontmatter_satirlar.append(f"allowed-tools: {izin_araclar}")
    frontmatter_satirlar.append("---")
    frontmatter_satirlar.append("")

    icerik = "\n".join(frontmatter_satirlar) + talimatlar.strip() + "\n"
    skill_md = hedef / "SKILL.md"
    skill_md.write_text(icerik, encoding="utf-8")

    # Index'i guncelle
    try:
        skill_index_yenile()
    except Exception as _e:
        logger.warning("[Skill index] Guncelleme basarisiz: %s", _e)

    return (
        f"[Skill Olusturuldu]: '{ad}' -> {hedef}\n"
        f"Aciklama: {aciklama[:80]}\n"
        f"Dosya: {skill_md}\n"
        f"Dogrulama: {skill_dogrula(ad)}"
    )


# ── Skill scripts calistirma ─────────────────────────────────────────────────

def _uv_mevcut() -> bool:
    """uv paket yoneticisinin kurulu olup olmadigini kontrol et."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, timeout=3)
        return True
    except Exception:
        return False


def _pep723_mi(script_yol: Path) -> bool:
    """Script'in PEP 723 inline dep blogu icerip icermedigini kontrol et.

    PEP 723: # /// script  ... # /// blogu varsa inline bagimlilik bildirir.
    """
    try:
        icerik = script_yol.read_text(encoding="utf-8", errors="replace")
        return "# /// script" in icerik
    except Exception:
        return False


def skill_script_calistir(skill_adi: str, script_adi: str, arglar: str = "") -> str:
    """Skill icindeki scripts/ dizininden bir script calistir.

    Python scriptleri icin:
    - PEP 723 inline dep blogu varsa ve uv kuruluysa: uv run kullanir (izole env)
    - Yoksa standart python ile calistirir
    """
    dosya = skill_bul(skill_adi)
    if not dosya:
        return f"[Skill Script]: '{skill_adi}' bulunamadi."

    script_yol = dosya.parent / "scripts" / script_adi
    if not script_yol.exists():
        mevcut = [f.name for f in (dosya.parent / "scripts").iterdir()] if (dosya.parent / "scripts").exists() else []
        return f"[Skill Script]: '{script_adi}' bulunamadi. Mevcut: {mevcut}"

    uzanti = script_yol.suffix.lower()
    arg_liste = arglar.split() if arglar else []

    if uzanti == ".py":
        # PEP 723 + uv run destegi
        if _pep723_mi(script_yol) and _uv_mevcut():
            cmd = ["uv", "run", str(script_yol)] + arg_liste
            kaynak = "uv run (PEP 723)"
        else:
            cmd = [sys.executable, str(script_yol)] + arg_liste
            kaynak = "python"
    elif uzanti in {".sh", ".bash"}:
        cmd = ["bash", str(script_yol)] + arg_liste
        kaynak = "bash"
    elif uzanti in {".js", ".mjs"}:
        cmd = ["node", str(script_yol)] + arg_liste
        kaynak = "node"
    elif uzanti == ".ts":
        if shutil.which("deno"):
            cmd = ["deno", "run", "--allow-all", str(script_yol)] + arg_liste
            kaynak = "deno"
        elif shutil.which("bun"):
            cmd = ["bun", "run", str(script_yol)] + arg_liste
            kaynak = "bun"
        else:
            return f"[Skill Script]: TypeScript calistirmak icin deno veya bun gerekli."
    else:
        return f"[Skill Script]: '{uzanti}' uzantisi desteklenmiyor."

    try:
        sonuc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            cwd=str(dosya.parent),
        )
        cikti = sonuc.stdout[:2000] + (sonuc.stderr[:500] if sonuc.stderr else "")
        baslik = f"[Skill Script: {script_adi}] ({kaynak})"
        return f"{baslik}\n{cikti}" if cikti else f"{baslik} Cikti yok."
    except subprocess.TimeoutExpired:
        return f"[Skill Script]: '{script_adi}' 60 saniye icerisinde tamamlanamadi."
    except FileNotFoundError as e:
        return f"[Skill Script]: Calistirici bulunamadi: {e}"
    except Exception as e:
        return f"[Skill Script Hata]: {e}"


def skill_script_yardim(skill_adi: str, script_adi: str) -> str:
    """Script'i --help parametresiyle calistir, arayuz bilgisini al.

    Agent, bir script'i calistirmadan once arayuzunu ogrenebilir.
    """
    dosya = skill_bul(skill_adi)
    if not dosya:
        return f"[Skill Script Yardim]: '{skill_adi}' bulunamadi."

    script_yol = dosya.parent / "scripts" / script_adi
    if not script_yol.exists():
        return f"[Skill Script Yardim]: '{script_adi}' bulunamadi."

    return skill_script_calistir(skill_adi, script_adi, arglar="--help")


# ── Skill Eval Sistemi (agentskills.io evals/ standardı) ─────────────────────

def skill_eval_al(ad: str) -> dict:
    """Skill'in evals/evals.json dosyasini oku.

    Yapi (agentskills.io standardi):
    {
      "skill_name": "...",
      "evals": [
        {
          "id": 1,
          "prompt": "Kullanici mesaji",
          "expected_output": "Beklenen cikti aciklamasi",
          "files": ["evals/files/ornek.csv"],   (opsiyonel)
          "assertions": ["Cikti X icermeli"]    (opsiyonel)
        }
      ]
    }
    """
    dosya = skill_bul(ad)
    if not dosya:
        return {"hata": f"'{ad}' bulunamadi."}
    eval_dosya = dosya.parent / "evals" / "evals.json"
    if not eval_dosya.exists():
        return {"skill_name": ad, "evals": [], "bilgi": "Henuz eval yok. SKILL_EVAL_EKLE ile ekle."}
    try:
        return json.loads(eval_dosya.read_text(encoding="utf-8"))
    except Exception as e:
        return {"hata": f"evals.json okunamadi: {e}"}


def skill_eval_ekle(
    ad: str,
    prompt: str,
    expected_output: str,
    assertions: list = None,
    files: list = None,
) -> str:
    """Skill'e yeni bir eval test case ekle (evals/evals.json).

    Eval test case'leri skill kalitesini olcmek icin kullanilir:
    - should_trigger=True prompts: skill'in cagrilmasi beklenen durumlar
    - Assertions: ciktida olmasi gereken spesifik seyler

    Args:
        ad:              Skill adi
        prompt:          Gercekci kullanici mesaji (test girdisi)
        expected_output: Basarili cikti nasil gorünmeli (aciklama)
        assertions:      Dogrulanabilir kontrol listesi (opsiyonel)
        files:           Gerekli dosya yollari (opsiyonel)

    Returns:
        Basari mesaji veya hata.
    """
    dosya = skill_bul(ad)
    if not dosya:
        return f"[Eval Ekle]: '{ad}' skill bulunamadi."

    eval_dizin = dosya.parent / "evals"
    eval_dizin.mkdir(exist_ok=True)
    eval_dosya = eval_dizin / "evals.json"

    # Mevcut evals.json oku veya yeni olustur
    if eval_dosya.exists():
        try:
            mevcut = json.loads(eval_dosya.read_text(encoding="utf-8"))
        except Exception:
            mevcut = {"skill_name": ad, "evals": []}
    else:
        mevcut = {"skill_name": ad, "evals": []}

    # Yeni ID hesapla
    mevcut_evals = mevcut.get("evals", [])
    yeni_id = max((e.get("id", 0) for e in mevcut_evals), default=0) + 1

    yeni_case = {
        "id": yeni_id,
        "prompt": prompt,
        "expected_output": expected_output,
    }
    if assertions:
        yeni_case["assertions"] = assertions if isinstance(assertions, list) else [assertions]
    if files:
        yeni_case["files"] = files if isinstance(files, list) else [files]

    mevcut_evals.append(yeni_case)
    mevcut["evals"] = mevcut_evals

    eval_dosya.write_text(json.dumps(mevcut, ensure_ascii=False, indent=2), encoding="utf-8")
    return (
        f"[Eval Eklendi]: #{yeni_id} — '{ad}'\n"
        f"  Prompt: {prompt[:80]}\n"
        f"  Assertions: {len(yeni_case.get('assertions', []))} adet\n"
        f"  Toplam eval: {len(mevcut_evals)}"
    )


def skill_eval_listele(ad: str) -> str:
    """Skill'in eval test case'lerini okunabilir formatta listele."""
    veri = skill_eval_al(ad)
    if "hata" in veri:
        return f"[Eval]: {veri['hata']}"
    evals = veri.get("evals", [])
    if not evals:
        return f"[Eval]: '{ad}' icin henuz eval yok. SKILL_EVAL_EKLE ile ekle.\nIpucu: Gercekci prompt + beklenen cikti + dogrulanabilir assertions ekleyin."

    satirlar = [f"=== EVAL: {ad} ({len(evals)} test case) ==="]
    for e in evals:
        satirlar.append(f"\n[#{e['id']}] {e['prompt'][:80]}")
        satirlar.append(f"  Beklenen: {e.get('expected_output','')[:60]}")
        if e.get("assertions"):
            for a in e["assertions"][:3]:
                satirlar.append(f"  - {a}")
    return "\n".join(satirlar)


# ── Startup ozeti (progressive disclosure) ───────────────────────────────────

def skill_ozet_listesi(limit: int = 50) -> str:
    """Startup icin kisa name+description ozeti dondur (dusuk token)."""
    satirlar = []
    for dosya in _tum_skill_dosyalari():
        if len(satirlar) >= limit:
            break
        try:
            icerik = dosya.read_text(encoding="utf-8", errors="replace")
            meta = _frontmatter_parse(icerik)
            ad = dosya.parent.name
            aciklama = str(meta.get("description", "")).strip()[:80]
            satirlar.append(f"- {ad}: {aciklama}")
        except Exception as _e:
            logger.warning("[Skill duz liste] %s: %s", dosya.name if dosya else "?", _e)
    return "\n".join(satirlar) if satirlar else "[Skill]: Hicbir skill bulunamadi."


if __name__ == "__main__":
    print(f"Toplam skill: {skill_sayisi()}")
    print(f"Kategoriler ({len(kategorileri_listele())}): {kategorileri_listele()[:5]}")
    print()
    print("=== FTS5 index yenileniyor ===")
    n = skill_index_yenile()
    print(f"  Guncellenen: {n} skill")
    print()
    print("=== 'python' araması (FTS5) ===")
    for s in skill_ara("python", limit=5):
        print(f"  [{s.get('kategori','?')}] {s['ad']}: {s['aciklama'][:60]}")
    print()
    print("=== software-development kategorisi ===")
    for s in kategori_skill_listele("software-development", limit=3):
        print(f"  {s['ad']}: {s['aciklama'][:60]}")
    print()
    print("=== Aktivasyon testi (test-driven-development) ===")
    print(skill_aktivat("test-driven-development")[:400])
    print()
    print("=== Dogrulama testi ===")
    print(skill_dogrula("test-driven-development"))
    print()
    print("=== SKILL_OLUSTUR testi ===")
    sonuc = skill_olustur(
        "deneme-skill",
        "PDF dosyalarini isle ve metin cikar. Kullanici PDF analizi istediginde kullan.",
        "## Talimatlar\n1. PDF_OKU araci ile dosyayi ac.\n2. Metni analiz et.",
        kategori="test-category",
    )
    print(sonuc)
