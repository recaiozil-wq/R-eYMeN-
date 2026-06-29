# -*- coding: utf-8 -*-
"""
reymen_agent.py — ReYMeN ana agent modülü.
DeepSoek API, agent orchestrator, beceri bağlamı ve format temizleme.
"""

import json
import logging
logger = logging.getLogger(__name__)
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Optional

import requests

# ── Yeni Provider + Config sistemi (P0) ──────────────────────
try:
    from reymen.core.model_provider import (
        ProviderChain, varsayilan_zincir, CalistirSonuc
    )
    _PROVIDER_CHAIN_MEVCUT = True
except ImportError:
    _PROVIDER_CHAIN_MEVCUT = False
try:
    from reymen.core.config_manager import Config, varsayilan_config
    _CONFIG_MEVCUT = True
except ImportError:
    _CONFIG_MEVCUT = False


# ── Araçlar ──────────────────────────────────────────────────
_WEB_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def _web_ara(sorgu: str, max_sonuc: int = 5) -> str:
    """Web'de arama yapar — SearchDispatcher uzerinden (coklu back-end).
    
    Kullanilabilir engine'ler: duckduckgo, google, bing, firecrawl,
    brave, searxng, exa, auto (config'e gore en iyisi).
    """
    try:
        from reymen.arac.web_search_engine import _get_registry
        dispatcher = _get_registry()
        return dispatcher.ara(sorgu, engine="auto", max_sonuc=max_sonuc)
    except Exception as e:
        _get_logger().debug(f"Web arama hatasi: {e}")
        return ""

def _dosya_oku(yol: str) -> str:
    """Dosya okur (UTF-8, max 4000 karakter)."""
    try:
        with open(yol, "r", encoding="utf-8", errors="replace") as f:
            icerik = f.read(5000)
        return icerik[:4000]
    except Exception as e:
        return f"❌ Dosya okuma hatası: {e}"

def _dosya_yaz(yol: str, icerik: str) -> str:
    """Dosyaya yazar (UTF-8)."""
    try:
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
        return f"✅ {yol} yazıldı ({len(icerik)} karakter)"
    except Exception as e:
        return f"❌ Dosya yazma hatası: {e}"

_ARACLAR = {
    "ara": _web_ara,
    "web_ara": _web_ara,
    "dosya_oku": _dosya_oku,
    "dosya_yaz": _dosya_yaz,
}
# ── Global state ──────────────────────────────────────────────
_agent = None
_logger = None
_konusma_gecmisi: list = []

# ── ANSI Renk Sabitleri ─────────────────────────────────────
class _R:
    Y = '\033[33m'   # Sarı
    YB = '\033[1;33m' # Sarı Bold
    M = '\033[35m'   # Mor
    MB = '\033[1;35m'# Mor Bold
    C = '\033[36m'   # Cyan
    CB = '\033[1;36m'# Cyan Bold
    B = '\033[34m'   # Mavi
    BB = '\033[1;34m'# Mavi Bold
    G = '\033[32m'   # Yeşil
    GB = '\033[1;32m'# Yeşil Bold
    R = '\033[31m'   # Kırmızı
    RB = '\033[1;31m'# Kırmızı Bold
    W = '\033[37m'   # Beyaz
    WB = '\033[1;37m'# Beyaz Bold
    D = '\033[90m'   # Gri
    N = '\033[0m'    # Renk sıfırlama

# Son API çağrısının provider adı (CLI'da göstermek için)
_son_provider: str = ""

# ── Sabitler ──────────────────────────────────────────────────
MAX_YANIT_UZUNLUK = 4000
MAX_BECERI_UZUNLUK = 1500
MAX_MESAJ_UZUNLUK = 500
# ── Kalıcı Ayar Sistemi ──────────────────────────────────────
def _ayar_dosyasi_yolu() -> Path:
    """Ayar dosyasinin yolunu Config'den veya varsayilandan alir."""
    if _CONFIG_MEVCUT:
        cfg = varsayilan_config()
        skills_dir = cfg.get_path("skills.dir")
        if skills_dir:
            return skills_dir.parent / "agent_ayarlari.json"
    return Path(__file__).parent / ".ReYMeN" / "agent_ayarlari.json"

def _ayar_oku() -> dict:
    """Kalıcı ayarları JSON'dan oku."""
    _yol = _ayar_dosyasi_yolu()
    try:
        if _yol.exists():
            return json.loads(_yol.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("[reymen_agent] Exception (detaysiz)")
    return {}

def _ayar_yaz(ayarlar: dict) -> None:
    """Ayarları JSON'a yaz."""
    _yol = _ayar_dosyasi_yolu()
    try:
        _yol.parent.mkdir(parents=True, exist_ok=True)
        _yol.write_text(
            json.dumps(ayarlar, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.warning("[reymen_agent] Exception (detaysiz)")

def _ayar_al(anahtar: str, varsayilan=None):
    """Kalıcı ayardan değer oku (env var öncelikli)."""
    # Önce .env, sonra kalıcı ayar
    env_map = {"model": "DEFAULT_MODEL", "provider": "DEFAULT_PROVIDER"}
    if anahtar in env_map:
        env_val = os.environ.get(env_map[anahtar])
        if env_val:
            return env_val
    return _ayar_oku().get(anahtar, varsayilan)

def _ayar_degistir(anahtar: str, deger: str) -> str:
    """Runtime'da ayar değiştir ve JSON'a kaydet."""
    ayarlar = _ayar_oku()
    ayarlar[anahtar] = deger
    _ayar_yaz(ayarlar)
    # Provider degisikligi Config uzerinden de uygulanir
    return f"✅ {anahtar} → {deger}"

# ── Bellek Sistemi ────────────────────────────────────────────
_bellek: dict = {}

def _bellek_yukle() -> None:
    """OnceHafiza'dan kullanıcı belleğini yükler."""
    global _bellek
    try:
        from reymen.cereyan.once_hafiza import hafizada_ara as _oh_ara
        kayitlar = _oh_ara("---bellek---", kategori="bellek", min_guven=0.3)
        if kayitlar and isinstance(kayitlar, list) and len(kayitlar) > 0:
            ilk = kayitlar[0]
            icerik = ilk.get("icerik") or ilk.get("cevap") or "{}"
            if isinstance(icerik, str):
                _bellek = json.loads(icerik)
    except Exception:
        _bellek = {}

def _bellek_kaydet(anahtar: str, deger: str) -> None:
    """Kullanıcı tercihini belleğe kaydeder + OnceHafiza'ya yazar."""
    global _bellek
    _bellek[anahtar] = deger
    try:
        from reymen.cereyan.once_hafiza import kaydet as _oh_kaydet
        _oh_kaydet(
            hedef="---bellek---",
            kategori="bellek",
            icerik=json.dumps(_bellek, ensure_ascii=False, indent=2),
        )
    except Exception:
        logger.warning("[reymen_agent] Exception (detaysiz)")

def _bellek_bilgisi_getir() -> str:
    """System prompt'a eklenecek bellek bilgisi."""
    global _bellek
    if not _bellek:
        _bellek_yukle()
    if not _bellek:
        return ""
    return "\n\n## KULLANICI BİLGİLERİ:\n" + "\n".join(
        f"- **{k}:** {v}" for k, v in _bellek.items()
    )

# ── Multi-Provider Fallback Zinciri (ProviderChain ile) ──────
# ProviderChain: deepseek -> openrouter -> xai -> groq -> lmstudio
# Her provider 401/402/429/500 donerse siradakine gecer.

def _api_cagir_fallback(
    messages: list, system_content: str = ""
) -> tuple[str, str]:
    """
    ProviderChain uzerinden multi-provider fallback ile LLM cagrisi.
    Returns: (yanit, provider_name) veya ("", "")
    """
    if _PROVIDER_CHAIN_MEVCUT:
        chain = varsayilan_zincir()
        sonuc = chain.calistir(messages, system_content)
        if sonuc.basarili:
            return sonuc.yanit, sonuc.provider_adi
        logger.warning("[reymen_agent] ProviderChain basarisiz: %s", sonuc.hata)
        return "", ""

    # Eski fallback (ProviderChain yoksa)
    return _api_cagir_fallback_eski(messages, system_content)


# ═══════════════════════════════════════════════════════════════
# _get_logger
# ═══════════════════════════════════════════════════════════════


def _get_logger(name: str = "reymen_agent") -> logging.Logger:
    """Singleton logger oluşturur/döndürür."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        if not _logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            _logger.addHandler(handler)
            _logger.setLevel(logging.WARNING)
    return _logger


# ═══════════════════════════════════════════════════════════════
# _agent_instance
# ═══════════════════════════════════════════════════════════════


def _agent_instance(config: Optional[dict] = None) -> Any:
    """Agent singleton — AIAgentOrchestrator instance'ı döndürür."""
    global _agent
    if _agent is not None:
        return _agent
    try:
        from main import AIAgentOrchestrator

        _agent = AIAgentOrchestrator()
        return _agent
    except Exception as e:
        _get_logger().error(f"Agent baslatilamadi: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# _beceri_baglami_al
# ═══════════════════════════════════════════════════════════════


def _beceri_baglami_al(hedef: str) -> str:
    """closed_learning_loop._beceri_ara üzerinden beceri bağlamı alır."""
    try:
        from closed_learning_loop import _beceri_ara

        # Mesajı 500 karaktere kısalt
        sorgu = hedef[:MAX_MESAJ_UZUNLUK] if hedef else ""

        sonuc = _beceri_ara(sorgu)

        # Beceri bulunamadi / toplam kontrolü
        if not sonuc or "beceri bulunamadi" in sonuc.lower():
            return ""
        if "toplam" in sonuc.lower():
            return ""

        # Uzun metni kısalt
        if len(sonuc) > MAX_BECERI_UZUNLUK:
            sonuc = sonuc[:MAX_BECERI_UZUNLUK] + "..."

        return f"\n\n## İLGİLİ BECERİLER:\n{sonuc}\n"
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# _api_cagir_fallback_eski — Legacy fallback (ProviderChain yoksa)
# ═══════════════════════════════════════════════════════════════

_FALLBACK_PROVIDERS = [
    {
        "name": "xiaomi",
        "api_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "model": "MiniMax-Text-01",
        "env_key": "XIAOMI_API_KEY",
        "base_url": "https://api.minimax.chat/v1",
    },
    {
        "name": "xai",
        "api_url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-2-latest",
        "env_key": "XAI_API_KEY",
    },
    {
        "name": "deepseek",
        "api_url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    {
        "name": "groq",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
]


def _api_cagir_fallback_eski(
    messages: list, system_content: str = ""
) -> tuple[str, str]:
    """
    Eski fallback zinciri (ProviderChain mevcut degilse kullanilir).
    Returns: (yanit, provider_name) veya ("", "")
    """
    logger = _get_logger()

    for provider in _FALLBACK_PROVIDERS:
        api_key = os.environ.get(provider["env_key"])
        if not api_key:
            continue

        api_url = provider["api_url"]
        model = provider["model"]
        name = provider["name"]

        # MiniMax için özel format
        if name == "xiaomi":
            full_messages = []
            if system_content:
                full_messages.append({"role": "system", "content": system_content})
            full_messages.extend(messages)
            payload = {
                "model": model,
                "messages": full_messages,
                "max_tokens": 1500,
                "frequency_penalty": 0.8,
            }
        else:
            # OpenAI uyumlu format
            full_messages = []
            if system_content:
                full_messages.append({"role": "system", "content": system_content})
            full_messages.extend(messages)
            payload = {
                "model": model,
                "messages": full_messages,
                "max_tokens": 1500,
                "frequency_penalty": 0.8,
                "stop": ["\n\n\n", "\u56e0\u4e3a\u56e0\u4e3a", "becausebecause"],
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            logger.debug(f"[{name}] API çağrısı yapılıyor...")
            resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            yanit = data["choices"][0]["message"]["content"]
            logger.debug(f"[{name}] API yanıtı başarılı")
            return yanit, name
        except requests.exceptions.HTTPError as e:
            # 401/402/429 = provider bitmiş, diğerine geç
            status = e.response.status_code if e.response else 0
            if status in (401, 402, 429):
                logger.warning(f"[{name}] API hatası {status} — sonraki provider'a geçiliyor")
                continue
            # Diğer hatalar (500, timeout vs) — aynı provider'da kalma
            logger.error(f"[{name}] API hatası: {e}")
            continue
        except Exception as e:
            logger.error(f"[{name}] Beklenmeyen hata: {e}")
            continue

    return "", ""


# ═══════════════════════════════════════════════════════════════
# _tekrar_temizle — Sonsuz loop/tekrar temizleme
# ═══════════════════════════════════════════════════════════════


def _tekrar_temizle(text: str) -> str:
    """
    LLM çıktısındaki sonsuz tekrarları temizler.
    "因为因为因为..." → "因为" (ilk 3 taneden sonrasını siler)
    """
    if not text or len(text) < 20:
        return text

    import re

    # 1. Karakter tekrarı kontrolü (ör: "aaaaaaa" → "aaa")
    text = re.sub(r'(.)\1{5,}', r'\1\1\1', text)

    # 2. Kelime tekrarı kontrolü (ör: "because because because..." → "because")
    text = re.sub(r'(\b\w+\b)(\s+\1){4,}', r'\1', text)

    # 3. Cümle tekrarı kontrolü (ör: aynı cümle 3+ kez)
    satirlar = text.split('\n')
    temiz_satirlar = []
    onceki_ikisi = []
    for satir in satirlar:
        satir_stripped = satir.strip()
        if satir_stripped and satir_stripped in onceki_ikisi:
            continue  # Aynı cümle 3. kez geldiyse atla
        temiz_satirlar.append(satir)
        onceki_ikisi.append(satir_stripped)
        if len(onceki_ikisi) > 2:
            onceki_ikisi.pop(0)

    text = '\n'.join(temiz_satirlar)

    # 4. Çince karakter bloğu kontrolü (因为, 因为, 因为...)
    text = re.sub(r'(因为|因为|因为|因为|因为|因为|因为|因为|因为|因为){5,}',
                  'because', text)

    # 5. Uzunluk sınırı (4000 karakter)
    if len(text) > 4000:
        text = text[:4000] + "\n\n[...devamı kesildi — tekrar algılandı]"

    return text


# ═══════════════════════════════════════════════════════════════
# _deepseek_sohbet (multi-provider fallback ile)
# ═══════════════════════════════════════════════════════════════


def _deepseek_sohbet(messages: Any, config: Optional[dict] = None) -> str:
    """LLM'e sohbet isteği gönderir — multi-provider fallback ile."""
    global _son_provider
    logger = _get_logger()

    # Mesajı string'den listeye çevir
    if isinstance(messages, str):
        user_message = messages
    elif isinstance(messages, list):
        user_texts = [
            m["content"]
            for m in messages
            if isinstance(m, dict) and m.get("role") == "user"
        ]
        user_message = user_texts[-1] if user_texts else str(messages)
    else:
        user_message = str(messages)

    # ── ADIM 1: Selam/Sohbet mi? ─────────────────────────────────
    selam_ifadeleri = {"selam", "merhaba", "hey", "hi", "hello", "naber",
                       "nasılsın", "nasilsin", "iyi misin", "iyimisin",
                       "günaydın", "gunaydin", "iyi geceler", "tünaydın",
                       "slm", "sa", "as", "ne haber", "ne yapıyorsun"}
    ilk_kelime = user_message.strip().lower().split()[0] if user_message.strip() else ""
    if ilk_kelime in selam_ifadeleri or user_message.strip().lower() in selam_ifadeleri:
        mesaj_listesi = [{"role": "user", "content": user_message}]
        system_content = "Sen yardımsever bir ReYMeN asistansın. Kısa ve samimi yanıt ver."
        yanit, provider = _api_cagir_fallback(mesaj_listesi, system_content)
        _son_provider = provider
        return _tekrar_temizle(yanit) if yanit else "Merhaba! Nasıl yardımcı olabilirim?"

    # ── ADIM 1.5: Araç çağrısı mı? ────────────────────────────
    alt_msg = user_message.strip().lower()
    for arac_adi, arac_fonk in _ARACLAR.items():
        if alt_msg.startswith(arac_adi + " ") or alt_msg == arac_adi:
            # Parametreyi çıkar: "ara altın ons" → "altın ons"
            param = user_message.strip()[len(arac_adi):].strip()
            if param:
                return arac_fonk(param)
            return f"**{arac_adi}** için parametre gerekli.\nKullanım: `{arac_adi} <sorgu>`"

    # ── ADIM 2: OnceHafiza'da var mi? ────────────────────────────
    try:
        from reymen.cereyan.once_hafiza import hafizada_ara as _oh_ara
        kayitlar = _oh_ara(user_message, min_guven=0.7)
        if kayitlar and isinstance(kayitlar, list) and len(kayitlar) > 0:
            cevap = kayitlar[0].get("icerik") or kayitlar[0].get("cevap") or ""
            if cevap:
                return cevap[:4000]
    except Exception:
        logger.warning("[reymen_agent] Exception (detaysiz)")

    # Beceri bağlamını al
    beceri_baglama = _beceri_baglami_al(user_message)

    # System mesajı oluştur (SOUL.md + AGENTS.md + Bellek ile)
    system_content = ""
    _proje_koku = Path(__file__).parent
    if _CONFIG_MEVCUT:
        try:
            _proje_koku = Path(varsayilan_config().get("general.project_root", str(_proje_koku)))
        except Exception:
            pass
    soul_path = _proje_koku / "SOUL.md"
    if soul_path.exists():
        try:
            soul_text = soul_path.read_text(encoding="utf-8", errors="replace").strip()
            if soul_text:
                system_content += soul_text + "\n\n"
        except Exception:
            logger.warning("[reymen_agent] Exception (detaysiz)")
    agents_path = _proje_koku / "AGENTS.md"
    if agents_path.exists():
        try:
            agents_text = agents_path.read_text(encoding="utf-8", errors="replace").strip()
            if agents_text:
                system_content += agents_text + "\n\n"
        except Exception:
            logger.warning("[reymen_agent] Exception (detaysiz)")
    if not system_content:
        system_content = "Sen yardımsever bir ReYMeN asistansın. Kullanıcıya net ve doğrudan yanıtlar ver."
    # Bellek bilgisini ekle
    system_content += _bellek_bilgisi_getir()
    if beceri_baglama:
        system_content += beceri_baglama

    # ── Konuşma geçmişi ──────────────────────────────────────────
    global _konusma_gecmisi
    try:
        _konusma_gecmisi.append({"role": "user", "content": user_message})
        if len(_konusma_gecmisi) > 20:
            _konusma_gecmisi = _konusma_gecmisi[-10:]
    except Exception:
        _konusma_gecmisi = [{"role": "user", "content": user_message}]

    mesaj_listesi = [{"role": "system", "content": system_content}] if system_content else []
    for m in _konusma_gecmisi[:-1]:
        mesaj_listesi.append(m)
    mesaj_listesi.append({"role": "user", "content": user_message})

    yanit, provider = _api_cagir_fallback(mesaj_listesi, system_content)
    _son_provider = provider

    if yanit:
        # Tekrar/loop temizleme
        yanit = _tekrar_temizle(yanit)
        # Yaniti gecmise ekle
        try:
            _konusma_gecmisi.append({"role": "assistant", "content": yanit})
            if len(_konusma_gecmisi) > 20:
                _konusma_gecmisi = _konusma_gecmisi[-10:]
        except Exception:
            logger.warning("[reymen_agent] Exception (detaysiz)")
        # ── OTOMATİK BELLEK: Kullanıcı bilgilerini çıkar ve kaydet ──
        try:
            import re as _re
            # İsim (benim adım X, ismim X)
            _isim_m = _re.search(r'(?:benim ad[ıi]m|ismim|ad[ıi]m)\s*(?:da|de)?\s*(\w+(?:\s+\w+)?)', user_message, _re.IGNORECASE)
            if _isim_m:
                _bellek_kaydet("isim", _isim_m.group(1).strip())
            # Şehir (X'de yaşıyorum, X şehrinde)
            _sehir_m = _re.search(r'(\w+)\s*(?:şehrinde|ilinde|da|de)\s*yaş', user_message, _re.IGNORECASE)
            if _sehir_m:
                _bellek_kaydet("sehir", _sehir_m.group(1).strip())
        except Exception:
            logger.warning("[reymen_agent] Exception (detaysiz)")
        return yanit

    return "Tüm API provider'ları başarısız oldu. Lütfen API anahtarlarını kontrol edin."


# ═══════════════════════════════════════════════════════════════
# _agent_loop
# ═══════════════════════════════════════════════════════════════


def _agent_loop(hedef: str, config: Optional[dict] = None) -> str:
    """Agent loop — orchestrator üzerinden konuşma çalıştırır."""
    logger = _get_logger()
    logger.debug(f"Agent loop başlatılıyor: {hedef[:50]}...")

    try:
        agent = _agent_instance(config)
        if agent is None:
            logger.warning("Agent yok, fallback kullanılıyor")
            return _deepseek_fallback(hedef)

        # Agent ile konuşmayı çalıştır
        agent.run_conversation(hedef)

        # Yanıtı conversation_history'den al
        yanit = None
        if hasattr(agent, "conversation_history") and agent.conversation_history:
            for msg in reversed(agent.conversation_history):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    yanit = msg.get("content", "")
                    break

        # Fallback: last_response
        if not yanit and hasattr(agent, "last_response") and agent.last_response:
            yanit = agent.last_response

        # Fallback: _yanit_ayikla
        if not yanit:
            raw = str(getattr(agent, "conversation_history", ""))
            yanit = _yanit_ayikla(raw)

        # 4000 karakter sınırı
        if yanit and len(yanit) > MAX_YANIT_UZUNLUK:
            yanit = yanit[:MAX_YANIT_UZUNLUK]

        return yanit or ""
    except Exception as e:
        logger.error(f"Agent loop hatası: {e}")
        return _deepseek_fallback(str(e))


# ═══════════════════════════════════════════════════════════════
# _yanit_ayikla
# ═══════════════════════════════════════════════════════════════


def _yanit_ayikla(raw: str) -> str:
    """Ham çıktıdan yanıt metnini ayıklar."""
    if not raw:
        return ""

    satirlar = raw.split("\n")

    # Markör öncelik sırası (en yüksek → düşük)
    markorler = [
        ("[TAMAMLANDI]", 3),
        ("[SONUC]", 2),
        ("[YANIT]", 1),
    ]

    for markor, oncelik in markorler:
        for satir in satirlar:
            if markor in satir:
                icerik = satir.split(markor, 1)[1].strip()
                if len(icerik) >= 3:
                    return icerik

    # Markör bulunamadı — son 5 satırdan en uzun içerikli satır
    son_satirlar = satirlar[-5:]

    # Filtrele: kısa/kalıp satırları atla
    filtrelenmis = []
    for satir in son_satirlar:
        satir_stripped = satir.strip()
        if not satir_stripped:
            continue
        if satir_stripped == "---":
            continue
        if satir_stripped == "===":
            continue
        if "[Budget]" in satir_stripped or "[Bütçe]" in satir_stripped:
            continue
        if "--- TUR" in satir_stripped:
            continue
        filtrelenmis.append(satir_stripped)

    if not filtrelenmis:
        # Hepsi filtrelendiyse son satırı al
        return son_satirlar[-1].strip() if son_satirlar else ""

    # En uzun içerikli satırı seç
    return max(filtrelenmis, key=len)


# ═══════════════════════════════════════════════════════════════
# _deepseek_fallback
# ═══════════════════════════════════════════════════════════════


def _deepseek_fallback(
    error: str, messages: Any = None, config: Optional[dict] = None
) -> str:
    """Fallback — agent başarısız olursa multi-provider fallback ile dener."""
    logger = _get_logger()
    logger.warning(f"Fallback kullanılıyor: {error}")

    # Kullanılacak mesaj
    if messages is None:
        mesaj = f"Hata oluştu: {error}. Lütfen kullanıcıya yardımcı ol."
    elif isinstance(messages, str):
        mesaj = messages
    else:
        mesaj = str(messages)

    system_content = (
        "Sen bir fallback asistansın. Ana sistem hatası nedeniyle "
        "devreye girdin. Kullanıcıya yardımcı ol."
    )

    # Fallback zincirinde dene
    mesaj_listesi = [{"role": "user", "content": mesaj}]
    yanit, provider = _api_cagir_fallback(mesaj_listesi, system_content)

    if yanit:
        return yanit

    return "Tüm API provider'ları başarısız oldu. Lütfen API anahtarlarını kontrol edin."


# ═══════════════════════════════════════════════════════════════
# _format_temizle
# ═══════════════════════════════════════════════════════════════


def _format_temizle(text: str) -> str:
    """Metin formatını temizler — backtick ve kod bloklarını düzeltir."""
    if not text:
        return text

    # Kod bloğu içinde olup olmadığımızı takip et
    def _kod_ici_indexler(satirlar):
        """Kod bloğu içindeki satırların index setini döndürür."""
        kod_ici = set()
        acik = False
        for i, satir in enumerate(satirlar):
            if satir.startswith("```"):
                acik = not acik
            elif acik:
                kod_ici.add(i)
        return kod_ici

    satirlar = text.split("\n")
    kod_ici = _kod_ici_indexler(satirlar)

    yeni_satirlar = []
    for i, satir in enumerate(satirlar):
        if i in kod_ici:
            # Kod bloğu içindeki satırları değiştirme
            yeni_satirlar.append(satir)
            continue

        yeni_satir = satir

        # 4+ backtick → 3 backtick
        if yeni_satir.startswith("````"):
            # Kaç backtick var?
            count = 0
            for ch in yeni_satir:
                if ch == "`":
                    count += 1
                else:
                    break
            if count >= 4:
                gerisi = yeni_satir[count:]
                yeni_satir = "```" + gerisi

        # Çift backtick + dil → üçlü backtick + dil (açılış)
        if yeni_satir.startswith("``") and not yeni_satir.startswith("```"):
            gerisi = yeni_satir[2:]
            if gerisi and not gerisi.startswith("`"):
                yeni_satir = "```" + gerisi

        # Satır başı tek backtick → üçlü backtick
        if yeni_satir.startswith("`") and not yeni_satir.startswith("``"):
            # Kod bloğu açma mı yoksa inline kod mu?
            gerisi = yeni_satir[1:]
            if gerisi.strip():
                yeni_satir = "```" + gerisi

        yeni_satirlar.append(yeni_satir)

    # Kod bloğu kapanışını düzelt: tek backtick → üçlü
    metin = "\n".join(yeni_satirlar)
    if metin.rstrip().endswith("`") and not metin.rstrip().endswith("```"):
        # Son satır tek backtick ile bitiyor
        # ``` ile başlayan bir bloğun kapanışı mı?
        satirlar_yeni = metin.split("\n")
        acik_blok_sayisi = 0
        for s in satirlar_yeni:
            if s.startswith("```") and s.strip() == "```":
                acik_blok_sayisi += 1
            elif s.startswith("```"):
                acik_blok_sayisi += 1

        if acik_blok_sayisi % 2 != 0:
            # Açık blok var, kapat
            for j in range(len(satirlar_yeni) - 1, -1, -1):
                s = satirlar_yeni[j]
                if s.rstrip().endswith("`") and not s.rstrip().endswith("```"):
                    # Tek backtick ile biten satır
                    if s.rstrip().endswith("`"):
                        # Son backtick(ler)i say
                        sondaki_backtick = 0
                        for ch in reversed(s.rstrip()):
                            if ch == "`":
                                sondaki_backtick += 1
                            else:
                                break
                        if sondaki_backtick == 1:
                            satirlar_yeni[j] = s.rstrip()[:-1].rstrip() + "```"
                            break
            metin = "\n".join(satirlar_yeni)

    # 2+ ardışık Python kodu satırını blokla (kod bloğu dışında)
    satirlar_son = metin.split("\n")
    kod_ici2 = _kod_ici_indexler(satirlar_son)
    yeni_satirlar2 = []
    i = 0
    while i < len(satirlar_son):
        if i in kod_ici2:
            yeni_satirlar2.append(satirlar_son[i])
            i += 1
            continue

        # 2+ ardışık Python kodu satırı ara
        python_satirlari = []
        j = i
        while j < len(satirlar_son) and j not in kod_ici2:
            s = satirlar_son[j]
            # Python kodu: indent (4 boşluk) veya def/class/if/for/with ile başlayan
            if (
                s.startswith("    ")
                or s.startswith("\t")
                or s.startswith("def ")
                or s.startswith("class ")
                or s.startswith("if ")
                or s.startswith("for ")
                or s.startswith("while ")
                or s.startswith("with ")
                or s.startswith("try:")
                or s.startswith("except")
                or s.startswith("elif ")
                or s.startswith("else:")
                or s.startswith("return ")
                or s.startswith("import ")
                or s.startswith("from ")
                or s.startswith("async ")
                or s.startswith("@")
            ):
                python_satirlari.append(s)
                j += 1
            else:
                break

        if len(python_satirlari) >= 2:
            yeni_satirlar2.append("```python")
            yeni_satirlar2.extend(python_satirlari)
            yeni_satirlar2.append("```")
            i = j
        else:
            yeni_satirlar2.append(satirlar_son[i])
            i += 1

    return "\n".join(yeni_satirlar2).strip()


# ═══════════════════════════════════════════════════════════════
# isleyen_gorev
# ═══════════════════════════════════════════════════════════════


def isleyen_gorev(
    task: str, use_agent: bool = False, chat_id: Optional[str] = None
) -> str:
    """Ana işlev — görevi işler ve yanıt döndürür."""
    logger = _get_logger()
    logger.debug(f"Görev işleniyor: {task[:50]}... (use_agent={use_agent}, chat_id={chat_id})")

    if use_agent:
        return _agent_loop(task)
    else:
        return _deepseek_sohbet(task)


# ═══════════════════════════════════════════════════════════════
# CLI ARAYÜZÜ — python reymen_agent.py "soru"
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import io as _io
    if sys.stdout and hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, _io.TextIOWrapper):
        try:
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            logger.warning("[reymen_agent] Exception (detaysiz)")

    # .env'den key oku
    try:
        from dotenv import load_dotenv
        _env_yolu = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        load_dotenv(_env_yolu)
    except ImportError:
        logger.warning("[reymen_agent] ImportError (detaysiz)")

    # Fallback: .env'yi manuel oku (dotenv calismazsa)
    if not os.environ.get("DEEPSEEK_API_KEY"):
        _env_dosyalari = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "ReYMeN", ".env"),
            os.path.join(os.path.expanduser("~"), ".config", "reymen", ".env"),
        ]
        for _env_yolu in _env_dosyalari:
            try:
                with open(_env_yolu, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip())
                if os.environ.get("DEEPSEEK_API_KEY"):
                    break
            except Exception:
                continue

    if len(sys.argv) > 1:
        # Tek seferlik soru
        soru = " ".join(sys.argv[1:])
        yanit = _deepseek_sohbet(soru)
        print(f"\n{_R.D}-----------------{_R.N}")
        print(f"{_R.W}{yanit}{_R.N}")
        if _son_provider:
            print(f"{_R.B}Kaynak: {_son_provider}{_R.N}")
        print(f"{_R.D}-----------------{_R.N}")
    else:
        # Interaktif sohbet
        print(f"{_R.GB}ReYMeN{_R.N} Hizli Mod ({_R.D}/cikis{_R.N} ile cik, {_R.D}/ayarlar{_R.N} ile ayarlari gor)")
        while True:
            try:
                soru = input(f"{_R.G}ReYMeN> {_R.N}").strip()
                if not soru or soru.lower() in ["/cikis", "/quit", "/exit", "q"]:
                    break
                # ── Kalıcı ayar komutları ──────────────────────────
                if soru.startswith("/ayarlar"):
                    ayarlar = _ayar_oku()
                    for k, v in ayarlar.items():
                        print(f"  {k}: {v}")
                    continue
                if soru.startswith("/model"):
                    model = soru[len("/model"):].strip()
                    if model:
                        print(_ayar_degistir("model", model))
                    else:
                        print(f"Mevcut: {_ayar_al('model', 'deepseek-v4-flash')}")
                    continue
                if soru.startswith("/provider"):
                    prov = soru[len("/provider"):].strip()
                    if prov:
                        print(_ayar_degistir("provider", prov))
                    else:
                        print(f"Mevcut: {_ayar_al('provider')}")
                    continue
                yanit = _deepseek_sohbet(soru)
                print(f"{_R.D}-----------------{_R.N}")
                print(f"{_R.W}{yanit}{_R.N}")
                if _son_provider:
                    print(f"{_R.B}Kaynak: {_son_provider}{_R.N}")
                print(f"{_R.D}-----------------{_R.N}")
            except (KeyboardInterrupt, EOFError):
                break
        print(f"\n{_R.G}Gorusuruz!{_R.N}")


# ═══════════════════════════════════════════════════════════════
# kopru_deepseek_istek
# ═══════════════════════════════════════════════════════════════


def kopru_deepseek_istek(messages: Any, config: Optional[dict] = None) -> str:
    """Köprü entegrasyonu — isleyen_gorev'e yönlendirir."""
    logger = _get_logger()
    logger.info("Köprü isteği alındı, isleyen_gorev'e yönlendiriliyor...")

    if isinstance(messages, str):
        return isleyen_gorev(messages, chat_id="kopru")
    elif isinstance(messages, list):
        # Liste ise son user mesajını çıkar
        user_texts = [
            m["content"]
            for m in messages
            if isinstance(m, dict) and m.get("role") == "user"
        ]
        mesaj = user_texts[-1] if user_texts else str(messages)
        return isleyen_gorev(mesaj, chat_id="kopru")
    else:
        return isleyen_gorev(str(messages), chat_id="kopru")
