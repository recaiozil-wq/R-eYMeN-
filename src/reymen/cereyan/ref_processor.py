# -*- coding: utf-8 -*-
"""ref_processor.py — @file / @url referans islemcisi.

Kullanici mesajindaki @file:path ve @url:https://... pattern'lerini
regex ile yakalar, ilgili icerigi otomatik okur ve referans olarak
context'e ekler.

Kullanim:
    from reymen.cereyan.ref_processor import ref_isle

    zengin_metin, ref_liste = ref_isle("su dosyaya bak: @file:config.yaml")
"""

import logging
import re
import os
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# Regex pattern: @file:path veya @url:https://...
#   @file:./dosya.txt   → goreli yol
#   @file:C:/yol/dosya  → mutlak yol
#   @url:https://ornek.com  → URL
_RE_FILE = re.compile(r"@file\:([^\s\"']+)")
_RE_URL = re.compile(r"@url\:([^\s\"']+)")

# Varsayilan maksimum karakter siniri (10K)
_VARSAYILAN_MAX_KARAKTER = 10000

# Ref isleminin acik/kapali oldugunu belirten modul seviyesi flag
# config.yaml'daki ref_processor: true/false degerine gore ayarlanir
_REF_PROCESSOR_AKTIF = True


def _config_oku() -> bool:
    """config.yaml'dan ref_processor ayarini oku.

    Returns:
        True (acik) / False (kapali)
    """
    try:
        import yaml
        for y in [
            Path.cwd() / "config.yaml",
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
        ]:
            if y.exists():
                with open(y, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                val = cfg.get("ref_processor")
                if isinstance(val, bool):
                    return val
                val = cfg.get("ref_processor.enabled")
                if isinstance(val, bool):
                    return val
                break
    except Exception:
        pass
    return True  # varsayilan: acik


_REF_PROCESSOR_AKTIF = _config_oku()


def _dosya_oku(dosya_yolu: str, max_karakter: int = _VARSAYILAN_MAX_KARAKTER) -> Tuple[bool, str, str]:
    """@file: ile belirtilen dosyayi guvenlik kontrolunden gecirerek oku.

    Args:
        dosya_yolu: Dosya yolu (goreli veya mutlak)
        max_karakter: Okunacak maksimum karakter sayisi

    Returns:
        (basarili, icerik, hata_mesaji)
    """
    try:
        # Guvenlik kontrolu
        try:
            from reymen.guvenlik.file_safety import guvenli_mi
            guvenli, hata = guvenli_mi(dosya_yolu)
            if not guvenli:
                return False, "", f"Guvenlik engeli: {hata}"
        except ImportError:
            pass  # file_safety yoksa kontrolsuz devam et

        # Yolu coz
        yol = Path(dosya_yolu)
        if not yol.is_absolute():
            # Goreli yollari proje kokune gore coz
            proje_kok = Path(__file__).resolve().parent.parent.parent
            yol = (proje_kok / dosya_yolu).resolve()

        if not yol.exists():
            return False, "", f"Dosya bulunamadi: {yol}"
        if not yol.is_file():
            return False, "", f"Bir dosya degil: {yol}"

        # Dosyayi oku (binary degilse)
        try:
            icerik = yol.read_text(encoding="utf-8", errors="replace")
        except (UnicodeDecodeError, LookupError):
            # Binary olabilir, guvenlik geregi okuma
            return False, "", f"Okunamiyor (binary olabilir): {yol.name}"

        if len(icerik) > max_karakter:
            log.warning("[RefProcessor] Dosya cok buyuk, ilk %d karakter alindi: %s",
                        max_karakter, yol.name)
            icerik = icerik[:max_karakter] + "\n\n... [kesildi]"

        return True, icerik, ""

    except Exception as e:
        log.error("[RefProcessor] Dosya okuma hatasi: %s: %s", dosya_yolu, e)
        return False, "", f"Dosya okuma hatasi: {e}"


def _url_oku(url: str, max_karakter: int = _VARSAYILAN_MAX_KARAKTER) -> Tuple[bool, str, str]:
    """@url: ile belirtilen URL'yi guvenlik kontrolunden gecirerek icerigini cek.

    Args:
        url: HTTP/HTTPS URL
        max_karakter: Okunacak maksimum karakter sayisi

    Returns:
        (basarili, icerik, hata_mesaji)
    """
    # requests import
    try:
        import requests as _requests
    except ImportError:
        return False, "", "requests kutuphanesi yuklu degil (pip install requests)"

    try:
        # Guvenlik kontrolu
        try:
            from reymen.guvenlik.url_safety import url_guvenli_mi
            guvenli, hata = url_guvenli_mi(url)
            if not guvenli:
                return False, "", f"URL guvenlik engeli: {hata}"
        except ImportError:
            pass

        # HTTP istegi
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        yanit = _requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        yanit.raise_for_status()

        # Icerik tipine gore isle
        content_type = yanit.headers.get("Content-Type", "").lower()
        if "text/" not in content_type and "application/json" not in content_type \
           and "application/xml" not in content_type and "html" not in content_type:
            return False, "", f"Desteklenmeyen icerik turu: {content_type}"

        # Encoding tespiti
        yanit.encoding = yanit.apparent_encoding or "utf-8"
        icerik = yanit.text

        # HTML ise duz metne cevirmeyi dene
        if "html" in content_type:
            try:
                # Basit HTML tag temizleme
                temiz = re.sub(r"<[^>]+>", " ", icerik)
                temiz = re.sub(r"\s+", " ", temiz).strip()
                if len(temiz) > len(icerik) * 0.3:  # anlamli bir metinse
                    icerik = temiz
            except Exception:
                pass  # HTML temizleme basarisiz olursa ham icerigi kullan

        if len(icerik) > max_karakter:
            log.warning("[RefProcessor] URL icerigi cok buyuk, ilk %d karakter alindi: %s",
                        max_karakter, url)
            icerik = icerik[:max_karakter] + "\n\n... [kesildi]"

        return True, icerik, ""

    except _requests.exceptions.Timeout:
        return False, "", f"URL zaman asimi: {url}"
    except _requests.exceptions.ConnectionError:
        return False, "", f"URL baglanti hatasi: {url}"
    except _requests.exceptions.RequestException as e:
        return False, "", f"URL istek hatasi: {e}"
    except Exception as e:
        log.error("[RefProcessor] URL okuma hatasi: %s: %s", url, e)
        return False, "", f"URL okuma hatasi: {e}"


def ref_isle(metin: str,
             max_karakter: int = _VARSAYILAN_MAX_KARAKTER,
             aktif: Optional[bool] = None) -> Tuple[str, List[dict]]:
    """Metindeki @file: ve @url: referanslarini isle.

    Ornek:
        >>> ref_isle("su dosyayi oku @file:README.md ve su siteye bak @url:https://ornek.com")
        (
            "su dosyayi oku [REF:README.md] ve su siteye bak [REF:ornek.com]",
            [
                {"tip": "file", "kaynak": "README.md", "icerik": "# Proje...", "basarili": True},
                {"tip": "url",  "kaynak": "https://ornek.com", "icerik": "<html>...", "basarili": True},
            ]
        )

    Args:
        metin: Kullanici mesaji
        max_karakter: Her kaynak icin maksimum karakter
        aktif: True/False ile ac/kapa. None = modul seviyesi _REF_PROCESSOR_AKTIF

    Returns:
        (zengin_metin, referans_listesi)
            zengin_metin: Referanslarin [REF:...] ile degistirildigi metin
            referans_listesi: [{tip, kaynak, icerik, basarili, hata}, ...]
    """
    if aktif is False or (aktif is None and not _REF_PROCESSOR_AKTIF):
        return metin, []

    referanslar: List[dict] = []
    zengin_metin = metin

    # -- @file: isle --
    for eslesme in _RE_FILE.finditer(metin):
        dosya_yolu = eslesme.group(1).strip()
        basarili, icerik, hata = _dosya_oku(dosya_yolu, max_karakter)
        dosya_adi = Path(dosya_yolu).name

        ref_kayit = {
            "tip": "file",
            "kaynak": dosya_yolu,
            "icerik": icerik if basarili else "",
            "basarili": basarili,
            "hata": hata if not basarili else "",
            "etiket": dosya_adi,
        }
        referanslar.append(ref_kayit)

        if basarili:
            zengin_metin = zengin_metin.replace(
                eslesme.group(0), f"[REF:{dosya_adi}]"
            )
        else:
            log.warning("[RefProcessor] @file basarisiz: %s — %s", dosya_yolu, hata)
            zengin_metin = zengin_metin.replace(
                eslesme.group(0), f"[REF:{dosya_adi}:HATA]"
            )

    # -- @url: isle --
    for eslesme in _RE_URL.finditer(metin):
        url = eslesme.group(1).strip()
        basarili, icerik, hata = _url_oku(url, max_karakter)

        # URL'den kisa bir etiket olustur
        parsed = urlparse(url)
        etiket = parsed.netloc or url[:30]

        ref_kayit = {
            "tip": "url",
            "kaynak": url,
            "icerik": icerik if basarili else "",
            "basarili": basarili,
            "hata": hata if not basarili else "",
            "etiket": etiket,
        }
        referanslar.append(ref_kayit)

        if basarili:
            zengin_metin = zengin_metin.replace(
                eslesme.group(0), f"[REF:{etiket}]"
            )
        else:
            log.warning("[RefProcessor] @url basarisiz: %s — %s", url, hata)
            zengin_metin = zengin_metin.replace(
                eslesme.group(0), f"[REF:{etiket}:HATA]"
            )

    return zengin_metin, referanslar


def ref_context_olustur(referanslar: List[dict]) -> Optional[str]:
    """Referans listesinden LLM'e verilecek context stringi olustur.

    Args:
        referanslar: ref_isle()'den donen liste

    Returns:
        Context stringi veya None (ref yoksa)
    """
    if not referanslar:
        return None

    bolumler = []
    for ref in referanslar:
        if not ref.get("basarili"):
            continue
        tip = ref["tip"]
        etiket = ref.get("etiket", ref["kaynak"])
        icerik = ref.get("icerik", "")

        bolum = (
            f"--- REF:{etiket} ({tip.upper()}) ---\n"
            f"{icerik}\n"
            f"--- REF:{etiket} SONU ---"
        )
        bolumler.append(bolum)

    if not bolumler:
        return None

    context = (
        "[REFERANSLAR]\n"
        "Asagida kullanicinin @file/@url ile belirttigi referanslarin "
        "icerigi yer almaktadir:\n\n"
        + "\n\n".join(bolumler) +
        "\n[/REFERANSLAR]"
    )
    return context
