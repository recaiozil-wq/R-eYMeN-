# -*- coding: utf-8 -*-
"""
akilli_yonlendirici.py — Mixture-of-Experts Gorev Yonlendiricisi.

Buyuk LLM sistemlerinden ilham alinan ilke:
  "Her gorev icin en uygun modeli otomatik sec."
  - Groq  → hizli/basit (siniflandirma, ozet, evet/hayir)
  - DeepSeek R1 → derin mantik, matematik, kod hata ayiklama
  - Anthropic Claude → guvenligi kritik, uzun analiz, yaratici
  - OpenAI GPT-4o → dengeli/genel
  - Yerel (LMStudio/Ollama) → varsayilan/gizlilik

Kullanim (beyin.py icinde):
    from akilli_yonlendirici import gorev_icin_model_sec
    provider, model = gorev_icin_model_sec(hedef, musait_providerlar)
    cevap = beyin.dusun(sistem, mesajlar, provider=provider, model=model)
"""

import re
from typing import Optional

# ── Gorev kategorileri ────────────────────────────────────────────────────────

GOREV_KATEGORILERI = {
    "hizli": {
        "aciklama": "Siniflandirma, evet/hayir, tek kelime yanit, basit ozet",
        "anahtar_kelimeler": [
            r"\bkisa\b", r"\bhizli\b", r"\beylt\b", r"\bbasit\b",
                        r"\bsiniflandir\b", r"\bkategori\b", r"\bevet\b", r"\bhayir\b",
                        r"\bkontrol\s+et\b", r"\bvar\s+mi\b", r"\bdogru\s+mu\b",
        ],
        "tercih_sirasi": ["groq", "lmstudio", "ollama", "deepseek", "openai"],
        "model_tercihleri": {
            "groq":   "llama-3.1-8b-instant",
            "openai": "gpt-4o-mini",
        },
        "max_token": 512,
    },
    "kod": {
        "aciklama": "Kod yazma, hata ayiklama, refactoring, test",
        "anahtar_kelimeler": [
            r"\bkod\b", r"\bpython\b", r"\bscript\b", r"\bfonksiyon\b",
                        r"\bsyntax\b", r"\bhata\s+ayikla\b", r"\bdebug\b",
                        r"\brefactor\b", r"\btest\s+yaz\b", r"\bapi\b",
                        r"\bclass\b", r"\bmodul\b", r"\bimport\b",
        ],
        "tercih_sirasi": ["deepseek", "openai", "anthropic", "groq", "lmstudio"],
        "model_tercihleri": {
            "deepseek": "deepseek-reasoner",
            "openai":   "gpt-4o",
            "anthropic": "claude-sonnet-4-6",
        },
        "max_token": 4096,
    },
    "mantik": {
        "aciklama": "Derin akil yurutme, matematik, strateji, planlama",
        "anahtar_kelimeler": [
            r"\bmatematik\b", r"\bdenklem\b", r"\bkanit\b",
                        r"\bstrateji\b", r"\bplan\b", r"\bneden\b", r"\banaliz\b",
                        r"\bkarsila[şs]tır\b", r"\bkarsila[şs]tir\b", r"\boptimize\b", r"\ben\s+iyi\b",
                        r"\bkarar\b", r"\bderinlemesine\b", r"\bdetayli\b",
        ],
        "tercih_sirasi": ["deepseek", "anthropic", "openai", "groq", "lmstudio"],
        "model_tercihleri": {
            "deepseek": "deepseek-reasoner",
            "anthropic": "claude-opus-4-8",
            "openai":   "o4-mini",
        },
        "max_token": 8192,
    },
    "yaratici": {
        "aciklama": "Yaratici yazim, fikir uretme, senaryo, pazarlama",
        "anahtar_kelimeler": [
            r"\byaz\b", r"\bhikaye\b", r"\bsenaryo\b", r"\bfikir\b",
                        r"\byaratici\b", r"\bslogan\b", r"\bpazarla\b",
                        r"\bicerik\b", r"\bcreative\b", r"\bblog\b",
        ],
        "tercih_sirasi": ["anthropic", "openai", "groq", "deepseek", "lmstudio"],
        "model_tercihleri": {
            "anthropic": "claude-sonnet-4-6",
            "openai":   "gpt-4o",
        },
        "max_token": 4096,
    },
    "guvensiz": {
        "aciklama": "Guvenlik kritik, PII, hassas veri, hukuki, medikal",
        "anahtar_kelimeler": [
            r"\bgizli\b", r"\bsifre\b", r"\bpii\b", r"\bhukuki\b",
            r"\bmedikal\b", r"\bgdpr\b", r"\bkisise\s+veri\b",
            r"\bsaglik\b", r"\bfinans\b",
        ],
        "tercih_sirasi": ["anthropic", "lmstudio", "ollama", "openai"],
        "model_tercihleri": {
            "anthropic": "claude-haiku-4-5-20251001",
        },
        "max_token": 2048,
    },
    "genel": {
        "aciklama": "Genel amaclı gorev",
        "anahtar_kelimeler": [],
        "tercih_sirasi": ["lmstudio", "ollama", "groq", "deepseek", "openai", "anthropic"],
        "model_tercihleri": {},
        "max_token": 2048,
    },
}


# ── Siniflandirici ────────────────────────────────────────────────────────────

def gorevi_siniflandir(hedef: str) -> str:
    """Hedef metninden gorev kategorisini tahmin et.

    Oncelik sirasi: guvensiz > kod > mantik > yaratici > hizli > genel
    """
    hedef_lower = hedef.lower()
    oncelik_sirasi = ["guvensiz", "kod", "mantik", "yaratici", "hizli"]

    for kategori in oncelik_sirasi:
        kaliplar = GOREV_KATEGORILERI[kategori]["anahtar_kelimeler"]
        for kalip in kaliplar:
            if re.search(kalip, hedef_lower):
                return kategori
    return "genel"


def gorev_icin_model_sec(
    hedef: str,
    musait_providerlar: list[str],
    kuvvetli_mod: bool = False,
) -> tuple[str, str]:
    """Goreve gore en uygun (provider, model) cifti sec.

    Args:
        hedef:               Kullanicinin hedef metni.
        musait_providerlar:  API anahtari olan providerlar listesi.
        kuvvetli_mod:        True → daha guclu model sec (karmasik gorevler).

    Returns:
        (provider_adi, model_adi) — bulamazsa ("lmstudio", "varsayilan")
    """
    if not musait_providerlar:
        return "lmstudio", "varsayilan"

    kategori = gorevi_siniflandir(hedef)
    bilgi = GOREV_KATEGORILERI.get(kategori, GOREV_KATEGORILERI["genel"])
    tercih = bilgi["tercih_sirasi"]

    # Kuvvetli modda mantik kategorisini kullan (tercih + model tercihleri)
    if kuvvetli_mod and kategori in ("genel", "hizli"):
        tercih = GOREV_KATEGORILERI["mantik"]["tercih_sirasi"]
        bilgi = GOREV_KATEGORILERI["mantik"]

    for prov in tercih:
        if prov in musait_providerlar:
            model = bilgi["model_tercihleri"].get(prov, _varsayilan_model(prov))
            return prov, model

    # Hicbiri uygun degilse ilk musait olanı sec
    prov = musait_providerlar[0]
    return prov, _varsayilan_model(prov)


def musait_providerlar_bul(config: dict) -> list[str]:
    """Config'den API anahtari olan providerlar listesini cikar."""
    musait = []
    # Yerel providerlar her zaman musait
    yerel = {"lmstudio", "ollama"}
    for pname, pconf in config.get("providers", {}).items():
        if pname in yerel:
            musait.append(pname)
            continue
        anahtar = pconf.get("api_key", "")
        if anahtar and not anahtar.startswith("***") and anahtar != "not-needed":
            musait.append(pname)
    # Gecersizleri filtrele
    return [p for p in musait if p in config.get("providers", {})]


def _varsayilan_model(provider: str) -> str:
    return {
        "deepseek":  "deepseek-chat",
        "openai":    "gpt-4o-mini",
        "anthropic": "claude-haiku-4-5-20251001",
        "groq":      "llama-3.1-8b-instant",
        "ollama":    "llama3.1:8b",
        "moonshot":  "moonshot-v1-8k",
        "lmstudio":  "varsayilan",
    }.get(provider, "varsayilan")


# ── Stratejik Ajan Secici (hata mesajina gore persona degistir) ───────────────

AJAN_PERSONALARI = {
    "genel_cozucu": {
        "sistem_talimati": (
            "Sen yuksek mantik ve analitik dusunme yetenegine sahip genel bir problem cozucususun. "
            "Sorunlari atomik adimlara bolerek ilerle, her eylemin sonucunu titizlikle gozlemle."
        ),
        "tanim": "Genel Mantik ve Gorev Planlama Uzmani"
    },
    "kod_uzmani": {
        "sistem_talimati": (
            "Sen kidemli bir Python yazilim muhendisligi ve hata ayiklama (debugging) uzmanisin. "
            "Yalnizca kodun sozdizimi (syntax), mantik (logic), tip guvenligi ve kutuphane bagimlilik hatalarina odaklan."
        ),
        "tanim": "Python Derleme ve Hata Ayiklama Uzmani"
    },
    "sistem_mimari": {
        "sistem_talimati": (
            "Sen karmasik entegrasyonlar, dosya yollari, API baglantilari ve cevre birimleri uzmanisin. "
            "Baglanti kopukluklari, yetkilendirme sorunlari ve girdi/cikti (I/O) dar bogazlarini cozersin."
        ),
        "tanim": "Altyapi ve Sistem Entegrasyon Uzmani"
    },
    "guvenlik_uzmani": {
        "sistem_talimati": (
            "Sen bir siber guvenlik uzmanisin. Yetki sorunlari, API anahtarlari, erisim kontrolleri "
            "ve guvenlik aciklarini tespit edip cozersin. Riskli islemlerde HITL onayi iste."
        ),
        "tanim": "Guvenlik ve Yetkilendirme Uzmani"
    },
    "veri_uzmani": {
        "sistem_talimati": (
            "Sen bir veri muhendisi ve analistisin. Veri tabani sorgulari, dosya formatlari, "
            "veri donusumleri ve buyuk veri kumeleriyle calisma konusunda uzmansin."
        ),
        "tanim": "Veri ve Veritabani Uzmani"
    }
}


def stratejik_ajan_sec(mevcut_ajan: str, hata_mesaji: str | None) -> str:
    """Hata mesajina gore en uygun ajan personasini sec.
    
    LLM cagrisi yapmadan, kural tabanli olarak milisaniyelerde karar verir.
    
    Args:
        mevcut_ajan: Su anki ajan ID'si
        hata_mesaji: Hata mesaji (None ise mevcut ajan korunur)
    
    Returns:
        Yeni ajan ID'si
    """
    if not hata_mesaji:
        return mevcut_ajan
    
    hata = hata_mesaji.lower()
    
    # Kod hatalari
    if any(e in hata for e in [
        "syntaxerror", "indentationerror", "nameerror", "typeerror", 
        "attributeerror", "importerror", "modulenotfounderror", 
        "valueerror", "keyerror", "indexerror", "traceback",
        "unsupported operand", "is not defined", "cannot import",
        "taberror", "stopiteration"
    ]):
        return "kod_uzmani"
    
    # Sistem/Altyapi hatalari
    if any(e in hata for e in [
        "filenotfounderror", "connectionerror", "timeout", 
        "permissionerror", "api_key", "not found", "connection refused",
        "connection reset", "broken pipe", "no such file",
        "econnrefused", "econnreset", "etimedout",
        "filenotfound", "is a directory"
    ]):
        return "sistem_mimari"
    
    # Guvenlik hatalari
    if any(e in hata for e in [
        "authentication", "authorization", "forbidden", "unauthorized",
        "access denied", "invalid token", "credentials", "apikey",
        "ssl", "certificate", "ratelimit", "rate limit"
    ]):
        return "guvenlik_uzmani"
    
    # Veri hatalari
    if any(e in hata for e in [
        "database", "sqlite", "sqlerror", "integrityerror",
        "jsondecode", "json.decoder", "yaml", "parsing", "utf-8",
        "encoding", "decode", "unicode", "pickle", "csv",
    ]):
        return "veri_uzmani"
    
    return mevcut_ajan


def ajan_talimatini_getir(ajan_id: str) -> str:
    """Belirtilen ajanin sistem promptunu dondur."""
    return AJAN_PERSONALARI.get(ajan_id, AJAN_PERSONALARI["genel_cozucu"])["sistem_talimati"]


# ── Kullanici arayuzu ─────────────────────────────────────────────────────────

def yonlendirme_acikla(hedef: str, musait_providerlar: list[str]) -> str:
    """Secilen yonlendirme kararini acikla (debug/log icin)."""
    kategori = gorevi_siniflandir(hedef)
    prov, model = gorev_icin_model_sec(hedef, musait_providerlar)
    return (
        f"[Router] Kategori: {kategori} | "
        f"Secilen: {prov}/{model} | "
        f"Musait: {musait_providerlar}"
    )


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== akilli_yonlendirici.py Test ===\n")

    ornekler = [
        ("Bu dosya var mi kontrol et", ["lmstudio", "groq"]),
        ("Python kodundaki syntax hatasini bul ve duzelt", ["lmstudio", "deepseek", "openai"]),
        ("Fibonacci serisini O(n) ile nasil hesaplarim, karsila stir", ["lmstudio", "deepseek", "anthropic"]),
        ("Urun icin catchy bir slogan yaz", ["lmstudio", "anthropic", "openai"]),
        ("Kullanicinin TC kimlik numarasini isle", ["lmstudio", "anthropic"]),
        ("Hava durumunu kontrol et", ["lmstudio"]),
    ]

    for hedef, musait in ornekler:
        kategori = gorevi_siniflandir(hedef)
        prov, model = gorev_icin_model_sec(hedef, musait)
        print(f"Hedef: {hedef[:50]}")
        print(f"  Kategori: {kategori}  ->  {prov}/{model}")
        print()

    print("[Test] Tamamlandi.")
