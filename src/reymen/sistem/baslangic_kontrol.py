# -*- coding: utf-8 -*-
"""
baslangic_kontrol.py — ReYMeN Başlangıç ve Ortam Kontrolü.

Program açılışında çalışır:
  1. Harici API anahtarı var mı? → varsa o provider ile başlat
  2. Yoksa Ollama çalışıyor mu?  → çalışmıyorsa uyarı ver
  3. llava modeli yüklü mü?      → yoksa indir seçeneği sun
  4. /model komutu               → çalışma sırasında model değiştir
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

OLLAMA_BASE   = "http://localhost:11434"
LMSTUDIO_BASE = "http://localhost:1234"
_HTTP_TIMEOUT = 3

# Kontrol edilecek harici API anahtarları (env değişken adı → provider adı)
HARICI_API_ENV = {
    "DEEPSEEK_API_KEY":  "DeepSeek",
    "ANTHROPIC_API_KEY": "Anthropic",
    "OPENAI_API_KEY":    "OpenAI",
    "GROQ_API_KEY":      "Groq",
    "MOONSHOT_API_KEY":  "Moonshot",
}

# Ollama'dan indirilecek modeller (hafif genel + görsel)
ONERILIR_MODEL   = "llama3.2:3b"   # küçük ama yetenekli
GORUNTUSEL_MODEL = "llava:7b"      # görsel/OCR için


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _reymen_env_yolu() -> Path:
    """Platform-bagimsiz .env yolu (Windows / Linux / macOS)."""
    import platform
    ev = Path.home()
    if platform.system() == "Windows":
        return ev / "AppData" / "Local" / "reymen" / ".env"
    return ev / ".config" / "reymen" / ".env"


def _env_deger(anahtar: str) -> str:
    """Env veya ReYMeN .env dosyasından değer oku."""
    deger = os.environ.get(anahtar, "").strip()
    if deger:
        return deger
    env_dosya = _reymen_env_yolu()
    if env_dosya.exists():
        try:
            for satir in env_dosya.read_text(encoding="utf-8").splitlines():
                if satir.startswith(f"{anahtar}="):
                    val = satir.split("=", 1)[1].strip()
                    if val and not val.startswith("***"):
                        return val
        except OSError as _baslangi_e60:
            print(f"[UYARI] baslangic_kontrol.py:61 - {_baslangi_e60}")
    return ""


def api_anahtari_var_mi() -> dict:
    """Tanımlı harici API anahtarlarını döndür. {provider_adi: anahtar}"""
    bulunanlar = {}
    for env_adi, provider_adi in HARICI_API_ENV.items():
        val = _env_deger(env_adi)
        if val:
            bulunanlar[provider_adi] = val
    return bulunanlar


def lmstudio_modeller(base_url: str = LMSTUDIO_BASE) -> list:
    """LM Studio'da yuklü modellerin isim listesini donDur."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base_url}/v1/models",
            headers={"Authorization": "Bearer not-needed"},
        )
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            return [m["id"] for m in json.loads(r.read().decode()).get("data", [])]
    except Exception:
        return []


def ollama_calisiyor_mu() -> bool:
    """Ollama servisinin calisip calismadigini kontrol et."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=_HTTP_TIMEOUT) as r:
            return r.status == 200
    except Exception:
        return False


def ollama_modeller() -> list:
    """Ollama'da yüklü modellerin isim listesini döndür."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5) as r:
            data = json.loads(r.read().decode())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def llava_yuklu_mu() -> bool:
    """llava modeli yüklü mü?"""
    return any("llava" in m.lower() for m in ollama_modeller())


def model_indir(model_adi: str) -> bool:
    """Ollama API üzerinden model indir, ilerlemeyi konsola yaz."""
    print(f"\n  İndiriliyor: {model_adi} ...")
    try:
        import urllib.request
        istek = json.dumps({"name": model_adi, "stream": True}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/pull",
            data=istek,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        onceki_durum = ""
        with urllib.request.urlopen(req, timeout=600) as r:
            for satir in r:
                if not satir.strip():
                    continue
                try:
                    veri = json.loads(satir.decode())
                except json.JSONDecodeError:
                    continue

                durum = veri.get("status", "")
                toplam = veri.get("total", 0)
                tamamlanan = veri.get("completed", 0)

                if toplam and tamamlanan:
                    yuzde = int(tamamlanan / toplam * 100)
                    ilerleme = f"[{'█' * (yuzde // 5):<20}] {yuzde}%"
                    print(f"\r  {durum}: {ilerleme}", end="", flush=True)
                elif durum != onceki_durum and durum:
                    print(f"\r  {durum:<60}", end="", flush=True)
                onceki_durum = durum

        print(f"\r  {model_adi} indirildi.{' ' * 40}")
        return True
    except Exception as e:
        print(f"\n  [Hata] {model_adi} indirilemedi: {e}")
        return False


# ── Ana başlangıç kontrolü ────────────────────────────────────────────────────

def baslangic_kontrolu(config: dict) -> dict:
    """
    Program başlangıcında çalışır. Config'i doğrular/günceller.
    - Harici API varsa kullan → Ollama kontrolü atla
    - Yoksa Ollama + llava zorunlu
    """
    # (baslangiç banner startup_ekrani.py tarafindan gosterilir)

    # 0. Kaydedilmis bulut tercihi var mi? → LM Studio'yu gecersiz kilma
    _BULUT_ENV_MAP = {
        "deepseek":   "DEEPSEEK_API_KEY",
        "openai":     "OPENAI_API_KEY",
        "anthropic":  "ANTHROPIC_API_KEY",
        "groq":       "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    try:
        _setup_dosya = Path(__file__).parent / ".ReYMeN" / "setup.json"
        if _setup_dosya.exists():
            _saved = json.loads(_setup_dosya.read_text(encoding="utf-8"))
            _tercih_prov  = _saved.get("tercih_provider", "")
            _tercih_model = _saved.get("tercih_model", "")
            if _tercih_prov and _tercih_prov not in ("lmstudio", "ollama") and _tercih_model:
                _env_key = _BULUT_ENV_MAP.get(_tercih_prov, "")
                if _env_key and os.environ.get(_env_key, "").strip():
                    config["default_provider"] = _tercih_prov
                    config["default_model"]    = _tercih_model
                    return config
    except Exception as _baslangi_e186:
        print(f"[UYARI] baslangic_kontrol.py:187 - {_baslangi_e186}")

    # 1. LM Studio kontrolü (API anahtarına gerek yok)
    ls_url = config.get("providers", {}).get("lmstudio", {}).get("base_url", LMSTUDIO_BASE)
    ls_modeller = lmstudio_modeller(ls_url)
    if ls_modeller:
        vizyon_m = next((m for m in ls_modeller if "llava" in m.lower() or "vision" in m.lower()), None)
        if vizyon_m:
            config.setdefault("auxiliary", {}).setdefault("vision", {})["model"] = vizyon_m
        config["default_model"]    = ls_modeller[0]
        config["default_provider"] = "lmstudio"
        return config

    # 2. Harici API anahtarı kontrolü
    aktif_api = api_anahtari_var_mi()
    if aktif_api:
        provider_listesi = ", ".join(aktif_api.keys())
        return config   # Ollama'ya gerek yok

    # 3. API yok → Ollama zorunlu
    print("\n  LM Studio ve harici API anahtarı bulunamadı.")
    print("  Yerel calisma icin Ollama gereklidir.\n")

    if not ollama_calisiyor_mu():
        print("  [UYARI] Ollama calismiyor veya kurulu degil!")
        print()
        print("  Secenekler:")
        print("    1. Ollama'yı baslatın : ollama serve")
        print("    2. Ollama kurun       : https://ollama.ai/download")
        print("    3. LM Studio'yu baslatın")
        print("    4. API anahtarı ekleyin (.env dosyasına DEEPSEEK_API_KEY vb.)")
        print()
        yanit = input("  Ollama zaten calisıyor, tekrar kontrol et? [e/h]: ").strip().lower()
        if yanit == "e" and ollama_calisiyor_mu():
            print("  Ollama baglantısı saglandi.")
        else:
            print("  Devam ediliyor — LLM erismeden calısacak (sınırlı mod).")
            return config

    # 3. Ollama çalışıyor — model listesini göster
    mevcut_modeller = ollama_modeller()
    print(f"  Ollama çalışıyor — {len(mevcut_modeller)} model yüklü:")
    for m in mevcut_modeller:
        isaretci = "  →" if "llava" in m.lower() else "   "
        print(f"  {isaretci} {m}")

    # 4. llava kontrolü
    if not llava_yuklu_mu():
        print()
        print("  [BİLGİ] Görsel/OCR işlevleri için 'llava' modeli gereklidir.")
        print(f"  İndirilecek modeller:")
        print(f"    • {ONERILIR_MODEL}  (genel amaçlı, hafif)")
        print(f"    • {GORUNTUSEL_MODEL} (görsel analiz)")
        print()
        print("  [İ] İndir    [G] Geç    [Ç] Çıkış")
        yanit = input("  Seçiminiz: ").strip().upper()

        if yanit == "İ" or yanit == "I":
            # Genel model — sadece listede yoksa indir
            genel_yuklu = any(ONERILIR_MODEL.split(":")[0] in m for m in mevcut_modeller)
            if not genel_yuklu:
                model_indir(ONERILIR_MODEL)
            else:
                print(f"  {ONERILIR_MODEL} zaten mevcut, atlanıyor.")
            model_indir(GORUNTUSEL_MODEL)
            # Config'i llava'ya güncelle
            if "auxiliary" in config:
                config["auxiliary"]["vision"]["model"] = GORUNTUSEL_MODEL

        elif yanit == "Ç" or yanit == "C":
            print("  Çıkılıyor.")
            sys.exit(0)
        else:
            print("  Geçiliyor — llava olmadan devam ediliyor.")
    else:
        # llava var, modeli config'e yaz
        llava_adi = next(m for m in mevcut_modeller if "llava" in m.lower())
        if "auxiliary" in config:
            config["auxiliary"]["vision"]["model"] = llava_adi
        print(f"\n  Görsel model hazır: {llava_adi}")

    # 5. Varsayılan provider'ı Ollama'ya ayarla
    if not config.get("default_provider") or config["default_provider"] in ("lmstudio",):
        if mevcut_modeller:
            config["default_provider"] = "ollama"
            config["default_model"] = mevcut_modeller[0]
            # Ollama provider girişi ekle
            config.setdefault("providers", {})["ollama"] = {
                "base_url": OLLAMA_BASE,
                "api_key": "not-needed",
            }
            print(f"  Aktif model: {mevcut_modeller[0]}")

    # 6. Arka planda güncelleme kontrolü başlat (kullanıcıyı bekletmez)
    try:
        from reymen.sistem.guncelle import arka_plan_baslat
        arka_plan_baslat()
    except ImportError as _baslangi_e284:
        print(f"[UYARI] baslangic_kontrol.py:285 - {_baslangi_e284}")

    return config


# Bulut sağlayıcı → (model_adi, aciklama) listesi
_BULUT_MODELLER = {
    "deepseek":  [("deepseek-chat", "DeepSeek Chat"), ("deepseek-reasoner", "DeepSeek Reasoner")],
    "openai":    [("gpt-4o", "GPT-4o"), ("gpt-4o-mini", "GPT-4o Mini")],
    "anthropic": [("claude-haiku-4-5-20251001", "Claude Haiku 4.5"), ("claude-sonnet-4-6", "Claude Sonnet 4.6")],
    "groq":      [("llama-3.1-70b-versatile", "LLaMA 3.1 70B (Groq)"), ("mixtral-8x7b-32768", "Mixtral 8x7B")],
    "moonshot":  [("moonshot-v1-8k", "Moonshot 8k"), ("moonshot-v1-32k", "Moonshot 32k")],
}

# Bulut provider → env degisken adi
_BULUT_ENV = {
    "deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
}


# ── /model komutu ─────────────────────────────────────────────────────────────

def model_degistir(agent) -> bool:
    """
    Calisma sırasında /model komutuyla model degistirir.
    LM Studio, Ollama ve API anahtarı olan bulut saglayıcıları listeler.

    Returns:
        True  → model degistirildi
        False → iptal
    """
    mevcut_p = agent.config.get("default_provider", "?")
    mevcut_m = agent.config.get("default_model",    "?")
    ls_url   = agent.config.get("providers", {}).get("lmstudio", {}).get("base_url", LMSTUDIO_BASE)

    print(f"\n  Mevcut: [{mevcut_p}] {mevcut_m}")
    print("  " + "─" * 50)

    secenekler = []  # [(provider, model, aciklama), ...]
    idx = 1

    # LM Studio modelleri
    ls_mods = lmstudio_modeller(ls_url)
    if ls_mods:
        print(f"\n  LM Studio ({ls_url}):")
        for m in ls_mods[:6]:
            isaret = "→" if m == mevcut_m and mevcut_p == "lmstudio" else " "
            print(f"  {isaret} [{idx}] {m}")
            secenekler.append(("lmstudio", m, m))
            idx += 1

    # Ollama modelleri
    if ollama_calisiyor_mu():
        oll_mods = ollama_modeller()
        if oll_mods:
            print(f"\n  Ollama ({OLLAMA_BASE}):")
            for m in oll_mods[:6]:
                isaret = "→" if m == mevcut_m and mevcut_p == "ollama" else " "
                print(f"  {isaret} [{idx}] {m}")
                secenekler.append(("ollama", m, m))
                idx += 1

    # Bulut modeller (sadece API anahtarı olanlar)
    for provider, mods in _BULUT_MODELLER.items():
        env_adi = _BULUT_ENV.get(provider, "")
        anahtar = os.environ.get(env_adi, "").strip()
        if anahtar and not anahtar.startswith("***"):
            print(f"\n  {provider.capitalize()} (API key mevcut):")
            for model_adi, aciklama in mods:
                isaret = "→" if model_adi == mevcut_m and mevcut_p == provider else " "
                print(f"  {isaret} [{idx}] {aciklama}")
                secenekler.append((provider, model_adi, aciklama))
                idx += 1

    if not secenekler:
        print("  [/model] Hicbir model bulunamadı.")
        return False

    print(f"\n  [0] Iptal")
    yanit = input("\n  Secin (numara veya model adı): ").strip()

    if yanit == "0" or not yanit:
        print("  Iptal edildi.")
        return False

    # Numara ile seçim
    if yanit.isdigit():
        num = int(yanit) - 1
        if 0 <= num < len(secenekler):
            yeni_provider, yeni_model, _ = secenekler[num]
        else:
            print("  Gecersiz numara.")
            return False
    else:
        # İsim ile kısmi eşleşme
        eslesen = [(p, m, a) for p, m, a in secenekler if yanit.lower() in m.lower() or yanit.lower() in a.lower()]
        if not eslesen:
            print(f"  '{yanit}' adında model bulunamadı.")
            return False
        yeni_provider, yeni_model, _ = eslesen[0]

    # Agent config'ini guncelle
    agent.config["default_model"]    = yeni_model
    agent.config["default_provider"] = yeni_provider

    if yeni_provider == "ollama":
        agent.config.setdefault("providers", {})["ollama"] = {
            "base_url": OLLAMA_BASE,
            "api_key": "not-needed",
        }

    # Provider'i dogrula (kredi kontrolu)
    if yeni_provider not in ("lmstudio", "ollama", "groq", "moonshot"):
        print(f"  {yeni_provider} kontrol ediliyor...")
        import urllib.request as _ureq
        import urllib.error as _uerr
        try:
            prov_conf = agent.config.get("providers", {}).get(yeni_provider, {})
            base_url = prov_conf.get("base_url", "")
            api_key = prov_conf.get("api_key", "") or _env_deger(_BULUT_ENV.get(yeni_provider, ""))
            if not api_key:
                print(f"  [HATA] API anahtari bulunamadi ({yeni_provider})")
                return False

            req = _ureq.Request(
                f"{base_url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                method="GET",
            )
            with _ureq.urlopen(req, timeout=5) as resp:
                pass
        except _uerr.HTTPError as e:
            if e.code == 402:
                print(f"  [HATA] {yeni_provider} kredisi yok (HTTP 402)")
                print("  Lutfen baska bir model secin.")
                return False
            elif e.code == 401:
                print(f"  [HATA] {yeni_provider} API anahtari gecersiz (HTTP 401)")
                return False
            else:
                print(f"  [HATA] {yeni_provider} erisim hatasi: HTTP {e.code}")
                print("  Bu modeli tekrar denemek icin /model yazin.")
                return False
        except Exception as e:
            print(f"  [UYARI] {yeni_provider} dogrulama basarisiz: {e}")
            print("  Devam ediliyor...")

    # Provider'i yeniden olustur
    try:
        from reymen.cereyan.beyin import Beyin
        yeni_beyin = Beyin(agent.config)
        agent.provider = yeni_beyin
        # planlayici da yenile (Planlayici(provider) alıyor)
        try:
            from reymen.cereyan.planlayici import Planlayici
            agent.planlayici = Planlayici(agent.provider)
        except Exception as _baslangi_e443:
            print(f"[UYARI] baslangic_kontrol.py:444 - {_baslangi_e443}")
        print(f"\n  [OK] Model degistirildi: [{yeni_provider}] {yeni_model}")
        return True
    except Exception as e:
        print(f"  [Hata] Provider yenilenirken sorun: {e}")
        return False


if __name__ == "__main__":
    print("=== Başlangıç Kontrol Testi ===")
    print(f"API anahtarları: {api_anahtari_var_mi()}")
    print(f"Ollama çalışıyor: {ollama_calisiyor_mu()}")
    print(f"Yüklü modeller: {ollama_modeller()}")
    print(f"llava yüklü: {llava_yuklu_mu()}")
