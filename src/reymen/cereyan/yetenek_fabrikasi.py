# -*- coding: utf-8 -*-
"""
yetenek_fabrikasi.py — YetenekFabrikasi.
Yetenek (beceri) olusturma, ogretme, test etme ve silme modulu.
ReYMeN kimligi: Turkce docstring, try/except, class-based.

Degisiklik (v2): YAML Frontmatter, beceri_karti_uret(), frontmatter yonetimi.
"""
import os
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ── Yardimci Fonksiyonlar ────────────────────────────────────────────

def _guvenli_ad(ad: str) -> str:
    """Yetene adini guvenli dosya adina donustur."""
    try:
        guvenli = ad.lower().strip()
        guvenli = guvenli.replace(" ", "_")
        guvenli = "".join(c for c in guvenli if c.isalnum() or c in "_-")
        return guvenli or "bilinmeyen"
    except Exception:
        return "bilinmeyen"


def _skill_id_uret(ad: str) -> str:
    """Benzersiz skill_id olustur (ad'dan MD5 hash)."""
    temiz = _guvenli_ad(ad)
    return hashlib.md5(temiz.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def _frontmatter_olustur(ad: str, usage_count: int = 1) -> str:
    """YAML frontmatter bloku olustur."""
    skill_id = _skill_id_uret(ad)
    bugun = datetime.now().strftime("%Y-%m-%d")
    return (
        "---\n"
        f"skill_id: {skill_id}\n"
        f"usage_count: {usage_count}\n"
        f"last_used: {bugun}\n"
        "---\n"
    )


def _frontmatter_parse(icerik: str) -> dict:
    """YAML frontmatter'i cozumle. Yoksa bos dict doner.
    Windows CRLF (\\r\\n) ve Unix LF (\\n) ile uyumludur."""
    # Normalize line endings
    icerik = icerik.replace("\r\n", "\n")
    if not icerik.startswith("---\n"):
        return {}
    try:
        # --- ile baslayip ikinci --- ile biten kismi al
        ikinci = icerik.find("\n---\n", 4)
        if ikinci == -1:
            return {}
        blok = icerik[4:ikinci]
        meta = {}
        for satir in blok.strip().split("\n"):
            if ":" in satir:
                anahtar, _, deger = satir.partition(":")
                anahtar = anahtar.strip()
                deger = deger.strip()
                # Sayisal degerleri donustur
                try:
                    if "." in deger:
                        deger = float(deger)
                    else:
                        deger = int(deger)
                except (ValueError, TypeError) as _e:
                    pass  # string olarak kal
                meta[anahtar] = deger
        return meta
    except Exception:
        return {}


def _frontmatter_guncelle(dosya_yolu: Path, alan: str, deger) -> bool:
    """Mevcut .md dosyasindaki frontmatter'da bir alani guncelle.
    Dosyada frontmatter yoksa ekler.
    Windows CRLF (\\r\\n) ve Unix LF (\\n) ile uyumludur.
    """
    try:
        if not dosya_yolu.exists():
            return False
        icerik = dosya_yolu.read_text(encoding="utf-8", errors="replace")
        # Normalize line endings
        icerik_norm = icerik.replace("\r\n", "\n")
        meta = _frontmatter_parse(icerik_norm)

        # Frontmatter var mi?
        if icerik_norm.startswith("---\n"):
            ikinci = icerik_norm.find("\n---\n", 4)
            if ikinci == -1:
                return False
            # Eski frontmatter'i cikar, yenisini yaz
            govde = icerik_norm[ikinci + 5:]  # \n---\n'den sonrasi
        else:
            govde = icerik_norm

        meta[alan] = deger

        # Tum alanlari koruyarak frontmatter olustur
        skill_id = meta.get("skill_id", dosya_yolu.stem)
        # Eger dogrudan skill_id guncelleniyorsa hash'i yenileme
        if alan == "skill_id":
            from hashlib import md5
            skill_id = md5(str(deger).encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
        usage_count = meta.get("usage_count", 1)
        if isinstance(usage_count, (int, float)):
            usage_count = int(usage_count)
        else:
            usage_count = 1
        from datetime import datetime
        bugun = datetime.now().strftime("%Y-%m-%d")
        last_used = meta.get("last_used", bugun)
        if not isinstance(last_used, str):
            last_used = bugun

        yeni_fm = (
            "---\n"
            f"skill_id: {skill_id}\n"
            f"usage_count: {usage_count}\n"
            f"last_used: {last_used}\n"
        )
        # Diger ozel alanlari koru (ad, aciklama, vs.)
        korunan = {"skill_id", "usage_count", "last_used"}
        for k, v in meta.items():
            if k not in korunan:
                yeni_fm += f"{k}: {v}\n"
        yeni_fm += "---\n"

        # Direkt yeni frontmatter + govde yaz
        yeni_icerik = yeni_fm + govde.lstrip("\n")
        dosya_yolu.write_text(yeni_icerik, encoding="utf-8")
        return True
    except Exception as hata:
        print(f"[Frontmatter] Guncelleme hatasi: {hata}")
        return False


# ── Standalone Fonksiyon (closed_learning_loop.py icin) ──────────────

def beceri_karti_uret(beceri_adi: str, aciklama: str,
                      adimlar: str, skills_dir: str = None) -> str:
    """Basarili gorev adimlarindan .md beceri karti olustur.

    YAML frontmatter (skill_id, usage_count, last_used) icerir.
    Dosya varsa ustune yazar (guncelleme amaciyla).

    Args:
        beceri_adi: Beceri adi
        aciklama: Kisa aciklama
        adimlar: Uygulama adimlari (string)
        skills_dir: Skills dizini (varsayilan: ./skills/)

    Returns:
        str: Olusturulan dosyanin tam yolu
    """
    try:
        if skills_dir is None:
            skills_dir = os.path.join(os.getcwd(), "skills")
        hedef_dir = Path(skills_dir)
        hedef_dir.mkdir(parents=True, exist_ok=True)

        guvenli = _guvenli_ad(beceri_adi)
        dosya_yolu = hedef_dir / f"{guvenli}.md"

        # Mevcut dosyadaki frontmatter'i koru
        mevcut_meta = {}
        if dosya_yolu.exists():
            mevcut_icerik = dosya_yolu.read_text(encoding="utf-8", errors="replace")
            mevcut_meta = _frontmatter_parse(mevcut_icerik)

        bugun = datetime.now().strftime("%Y-%m-%d")
        usage_count = mevcut_meta.get("usage_count", 1)
        if isinstance(usage_count, (int, float)):
            usage_count = int(usage_count)
        else:
            usage_count = 1

        frontmatter = _frontmatter_olustur(beceri_adi, usage_count)

        icerik = frontmatter + (
            f"# {beceri_adi}\n\n"
            f"{aciklama}\n\n"
            f"## Uygulama Adimlari\n\n"
            f"{adimlar}\n\n"
            f"## Kullanim\n\n"
            f"Bu beceri `{beceri_adi}` ile cagrilabilir.\n"
        )

        dosya_yolu.write_text(icerik, encoding="utf-8")
        print(f"[BeceriKarti] Olusturuldu: {dosya_yolu}")
        return str(dosya_yolu)
    except Exception as hata:
        print(f"[BeceriKarti] Hata: {hata}")
        raise


# ── Sinif ────────────────────────────────────────────────────────────

class YetenekFabrikasi:
    """YetenekFabrikasi: Yapay zeka yeteneklerini yonetir.

    Yeni yetenekler olusturur, mevcut yeteneklere veri ogretir,
    yetenekleri test eder ve gereksiz yetenekleri siler.
    Tum yetenekler skills/ dizininde .md dosyasi olarak saklanir.
    """

    def __init__(self, skills_dir=None):
        """YetenekFabrikasi baslat.

        Args:
            skills_dir: Yetenek depo dizini (varsayilan: skills/)
        """
        self._skills_dir = Path(skills_dir) if skills_dir else Path.cwd() / "skills"
        self._yetenek_ortusu = {}
        self._test_sonuclari = []

        try:
            self._skills_dir.mkdir(parents=True, exist_ok=True)
            self._yetenekleri_tara()
        except OSError as hata:
            print(f"[YetenekFabrikasi] Skills dizini olusturulamadi: {hata}")

    def _yetenekleri_tara(self):
        """Mevcut yetenek dosyalarini tara (frontmatter'i da oku)."""
        try:
            for dosya in self._skills_dir.glob("*.md"):
                try:
                    ad = dosya.stem
                    icerik = dosya.read_text(encoding="utf-8", errors="replace")
                    meta = _frontmatter_parse(icerik)
                    self._yetenek_ortusu[ad] = {
                        "ad": ad,
                        "dosya_yolu": str(dosya),
                        "boyut": len(icerik),
                        "son_degisiklik": datetime.fromtimestamp(
                            dosya.stat().st_mtime
                        ).isoformat(),
                        "frontmatter": meta,
                    }
                except OSError:
                    continue
        except Exception as hata:
            print(f"[YetenekFabrikasi] Tarama hatasi: {hata}")

    def yetenek_olustur(self, ad, kod, aciklama=""):
        """Yeni bir yetenek olustur (YAML frontmatter ile).

        Args:
            ad: Yetenek adi
            kod: Yetenek kodu (Python veya shell)
            aciklama: Yetenek aciklamasi

        Returns:
            dict: Olusturma sonucu
        """
        try:
            if not ad or not isinstance(ad, str):
                raise ValueError("Gecersiz yetenek adi")
            if not kod or not isinstance(kod, str):
                raise ValueError("Gecersiz yetenek kodu")

            guvenli = _guvenli_ad(ad)
            dosya_yolu = self._skills_dir / f"{guvenli}.md"

            if dosya_yolu.exists():
                return {
                    "basarili": False,
                    "hata": f"Yetenek zaten mevcut: {ad}",
                    "dosya": str(dosya_yolu),
                }

            bugun = datetime.now().strftime("%Y-%m-%d")
            frontmatter = _frontmatter_olustur(ad, 1)

            icerik = frontmatter + (
                f"# YETENEK: {ad}\n"
                f"## OLUSTURMA\n"
                f"Tarih: {datetime.now().isoformat()}\n"
                f"Aciklama: {aciklama or 'Aciklama yok'}\n\n"
                f"## KOD\n"
                f"```python\n"
                f"{kod}\n"
                f"```\n\n"
                f"## KULLANIM\n"
                f"Bu yetenek '{ad}' ile cagrilabilir.\n"
                f"Ornek:\n"
                f"```python\n"
                f"# {guvenli}()\n"
                f"```\n"
            )

            dosya_yolu.write_text(icerik, encoding="utf-8")

            kayit = {
                "ad": ad,
                "guvenli_ad": guvenli,
                "dosya_yolu": str(dosya_yolu),
                "olusturma": datetime.now().isoformat(),
                "boyut": len(icerik),
                "frontmatter": _frontmatter_parse(icerik),
            }
            self._yetenek_ortusu[guvenli] = kayit

            return {
                "basarili": True,
                "mesaj": f"Yetenek olusturuldu: {ad}",
                "dosya": str(dosya_yolu),
                "kayit": kayit,
            }

        except ValueError as e:
            return {"basarili": False, "hata": str(e)}
        except OSError as e:
            return {"basarili": False, "hata": f"Dosya yazma hatasi: {e}"}
        except Exception as hata:
            print(f"[YetenekFabrikasi] Olusturma hatasi: {hata}")
            return {"basarili": False, "hata": str(hata)}

    def yetenek_ogret(self, ad, veri):
        """Bir yetenege yeni veri ogret (guncelle).

        Args:
            ad: Yetenek adi
            veri: Eklenecek veri (string veya dict)

        Returns:
            dict: Ogretme sonucu
        """
        try:
            guvenli = _guvenli_ad(ad)
            dosya_yolu = self._skills_dir / f"{guvenli}.md"

            if not dosya_yolu.exists():
                # Otomatik olustur
                return self.yetenek_olustur(ad, str(veri), "Otomatik olusturuldu")

            mevcut_icerik = dosya_yolu.read_text(encoding="utf-8")

            if isinstance(veri, dict):
                veri_str = json.dumps(veri, ensure_ascii=False, indent=2)
            else:
                veri_str = str(veri)

            yeni_icerik = (
                mevcut_icerik.rstrip() + "\n\n"
                f"## OGRETILEN VERI ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
                f"```\n{veri_str}\n```\n"
            )

            dosya_yolu.write_text(yeni_icerik, encoding="utf-8")

            # usage_count artir
            _frontmatter_guncelle(dosya_yolu, "usage_count",
                                  _frontmatter_parse(yeni_icerik).get("usage_count", 0) + 1)
            _frontmatter_guncelle(dosya_yolu, "last_used",
                                  datetime.now().strftime("%Y-%m-%d"))

            # Tekrar oku (frontmatter guncellenmis olabilir)
            son_icerik = dosya_yolu.read_text(encoding="utf-8")
            k = self._yetenek_ortusu.get(guvenli, {})
            k.update({
                "ad": ad,
                "dosya_yolu": str(dosya_yolu),
                "boyut": len(son_icerik),
                "son_ogretme": datetime.now().isoformat(),
                "frontmatter": _frontmatter_parse(son_icerik),
            })
            self._yetenek_ortusu[guvenli] = k

            return {
                "basarili": True,
                "mesaj": f"Veri eklendi: {ad}",
                "dosya": str(dosya_yolu),
                "yeni_boyut": len(son_icerik),
            }

        except OSError as e:
            return {"basarili": False, "hata": f"Dosya hatasi: {e}"}
        except Exception as hata:
            print(f"[YetenekFabrikasi] Ogretme hatasi: {hata}")
            return {"basarili": False, "hata": str(hata)}

    def yetenek_test_et(self, ad):
        """Bir yetenegi test et.

        Args:
            ad: Yetenek adi

        Returns:
            dict: Test sonucu
        """
        try:
            guvenli = _guvenli_ad(ad)
            dosya_yolu = self._skills_dir / f"{guvenli}.md"

            if not dosya_yolu.exists():
                return {
                    "basarili": False,
                    "hata": f"Yetenek bulunamadi: {ad}",
                    "test_sonucu": "basarisiz",
                }

            dosya_bilgi = dosya_yolu.stat()
            icerik = dosya_yolu.read_text(encoding="utf-8")

            # Test kontrolleri
            hatalar = []
            uyarilar = []

            if dosya_bilgi.st_size == 0:
                hatalar.append("Dosya bos")

            # Frontmatter kontrolu
            meta = _frontmatter_parse(icerik)
            if not meta:
                uyarilar.append("YAML frontmatter bulunamadi")
            else:
                if "skill_id" not in meta:
                    uyarilar.append("skill_id eksik")
                if "usage_count" not in meta:
                    uyarilar.append("usage_count eksik")
                if "last_used" not in meta:
                    uyarilar.append("last_used eksik")

            # Govde kontrolu (frontmatter'dan sonrasi)
            govde = icerik
            icerik_norm2 = icerik.replace("\r\n", "\n")
            if icerik_norm2.startswith("---\n"):
                ikinci = icerik_norm2.find("\n---\n", 4)
                if ikinci != -1:
                    govde = icerik_norm2[ikinci + 5:]

            if not govde.startswith("#"):
                uyarilar.append("Gecersiz format: # ile baslamali")

            if "```" not in govde:
                uyarilar.append("Kod blogu bulunamadi")

            satir_sayisi = len(icerik.splitlines())
            if satir_sayisi < 5:
                uyarilar.append("Cok kisa icerik (5 satirdan az)")

            test_basarili = len(hatalar) == 0

            test_kaydi = {
                "zaman": datetime.now().isoformat(),
                "yetenek": ad,
                "test_basarili": test_basarili,
                "hatalar": hatalar,
                "uyarilar": uyarilar,
                "satir_sayisi": satir_sayisi,
                "dosya_boyutu": dosya_bilgi.st_size,
                "frontmatter": meta,
            }
            self._test_sonuclari.append(test_kaydi)

            return {
                "basarili": test_basarili,
                "mesaj": "Test basarili" if test_basarili else "Test basarisiz",
                "test_sonucu": "basarili" if test_basarili else "basarisiz",
                "hatalar": hatalar,
                "uyarilar": uyarilar,
                "detay": test_kaydi,
            }

        except OSError as e:
            return {"basarili": False, "hata": f"Dosya hatasi: {e}", "test_sonucu": "hata"}
        except Exception as hata:
            print(f"[YetenekFabrikasi] Test hatasi: {hata}")
            return {"basarili": False, "hata": str(hata), "test_sonucu": "hata"}

    def yetenek_sil(self, ad):
        """Bir yetenegi sil.

        Args:
            ad: Silinecek yetenek adi

        Returns:
            dict: Silme sonucu
        """
        try:
            guvenli = _guvenli_ad(ad)
            dosya_yolu = self._skills_dir / f"{guvenli}.md"

            if not dosya_yolu.exists():
                return {"basarili": False, "hata": f"Yetenek bulunamadi: {ad}"}

            dosya_yolu.unlink()

            if guvenli in self._yetenek_ortusu:
                del self._yetenek_ortusu[guvenli]

            return {
                "basarili": True,
                "mesaj": f"Yetenek silindi: {ad}",
                "dosya": str(dosya_yolu),
            }

        except OSError as e:
            return {"basarili": False, "hata": f"Silme hatasi: {e}"}
        except Exception as hata:
            print(f"[YetenekFabrikasi] Silme hatasi: {hata}")
            return {"basarili": False, "hata": str(hata)}

    def yetenek_listele(self):
        """Tum yetenekleri listele.

        Returns:
            list: Yetenek bilgileri
        """
        return list(self._yetenek_ortusu.values())

    def yetenek_bul(self, ad):
        """Bir yetenegi ara.

        Args:
            ad: Yetenek adi

        Returns:
            dict: Yetenek bilgisi veya None
        """
        try:
            guvenli = _guvenli_ad(ad)
            return self._yetenek_ortusu.get(guvenli)
        except Exception:
            return None

    def yetenek_oku(self, ad):
        """Bir yetenegin icerigini oku (frontmatter dahil).

        Args:
            ad: Yetenek adi

        Returns:
            str: Icerik veya None
        """
        try:
            guvenli = _guvenli_ad(ad)
            dosya_yolu = self._skills_dir / f"{guvenli}.md"
            if dosya_yolu.exists():
                return dosya_yolu.read_text(encoding="utf-8")
            return None
        except Exception:
            return None

    def test_gecmisi(self, limit=10):
        """Test gecmisini getir.

        Args:
            limit: Kac kayit

        Returns:
            list: Test kayitlari
        """
        return self._test_sonuclari[-limit:]

    def istatistik(self):
        """Yetenek istatistikleri.

        Returns:
            dict: Istatistikler
        """
        try:
            yetenek_sayisi = len(self._yetenek_ortusu)
            toplam_boyut = sum(
                k.get("boyut", 0) for k in self._yetenek_ortusu.values()
            )
            test_sayisi = len(self._test_sonuclari)
            basarili_test = sum(1 for t in self._test_sonuclari if t.get("test_basarili"))

            return {
                "yetenek_sayisi": yetenek_sayisi,
                "toplam_boyut_bytes": toplam_boyut,
                "ortalama_boyut": round(toplam_boyut / max(yetenek_sayisi, 1), 0),
                "test_sayisi": test_sayisi,
                "basarili_test": basarili_test,
                "skills_dizini": str(self._skills_dir),
            }
        except Exception as hata:
            return {"hata": str(hata)}


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yf = YetenekFabrikasi(skills_dir=os.path.join(tmpdir, "skills"))

        sonuc = yf.yetenek_olustur(
            "dosya_yaz",
            "with open(dosya_adi, 'w') as f:\n    f.write(icerik)",
            "Dosyaya metin yazar"
        )
        print(f"Olustur: {sonuc['mesaj']}")

        # Frontmatter'ı kontrol et
        icerik = yf.yetenek_oku("dosya_yaz")
        if icerik:
            meta = _frontmatter_parse(icerik)
            print(f"Frontmatter: {meta}")

        sonuc = yf.yetenek_ogret("dosya_yaz", {"ornek": "test.txt", "icerik": "merhaba"})
        print(f"Ogret: {sonuc['mesaj']}")

        test = yf.yetenek_test_et("dosya_yaz")
        print(f"Test: {test['mesaj']} | Uyarilar: {test.get('uyarilar', [])}")

        liste = yf.yetenek_listele()
        print(f"Liste: {len(liste)} yetenek")

        print(f"Istatistik: {yf.istatistik()}")

        # Standalone fonksiyon testi
        yol = beceri_karti_uret(
            "ornek_beceri",
            "Ornek bir beceri",
            "1. Adim: yap\n2. Adim: bitir",
            os.path.join(tmpdir, "skills")
        )
        print(f"beceri_karti_uret: {yol}")
        print(Path(yol).read_text(encoding="utf-8"))

        sil = yf.yetenek_sil("dosya_yaz")
        print(f"Sil: {sil['mesaj']}")
