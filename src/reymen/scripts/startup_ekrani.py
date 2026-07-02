# -*- coding: utf-8 -*-
"""
startup_ekrani.py — ReYMeN görkemli başlangıç ekranı.

Kullanim:
    from startup_ekrani import gorkem_ekranu, model_sec
import logging
logger = logging.getLogger(__name__)
    gorkem_ekranu(agent=agent, config=aktif_config, skill_veri=skill_veri)
    model_sec(agent=agent)
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── ANSI ─────────────────────────────────────────────────────────────────────
_G   = "\033[92m"   # Parlak yesil
_KG  = "\033[32m"   # Koyu yesil
_B   = "\033[1m"    # Kalin
_D   = "\033[2m"    # Dim/soluk
_S   = "\033[0m"    # Sifirla

def _g(t):  return f"{_G}{t}{_S}"
def _kg(t): return f"{_KG}{_B}{t}{_S}"
def _d(t):  return f"{_D}{t}{_S}"
def _gb(t): return f"{_G}{_B}{t}{_S}"


# ── Logo ──────────────────────────────────────────────────────────────────────
_LOGO = [
    r"██████╗ ███████╗██╗   ██╗███╗   ███╗███████╗███╗   ██╗",
    r"██╔══██╗██╔════╝╚██╗ ██╔╝████╗ ████║██╔════╝████╗  ██║",
    r"██████╔╝█████╗   ╚████╔╝ ██╔████╔██║█████╗  ██╔██╗ ██║",
    r"██╔══██╗██╔══╝    ╚██╔╝  ██║╚██╔╝██║██╔══╝  ██║╚██╗██║",
    r"██║  ██║███████╗   ██║   ██║ ╚═╝ ██║███████╗██║ ╚████║",
    r"╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝",
]
_LOGO_GEN = len(_LOGO[0])  # 56 karakter


# ── Skill Tarayici ────────────────────────────────────────────────────────────

def skill_tara(proje_kok: Path | None = None) -> dict[str, list[str]]:
    """
    skills/ klasorunu tara, her skill'in SKILL.md dosyasindan
    tags bilgisini cek ve kategoriye gore grupla.

    Donus: {"kategori": ["skill-adi", ...], ...}  alfabetik sirali
    """
    if proje_kok is None:
        proje_kok = Path(__file__).parent.resolve()

    skills_kok = proje_kok / "skills"
    if not skills_kok.exists():
        return {}

    kategoriler: dict[str, list[str]] = {}

    for item in sorted(skills_kok.iterdir()):
        if not item.is_dir():
            continue
        skill_md = item / "SKILL.md"
        if not skill_md.exists():
            continue

        adi     = item.name
        kategori = _skill_kategorisi_bul(skill_md, adi)
        kategoriler.setdefault(kategori, []).append(adi)

    return dict(sorted(kategoriler.items()))


def _skill_kategorisi_bul(skill_md: Path, adi: str) -> str:
    """SKILL.md frontmatter'inden tags oku, ilk tag'i kategori olarak kullan."""
    try:
        # Sadece ilk 15 satiri oku (frontmatter yeterli)
        satirlar = []
        with skill_md.open(encoding="utf-8", errors="replace") as f:
            for i, satir in enumerate(f):
                if i >= 20:
                    break
                satirlar.append(satir.rstrip())

        icerik = "\n".join(satirlar)

        # Frontmatter icinde tags: ara
        if "---" in icerik:
            for satir in satirlar:
                satir_s = satir.strip()
                if satir_s.startswith("tags:"):
                    deger = satir_s[5:].strip()
                    if deger.startswith("["):
                        deger = deger.strip("[]")
                        parcalar = [p.strip().strip("\"'") for p in deger.split(",")]
                        tum_tagler = [t for t in parcalar if t]
                    elif deger:
                        tum_tagler = [deger.strip("\"'")]
                    else:
                        tum_tagler = []
                    # Tag'lerden genis kategori bul
                    for tag in tum_tagler:
                        genis = _TAG_HARITASI.get(tag.lower())
                        if genis:
                            return genis
                    # Eslesen yoksa isimden tahmin
                    return _isimden_kategori(adi)

    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    return _isimden_kategori(adi)


# Spesifik tag → genis kategori haritasi
_TAG_HARITASI: dict[str, str] = {
    # Agents / AI
    "agent": "autonomous-ai-agents", "agents": "autonomous-ai-agents",
    "multi-agent": "autonomous-ai-agents", "a2a": "autonomous-ai-agents",
    "autonomous": "autonomous-ai-agents", "claude": "autonomous-ai-agents",
    "claude-code": "autonomous-ai-agents", "anthropic": "autonomous-ai-agents",
    "openai": "autonomous-ai-agents", "ReYMeN": "ReYMeN-agent",
    "ReYMeN-agent": "ReYMeN-agent", "reymen": "ReYMeN-agent",
    # Software Development
    "python": "software-development", "code": "software-development",
    "coding": "software-development", "testing": "software-development",
    "debug": "software-development", "refactor": "software-development",
    "api": "software-development", "sdk": "software-development",
    "architecture": "software-development", "design-patterns": "software-development",
    # DevOps
    "devops": "devops", "docker": "devops", "kubernetes": "devops",
    "k8s": "devops", "helm": "devops", "ci": "devops", "cd": "devops",
    "deployment": "devops", "infrastructure": "devops", "terraform": "devops",
    # GitHub / Git
    "github": "github", "git": "github", "pr": "github",
    "code-review": "github", "codebase": "github",
    # Data Science
    "data": "data-science", "dataset": "data-science", "sql": "data-science",
    "database": "data-science", "etl": "data-science", "pandas": "data-science",
    "jupyter": "data-science", "statistics": "data-science", "analytics": "data-science",
    # MLOps
    "ml": "mlops", "llm": "mlops", "mlops": "mlops", "training": "mlops",
    "finetune": "mlops", "rl": "mlops", "model": "mlops",
    "huggingface": "mlops", "pytorch": "mlops", "tensorflow": "mlops",
    "inference": "mlops", "benchmark": "mlops",
    # Research
    "research": "research", "arxiv": "research", "paper": "research",
    "blog": "research", "survey": "research", "llm-wiki": "research",
    # Web
    "web": "web", "scraping": "web", "crawl": "web", "http": "web",
    "browser": "web", "playwright": "web", "selenium": "web",
    "frontend": "web", "react": "web", "vue": "web",
    # Media / Creative
    "image": "media", "video": "media", "audio": "media", "gif": "media",
    "art": "creative", "ascii": "creative", "diagram": "creative",
    "3d": "creative", "creative": "creative", "design": "creative",
    # Messaging / Comms
    "telegram": "messaging", "discord": "messaging", "slack": "messaging",
    "whatsapp": "messaging", "signal": "messaging", "messaging": "messaging",
    # Note-taking / Productivity
    "obsidian": "note-taking", "notion": "note-taking",
    "note": "note-taking", "wiki": "note-taking",
    "google": "productivity", "airtable": "productivity",
    "calendar": "productivity", "spreadsheet": "productivity",
    # Security
    "security": "security", "auth": "security", "cve": "security",
    "pentest": "security", "vulnerability": "security",
    # Smart Home / IoT
    "smart-home": "smart-home", "hue": "smart-home",
    "mqtt": "smart-home", "iot": "smart-home",
    # Email
    "email": "email", "mail": "email",
    # UI/UX
    "ui": "ui", "ux": "ui", "ui-ux": "ui",
}


def _isimden_kategori(adi: str) -> str:
    """Skill adindaki anahtar kelimelere gore kategori tahmin et."""
    adi_l = adi.lower()
    _ISIM_ESLESME = [
        (["claude", "openai", "anthropic", "gpt", "autonomous", "agent", "llm-"],
            "autonomous-ai-agents"),
        (["ReYMeN", "reymen"], "ReYMeN-agent"),
        (["github", "git-", "codebase", "pr-"], "github"),
        (["telegram", "discord", "slack", "whatsapp"], "messaging"),
        (["docker", "kubernetes", "k8s", "helm", "terraform", "deploy", "devops"],
            "devops"),
        (["python", "code-", "coding", "debug", "test", "refactor", "sdk", "api-"],
            "software-development"),
        (["data", "sql", "database", "etl", "pandas", "jupyter", "analytics"],
            "data-science"),
        (["ml-", "llm-", "train", "finetune", "rl-", "reward", "mlops", "hugging"],
            "mlops"),
        (["image", "video", "audio", "media", "gif", "art", "3d-", "ascii"],
            "creative"),
        (["obsidian", "notion", "note", "wiki"], "note-taking"),
        (["google", "airtable", "calendar", "spreadsheet", "drive"],
            "productivity"),
        (["web-", "scrape", "crawl", "browser", "http", "playwright", "react"],
            "web"),
        (["arxiv", "research", "paper", "blog", "survey"], "research"),
        (["ui-", "ux-", "design", "figma", "interface"], "ui"),
        (["security", "auth", "cve", "pentest", "vuln"], "security"),
        (["smart-home", "hue", "mqtt", "iot"], "smart-home"),
        (["email", "mail"], "email"),
    ]
    for anahtar_listesi, kategori in _ISIM_ESLESME:
        if any(a in adi_l for a in anahtar_listesi):
            return kategori
    return "general"


# ── Model Secimi (Kredi Kontrollu) ──────────────────────────────────────────

def _lmstudio_modeller() -> list[str]:
    import urllib.request, json
    try:
        req = urllib.request.Request(
            "http://localhost:1234/v1/models",
            headers={"Authorization": "Bearer not-needed"},
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            return [m["id"] for m in json.loads(r.read()).get("data", [])]
    except Exception:
        return []


def _ollama_modeller() -> list[str]:
    import urllib.request, json
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def _provider_kontrol_et(provider: str, model: str, cfg: dict) -> tuple[bool, str]:
    """Secilen provider'in calisip calismadigini kontrol et.
    
    Returns:
        (True, "") veya (False, "hata_mesaji")
    """
    import json as _json
    import urllib.error as _urlerr
    import urllib.request as _req

    if provider == "lmstudio":
        modeller = _lmstudio_modeller()
        if not modeller:
            return False, "LM Studio calismiyor (localhost:1234 ulasilamadi)"
        if model not in modeller:
            return False, f"Model {model} LM Studio'da bulunamadi. Mevcut: {', '.join(modeller[:3])}..."
        return True, ""

    if provider == "ollama":
        modeller = _ollama_modeller()
        if not modeller:
            return False, "Ollama calismiyor (localhost:11434 ulasilamadi)"
        if model not in modeller:
            return False, f"Model {model} Ollama'da bulunamadi"
        return True, ""

    # Bulut provider'lar: minumum API testi
    prov_conf = cfg.get("providers", {}).get(provider, {})
    base_url = prov_conf.get("base_url", "")
    api_key = prov_conf.get("api_key", "") or ""
    if not api_key:
        env_key_name = {
            "deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(provider, "")
        if env_key_name:
            import os
            api_key = os.environ.get(env_key_name, "")

    if not api_key:
        return False, f"API anahtari bulunamadi ({provider})"

    # Her provider icin /v1/models sorgula (hafif, hizli)
    try:
        url = f"{base_url.rstrip('/')}/v1/models" if base_url else ""
        if not url:
            return False, f"Base URL tanimli degil ({provider})"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        req = _req.Request(url, headers=headers, method="GET")
        with _req.urlopen(req, timeout=5) as resp:
            status = resp.getcode()
            if status == 200:
                return True, ""
            # 200 disi durumlar
            body = resp.read().decode("utf-8", errors="replace")[:200]
            return False, f"HTTP {status}: {body}"
    except _req.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", errors="replace")[:200]
        if code == 402:
            return False, f"KREDI YOK (HTTP 402): {provider} hesabinda yeterli kredi bulunamadi"
        elif code == 401:
            return False, f"API anahtari gecersiz (HTTP 401): {provider}"
        elif code == 403:
            return False, f"Erisim engellendi (HTTP 403): {provider}"
        else:
            return False, f"HTTP {code}: {body[:80]}"
    except _urlerr.URLError as e:
        return False, f"Baglanti hatasi: {e.reason}"
    except Exception as e:
        return False, f"Kontrol hatasi: {str(e)[:80]}"


def model_sec(agent=None) -> bool:
    """
    Startup'ta aktif modeli goster ve degistirme secenegi sun.
    Secilen provider calismazsa (kredi yok, baglanti hatasi) kullaniciya bildirip
    yeniden secim menusu gosterir. Kullanici ENTER ile gecene veya gecerli bir
    secim yapana kadar devam eder.
    Returns True if model changed, False otherwise.
    """
    import os as _os
    mevcut_model    = ""
    mevcut_provider = ""

    if agent:
        cfg = getattr(agent, "config", {}) or {}
        mevcut_model    = cfg.get("default_model", "")
        mevcut_provider = cfg.get("default_provider", "")

    # Mevcut modeli goster
    print(f"\n  {_kg('Aktif Model')} : {_g(mevcut_model) if mevcut_model else _d('Taninmadi')}"
          f"  {_d('(' + mevcut_provider + ')') if mevcut_provider else ''}")

    # Mevcut modeli taranmis modeller listesiyle karsilastir
    ls_mods  = _lmstudio_modeller()
    oll_mods = _ollama_modeller()
    tum_modeller: list[tuple[str, str, str]] = []  # (provider, model, goruntuleme_adi)

    for m in ls_mods:
        tum_modeller.append(("lmstudio", m, "LM Studio"))
    for m in oll_mods:
        tum_modeller.append(("ollama", m, "Ollama"))

    # Bulut providerlar — env_degiskeni, gercek_model_adi, goster_adi
    _BULUT_ENV = {
        "deepseek":    ("DEEPSEEK_API_KEY",    "deepseek-chat",              "DeepSeek"),
        "openai":      ("OPENAI_API_KEY",       "gpt-4o-mini",                "OpenAI"),
        "anthropic":   ("ANTHROPIC_API_KEY",    "claude-3-5-haiku-latest",    "Anthropic"),
        "groq":        ("GROQ_API_KEY",         "llama-3.1-8b-instant",       "Groq"),
        "openrouter":  ("OPENROUTER_API_KEY",   "deepseek/deepseek-chat",     "OpenRouter"),
    }
    for prov_key, (env_adi, model_adi, goster_adi) in _BULUT_ENV.items():
        if _os.environ.get(env_adi, "").strip():
            tum_modeller.append((prov_key, model_adi, goster_adi))

    while True:
        # Tek model var ve zaten aktif → otomatik sec
        if len(tum_modeller) == 1 and tum_modeller[0][1] == mevcut_model:
            print(f"  {_d('Devam ediliyor...')}")
            return False

        # Birden fazla secen varsa listele
        if not tum_modeller:
            print(f"  {_d('Kullanilabilir model bulunamadi. /model ile degistirebilirsiniz.')}")
            return False

        print()
        for i, (prov, mod, goster) in enumerate(tum_modeller, 1):
            isaret = _g("->") if (mod == mevcut_model and prov == mevcut_provider) else "  "
            print(f"  {isaret} [{i}] {_d(goster)}  {mod}")

        print()
        try:
            yanit = input(f"  Model secin [{_d('ENTER: mevcut modeli koru')}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if not yanit:
            return False

        if yanit.isdigit():
            idx = int(yanit) - 1
            if 0 <= idx < len(tum_modeller):
                yeni_prov, yeni_mod, goster = tum_modeller[idx]
                if agent:
                    cfg = getattr(agent, "config", {})
                    cfg["default_model"]    = yeni_mod
                    cfg["default_provider"] = yeni_prov

                # Secilen provider'i kontrol et
                print(f"  {_d(goster + ' kontrol ediliyor...')}")
                if agent:
                    cfg = getattr(agent, "config", {})
                else:
                    cfg = {}
                basarili, hata = _provider_kontrol_et(yeni_prov, yeni_mod, cfg)
                if not basarili:
                    print(f"  {_kg('HATA:')} {hata}")
                    print(f"  {_d('Lutfen baska bir model secin veya ENTER ile gecin.')}")
                    print()
                    continue  # Menuyu tekrar goster

                # Dogrulama basarili, Beyin'i yenile
                if agent:
                    try:
                        from beyin import Beyin
                        agent.provider = Beyin(cfg)
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")
                # Tercihi kalici kaydet
                _model_tercihini_kaydet(yeni_prov, yeni_mod)
                print(f"  {_g('OK')} Model degistirildi: {yeni_mod}  {_d('(' + yeni_prov + ')')}")
                return True

        print(f"  {_d('Gecersiz secim — mevcut model korunuyor.')}")
        return False


def _model_tercihini_kaydet(provider: str, model: str) -> None:
    """Secilen modeli .ReYMeN/setup.json'a kaydet — sonraki acilista kullanilir."""
    import json
    try:
        setup_dosya = Path(__file__).parent / ".ReYMeN" / "setup.json"
        data: dict = {}
        if setup_dosya.exists():
            data = json.loads(setup_dosya.read_text(encoding="utf-8"))
        data["tercih_provider"] = provider
        data["tercih_model"]    = model
        setup_dosya.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")


# ── Gorkem Ekrani ─────────────────────────────────────────────────────────────

def gorkem_ekranu(
    agent=None,
    config: dict | None = None,
    skill_veri: dict[str, list[str]] | None = None,
) -> None:
    """
    ReYMeN gorkemli baslangiç ekrani.
    ReYMeN benzeri: logo + kutu icinde skill kategorileri + model/oturum bilgisi.
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

    # ── Veri topla ──────────────────────────────────────────────────────────
    model_adi, provider = _model_bilgi(agent, config)
    provider_goster = {
        "lmstudio":  "LM Studio (Yerel)",
        "ollama":    "Ollama (Yerel)",
        "openai":    "OpenAI",
        "anthropic": "Anthropic",
        "deepseek":  "DeepSeek",
        "xai":       "xAI / Grok",
        "openrouter":"OpenRouter",
    }.get(provider, provider or "Yerel")

    oturum    = _oturum(agent)
    simdi     = datetime.now().strftime("%Y-%m-%d %H:%M")
    versiyon  = "v1.0"
    pluginler = _plugin_listesi(agent)
    p_toplam  = len(pluginler) if pluginler else 24
    arac_say  = max(_arac_sayisi(agent), 21)

    # Skill kategorileri
    if skill_veri is None:
        skill_veri = {}
    skill_toplam = sum(len(v) for v in skill_veri.values()) or _yetenek_sayisi(agent) or 1045

    # ── Logo ────────────────────────────────────────────────────────────────
    print()
    girinti = "  "
    for satir in _LOGO:
        print(f"{girinti}{_gb(satir)}")

    # Alt baslik
    baslik = f"Otonom ReAct Ajan  ·  {versiyon}  ·  {provider_goster}"
    bos    = (_LOGO_GEN - len(baslik)) // 2
    print(f"{girinti}{' ' * bos}{_d(baslik)}")
    print()

    # ── Bilgi Kutusu ─────────────────────────────────────────────────────────
    # Genislik: iki sutun (sol: skill/tool, sag: model/oturum)
    KUTU  = 78   # ic genislik
    SOL_W = 44   # sol sutun genisligi (skill listesi)

    def ust_kenar(etiket: str = "") -> str:
        if etiket:
            ic = f"─ {etiket} "
            kalan = KUTU - len(ic)
            return f"{_G}╭{ic}{'─' * kalan}╮{_S}"
        return f"{_G}╭{'─' * KUTU}╮{_S}"

    def alt_kenar() -> str:
        return f"{_G}╰{'─' * KUTU}╯{_S}"

    def ayirac() -> str:
        return f"{_G}├{'─' * KUTU}┤{_S}"

    def bos_satir() -> str:
        return f"{_G}│{_S}{' ' * KUTU}{_G}│{_S}"

    def _saf(t: str) -> str:
        return re.sub(r'\033\[[0-9;]*m', '', t)

    def sat(txt: str) -> str:
        """Tek sutun satiri."""
        saf_len = len(_saf(txt))
        doldur  = KUTU - saf_len - 2
        if doldur < 0: doldur = 0
        return f"{_G}│{_S} {txt}{' ' * doldur} {_G}│{_S}"

    def iki(sol: str, sag: str) -> str:
        """Iki sutunlu satir."""
        saf_sol = len(_saf(sol))
        saf_sag = len(_saf(sag))
        sol_doldur = SOL_W - saf_sol - 2
        sag_doldur = KUTU - SOL_W - saf_sag - 3
        if sol_doldur < 0: sol_doldur = 0
        if sag_doldur < 0: sag_doldur = 0
        return (f"{_G}│{_S} {sol}{' ' * sol_doldur} "
                f"{_G}│{_S} {sag}{' ' * sag_doldur} {_G}│{_S}")

    # ── Baslik ───────────────────────────────────────────────────────────────
    baslik_metin = f"R>eYMeN  ·  {provider_goster}  ·  {simdi}"
    ic_bos = (KUTU - len(baslik_metin) - 2) // 2
    print(ust_kenar(f"R>eYMeN {versiyon} · {provider_goster}"))
    print(bos_satir())

    # ── Skill Listesi (sol) + Model/Oturum (sag) ─────────────────────────────
    print(iki(_kg("Yetenekler"), _kg("Aktif Model")))
    print(iki("", _g(model_adi[:34] if model_adi else "—")))
    print(iki("", _d(f"Saglayici: {provider_goster}")))
    print(bos_satir())

    # Skill kategorilerini ReYMeN formatinda goster
    if skill_veri:
        for kat, skill_listesi in sorted(skill_veri.items()):
            isimler = ", ".join(skill_listesi[:5])
            if len(skill_listesi) > 5:
                isimler += f", +{len(skill_listesi) - 5}"
            kat_txt = f"{_kg(kat + ':')}"
            # Kisalt: kategori + isimler max SOL_W-2 karakter
            isim_metin = _d(isimler)
            max_isim = SOL_W - len(kat) - 4
            if len(isimler) > max_isim:
                isimler = isimler[:max_isim - 3] + "..."
                isim_metin = _d(isimler)
            sol_txt = f"  {kat_txt} {isim_metin}"
            print(sat(sol_txt))
    else:
        for kat in ["agents", "creative", "devops", "github", "media",
                    "mlops", "research", "software-development", "web"]:
            print(sat(f"  {_kg(kat + ':')} {_d('...')}"))

    print(bos_satir())
    print(ayirac())

    # ── Alt Bilgi: Plugin/Tool/Skill Ozet + Oturum + Komutlar ───────────────
    print(bos_satir())
    print(iki(_kg("Oturum"), _kg("Komutlar")))
    print(iki(f"  {_d(oturum)}", f"  {_d('/model  /hafiza  /yansima  /cikis')}"))

    ozet = (f"{_g(str(p_toplam))} plugin  ·  "
            f"{_g(str(arac_say))} arac  ·  "
            f"{_g(str(skill_toplam))} yetenek")
    print(bos_satir())
    print(sat(f"  {ozet}  ·  {_d('/help ile tum komutlar')}"))
    print(bos_satir())
    print(alt_kenar())

    # Karsilama
    print()
    print(f"  {_g('Hazir!')}  {_d('Gorev veya sorunuzu yazin.')}")
    print()


# ── Yardimcilar ───────────────────────────────────────────────────────────────

def _model_bilgi(agent, config) -> tuple[str, str]:
    if config:
        m = config.get("default_model", "")
        p = config.get("default_provider", "")
        if m:
            return m, p
    if agent:
        cfg = getattr(agent, "config", {}) or {}
        m = cfg.get("default_model", "")
        p = cfg.get("default_provider", "")
        if m:
            return m, p
    return "—", "—"


def _oturum(agent) -> str:
    for attr in ("oturum_id", "_oturum_id", "session_id"):
        v = getattr(agent, attr, None)
        if v:
            return str(v)[:18]
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _plugin_listesi(agent) -> list[str]:
    if not agent:
        return []
    for attr in ("_yuklenen_pluginler", "yuklenen_pluginler"):
        v = getattr(agent, attr, None)
        if v:
            return list(v)
    motor = getattr(agent, "motor", None)
    if motor:
        for attr in ("_yuklenen_pluginler", "yuklenen_pluginler", "plugin_adlari"):
            v = getattr(motor, attr, None)
            if v:
                return list(v)
    return []


def _arac_sayisi(agent) -> int:
    if not agent:
        return 0
    motor = getattr(agent, "motor", None)
    if motor:
        for attr in ("tool_registry", "_tool_registry"):
            reg = getattr(motor, attr, None)
            if reg:
                araclar = getattr(reg, "araclar", None) or getattr(reg, "_araclar", {})
                if araclar:
                    return len(araclar)
    return 0


def _yetenek_sayisi(agent) -> int:
    if not agent:
        return 0
    for attr in ("_skill_sayisi", "skill_sayisi"):
        v = getattr(agent, attr, None)
        if isinstance(v, int):
            return v
    return 0
