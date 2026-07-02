"""
_puanla.py — Web Tetikleyici Puanlama Motoru

Web araması sonucu gelen bilgiyi puanlar:
- Güncellik (tarih)
- Kaynak güvenilirliği (resmi doküman > forum > LLM)
- Doğrulama sayısı (kaç kaynak aynı şeyi söylüyor)
- OnceHafiza ile karşılaştırma (çelişki varsa düşük puan)

Puan > 0.7 → hafızaya kaydet
Puan 0.4-0.7 → kullanıcıya danış
Puan < 0.4 → reddet
"""

import re
from datetime import datetime, date

# Kaynak güvenilirlik puanları
KAYNAK_PUAN = {
    "resmi_dokuman": 1.0,      # PyPI, GitHub resmi, Microsoft docs
    "stackoverflow": 0.8,      # StackOverflow / GitHub Issues
    "blog": 0.6,               # Teknik blog
    "forum": 0.5,              # Forum tartışması
    "video": 0.7,              # YouTube (doğrulama gerektirir)
    "llm": 0.4,                # Başka bir LLM'in cevabı
    "bilinmiyor": 0.3,         # Kaynağı belirsiz
}

# Alan adı → kaynak tipi eşleme
ALAN_ADI_PUAN = {
    "docs.microsoft.com": 1.0,
    "learn.microsoft.com": 1.0,
    "github.com": 0.9,
    "pypi.org": 1.0,
    "stackoverflow.com": 0.8,
    "stackexchange.com": 0.8,
    "medium.com": 0.6,
    "dev.to": 0.6,
    "youtube.com": 0.7,
    "youtu.be": 0.7,
    "reddit.com": 0.5,
    "wikipedia.org": 0.7,
}


def kaynak_turu_bul(url: str) -> str:
    """URL'den kaynak türünü tahmin et."""
    if not url:
        return "bilinmiyor"
    for alan, puan in ALAN_ADI_PUAN.items():
        if alan in url.lower():
            for tur, _ in KAYNAK_PUAN.items():
                if tur == "resmi_dokuman" and puan >= 1.0:
                    return "resmi_dokuman"
            return "stackoverflow" if "stack" in url.lower() else "blog"
    return "bilinmiyor"


def kaynak_guvenirlik_puan(url: str) -> float:
    """URL'den kaynak güvenilirlik puanı hesapla."""
    if not url:
        return KAYNAK_PUAN["bilinmiyor"]
    for alan, puan in ALAN_ADI_PUAN.items():
        if alan in url.lower():
            return puan
    return KAYNAK_PUAN["bilinmiyor"]


def guncellik_puan(tarih_str: str = None) -> float:
    """
    Bilginin güncelliğini puanla.
    - 30 günden yeni: 1.0
    - 6 aydan yeni: 0.8
    - 1 yıldan yeni: 0.5
    - 2 yıldan eski: 0.2
    """
    if not tarih_str:
        return 0.5  # Tarih yoksa ortalama
    
    try:
        tarih = datetime.strptime(tarih_str[:10], "%Y-%m-%d").date()
        bugun = date.today()
        fark = (bugun - tarih).days
        
        if fark <= 30:
            return 1.0
        elif fark <= 180:  # 6 ay
            return 0.8
        elif fark <= 365:  # 1 yıl
            return 0.5
        else:
            return 0.2
    except (ValueError, TypeError, OSError):
        return 0.5


def dogrulama_puan(kaynak_sayisi: int) -> float:
    """Kaç farklı kaynak aynı bilgiyi doğruluyor."""
    if kaynak_sayisi >= 3:
        return 1.0
    elif kaynak_sayisi == 2:
        return 0.8
    elif kaynak_sayisi == 1:
        return 0.5
    return 0.0


def celiski_puan(oncehafiza_guven: float, web_icerik_uyum: float) -> float:
    """
    OnceHafiza'daki bilgi ile web'den gelen bilgi arasındaki uyum.
    oncehafiza_guven: DB'deki güven skoru (0-1)
    web_icerik_uyum: İki kaynağın ne kadar uyumlu olduğu (0-1)
    """
    if web_icerik_uyum >= 0.8:
        return 1.0  # Uyumlu
    elif web_icerik_uyum >= 0.5:
        return 0.6  # Kısmen uyumlu
    else:
        return 0.0  # Çelişki


def hesapla(
    url: str = None,
    tarih: str = None,
    kaynak_sayisi: int = 1,
    oncehafiza_guven: float = None,
    web_icerik_uyum: float = None,
    agirlik_guncellik: float = 0.3,
    agirlik_kaynak: float = 0.3,
    agirlik_dogrulama: float = 0.2,
    agirlik_celiski: float = 0.2,
) -> dict:
    """
    Ana puanlama fonksiyonu.
    
    Parametreler:
        url: Bilginin kaynak URL'si
        tarih: Bilginin yayın tarihi (YYYY-MM-DD)
        kaynak_sayisi: Kaç farklı kaynak doğruluyor
        oncehafiza_guven: DB'deki mevcut güven (0-1)
        web_icerik_uyum: İçerik uyumu (0-1)
    
    Dönen:
        {
            "puan": float (0-1),
            "karar": "kaydet" | "danis" | "reddet",
            "detay": { ... }
        }
    """
    p_guncellik = guncellik_puan(tarih)
    p_kaynak = kaynak_guvenirlik_puan(url)
    p_dogrulama = dogrulama_puan(kaynak_sayisi)
    
    if oncehafiza_guven is not None and web_icerik_uyum is not None:
        p_celiski = celiski_puan(oncehafiza_guven, web_icerik_uyum)
    else:
        p_celiski = 0.5  # Karşılaştırma yoksa nötr
    
    puan = (
        p_guncellik * agirlik_guncellik +
        p_kaynak * agirlik_kaynak +
        p_dogrulama * agirlik_dogrulama +
        p_celiski * agirlik_celiski
    )
    
    # Karar
    if puan >= 0.7:
        karar = "kaydet"
    elif puan >= 0.4:
        karar = "danis"
    else:
        karar = "reddet"
    
    return {
        "puan": round(puan, 3),
        "karar": karar,
        "detay": {
            "guncellik": round(p_guncellik, 3),
            "kaynak_guven": round(p_kaynak, 3),
            "dogrulama": round(p_dogrulama, 3),
            "celiski": round(p_celiski, 3),
            "url": url,
        }
    }


def karar_aciklamasi(sonuc: dict) -> str:
    """Puanlama sonucunu insan okunabilir hale getir."""
    puan = sonuc["puan"]
    karar = sonuc["karar"]
    detay = sonuc["detay"]
    
    if karar == "kaydet":
        return (f"✅ PUAN={puan} → KAYDET (güncellik={detay['guncellik']}, "
                f"kaynak={detay['kaynak_guven']}, doğrulama={detay['dogrulama']})")
    elif karar == "danis":
        return (f"⚠️ PUAN={puan} → DANIŞ (güncellik={detay['guncellik']}, "
                f"kaynak={detay['kaynak_guven']}, çelişki={detay['celiski']})")
    else:
        return (f"❌ PUAN={puan} → REDDET (kaynak={detay['kaynak_guven']}, "
                f"doğrulama={detay['dogrulama']}, güncellik={detay['guncellik']})")


# === TEST ===
if __name__ == "__main__":
    testler = [
        # (url, tarih, kaynak_sayisi, oncehafiza_guven, web_icerik_uyum)
        ("https://docs.python.org/3/library/", "2026-06-01", 3, 0.9, 1.0),  # Kaydet
        ("https://stackoverflow.com/questions/123", "2025-12-01", 1, 0.8, 0.6),  # Danış
        ("https://random-forum.com/thread", "2023-01-01", 1, None, None),  # Reddet
        ("https://github.com/user/repo", "2026-05-15", 2, 0.5, 0.3),  # Danış (çelişki)
    ]
    
    for url, tarih, ks, og, wu in testler:
        s = hesapla(url=url, tarih=tarih, kaynak_sayisi=ks, 
                    oncehafiza_guven=og, web_icerik_uyum=wu)
        print(karar_aciklamasi(s))
