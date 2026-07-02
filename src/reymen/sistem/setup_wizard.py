# -*- coding: utf-8 -*-
"""setup_wizard.py — ReYMeN ilk kurulum sihirbazi (reymen setup).

Hermes'teki 'hermes setup' komutunun ReYMeN karsiligi.
reymen setup veya eksik kurulumda otomatik baslar.

Kontrol listesi:
  a) Hosgeldin mesaji + logo
  b) Python versiyon kontrolu (3.11+ gerekli)
  c) Git kontrolu
  d) FFmpeg kontrolu
  e) Playwright kontrolu (gerekirse kur)
  f) API key yapilandirmasi (DeepSeek oncelikli)
  g) config.yaml olusturma/kontrol
  h) SOUL.md kontrolu
  i) skills/ dizini kontrolu
"""

import os
import sys
import shutil
import subprocess
import json
import time
from pathlib import Path
from typing import Optional

# ── Renkler (reymen_launcher.py ile uyumlu) ──────────────────────────────────
_R   = "\033[0m"
_C   = "\033[96m"   # cyan
_G   = "\033[92m"   # green
_Y   = "\033[93m"   # yellow
_B   = "\033[94m"   # blue
_M   = "\033[95m"   # magenta
_W   = "\033[97m"   # white
_D   = "\033[2m"    # dim
_RED = "\033[91m"   # kirmizi

def _c(t):   return f"{_C}{t}{_R}"
def _g(t):   return f"{_G}{t}{_R}"
def _y(t):   return f"{_Y}{t}{_R}"
def _mavi(t): return f"{_B}{t}{_R}"
def _d(t):   return f"{_D}{t}{_R}"
def _r(t):   return f"{_RED}{t}{_R}"

# ── Logo ──────────────────────────────────────────────────────────────────────
_REYMEN_LOGO = f"""
{_c('██████╗ ███████╗██╗   ██╗███╗   ███╗███████╗███╗   ██╗')}
{_c('██╔══██╗██╔════╝╚██╗ ██╔╝████╗ ████║██╔════╝████╗  ██║')}
{_y('██████╔╝█████╗   ╚████╔╝ ██╔████╔██║█████╗  ██╔██╗ ██║')}
{_y('██╔══██╗██╔══╝    ╚██╔╝  ██║╚██╔╝██║██╔══╝  ██║╚██╗██║')}
{_mavi('██║  ██║███████╗   ██║   ██║ ╚═╝ ██║███████╗██║ ╚████║')}
{_mavi('╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝')}
"""


# ── Yardimcilar ───────────────────────────────────────────────────────────────
def _soru(prompt: str, varsayilan: str = "") -> str:
    """Kullanicidan girdi al, varsayilan deger destekli."""
    if varsayilan:
        cevap = input(f"  {prompt} [{_d(varsayilan)}] ").strip()
        return cevap if cevap else varsayilan
    return input(f"  {prompt} ").strip()


def _evet_hayir(prompt: str, varsayilan: bool = True) -> bool:
    """Evet/Hayir sorusu."""
    secenek = "[Y/n]" if varsayilan else "[y/N]"
    cevap = input(f"  {prompt} {secenek} ").strip().lower()
    if not cevap:
        return varsayilan
    return cevap in ("y", "yes", "e", "evet")


def _kontrol_ad(ad: str, durum: bool, mesaj: str = "") -> None:
    """Standart kontrol satiri yazdir."""
    ikon = _g("✓") if durum else _r("✗")
    ek = f" — {_d(mesaj)}" if mesaj else ""
    print(f"  {ikon} {ad}{ek}")


# ── 1. Python versiyon kontrolu ───────────────────────────────────────────────
def python_kontrol() -> bool:
    """Python 3.11+ kontrolu."""
    print(f"\n  {_c('▸ Python Versiyon Kontrolü')}")
    v = sys.version_info
    yeterli = v.major == 3 and v.minor >= 11
    if yeterli:
        _kontrol_ad(f"Python {v.major}.{v.minor}.{v.micro}", True)
    else:
        _kontrol_ad(f"Python {v.major}.{v.minor}.{v.micro}", False,
                     f"3.11+ gerekli! Su an: {v.major}.{v.minor}")
    return yeterli


# ── 2. Git kontrolu ───────────────────────────────────────────────────────────
def git_kontrol() -> bool:
    """Git yuklu mu kontrol et."""
    print(f"\n  {_c('▸ Git Kontrolü')}")
    git_path = shutil.which("git")
    if git_path:
        try:
            r = subprocess.run(["git", "--version"], capture_output=True,
                               text=True, timeout=5)
            versiyon = r.stdout.strip() if r.returncode == 0 else "bilinmiyor"
            _kontrol_ad(f"Git: {versiyon}", True)
            return True
        except Exception:
            _kontrol_ad("Git", False, "calistirilamadi")
            return False
    else:
        _kontrol_ad("Git", False, "PATH'te bulunamadi")
        return False


# ── 3. FFmpeg kontrolu ────────────────────────────────────────────────────────
def ffmpeg_kontrol() -> bool:
    """FFmpeg yuklu mu."""
    print(f"\n  {_c('▸ FFmpeg Kontrolü')}")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        try:
            r = subprocess.run(["ffmpeg", "-version"], capture_output=True,
                               text=True, timeout=5)
            ilk_satir = r.stdout.splitlines()[0] if r.stdout else "ffmpeg"
            _kontrol_ad(f"FFmpeg: {ilk_satir[:50]}...", True)
            return True
        except Exception:
            _kontrol_ad("FFmpeg", False, "calistirilamadi")
            return False
    else:
        _kontrol_ad("FFmpeg", False, "PATH'te bulunamadi")
        return False


# ── 4. Playwright kontrolu + kurulum ──────────────────────────────────────────
def playwright_kontrol(oto_kur: bool = False) -> bool:
    """Playwright yuklu mu, gerekirse kur."""
    print(f"\n  {_c('▸ Playwright Kontrolü')}")

    # 1) Python paketi var mi?
    import importlib.util as _iu
    paket_var = _iu.find_spec("playwright") is not None
    if not paket_var:
        _kontrol_ad("playwright paketi", False, "yuklu degil")
        if oto_kur:
            if _evet_hayir("  Playwright kurulsun mu?", True):
                print(f"  {_y('⟳')} pip install playwright ...")
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "playwright"],
                    capture_output=True, text=True, timeout=120
                )
                if r.returncode == 0:
                    _kontrol_ad("playwright paketi", True, "yuklendi")
                    paket_var = True
                else:
                    _kontrol_ad("playwright paketi", False,
                                 f"hata: {r.stderr[:80]}")
        else:
            _kontrol_ad("playwright paketi", False, "--fix ile otomatik kurulabilir")
    else:
        _kontrol_ad("playwright paketi", True)

    # 2) Browser binary'leri var mi?
    if paket_var:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browserler = [b for b in ["chromium", "firefox", "webkit"]
                              if getattr(p, b, None) is not None]
                _kontrol_ad(f"Playwright browser'lar ({', '.join(browserler)})", True)
        except Exception:
            _kontrol_ad("Playwright browser binary'leri", False,
                         "chromium install gerekebilir")
            if oto_kur and _evet_hayir("  Playwright browser'lari kuralim mi?", True):
                print(f"  {_y('⟳')} playwright install chromium ...")
                r = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True, text=True, timeout=300
                )
                if r.returncode == 0:
                    _kontrol_ad("Playwright chromium", True, "yuklendi")
                else:
                    _kontrol_ad("Playwright install", False, r.stderr[:80])
    return paket_var


# ── 5. API Key yapilandirmasi ─────────────────────────────────────────────────
def _api_key_kontrol(env_var: str, ad: str, dosya_yolu: Path) -> Optional[str]:
    """Belirtilen env var'ini kontrol et, yoksa kullaniciya sor."""
    # Once .env'den oku
    anahtar = os.environ.get(env_var, "")

    if not anahtar and dosya_yolu.exists():
        # .env dosyasindan oku
        for satir in dosya_yolu.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir.startswith(f"{env_var}="):
                anahtar = satir.split("=", 1)[1].strip().strip("\"'")
                break

    if anahtar:
        gizli = anahtar[:8] + "..." + anahtar[-4:] if len(anahtar) > 12 else "***"
        _kontrol_ad(f"{ad} ({env_var})", True, gizli)
        return anahtar
    else:
        _kontrol_ad(f"{ad} ({env_var})", False, "ANAHTAR YOK")
        return None


def api_key_yapilandir(proje_kok: Path, oto_kur: bool = False) -> dict:
    """API anahtarlarini kontrol et ve yapilandir."""
    print(f"\n  {_c('▸ API Key Yapılandırması')}")
    env_yol = proje_kok / ".env"

    oncelikli_provider = "DeepSeek"
    oncelikli_env = "DEEPSEEK_API_KEY"

    sonuclar = {}

    # DeepSeek (oncelikli)
    anahtar = _api_key_kontrol(oncelikli_env, oncelikli_provider, env_yol)
    sonuclar[oncelikli_env] = anahtar is not None

    if not anahtar and oto_kur:
        print(f"\n  {_y('!')} {oncelikli_provider} API anahtari bulunamadi.")
        print(f"  {_d('Almak icin: https://platform.deepseek.com/api_keys')}")
        girilen = _soru(f"{oncelikli_provider} API Key girin (bos gecmek icin Enter):")
        if girilen:
            # .env'ye yaz
            _env_anahtar_ekle(env_yol, oncelikli_env, girilen)
            os.environ[oncelikli_env] = girilen
            sonuclar[oncelikli_env] = True
            _kontrol_ad(f"{oncelikli_provider} API Key", True, "kaydedildi")

    # Diger provider'lar (opsiyonel)
    diger_providerlar = [
        ("OPENROUTER_API_KEY", "OpenRouter"),
        ("GROQ_API_KEY", "Groq"),
        ("XAI_API_KEY", "xAI"),
        ("XIAOMI_API_KEY", "Xiaomi/MiniMax"),
        ("ANTHROPIC_API_KEY", "Anthropic"),
        ("OPENAI_API_KEY", "OpenAI"),
    ]

    for env_var, ad in diger_providerlar:
        anahtar = _api_key_kontrol(env_var, ad, env_yol)
        sonuclar[env_var] = anahtar is not None
        if not anahtar and oto_kur and _evet_hayir(f"  {ad} API key eklemek ister misiniz?", False):
            girilen = _soru(f"  {ad} API Key girin (bos gecmek icin Enter):")
            if girilen:
                _env_anahtar_ekle(env_yol, env_var, girilen)
                os.environ[env_var] = girilen
                sonuclar[env_var] = True

    return sonuclar


def _env_anahtar_ekle(env_yol: Path, key: str, value: str) -> None:
    """.env dosyasina anahtar ekle (varolan satiri guncelle, yoksa ekle)."""
    if not env_yol.exists():
        env_yol.write_text(f"{key}={value}\n", encoding="utf-8")
        return

    lines = env_yol.read_text(encoding="utf-8").splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"#{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")

    env_yol.write_text("".join(lines), encoding="utf-8")


# ── 6. config.yaml kontrolu ───────────────────────────────────────────────────
KURULUM_ANAHTARI = "kurulum_tamamlandi"
VARSAYILAN_CONFIG = {
    "agent": {
        "api_max_retries": 1,
        "api_timeout": 60,
        "environment_probe": True,
        "gateway_timeout": 1800,
        "max_turns": 90,
        "parallel_tool_call_guidance": True,
        "task_completion_guidance": True,
        "tool_use_enforcement": "auto",
    },
    "model": {
        "default": "deepseek-v4-flash",
        "provider": "deepseek",
        "api_mode": "chat_completions",
    },
    "display": {
        "language": "tr",
        "interface": "gateway",
        "compact": False,
    },
    "memory": {
        "enabled": True,
        "max_chars": 10000,
    },
    "kurulum_tamamlandi": False,
}


def config_kontrol(proje_kok: Path, oto_kur: bool = False) -> bool:
    """config.yaml kontrol et, yoksa olustur."""
    print(f"\n  {_c('▸ config.yaml Kontrolü')}")
    config_yol = proje_kok / "config.yaml"

    if config_yol.exists():
        icerik = config_yol.read_text(encoding="utf-8")
        _kontrol_ad("config.yaml", True, f"{len(icerik)} bayt")
        # kurulum_tamamlandi anahtari var mi kontrol et
        if KURULUM_ANAHTARI not in icerik and oto_kur:
            if _evet_hayir(f"  config.yaml'de '{KURULUM_ANAHTARI}' anahtari yok. Eklensin mi?", True):
                _config_anahtar_ekle(config_yol)
        return True
    else:
        _kontrol_ad("config.yaml", False, "DOSYA YOK")
        if oto_kur:
            if _evet_hayir("  Varsayilan config.yaml olusturulsun mu?", True):
                _config_olustur(config_yol, proje_kok)
                return True
        return False


def _config_olustur(config_yol: Path, proje_kok: Path) -> None:
    """Varsayilan config.yaml olustur."""
    import yaml as _yaml

    config = dict(VARSAYILAN_CONFIG)

    # Mevcut .env'den model/provider oku
    env_yol = proje_kok / ".env"
    if env_yol.exists():
        for satir in env_yol.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir.startswith("REYMEN_PROVIDER="):
                config["model"]["provider"] = satir.split("=", 1)[1].strip().strip("\"'")
            elif satir.startswith("REYMEN_MODEL="):
                config["model"]["default"] = satir.split("=", 1)[1].strip().strip("\"'")

    try:
        with open(config_yol, "w", encoding="utf-8") as f:
            _yaml.dump(config, f, default_flow_style=False, allow_unicode=True,
                       sort_keys=False)
        _kontrol_ad("config.yaml olusturuldu", True)
    except Exception as e:
        _kontrol_ad("config.yaml olusturulamadi", False, str(e))


def _config_anahtar_ekle(config_yol: Path) -> None:
    """config.yaml'e kurulum_tamamlandi anahtarini ekle."""
    try:
        icerik = config_yol.read_text(encoding="utf-8")
        # Dosyanin sonuna ekle
        icerik += f"\n# Kurulum durumu (setup_wizard)\n{KURULUM_ANAHTARI}: false\n"
        config_yol.write_text(icerik, encoding="utf-8")
        _kontrol_ad(f"'{KURULUM_ANAHTARI}' eklendi", True)
    except Exception as e:
        _kontrol_ad(f"'{KURULUM_ANAHTARI}' eklenemedi", False, str(e))


def kurulum_durumu_guncelle(proje_kok: Path, tamamlandi: bool = True) -> bool:
    """config.yaml'de kurulum_tamamlandi'yi guncelle."""
    config_yol = proje_kok / "config.yaml"
    if not config_yol.exists():
        return False

    try:
        icerik = config_yol.read_text(encoding="utf-8")
        import re
        yeni_icerik, sayi = re.subn(
            rf"^{KURULUM_ANAHTARI}\s*:\s*(true|false)",
            f"{KURULUM_ANAHTARI}: {str(tamamlandi).lower()}",
            icerik,
            flags=re.MULTILINE,
        )
        if sayi == 0:
            # Anahtar yoksa ekle
            yeni_icerik = icerik.rstrip() + f"\n{KURULUM_ANAHTARI}: {str(tamamlandi).lower()}\n"

        config_yol.write_text(yeni_icerik, encoding="utf-8")

        # JSON durum dosyasina da yaz
        durum_yol = proje_kok / "durum.json"
        if durum_yol.exists():
            try:
                durum = json.loads(durum_yol.read_text(encoding="utf-8"))
                durum["kurulum"] = {
                    "tamamlandi": tamamlandi,
                    "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                durum_yol.write_text(json.dumps(durum, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
            except Exception:
                pass

        return True
    except Exception:
        return False


def kurulum_tamamlandi_mi(proje_kok: Path) -> bool:
    """config.yaml'den kurulum durumunu oku."""
    config_yol = proje_kok / "config.yaml"
    if not config_yol.exists():
        return False

    try:
        icerik = config_yol.read_text(encoding="utf-8")
        import re
        eslesme = re.search(rf"^{KURULUM_ANAHTARI}\s*:\s*(true|false)", icerik, re.MULTILINE)
        if eslesme:
            return eslesme.group(1) == "true"
    except Exception:
        pass

    return False


# ── 7. SOUL.md kontrolu ───────────────────────────────────────────────────────
def soul_kontrol(proje_kok: Path, oto_kur: bool = False) -> bool:
    """SOUL.md kontrol et, yoksa olustur."""
    print(f"\n  {_c('▸ SOUL.md Kontrolü')}")
    soul_yol = proje_kok / "SOUL.md"

    if soul_yol.exists():
        icerik = soul_yol.read_text(encoding="utf-8")
        _kontrol_ad("SOUL.md", True, f"{len(icerik)} karakter")
        return True
    else:
        _kontrol_ad("SOUL.md", False, "DOSYA YOK")
        if oto_kur:
            if _evet_hayir("  Varsayilan SOUL.md olusturulsun mu?", True):
                _soul_olustur(soul_yol)
                return True
        return False


def _soul_olustur(soul_yol: Path) -> None:
    """Varsayilan SOUL.md olustur."""
    icerik = """# ReYMeN — SOUL.md

> ReYMeN, yardimsever ve bagimsiz bir AI asistanidir.
> Kisa ve oz cevap verir. Turkce konusur.

## Kisilik

- Yardimsever ve anlayisli
- Dogrudan ve net
- Karmasik konulari basitlestirir
- Surekli ogrenir ve gelisir

## Yetenekler

- Dogal dil anlama ve uretme
- Kod yazma ve analiz
- Dosya sistemi erisimi
- Web aramasi
- Gorsel tanima

## Sinirlar

- Gercek zamanli bilgi icin web aramasi yapabilir
- Dosya olusturabilir ve duzenleyebilir
- Terminal komutlari calistirabilir
"""
    soul_yol.write_text(icerik, encoding="utf-8")
    _kontrol_ad("SOUL.md", True, "varsayilan olarak olusturuldu")


# ── 8. skills/ dizini kontrolu ────────────────────────────────────────────────
def skills_kontrol(proje_kok: Path, oto_kur: bool = False) -> bool:
    """skills/ dizinini kontrol et."""
    print(f"\n  {_c('▸ Skills Dizini Kontrolü')}")

    skills_dizinleri = [
        proje_kok / "skills",
        proje_kok / ".ReYMeN" / "skills",
    ]

    bulunan = [d for d in skills_dizinleri if d.exists() and d.is_dir()]
    if bulunan:
        for d in bulunan:
            dosya_sayisi = len(list(d.iterdir())) if list(d.iterdir()) else 0
            _kontrol_ad(f"skills: {d.name}", True, f"{dosya_sayisi} dosya")
        return True
    else:
        _kontrol_ad("skills/ dizini", False, "HICBIRI YOK")
        if oto_kur:
            if _evet_hayir("  skills/ dizini olusturulsun mu?", True):
                skills_dizini = proje_kok / "skills"
                skills_dizini.mkdir(parents=True, exist_ok=True)
                (skills_dizini / ".gitkeep").write_text("")
                _kontrol_ad("skills/", True, "olusturuldu")

                # .ReYMeN/skills/ de olustur
                reymen_skills = proje_kok / ".ReYMeN" / "skills"
                reymen_skills.mkdir(parents=True, exist_ok=True)
                (reymen_skills / ".gitkeep").write_text("")
                return True
        return False


# ── Ana Setup Sihirbazi ───────────────────────────────────────────────────────
def setup_calistir(proje_kok: Optional[Path] = None, oto_kur: bool = False,
                   sadece_kontrol: bool = False) -> dict:
    """Ana setup sihirbazini calistir.

    Args:
        proje_kok: Proje kok dizini (None = otomatik bul)
        oto_kur: Eksikleri otomatik duzeltmeye calis
        sadece_kontrol: Sadece kontrol et, hicbir sey degistirme

    Returns:
        dict: {\"basarili\": bool, \"sonuclar\": {...}, \"hata\": str}
    """
    if proje_kok is None:
        proje_kok = Path(__file__).parent.parent.parent.resolve()
        # reymen_launcher.py'nin oldugu yer
        launcher = Path(__file__).parent.parent.parent.parent / "reymen_launcher.py"
        if launcher.exists():
            proje_kok = launcher.parent

    proje_kok = Path(proje_kok).resolve()
    print()
    print(f"  {'═' * 55}")
    print(f"  {_c('ReYMeN Kurulum Sihirbazi')}    {_d('v1.0.0')}")
    print(f"  {'═' * 55}")
    print(f"  {_d('Proje:')} {proje_kok}")
    print(f"  {_d('Tarih:')} {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {'═' * 55}")
    print(f"  {_g('Hosgeldiniz!')} ReYMeN Ajan kurulumu basliyor.")
    print()

    sonuclar = {}
    hatali = 0
    toplam = 0

    # a) Logo zaten yukarda basildi

    # b) Python kontrol
    toplam += 1
    sonuclar["python"] = python_kontrol()
    if not sonuclar["python"]:
        hatali += 1

    # c) Git kontrol
    toplam += 1
    sonuclar["git"] = git_kontrol()
    if not sonuclar["git"]:
        hatali += 1

    # d) FFmpeg kontrol
    toplam += 1
    sonuclar["ffmpeg"] = ffmpeg_kontrol()
    if not sonuclar["ffmpeg"]:
        hatali += 1

    # e) Playwright kontrol
    toplam += 1
    sonuclar["playwright"] = playwright_kontrol(oto_kur=oto_kur)
    if not sonuclar["playwright"]:
        hatali += 1

    # f) API Key yapilandirmasi
    toplam += 1
    api_sonuclar = api_key_yapilandir(proje_kok, oto_kur=oto_kur)
    sonuclar["api_keys"] = api_sonuclar
    deepseek_ok = api_sonuclar.get("DEEPSEEK_API_KEY", False)
    if not deepseek_ok:
        hatali += 1

    # g) config.yaml kontrol
    toplam += 1
    sonuclar["config"] = config_kontrol(proje_kok, oto_kur=oto_kur)
    if not sonuclar["config"]:
        hatali += 1

    # h) SOUL.md kontrol
    toplam += 1
    sonuclar["soul"] = soul_kontrol(proje_kok, oto_kur=oto_kur)
    if not sonuclar["soul"]:
        hatali += 1

    # i) skills/ dizini kontrol
    toplam += 1
    sonuclar["skills"] = skills_kontrol(proje_kok, oto_kur=oto_kur)
    if not sonuclar["skills"]:
        hatali += 1

    # ── Ozet ──────────────────────────────────────────────────────────────────
    print(f"\n  {'─' * 55}")
    print(f"  {_c('Kurulum Özeti')}")
    print(f"  {'─' * 55}")

    for ad, durum in sonuclar.items():
        if ad == "api_keys":
            for k, v in durum.items():
                gizli_ad = k.replace("_API_KEY", "").replace("_", " ").strip()
                _kontrol_ad(f"  API: {gizli_ad}", v)
        else:
            _kontrol_ad(f"  {ad}", durum)

    print(f"  {'─' * 55}")
    if hatali == 0:
        print(f"  {_g('✓ Tum kontroller basarili!')}")
        print(f"  {_g('ReYMeN kullanima hazir.')}")
    else:
        print(f"  {_y(f'{hatali}/{toplam} kontrol basarisiz')}")
        if oto_kur:
            print(f"  {_y('Bazilari otomatik duzeltilmis olabilir.')}")
        else:
            print(f"  {_y('--fix ile otomatik duzeltmeyi dene.')}")

    print(f"  {'─' * 55}")
    print()

    basarili = hatali == 0

    # Kurulum durumunu kaydet
    if basarili or oto_kur:
        kurulum_durumu_guncelle(proje_kok, tamamlandi=(hatali == 0))

    return {
        "basarili": basarili,
        "sonuclar": sonuclar,
        "hatali": hatali,
        "toplam": toplam,
        "proje_kok": str(proje_kok),
    }


# ── Dogrudan calistirma ────────────────────────────────────────────────────────
def main() -> int:
    """Komut satirindan calistirildiginda."""
    import argparse

    parser = argparse.ArgumentParser(description="ReYMeN Kurulum Sihirbazi")
    parser.add_argument("--fix", action="store_true",
                        help="Eksikleri otomatik duzeltmeye calis")
    parser.add_argument("--check", action="store_true",
                        help="Sadece kontrol et, degisiklik yapma")
    parser.add_argument("--proje", type=str, default=None,
                        help="Proje kok dizini")

    args = parser.parse_args()

    proje_kok = Path(args.proje) if args.proje else None
    sonuc = setup_calistir(
        proje_kok=proje_kok,
        oto_kur=args.fix,
        sadece_kontrol=args.check,
    )

    return 0 if sonuc["basarili"] else 1


if __name__ == "__main__":
    sys.exit(main())
