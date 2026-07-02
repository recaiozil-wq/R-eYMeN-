# -*- coding: utf-8 -*-
"""conversation_loop.py — ReYMeN Agent seviyesi konusma dongusu.

Ajan ile kullanici arasindaki etkilesimi yonetir:
- Amaç belirleme ve takip (task_id, budget)
- Provider-agnostik API mesaj formati (OpenAI / Anthropic / Codex / LM Studio)
- Context compression (esik asilinca otomatik sikistirma)
- Prompt caching (Anthropic icin cache_control marker'lari)
- Interruptible API call (Ctrl+C destekli, thread bazli)
- Tool call dongusu (tool_calls geldikce calistir, sonuclari ekle, devam)
- Iteration budget
- Hata yonetimi: her adimda try/except
- Loglama: her adimda logging.INFO / ERROR
"""

import json
import logging
import os
import re
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from dotenv import load_dotenv
_env_yolu = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_yolu.exists():
    load_dotenv(_env_yolu, override=False)

# Proje kokunu sys.path'e ekle (gateway bagimsiz calisma icin)
_PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(_PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(_PROJE_KOK))

logger = logging.getLogger(__name__)

log = logging.getLogger("conversation_loop")

# Kullaniciya gereksiz log gosterme - sadece ERROR ve uzeri
logging.getLogger('reymen').setLevel(logging.ERROR)
logging.getLogger('conversation_loop').setLevel(logging.ERROR)
# Tum alt logger'lari da kapat
for _l in ['CUA', 'Motor', 'motor', 'ReYMeN', 'beyin', 'plugin', 'cron', 'skill']:
    logging.getLogger(_l).setLevel(logging.ERROR)

# ── Konusmadan Skill Cikarma ────────────────────────────
try:
    from reymen.arac.konusmadan_skill import konusmadan_skill_cikar as _skill_cikar
    _SKILL_CIKAR_AKTIF = True
except ImportError:
    _SKILL_CIKAR_AKTIF = False

# ── @file/@url Referans Isleme (ref_processor) ─────────
try:
    from reymen.cereyan.ref_processor import ref_isle as _ref_isle
    from reymen.cereyan.ref_processor import ref_context_olustur as _ref_context_olustur
    _REF_PROCESSOR_AKTIF = True
except ImportError:
    _ref_isle = None
    _ref_context_olustur = None
    _REF_PROCESSOR_AKTIF = False

# ── Nudge / latent kullanıcı modeli ───────────────────────────────────
try:
    from reymen.cereyan.nudge_model import NudgeModel
    _NUDGE_AKTIF = True
except ImportError:
    NudgeModel = None
    _NUDGE_AKTIF = False

# ── Skill iyileştirici ─────────────────────────────────────────────────
try:
    from reymen.scripts.skill_iyilestirici import SkillIyilestirici
    _SKILL_IYI_AKTIF = True
except ImportError:
    SkillIyilestirici = None
    _SKILL_IYI_AKTIF = False

# ── Adaptif öğrenme ────────────────────────────────────────────────────
try:
    from reymen.cereyan.adaptif_ogrenme import AdaptifOgrenme
    _ADAPTIF_AKTIF = True
except ImportError:
    AdaptifOgrenme = None
    _ADAPTIF_AKTIF = False

# ── Proaktif kontrol (her cevap sonrası eksik analizi) ────────────────
try:
    from reymen.cereyan.proaktif_kontrol import soru_sonrasi_kontrol as _proaktif_kontrol
    _PROAKTIF_AKTIF = True
except ImportError:
    _proaktif_kontrol = None
    _PROAKTIF_AKTIF = False

# ── Yeni import'lar: circuit breaker, streaming, error classify ─────
try:
    from reymen.cereyan.iteration_budget import IterationBudget
except ImportError:
    IterationBudget = None

try:
    from turn_retry_state import TurnRetryState
except ImportError:
    TurnRetryState = None

# ── Opsiyonel modüller (graceful degrade) ─────────────────────────────

try:
    from turn_context import TurnYoneticisi, TurnContext
except ImportError:
    TurnYoneticisi = None
    TurnContext = None

try:
    from reymen.cereyan.iteration_budget import IterationBudget, standart_budget
    _BUDGET_AKTIF = True
except ImportError:
    IterationBudget = None
    standart_budget = None
    _BUDGET_AKTIF = False

try:
    from reymen.arac.prompt_builder import PromptBuilder
    _BUILDER_AKTIF = True
except ImportError:
    PromptBuilder = None
    _BUILDER_AKTIF = False

try:
    from reymen.hafiza.context_compressor import ContextCompressor as _Compressor
    _COMPRESS_AKTIF = True
except ImportError:
    _Compressor = None
    _COMPRESS_AKTIF = False

# `_CACHING_AKTIF` — provider'a gore dinamik olarak hesaplanir.
# ``caching_aktif_mi(provider)`` fonksiyonu ile provider prompt caching
# destekliyorsa True doner. Ayrica ``agent._use_prompt_caching`` da dikkate
# alinir (Anthropic / OpenRouter / DeepSeek / OpenAI).
try:
    from reymen.arac.prompt_caching import _prompt_caching_ekle, caching_aktif_mi
    # _CACHING_AKTIF artik dinamik: provider'a gore hesaplanir.
    # Dogrudan kullanim yerine caching_aktif_mi() fonksiyonu tercih edilir.
    _CACHING_AKTIF = None  # None = "provider'a bak" anlaminda
except ImportError:
    _prompt_caching_ekle = None
    caching_aktif_mi = None
    _CACHING_AKTIF = False

# Geriye uyumluluk: eski import hala calissin
try:
    from reymen.arac.prompt_caching import apply_anthropic_cache_control as _apply_anthropic_cache_control
except ImportError:
    _apply_anthropic_cache_control = None

try:
    from reymen.hafiza.session_db import AdvancedSessionStorage as _SessionStorage
    _SESSION_AKTIF = True
except ImportError:
    _SessionStorage = None
    _SESSION_AKTIF = False

# ── Session Search FTS5 (tam metin arama) ─────────────────────────
try:
    from reymen.cereyan.session_search import (
        SessionSearch as _SessionSearch,
        session_search_al as _session_search_al,
    )
    _SESSION_SEARCH_AKTIF = True
except ImportError:
    _SessionSearch = None
    _session_search_al = None
    _SESSION_SEARCH_AKTIF = False

# ── OnceHafiza (bellegi-oncelikli kontrol) ───────────────────────
try:
    from reymen.sistem.once_hafiza import hafizada_ara as _hafizada_ara
    _ONCE_HAFIZA_AKTIF = True
except ImportError:
    _hafizada_ara = None
    _ONCE_HAFIZA_AKTIF = False

# ── Rules Engine (Kural/izin yonetimi) ──────────────────────────
try:
    from reymen.sistem.kurallar import RulesEngine as _RulesEngine, engine_al as _rules_engine_al
    _RULES_ENGINE = _rules_engine_al()
    _RULES_AKTIF = True
    log.info("[Rules] Kural motoru aktif (%d kural)", _RULES_ENGINE.kural_sayisi)
except ImportError:
    _RULES_ENGINE = None
    _RULES_AKTIF = False

# ── Skill Activator (auto-activation) ────────────────────────────
try:
    from reymen.cereyan.skill_activator import SkillActivator as _SkillActivator
    _SKILL_ACTIVATOR = _SkillActivator()
    _SKILL_ACTIVATOR_AKTIF = True
    # Startup'ta tum skill'leri aktif et
    # Continuous Learning
    try:
        from reymen.cereyan.continuous_learning import session_baslat as _cl_baslat
        from reymen.cereyan.continuous_learning import ogrenme_baglani_al as _cl_baglam
        _CL_AKTIF = True
    except ImportError:
        _CL_AKTIF = False
    # Startup'ta tum skill'leri aktif et
    try:
        aktif_sayisi = _SKILL_ACTIVATOR.tumunu_aktif_et()
        log.info("[Baslangic] %d skill basariyla aktif edildi", aktif_sayisi)
    except Exception as e:
        log.warning("[Baslangic] Skill toplu aktivasyon basarisiz: %s", e)
except ImportError:
    _SKILL_ACTIVATOR = None
    _SKILL_ACTIVATOR_AKTIF = False

# ── Delegasyon Sistemi (P2) — Subagent + görev ayrıştırma ─────
try:
    from reymen.ag.delegasyon import (
        DelegasyonSistemi as _DelegasyonSistemi,
        sistem_al as _delegasyon_sistemi_al,
        konusma_dongusu_hook_bul as _delegasyon_hook_bul,
    )
    _DELEGASYON_AKTIF = True
    # Hook'u otomatik kaydet
    try:
        _delegasyon_hook = _delegasyon_hook_bul()
    except Exception:
        _delegasyon_hook = None
except ImportError:
    _DelegasyonSistemi = None
    _delegasyon_sistemi_al = None
    _delegasyon_hook_bul = None
    _DELEGASYON_AKTIF = False

# ── Plugin Sistemi (lifecycle hooks) ──────────────────────────────────
try:
    from reymen.plugin.manager import (
        PluginManager as _PluginManager,
        plugin_manager_al as _plugin_manager_al,
    )
    _PLUGIN_SISTEMI = _plugin_manager_al()  # singleton, config + auto_load
    _PLUGIN_AKTIF = _PLUGIN_SISTEMI.aktif
    log.info("[Plugin] Plugin sistemi aktif=%s (%d plugin yuklu)",
             _PLUGIN_AKTIF, _PLUGIN_SISTEMI.sayi)
except ImportError as _pie:
    _PLUGIN_SISTEMI = None
    _PLUGIN_AKTIF = False
    log.debug("[Plugin] Plugin sistemi yuklenemedi: %s", _pie)

# ── Hata sınıflandırıcı ve mesaj tamirci ─────────────────────────
try:
    from reymen.cereyan.hata_siniflandirici import (
        api_hatasini_siniflandir,
        classify_api_error,
        FailoverReason,
        SiniflandirilmisHata,
    )
    _HATA_SINIFLANDIRICI_AKTIF = True
except ImportError:
    api_hatasini_siniflandir = None  # type: ignore[assignment]
    classify_api_error = None  # type: ignore[assignment]
    FailoverReason = None  # type: ignore[assignment]
    SiniflandirilmisHata = None  # type: ignore[assignment]
    _HATA_SINIFLANDIRICI_AKTIF = False

try:
    from reymen.cereyan.mesaj_tamirci import (
        arac_cagri_argumanlarini_temizle,
        mesaj_siralamasi_tamir_et,
        surrogate_karakterleri_temizle,
        sanitize_tool_call_arguments,
        repair_message_sequence,
    )
    _MESAJ_TAMIRCI_AKTIF = True
except ImportError:
    arac_cagri_argumanlarini_temizle = None  # type: ignore[assignment]
    mesaj_siralamasi_tamir_et = None  # type: ignore[assignment]
    surrogate_karakterleri_temizle = None  # type: ignore[assignment]
    sanitize_tool_call_arguments = None  # type: ignore[assignment]
    repair_message_sequence = None  # type: ignore[assignment]
    _MESAJ_TAMIRCI_AKTIF = False

try:
    from reymen.cereyan.hook_dispatcher import (
        hook_cagir as _hook_cagir,
        hook_kaydet as _hook_kaydet,
        oturum_baslat_tetikle as _oturum_baslat_tetikle,
        oturum_bitir_tetikle as _oturum_bitir_tetikle,
        tur_baslat_tetikle as _tur_baslat_tetikle,
        tur_bitir_tetikle as _tur_bitir_tetikle,
        arac_cagri_tetikle as _arac_cagri_tetikle,
        arac_sonuc_tetikle as _arac_sonuc_tetikle,
        hata_tetikle as _hata_tetikle,
        context_sikistirma_tetikle as _context_sikistirma_tetikle,
    )
    _HOOK_AKTIF = True
    # Self-improvement hook'unu otomatik kaydet (her tur sonu metrik)
    try:
        from reymen.self_improve import conversation_loop_hook as _si_hook
        _hook_kaydet("on_turn_end", _si_hook)
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )
except ImportError:
    _hook_cagir = None  # type: ignore[assignment]
    _oturum_baslat_tetikle = _oturum_bitir_tetikle = None  # type: ignore[assignment]
    _tur_baslat_tetikle = _tur_bitir_tetikle = None  # type: ignore[assignment]
    _arac_cagri_tetikle = _arac_sonuc_tetikle = None  # type: ignore[assignment]
    _hata_tetikle = _context_sikistirma_tetikle = None  # type: ignore[assignment]
    _HOOK_AKTIF = False

try:
    from reymen.cereyan.stream_diagnostics import StreamSaglikTakibi as _StreamSaglikTakibi
    _STREAM_DIAG_AKTIF = True
except ImportError:
    _StreamSaglikTakibi = None  # type: ignore[assignment]
    _STREAM_DIAG_AKTIF = False

# ── Web arama (halusinasyon onleme) ─────────────────────────────
# Artık doğrudan DDGS yerine web_search_engine'deki SearchDispatcher kullanılır.
# _WEB_ARAMA_AKTIF, dispatcher her zaman hazır olduğu için True olarak kalır.
_WEB_ARAMA_AKTIF = True

# ── MCP (Model Context Protocol) entegrasyonu ────────────────────
try:
    from reymen.arac.native_mcp_client import NativeMCPClient as _NativeMCPClient
    _MCP_NATIVE_AKTIF = True
except ImportError:
    _NativeMCPClient = None
    _MCP_NATIVE_AKTIF = False

try:
    from reymen.arac.mcp_client_tool import (
        mcp_client as _mcp_client_get,
        mcp_client_baglan as _mcp_client_baglan,
        mcp_client_listele as _mcp_client_listele,
        motor_kaydet as _mcp_client_motor_kaydet,
    )
    _MCP_CLIENT_AKTIF = True
except ImportError:
    _mcp_client_get = None
    _mcp_client_baglan = None
    _mcp_client_listele = None
    _mcp_client_motor_kaydet = None
    _MCP_CLIENT_AKTIF = False

try:
    from reymen.arac.mcp_catalog import run as _mcp_catalog_run, listele as _mcp_catalog_listele
    _MCP_CATALOG_AKTIF = True
except ImportError:
    _mcp_catalog_run = None
    _mcp_catalog_listele = None
    _MCP_CATALOG_AKTIF = False

try:
    from reymen.arac.mcp_tool import MCPIstemci as _MCPIstemci, mcp_istemci as _mcp_istemci_get
    _MCP_TOOL_AKTIF = True
except ImportError:
    _MCPIstemci = None
    _mcp_istemci_get = None
    _MCP_TOOL_AKTIF = False

_MCP_AKTIF = _MCP_NATIVE_AKTIF or _MCP_CLIENT_AKTIF or _MCP_CATALOG_AKTIF or _MCP_TOOL_AKTIF

# ── Framework Adaptörleri (LangGraph / CrewAI / AutoGen) ─────────────
try:
    from reymen.arac.framework_adaptor import (
        FrameworkYonetici as _FrameworkYonetici,
        framework_adaptor as _framework_adaptor,
        framework_adaptor_durum as _framework_adaptor_durum,
    )
    _FRAMEWORK_ADAPTOR_AKTIF = True
    _framework_aktif_fw = _framework_adaptor.aktif_frameworkler
    # Log active frameworks (once only)
    _aktif_liste = [ad for ad, aktif in _framework_aktif_fw.items() if aktif]
    if _aktif_liste:
        log.info("[Framework] Adaptor aktif: %s", ", ".join(_aktif_liste))
    else:
        log.debug("[Framework] Adaptor yuklu ama hic framework kurulu degil")
except ImportError:
    _FrameworkYonetici = None
    _framework_adaptor = None
    _framework_adaptor_durum = None
    _FRAMEWORK_ADAPTOR_AKTIF = False

# ── Reasoning-Core (akil yurutme motoru) ──────────────────────────────
try:
    from reymen.sistem.ortak_komut import reasoning_loop as _reasoning_loop
    _REASONING_AKTIF = True
except ImportError:
    _reasoning_loop = None
    _REASONING_AKTIF = False

# ── Sabitler ──────────────────────────────────────────────────────────

# %50'yi asince context sikistirma baslat (ENV ile yapilandirilabilir)
CONTEXT_SIKISTIRMA_ESIGI = float(os.environ.get("CONTEXT_ESIK", "0.50"))

# Provider'a gore token limitleri (modern modeller icin)
# Envs: PROVIDER_LIMIT_<UPPER_NAME>=<TOKEN>
PROVIDER_LIMITS = {
    "deepseek":     int(os.environ.get("PROVIDER_LIMIT_DEEPSEEK", "128000")),
    "claude":       int(os.environ.get("PROVIDER_LIMIT_CLAUDE",   "200000")),
    "sonnet":       int(os.environ.get("PROVIDER_LIMIT_SONNET",   "200000")),
    "anthropic":    int(os.environ.get("PROVIDER_LIMIT_ANTHROPIC","200000")),
    "gpt4":         int(os.environ.get("PROVIDER_LIMIT_GPT4",     "128000")),
    "gpt4o":        int(os.environ.get("PROVIDER_LIMIT_GPT4O",    "128000")),
    "gemini":       int(os.environ.get("PROVIDER_LIMIT_GEMINI",   "128000")),
    "codex":        int(os.environ.get("PROVIDER_LIMIT_CODEX",    "200000")),
    "openrouter":   int(os.environ.get("PROVIDER_LIMIT_OPENROUTER","128000")),
}
# Varsayilan limit (hic eslesmezse)
PROVIDER_LIMIT_VARSAYILAN = int(os.environ.get("PROVIDER_LIMIT_DEFAULT", "128000"))

# Oncelik cache: basit selamlasma/kisa yanit patternleri icin
# LLM cagrisi yapmadan direkt yanit ver (0 maliyet)
ONCELIK_CACHE = {
    "merhaba":       "Merhaba! Nasil yardimci olabilirim?",
    "selam":         "Selam! Ne yapabilirim?",
    "slm":           "Selam! Ne yapabilirim?",
    "teşekkür":      "Rica ederim, baska bir sey?",
    "tesekkur":      "Rica ederim, baska bir sey?",
    "sagol":         "Ne demek, her zaman!",
    "sağol":         "Ne demek, her zaman!",
    "gorusuruz":     "Gorusmek uzere!",
    "görüşürüz":     "Görüşmek üzere!",
    "bye":           "Gorusmek uzere!",
    "hadi":          "Hadi bakalim, kolay gelsin!",
    "tamam":         "Tamam, hemen yapiyorum.",
    "ok":            "OK, hemen basliyorum.",
    "tmm":           "Tamam, hemen yapiyorum.",
    "eyvallah":      "Eyvallah, görüşürüz!",
}

# Yanıttaki "gorev bitti" tetikleyicileri
GOREV_BITTI_TETIK = ("GOREV_BITTI", "görev bitti", "tamamlandi", "TASK_DONE")


def motor_tools_schema_al(motor, maks_arac: int = 64) -> list:
    """Motor'daki araçlardan OpenAI-uyumlu tools schema listesi üretir.

    _plugin_araclar değerleri iki formatta olabilir:
      - {ad: callable}            — düz fonksiyon (açıklama yok)
      - {ad: (callable, str)}     — (fonk, açıklama) tuple

    Returns:
        [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
    """
    try:
        araclar: dict = {}
        if hasattr(motor, "_plugin_araclar") and motor._plugin_araclar:
            araclar.update(motor._plugin_araclar)
        elif hasattr(motor, "araclar") and motor.araclar:
            araclar.update(motor.araclar)

        schema = []
        for ad, deger in list(araclar.items())[:maks_arac]:
            if isinstance(deger, tuple) and len(deger) >= 2:
                aciklama = str(deger[1]) if deger[1] else ad
            else:
                aciklama = ad
            schema.append({
                "type": "function",
                "function": {
                    "name": ad,
                    "description": aciklama,
                    "parameters": {
                        "type": "object",
                        "properties": {"param": {"type": "string"}},
                        "required": [],
                    },
                },
            })
        return schema
    except Exception:
        return []


# Geriye uyumlu alias (alt çizgili)
_motor_tools_schema_al = motor_tools_schema_al

# Circuit breaker (ReYMeN Agent pattern'i)
# İYİLEŞTİRME 2: max_deneme=3, 3 başarısızsa → dur + bildir
CIRCUIT_BREAKER_MAX_HATA = int(os.environ.get("CB_MAX_HATA", "3"))
CIRCUIT_BREAKER_SURESI = int(os.environ.get("CB_SURESI", "0"))  # 0 = otomatik açılmaz
CIRCUIT_BREAKER_KALICI = True  # True = kullanıcı müdahalesi gerekene kadar kalıcı

# Mekanik retry: max 3 deneme, sonra circuit breaker
MAX_RETRY = int(os.environ.get("MAX_RETRY", "3"))

# Exponential backoff için max retry denemesi
MAX_API_RETRY = 3
# Aynı eylem 3x = takılma
TAKILMA_ESIĞI = 3

# Streaming sabitleri
STREAMING_AKTIF = os.environ.get("STREAMING_AKTIF", "true").lower() in ("true", "1")


class VisionAdapter:
    """Vision tool wrapper — conversation_loop.py'deki _vision_analiz'e kopru."""

    def __init__(self):
        self._loop_ref = None

    def _vision_analiz(self, sorgu: str) -> Optional[str]:
        if self._loop_ref is None:
            return "[VISION] ConversationLoop referansi yok."
        return self._loop_ref._vision_analiz(sorgu)


class ConversationLoop:
    """Ana konusma dongusu — geriye uyumlu + ReYMeN Agent seviyesi.

    Eski API:
        loop = ConversationLoop(motor=motor, beyin=beyin, max_tur=30)
        sonuc = loop.coz("bir dosya olustur")

    Yeni API:
        sonuc = loop.run_conversation(
            hedef="bir dosya olustur",
            provider="deepseek",
            baglam={"kullanici": "Ahmet"},
        )
    """

    def __init__(self, motor: Any = None, beyin: Any = None, max_tur: int = 30) -> None:
        self.motor = motor
        self.beyin = beyin
        self.max_tur = max_tur
        self.tur_yoneticisi = TurnYoneticisi(max_tur=max_tur) if TurnYoneticisi else None
        self._durum = "hazir"
        self._iptal_istegi = False
        self._konusma_gecmisi: list = []
        # Konusma gecmisi — son N mesaj (user/assistant) bir sonraki goreve aktarilir
        self._gecmis_mesajlar: list[dict] = []
        self._max_gecmis_mesaj = 10
        # Circuit breaker state
        self._cb_art_arda_hata = 0
        self._cb_son_hata_zamani = 0.0
        self._cb_acik = False
        # İyileştirme #2: Mekanik retry sayacı
        self._retry_sayaci = 0
        self._max_retry = MAX_RETRY
        self._retry_kalici_kilit = False
        # Takılma dedektörü
        self._onceki_eylemler: list[str] = []
        # Streaming
        self._stream_callback = None
        # A2A mesajlaşma
        self._a2a_broker = None
        self._a2a_agent = None
        try:
            from reymen.a2a import Broker as _Broker, Agent as _Agent
            self._a2a_broker = _Broker()
            self._a2a_agent = _Agent("conversation_loop", self._a2a_broker)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # ── MCP (Model Context Protocol) otomatik baslatma ─────────
        self._native_mcp = None
        if _MCP_NATIVE_AKTIF:
            try:
                self._native_mcp = _NativeMCPClient()
                mcp_sunucular = self._native_mcp.konfig_yukle()
                for cfg in mcp_sunucular:
                    baglanti = self._native_mcp._baglantilar.get(cfg.ad)
                    if baglanti is None:
                        from reymen.arac.native_mcp_client import MCPBaglanti
                        yeni = MCPBaglanti(cfg)
                        if yeni.baslat():
                            self._native_mcp._baglantilar[cfg.ad] = yeni
                            log.info("[MCP] %s otomatik baslatildi (%d tool)",
                                     cfg.ad, len(yeni.araclar))
                if self.motor:
                    self._mcp_motor_kaydet()
            except Exception as _mcp_e:
                log.warning("[MCP] Baslatma hatasi (sessiz): %s", _mcp_e)

        # MCP Client Tool (config'den yukle)
        if _MCP_CLIENT_AKTIF:
            try:
                # Config varsa zaten singleton otomatik yuklenir
                yonetici = _mcp_client_get()
                durum = yonetici.durum()
                if durum:
                    for ad, bilgi in durum.items():
                        log.info("[MCPClient] %s hazir (%d tool)",
                                 ad, bilgi.get('arac_sayisi', 0))
                    if self.motor:
                        _mcp_client_motor_kaydet(self.motor)
            except Exception as _mcp_e:
                log.warning("[MCPClient] Baslatma hatasi: %s", _mcp_e)

        # ── VisionAdapter baglantisi ──────────────────────────
        try:
            self._vision_adapter = VisionAdapter()
            self._vision_adapter._loop_ref = self
        except Exception:
            self._vision_adapter = None

        # ── Nudge / latent kullanıcı modeli ──────────────────────────
        self._nudge = None
        if _NUDGE_AKTIF:
            try:
                self._nudge = NudgeModel()
                log.info("[NUDGE] Latent kullanici modeli aktif")
            except Exception as e:
                log.warning("[NUDGE] Baslatma hatasi: %s", e)

        # ── Session Search FTS5 ─────────────────────────────────────
        self._session_search = None
        if _SESSION_SEARCH_AKTIF:
            try:
                self._session_search = _session_search_al()
                log.info("[SESSION_SEARCH] FTS5 arama motoru aktif")
            except Exception as e:
                log.warning("[SESSION_SEARCH] Baslatma hatasi: %s", e)

        # ── Adaptif öğrenme ─────────────────────────────────────────
        self._adaptif = None
        if _ADAPTIF_AKTIF:
            try:
                self._adaptif = AdaptifOgrenme()
                log.info("[ADAPTIF] Adaptif ogrenme aktif")
            except Exception as e:
                log.warning("[ADAPTIF] Baslatma hatasi: %s", e)

        # ── Skill iyileştirici ──────────────────────────────────────
        self._skill_iyi = None
        if _SKILL_IYI_AKTIF:
            try:
                self._skill_iyi = SkillIyilestirici()
                log.info("[SKILL_IYI] Skill iyilestirici aktif")
            except Exception as e:
                log.warning("[SKILL_IYI] Baslatma hatasi: %s", e)

    # ══════════════════════════════════════════════════════════════════
    # MEVCUT API — geriye uyumluluk
    # ══════════════════════════════════════════════════════════════════

    def coz(self, hedef: str, baglam: Optional[dict] = None) -> dict:
        """Bir hedefi cozmek icin konusma dongusunu baslat (eski API).

        Args:
            hedef:  Kullanicinin hedefi.
            baglam: Ek baglam (opsiyonel).

        Returns:
            Cozum sonucu dict'i.
        """
        self._durum = "calisiyor"
        baslama = time.time()
        tur = 0

        if self.tur_yoneticisi:
            ctx = self.tur_yoneticisi.yeni_tur()
            ctx.toplam_gereksinim_sayisi = 1
        else:
            ctx = None

        sonuc = {"hedef": hedef, "basarili": False, "turlar": 0, "hata": None}

        try:
            while tur < self.max_tur:
                tur += 1

                # ── Nudge gozlem (kullanici modeli) ────────────────
                if self._nudge and hedef:
                    try:
                        self._nudge.gozlemle(hedef, "")
                    except Exception:
                        pass

                if self.beyin:
                    eylem = self._beyin_eylem_sec(hedef, baglam)
                else:
                    # Beyin yok -> run_conversation'a yonlendir (ReYMeN stili ReAct loop)
                    return self.run_conversation(hedef, baglam)

                if eylem.get("tur") == "arac":
                    if self.tur_yoneticisi and ctx:
                        ctx.karar_ekle("arac_kullan", eylem.get("arac"))
                    arac_sonuc = self._arac_calistir(eylem)
                    if self.tur_yoneticisi and ctx:
                        ctx.karar_bitir(
                            arac_sonuc.get("basarili", False),
                            sonuc=arac_sonuc.get("cikti"),
                        )
                    baglam = baglam or {}
                    baglam["son_arac_sonucu"] = arac_sonuc

                    if arac_sonuc.get("tamamlandi"):
                        sonuc["basarili"] = True
                        if ctx:
                            ctx.cozum_ozeti = arac_sonuc.get("cikti", "")[:200]
                        break

                elif eylem.get("tur") == "mesaj":
                    sonuc["mesaj"] = eylem.get("icerik")
                    sonuc["basarili"] = True
                    break

                elif eylem.get("tur") == "hata":
                    sonuc["hata"] = eylem.get("icerik")
                    break

        except Exception as e:
            sonuc["hata"] = f"Dongu hatasi: {e}"
            sonuc["traceback"] = traceback.format_exc()

        sonuc["turlar"] = tur
        sonuc["sure"] = round(time.time() - baslama, 2)
        self._durum = "tamamlandi" if sonuc["basarili"] else "hata"

        if self.tur_yoneticisi and ctx:
            sonuc["tur_raporu"] = ctx.raporla()

        return sonuc

    # ══════════════════════════════════════════════════════════════════
    # YENİ API — run_conversation (ReYMeN Agent seviyesi)
    # ══════════════════════════════════════════════════════════════════

    def run_conversation(
        self,
        hedef: str,
        baglam: Optional[dict] = None,
        provider: Optional[str] = None,
    ) -> dict:
        """Konusma dongusu — ReYMeN-style ReAct loop (birebir ayni akis).

        Akis (ReYMeN ReAct):
          1. SETUP (task_id + session + budget + sistem_prompt)
          2. BUILD messages (system + gecmis + user + context)
          3. REACT LOOP (max_tur):
             a. API cagrisi (retry + fallback ile)
             b. tool_calls varsa -> _arac_calistir -> append -> loop
             c. text response -> break
          4. POST-PROCESS (kaydet + session kapat + log)

        ReYMeN'ten farkli olan (ReYMeN'e ozgu):
          - Sistem prompt _sistem_promptu_olustur ile build edilir (profil+SOUL)
          - Tool'lar motor.py uzerinden calisir (reymen motor)
          - OnceHafiza'ya sonuc otomatik kaydedilir (ogrenme)
          - A2A broadcast destegi

        Args:
            hedef:    Kullanicinin hedefi.
            baglam:   Ek baglam dicti (opsiyonel).
            provider: Provider override.

        Returns:
            Sonuc dicti (task_id, basarili, turlar, sure, yanit, ...).
        """
        # -- 1. SETUP ------------------------------------------------
        task_id = str(uuid.uuid4())[:8]
        try:
            if _CL_AKTIF:
                _cl_baslat(task_id)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        log.info("[%s] run_conversation basladi: %.60s", task_id, hedef)

        baslama = time.time()
        self._durum = "calisiyor"
        self._iptal_istegi = False
        api_call_count = 0
        max_tur = self.max_tur

        sonuc: dict = {
            "task_id":   task_id,
            "hedef":     hedef,
            "basarili":  False,
            "turlar":    0,
            "hata":      None,
            "provider":  provider,
            "yanit":     None,
        }

        # Session baslat
        session_id = None
        _storage = None
        if _SESSION_AKTIF and _SessionStorage:
            try:
                _storage = _SessionStorage()
                model_adi = (
                    getattr(self.beyin, "model", None)
                    if self.beyin else None
                )
                session_id = _storage.session_baslat(
                    source="run_conversation",
                    model=model_adi,
                    system_prompt=hedef[:500] if hedef else None,
                    billing_provider=provider,
                )
                sonuc["session_id"] = session_id
                log.info("[%s] Session acildi: %s", task_id, session_id)
                if _HOOK_AKTIF and _oturum_baslat_tetikle is not None:
                    try:
                        _oturum_baslat_tetikle(session_id=session_id, task_id=task_id, agent_adi="reymen")
                    except Exception:
                        logger.warning("[hook] sessiz_except")
                # Plugin: on_session_start
                if _PLUGIN_AKTIF and _PLUGIN_SISTEMI is not None:
                    try:
                        _PLUGIN_SISTEMI.hook_cagir(
                            "on_session_start",
                            session_id=session_id or task_id,
                            user_id=baglam.get("user_id", "unknown") if baglam else "unknown",
                        )
                    except Exception:
                        logger.warning("[plugin] on_session_start sessiz_except")
            except Exception as _se:
                log.warning("[%s] Session baslatma hatasi: %s", task_id, _se)

        budget = self._budget_olustur(hedef)

        if _HOOK_AKTIF and _tur_baslat_tetikle is not None:
            try:
                _tur_baslat_tetikle(tur=1, task_id=task_id, hedef=hedef[:100])
            except Exception:
                logger.warning("[hook] sessiz_except")

        # -- A2A mesaj kontrolu ------------------------------------------
        if self._a2a_agent is not None:
            try:
                a2a_msg = self._a2a_agent.receive(timeout=0.1)
                if a2a_msg is not None:
                    log.info("[%s] A2A mesaj alindi: sender=%s icerik=%.60s", task_id, a2a_msg.sender, str(a2a_msg.content))
                    self._konusma_gecmisi.append({
                        "role": "user",
                        "content": f"[A2A: {a2a_msg.sender}] {a2a_msg.content}",
                    })
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

        # -- 2. BUILD messages -------------------------------------------
        # System prompt: TEK sefer build edilir
        sistem_prompt = self._sistem_promptu_olustur(hedef, baglam)
        provider_tipi = self._provider_tipi_belirle(provider)
        sonuc["provider"] = provider_tipi

        # ReYMeN pattern: messages = [system] + conversation_history + [user]
        messages = [{"role": "system", "content": sistem_prompt}]

        # Konusma gecmisini ekle (son N mesaj)
        for m in self._konusma_gecmisi:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                messages.append(m)

        # Session context injection
        if _storage and session_id:
            try:
                session_baglam = self._session_context_injection(session_id, _storage)
                if session_baglam:
                    messages.append({"role": "user", "content": session_baglam})
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

        # Skill tarama (FTS5)
        try:
            skill_icerik = self._skill_tara(hedef)
            if skill_icerik:
                messages.append({"role": "user", "content": skill_icerik})
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # -- @file/@url Referans Isleme (ref_processor) -----------------
        if _REF_PROCESSOR_AKTIF and _ref_isle is not None and _ref_context_olustur is not None:
            try:
                ref_zengin_metin, ref_liste = _ref_isle(hedef)
                if ref_liste:
                    ref_context = _ref_context_olustur(ref_liste)
                    if ref_context:
                        messages.append({"role": "user", "content": ref_context})
                        log.info("[%s] %d referans eklendi (file=%d url=%d)",
                                 task_id,
                                 len(ref_liste),
                                 sum(1 for r in ref_liste if r.get("tip") == "file" and r.get("basarili")),
                                 sum(1 for r in ref_liste if r.get("tip") == "url" and r.get("basarili")))
                    # Basarisiz referanslari logla
                    for ref in ref_liste:
                        if not ref.get("basarili"):
                            log.warning("[%s] Ref basarisiz: %s=%s — %s",
                                        task_id, ref["tip"], ref["kaynak"], ref.get("hata", "?"))
                    # Orijinal mesajdaki @file/@url'leri [REF:] ile degistir
                    hedef = ref_zengin_metin
            except Exception as _ref_e:
                log.warning("[%s] RefProcessor hatasi: %s", task_id, _ref_e)

        # Kullanici mesaji (en son)
        # Plugin: on_message — mesaji değiştirme şansı
        if _PLUGIN_AKTIF and _PLUGIN_SISTEMI is not None:
            try:
                plugin_context = {"task_id": task_id, "baglam": baglam or {}}
                hedef = _PLUGIN_SISTEMI.hook_cagir_mesaj(
                    "on_message", message=hedef, context=plugin_context,
                )
            except Exception:
                logger.warning("[plugin] on_message sessiz_except")

        user_msg = hedef
        if baglam:
            import json as _json
            baglam_str = _json.dumps(baglam, ensure_ascii=False)
            user_msg = f"{baglam_str}\n\n{hedef}"
        messages.append({"role": "user", "content": user_msg})

        # Session Search: kullanici mesajini kaydet
        self._session_search_kaydet(session_id, user_msg, "user")

        # -- 3. REACT LOOP -----------------------------------------------
        final_yanit = None
        interrupted = False

        # Delegasyon kontrolu (subagent) — eger hedef subagent gerektiriyorsa
        # direkt conversation loop'a girmeden coz
        if _DELEGASYON_AKTIF and _delegasyon_sistemi_al is not None:
            try:
                delegasyon_sonuc = self._delegasyon_kontrol(hedef)
                if delegasyon_sonuc and delegasyon_sonuc.get("basarili"):
                    sonuc["basarili"] = True
                    sonuc["yanit"] = delegasyon_sonuc.get("yanit", "")
                    sonuc["delegasyon"] = delegasyon_sonuc
                    sonuc["turlar"] = 0
                    sonuc["sure"] = round(time.time() - baslama, 2)
                    self._durum = "tamamlandi"
                    log.info(
                        "[%s] Delegasyon ile cozuldu: mod=%s sure=%.1fs",
                        task_id,
                        delegasyon_sonuc.get("mod", "?"),
                        sonuc["sure"],
                    )
                    return sonuc
            except Exception as _de:
                log.warning("[%s] Delegasyon kontrol hatasi: %s", task_id, _de)

        while api_call_count < max_tur and budget.devam_etmeli_mi():
            api_call_count += 1

            if self._iptal_istegi:
                interrupted = True
                log.info("[%s] Interrupt istegi alindi", task_id)
                break

            budget.tur_basla()

            # API cagrisi (ReYMeN pattern: retry + fallback ile)
            api_yanit = None

            # ── Rules Engine: API cagrisi kontrolu ─────────────────────
            if _RULES_AKTIF and _RULES_ENGINE is not None:
                try:
                    import re as _re
                    # Provider/model adini bul
                    provider_info = provider_tipi or provider or "bilinmiyor"
                    api_hedef = f"llm_call:{provider_info}"
                    # Son kullanici mesajindan kisa bir kesit al
                    if messages and len(messages) > 1:
                        son_mesaj = str(messages[-1].get("content", ""))[:100]
                        if son_mesaj:
                            api_hedef = f"{api_hedef} {son_mesaj}"
                    kural_sonuc = _RULES_ENGINE.kontrol("api_cagrisi", api_hedef)
                    if not kural_sonuc.get("izin"):
                        log.warning("[%s] [Rules] API cagrisi ENGELLENDI: %s", task_id, kural_sonuc.get("sebep", ""))
                        sonuc["hata"] = f"API cagrisi engellendi: {kural_sonuc.get('sebep', '')}"
                        sonuc["kural"] = kural_sonuc
                        budget.tur_bitir(basarili=False)
                        break
                except Exception as _re:
                    log.debug("[%s] [Rules] API kontrol hatasi (sessiz): %s", task_id, _re)

            # Plugin: pre_llm_call — mesajları değiştirme şansı
            try:
                if _PLUGIN_AKTIF and _PLUGIN_SISTEMI is not None:
                    plugin_ctx = {"task_id": task_id, "tur": api_call_count}
                    messages, _ = _PLUGIN_SISTEMI.hook_cagir_pre_llm(messages, plugin_ctx)
            except Exception:
                logger.warning("[plugin] pre_llm_call sessiz_except")
            try:
                api_yanit = self._direct_api_call(messages, tools_bos=False)
            except Exception as _ae:
                log.warning("[%s] API cagri hatasi (tur %d): %s", task_id, api_call_count, _ae)
                try:
                    from reymen.cereyan.beyin import _provider_rotate
                    yeni_provider = _provider_rotate(provider_tipi)
                    if yeni_provider:
                        sonuc["provider"] = yeni_provider
                        log.info("[%s] Fallback provider: %s", task_id, yeni_provider)
                        api_yanit = self._direct_api_call(messages, tools_bos=False)
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")

            # Plugin: post_llm_call — yanıtı işleme şansı
            try:
                if _PLUGIN_AKTIF and _PLUGIN_SISTEMI is not None and api_yanit is not None:
                    plugin_ctx = {"task_id": task_id, "tur": api_call_count}
                    api_yanit = _PLUGIN_SISTEMI.hook_cagir_post_llm(api_yanit, plugin_ctx)
            except Exception:
                logger.warning("[plugin] post_llm_call sessiz_except")

            if api_yanit is None:
                sonuc["hata"] = f"API cagrisi basarisiz (tur {api_call_count})"
                log.warning("[%s] %s", task_id, sonuc["hata"])
                self._hata_cozumle(sonuc["hata"], kaynak="api_call")
                budget.tur_bitir(basarili=False)
                break

            # API yaniti: _direct_api_call simplified format dondurur
            # {"role": "assistant", "content": "...", "tool_calls": [...]}
            # NOT: OpenAI full response degil, direkt message dict
            tool_calls = self._tool_calls_al(api_yanit)
            yanit_icerik = self._yanit_icerigi_al(api_yanit)

            if tool_calls:
                # Once assistant mesajini ekle (tool_calls iceren)
                msg_kopya = dict(api_yanit)
                messages.append(msg_kopya)

                for tc in tool_calls:
                    # OpenAI tool call -> ReYMeN eylem formatina cevir
                    fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                    arac_adi = fn.get("name", "")
                    try:
                        import json as _json
                        parametreler = _json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        parametreler = {}
                    eylem = {"arac": arac_adi, "parametreler": parametreler, "tur": "arac"}

                    arac_sonuc = self._arac_calistir(eylem)
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc.get("id", str(uuid.uuid4())[:8]),
                        "content": arac_sonuc.get("cikti", str(arac_sonuc)),
                    }
                    messages.append(tool_msg)

                    if arac_sonuc.get("tamamlandi"):
                        final_yanit = arac_sonuc.get("cikti", "")
                        sonuc["basarili"] = True
                        break

                if sonuc["basarili"]:
                    budget.tur_bitir(basarili=True)
                    break

                budget.tur_bitir(basarili=True)
                continue
            elif yanit_icerik:
                final_yanit = yanit_icerik
                sonuc["basarili"] = True
                messages.append({"role": "assistant", "content": final_yanit})
                # Session Search: asistan yanitini kaydet
                self._session_search_kaydet(session_id, final_yanit, "assistant")
                budget.tur_bitir(basarili=True)
                break

            else:
                sonuc["hata"] = f"Bos yanit (tur {api_call_count})"
                self._hata_cozumle(sonuc["hata"], kaynak="bos_yanit")
                budget.tur_bitir(basarili=False)
                break

        if interrupted:
            self._durum = "iptal"
            sonuc["hata"] = "Kullanici tarafindan iptal edildi"

        sonuc["turlar"] = api_call_count
        sonuc["sure"] = round(time.time() - baslama, 2)
        if final_yanit:
            sonuc["yanit"] = final_yanit
        self._durum = "tamamlandi" if sonuc["basarili"] else "hata"

        # Yanit dogrulama
        if sonuc["basarili"] and final_yanit:
            yanit_metin = str(final_yanit)
            if not yanit_metin or len(yanit_metin.strip()) < 5:
                log.warning(
                    "[%s] DOGRULA: yanit cok kisa (%d char) - basarisiz sayiliyor",
                    task_id, len(yanit_metin.strip()),
                )
                sonuc["basarili"] = False
                sonuc["dogrulama_uyarisi"] = "yanit_cok_kisa"

        # -- 4. POST-PROCESS ---------------------------------------------

        # OnceHafiza'ya kaydet (ogrenme)
        if sonuc["basarili"] and final_yanit and len(str(final_yanit).strip()) > 20:
            try:
                self._gorev_sonrasi_hafiza(
                    hedef=hedef,
                    yanit=str(final_yanit)[:500],
                    task_id=task_id,
                )
                sonuc["kaydedildi"] = True
            except Exception as _ke:
                log.warning("[%s] KAYDET hatasi: %s", task_id, _ke)
                sonuc["kaydedildi"] = False

        # Konusmadan skill cikar
        if sonuc["basarili"] and _SKILL_CIKAR_AKTIF:
            try:
                _skill_cikar(
                    messages=self._konusma_gecmisi,
                    basari=True,
                    konu=hedef[:60],
                )
            except Exception as _sce:
                log.debug("[%s] Skill cikarma atlandi: %s", task_id, _sce)

        # Konusma gecmisini guncelle
        self._gecmis_mesajlar = [
            dict(m) for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ][-self._max_gecmis_mesaj:]

        # Hook: tur bitisi
        if _HOOK_AKTIF and _tur_bitir_tetikle is not None:
            try:
                _tur_bitir_tetikle(
                    tur=api_call_count,
                    basarili=sonuc["basarili"],
                    task_id=task_id,
                    kaynak="react_loop",
                )
            except Exception:
                logger.warning("[hook] sessiz_except")

        # A2A broadcast
        if self._a2a_agent is not None and final_yanit:
            try:
                self._a2a_broker.broadcast(
                    "conversation_loop",
                    {"task_id": task_id, "yanit": str(final_yanit)[:200]},
                    exclude={self._a2a_agent.id},
                )
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

        # Session kapat
        if _storage and session_id:
            try:
                end_reason = "completed" if sonuc["basarili"] else (
                    "cancelled" if self._durum == "iptal" else "error"
                )
                _storage.session_bitir(session_id, end_reason=end_reason)
                log.info("[%s] Session kapatildi: %s (%s)", task_id, session_id, end_reason)
                # Plugin: on_session_end
                if _PLUGIN_AKTIF and _PLUGIN_SISTEMI is not None:
                    try:
                        _PLUGIN_SISTEMI.hook_cagir(
                            "on_session_end",
                            session_id=session_id or task_id,
                            reason=end_reason,
                        )
                    except Exception:
                        logger.warning("[plugin] on_session_end sessiz_except")
                if _HOOK_AKTIF and _oturum_bitir_tetikle is not None:
                    try:
                        _oturum_bitir_tetikle(
                            session_id=session_id,
                            tur_sayisi=api_call_count,
                            basarili=sonuc["basarili"],
                            task_id=task_id,
                        )
                    except Exception:
                        logger.warning("[hook] sessiz_except")
            except Exception as _se:
                log.warning("[%s] Session bitirme hatasi: %s", task_id, _se)

        log.info(
            "[%s] run_conversation bitti: basarili=%s, tur=%d, sure=%.1fs",
            task_id, sonuc["basarili"], api_call_count, sonuc["sure"],
        )

        try:
            from reymen.self_improve import record_step, QualityMetric
            record_step(QualityMetric(
                success=sonuc.get("basarili", False),
                step_name=hedef[:60] if hedef else "",
                errors=1 if not sonuc.get("basarili") else 0,
                retries=getattr(self, "_retry_sayaci", 0),
                duration=sonuc.get("sure", 0),
                tokens_used=getattr(budget, "kullanilan_token", 0),
            ))
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # ── Proaktif kontrol: her cevap sonrası eksik analizi ─────────
        if _PROAKTIF_AKTIF and hedef and sonuc and sonuc.get("yanit"):
            try:
                _proaktif_kontrol(hedef, str(sonuc.get("yanit", "")))
            except Exception:
                pass

        # ── Hafif compaction kontrolu: her konusma sonrasi ───────────
        # MEMORY.md/USER.md %80 doluluk esigini gecerse otomatik compaction
        try:
            from reymen.cereyan.memory_compaction import hafif_compaction_kontrol
            _comp_sonuc = hafif_compaction_kontrol()
            if _comp_sonuc.get("islem_yapildi"):
                log.info("[%s] Compaction yapildi: %s",
                         task_id, _comp_sonuc.get("compaction", {}))
                sonuc["compaction"] = _comp_sonuc
        except ImportError:
            pass  # memory_compaction modulu yoksa sessiz gec
        except Exception as _comp_e:
            log.debug("[%s] Compaction kontrol hatasi (sessiz): %s",
                      task_id, _comp_e)

        return sonuc

    def _hata_coz(self, hata: Exception, hedef: str, task_id: str) -> Optional[str]:
        '''Hata alinca OnceHafiza+ogrenme.py ile cozum bul, yoksa LLM'e sor.
        Cozumu OnceHafiza'ya kaydeder, bir daha ayni hata gelmez.'''
        # 1. Ogrenme modulunden imza + cozum ara
        try:
            from reymen.core.ogrenme import imza_uret, cozum_bul, cozum_kaydet
            imza = imza_uret(hata)
            if imza:
                onceki_cozum = cozum_bul(imza)
                if onceki_cozum:
                    log.info("[%s] _hata_coz: onceki cozum bulundu: %.60s", task_id, str(onceki_cozum)[:60])
                    return onceki_cozum
        except ImportError:
            imza = None
            onceki_cozum = None

        # 2. OnceHafiza'da hata cozumu ara
        try:
            from reymen.sistem.once_hafiza import hafizada_ara as _ha
            hata_sorgu = f"hata: {str(hata)[:100]}"
            oh_sonuc = _ha(hata_sorgu, kategori="hata")
            if oh_sonuc:
                cozum = oh_sonuc.get("yanit") or oh_sonuc.get("sonuc") or oh_sonuc.get("cozum", "")
                if cozum:
                    log.info("[%s] _hata_coz: OnceHafiza'da cozum bulundu", task_id)
                    return cozum
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # 3. Yoksa LLM'e sor (cozum uret)
        try:
            cozum_soru = f"Hata alindi: {hata}. Cozum nedir? Kisa ve oz."
            ds_mesaj = [
                {"role": "system", "content": "Hata cozum onerisi ver. Kisa, oz, dogrudan."},
                {"role": "user", "content": cozum_soru}
            ]
            ds_yanit = self._direct_api_call(ds_mesaj, tools_bos=True)
            if ds_yanit:
                cozum = ds_yanit.get("content", "") or ""
                if cozum and len(cozum.strip()) > 5:
                    # LLM cozumunu OnceHafiza'ya kaydet
                    try:
                        from reymen.sistem.once_hafiza import kaydet as _kaydet
                        _kaydet(hedef=f"hata: {str(hata)[:100]}", cozum=str(cozum)[:500], kategori="hata", kaynak="hata_cozucu")
                        log.info("[%s] _hata_coz: LLM cozumu OnceHafiza'ya kaydedildi", task_id)
                    except Exception as _e:
                        __import__("logging").getLogger(__name__).warning(
                            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                        )
                    # ogrenme.py'ye de kaydet
                    try:
                        if imza:
                            cozum_kaydet(imza, type(hata).__name__, str(hata)[:100], str(cozum)[:500])
                    except Exception as _e:
                        __import__("logging").getLogger(__name__).warning(
                            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                        )
                    return cozum
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        return None

    def _hata_analiz_entegre(self, hata: Exception, task_id: str) -> None:
        '''hata_analiz.py modulunu cagir (varsa).'''
        try:
            from reymen.cereyan.hata_cozucu import HataKaydi, HataWatchdog
            watchdog = HataWatchdog()
            watchdog.baslat()
            kayit = HataKaydi(
                kaynak="conversation_loop",
                hata_tipi=type(hata).__name__,
                mesaj=str(hata)[:200],
            )
            log.info("[%s] _hata_analiz_entegre: HataWatchdog calisti", task_id)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

    def _oneri_uret(self, hedef: str) -> Optional[str]:
        '''OnceHafiza tabanli belirsiz gorev onerisi.
        Hedef cok kisa/belirsizse en alakali OnceHafiza kategorisini bulur.
        TEK tahmin: "Sanirim X demek istiyorsun" formatinda.
        '''
        if not _ONCE_HAFIZA_AKTIF or _hafizada_ara is None:
            return None
        try:
            sonuc = _hafizada_ara(hedef)
            if sonuc and sonuc.get("guven", 0) > 0.3:
                kate = sonuc.get("kategori") or sonuc.get("kaynak", "genel")
                return f"Sanirim {kate} ile ilgili bir sey istiyorsun, dogru mu?"
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return None

    def _takilma_kontrol(self, eylem_adi: str) -> bool:
        '''Ayni eylem 3x tekrarlanirsa True doner (takilma tespiti).'''
        self._onceki_eylemler.append(eylem_adi)
        if len(self._onceki_eylemler) > TAKILMA_ESIĞI:
            self._onceki_eylemler = self._onceki_eylemler[-TAKILMA_ESIĞI:]
        return (
            len(self._onceki_eylemler) >= TAKILMA_ESIĞI
            and len(set(self._onceki_eylemler[-TAKILMA_ESIĞI:])) == 1
        )

    def _gorev_sonrasi_hafiza(self, hedef: str, yanit: str, task_id: str) -> None:
        '''Gorev sonrasi OnceHafiza'yi guncelle (ogrenme).'''
        if not _ONCE_HAFIZA_AKTIF:
            return
        try:
            from reymen.sistem.once_hafiza import kaydet as _kaydet
            _kaydet(
                hedef=hedef,
                cozum=str(yanit)[:500],
                kategori="conversation",
                kaynak=f"run_conversation_{task_id}",
            )
            log.debug("[%s] _gorev_sonrasi_hafiza: kaydedildi", task_id)
        except Exception as _he:
            log.warning("[%s] _gorev_sonrasi_hafiza hatasi: %s", task_id, _he)

    def _vision_analiz(self, sorgu: str) -> Optional[str]:
        '''Gorsel/resim analizi. Sorguda URL/dosya yolu varsa analiz et.
        Once DeepSeek V4 Flash (multimodal) dene, olmazsa OpenRouter vision.
        Dosya yolunu otomatik tani: C:\... veya ./... veya ~/...
        '''
        import re as _re
        # URL bul
        url_match = _re.search(r'https?://[^\s]+\.(jpg|jpeg|png|gif|webp|bmp)', sorgu, _re.IGNORECASE)
        # Dosya yolu bul (Windows: C:\... , Unix: /... , relative: ./... veya ~/...)
        dosya_match = None
        if not url_match:
            dosya_match = _re.search(r'([a-zA-Z]:\\[^\s]+\.(jpg|jpeg|png|gif|webp|bmp))', sorgu, _re.IGNORECASE)
        if not url_match and not dosya_match:
            dosya_match = _re.search(r'(\.\.?/[^\s]+\.(jpg|jpeg|png|gif|webp|bmp))', sorgu, _re.IGNORECASE)

        if not url_match and not dosya_match:
            gorsel_kelimeler = [
            "foto", "fotoğraf", "fotograf", "resim", "gorsel", "görsel",
            "goruntu", "görüntü", "ekran", "ss", "screenshot", "screenshot",
            "image", "photo", "picture", "capture", "snapshot",
            "ne var", "bak", "göster", "goster", "analiz et", "incele",
        ]
            if not any(k in sorgu.lower() for k in gorsel_kelimeler):
                return None
            return None

        try:
            from openai import OpenAI
            import base64, os as _os

            api_key = _os.environ.get("DEEPSEEK_API_KEY", "")
            base_url = "https://api.deepseek.com"
            model = "deepseek-v4-flash"

            # Dosya varsa base64'e cevir
            resim_url = url_match.group(0) if url_match else ""
            if dosya_match:
                dosya_yol = dosya_match.group(1)
                if _os.path.exists(dosya_yol):
                    with open(dosya_yol, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    resim_url = f"data:image/jpeg;base64,{img_b64}"
                else:
                    return f"Dosya bulunamadi: {dosya_yol}"

            client = OpenAI(api_key=api_key, base_url=base_url)
            r = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Bu gorseli Turkce analiz et, detayli acikla."},
                            {"type": "image_url", "image_url": {"url": resim_url}}
                        ]
                    }
                ],
                max_tokens=1024,
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            # DeepSeek vision calismazsa OpenRouter dene
            try:
                or_key = _os.environ.get("OPENROUTER_API_KEY", "")
                if not or_key:
                    return f"DeepSeek vision hatasi: {e}.\nOPENROUTER_API_KEY ile Qwen-VL dene."
                client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
                r = client.chat.completions.create(
                    model="qwen/qwen-vl-plus:free",
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": "Bu gorseli Turkce analiz et."},
                        {"type": "image_url", "image_url": {"url": resim_url}}
                    ]}],
                    max_tokens=1024,
                )
                return r.choices[0].message.content.strip()
            except Exception as e2:
                return f"Gorsel analiz hatasi: {e2}"

    def _skill_bul(self, sorgu: str, limit: int = 2) -> Optional[str]:
        '''FTS5 skills_index.db'de sorguya en alakali skill'i bul.'''
        try:
            import sqlite3, re
            db_path = os.path.join(os.path.dirname(__file__), ".ReYMeN", "skills_index.db")
            if not os.path.exists(db_path):
                return None
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            # FTS5 ile ara
            kelimeler = re.findall(r'\w+', sorgu.lower())
            fts_query = " OR ".join(f'"{k}"' for k in kelimeler[:5] if len(k) > 2)
            if not fts_query:
                conn.close()
                return None
            cur.execute(
                "SELECT beceriler.name, beceriler_5n1k.ne FROM beceriler "
                "JOIN beceriler_5n1k ON beceriler.rowid = beceriler_5n1k.rowid "
                "WHERE beceriler MATCH ? LIMIT ?",
                (fts_query, limit)
            )
            rows = cur.fetchall()
            conn.close()
            if rows:
                metin = ""
                for name, aciklama in rows:
                    if name:
                        metin += f"- {name}: {str(aciklama or '')[:100]}\n"
                return metin.strip() if metin.strip() else None
            return None
        except Exception:
            return None

    def _ensemble_dogrula(self, ensemble: dict, sonuc: dict, task_id: str) -> dict:
        '''Ensemble sonucunu dogrula: en iyi aday bos/hataliysa 2.yi dene.'''
        sirali = sorted(ensemble.values(), key=lambda x: x["puan"], reverse=True)
        for aday in sirali:
            yanit = aday.get("yanit", "")
            if yanit and len(str(yanit).strip()) > 5:
                sonuc["basarili"] = True
                sonuc["yanit"] = yanit
                sonuc["kaynak"] = aday["kaynak"]
                sonuc["puan"] = aday["puan"]
                log.info("[%s] Dogrulama: %s secildi (puan=%.1f)", task_id, aday["kaynak"], aday["puan"])
                return sonuc
        # Hicbiri uygun degil
        sonuc["basarili"] = False
        sonuc["hata"] = "Tum kaynaklar basarisiz veya bos"
        sonuc["dogrulama_uyarisi"] = "hepsi_bos"
        log.warning("[%s] Dogrulama: tum adaylar bos/hatali", task_id)
        return sonuc

    # ── Delegasyon (P2) — Subagent yönetimi ──────────────────────

    def _delegasyon_kontrol(self, hedef: str) -> Optional[Dict[str, Any]]:
        """
        Hedef metnini kontrol eder, delegasyon gerekiyorsa subagent
        oluşturup çalıştırır.

        Delegasyon ipuçları:
            - "delege et", "subagent", "alt ajan", "görev devret"
            - "paralel", "aynı anda", "zincir"
            - Numaralı liste + "paralel" veya "zincir" kelimeleri

        Returns:
            Delegasyon sonucu dict veya None (delegasyon gerekmiyorsa)
        """
        if not _DELEGASYON_AKTIF:
            return None

        try:
            # Lazy import — GorevAyrıştırıcı
            from reymen.ag.delegasyon import GorevAyrıştırıcı
            
            hedef_lower = hedef.lower()

            # Delegasyon tetikleyicileri
            tek_tetik = ["delege et", "subagent çalıştır", "alt ajan", "görev devret"]
            paralel_tetik = ["paralel", "aynı anda", "eş zamanlı", "beraber"]
            zincir_tetik = ["zincir", "sırayla", "ardışık", "adım adım"]

            # Mod belirle
            mod = None
            for t in tek_tetik:
                if t in hedef_lower:
                    mod = "TEK"
                    break
            if not mod:
                for t in zincir_tetik:
                    if t in hedef_lower:
                        mod = "ZINCIR"
                        break
            if not mod:
                for t in paralel_tetik:
                    if t in hedef_lower:
                        mod = "PARALEL"
                        break

            if not mod:
                return None  # Delegasyon gerekmiyor

            sistem = _delegasyon_sistemi_al()
            if sistem is None:
                return None

            if mod == "TEK":
                agent = sistem.delege_et(goal=hedef)
                if agent.basarili_mi():
                    return {
                        "basarili": True,
                        "mod": "TEK",
                        "yanit": agent.result,
                        "agent_id": agent.id,
                        "sure": agent.sure,
                    }
                return {
                    "basarili": False,
                    "mod": "TEK",
                    "hata": agent.error,
                    "agent_id": agent.id,
                }

            elif mod == "PARALEL":
                alt_gorevler = GorevAyrıştırıcı.ayir(hedef)
                if len(alt_gorevler) >= 2:
                    gorev_dicts = [
                        {"goal": a.goal, "context": a.context}
                        for a in alt_gorevler[:3]
                    ]
                    agentler = sistem.paralel_delege(gorev_dicts)
                    basarili = sum(1 for a in agentler if a.basarili_mi())

                    if basarili > 0:
                        yanit_parts = [
                            f"[Paralel {basarili}/{len(agentler)} başarılı]"
                        ]
                        for a in agentler:
                            ikon = "✅" if a.basarili_mi() else "❌"
                            yanit_parts.append(f"{ikon} {a.goal[:50]}: {a.result[:200]}")
                        return {
                            "basarili": True,
                            "mod": "PARALEL",
                            "yanit": "\n".join(yanit_parts),
                            "agentler": [a.id for a in agentler],
                        }
                else:
                    # Paralel için yeterli görev yok, TEK dene
                    agent = sistem.delege_et(goal=hedef)
                    if agent.basarili_mi():
                        return {
                            "basarili": True,
                            "mod": "TEK",
                            "yanit": agent.result,
                            "agent_id": agent.id,
                        }

            elif mod == "ZINCIR":
                alt_gorevler = GorevAyrıştırıcı.ayir(hedef)
                if len(alt_gorevler) >= 2:
                    adim_dicts = [
                        {"goal": a.goal, "context": a.context}
                        for a in alt_gorevler
                    ]
                    agentler = sistem.zincir_delege(adim_dicts)
                    basarili = sum(1 for a in agentler if a.basarili_mi())

                    yanit_parts = [
                        f"[Zincir {basarili}/{len(agentler)} adım başarılı]"
                    ]
                    for i, a in enumerate(agentler, 1):
                        ikon = "✅" if a.basarili_mi() else "❌"
                        yanit_parts.append(f"Adım {i}: {ikon} {a.result[:200]}")
                    return {
                        "basarili": basarili > 0,
                        "mod": "ZINCIR",
                        "yanit": "\n".join(yanit_parts),
                        "agentler": [a.id for a in agentler],
                    }

            return None

        except Exception as e:
            logger.warning(f"[Delegasyon] Kontrol hatası: {e}")
            return None

    def _mcp_web_ara(self, sorgu: str, maks_sonuc: int = 3) -> Optional[str]:
        """MCP uzerinden web aramayi dene (Firecrawl / search server).

        Oncelik sirasi:
          1. native_mcp_client (NativeMCPClient) — firecrawl server
          2. mcp_client_tool (MCPClientYoneticisi) — firecrawl server
          3. mcp_tool (MCPIstemci) — firecrawl server
        """
        # 1. Native MCP Client
        if _MCP_NATIVE_AKTIF and hasattr(self, '_native_mcp') and self._native_mcp:
            try:
                baglantilar = getattr(self._native_mcp, '_baglantilar', {})
                for ad, baglanti in baglantilar.items():
                    if 'firecrawl' in ad.lower() or 'search' in ad.lower():
                        if getattr(baglanti, 'bagli', False):
                            sonuc = baglanti.arac_cagir('search', {'query': sorgu, 'limit': maks_sonuc})
                            if sonuc and sonuc not in ('[]', '{}', '', '[MCP] Baglanti aktif degil'):
                                return f"[MCP-{ad}] {sonuc}"
            except Exception as _e:
                logger.warning("[ConversationLoop] except Exception (L1374): %s", Exception)
                pass

        # 2. MCP Client Tool
        if _MCP_CLIENT_AKTIF:
            try:
                yonetici = _mcp_client_get()
                durum = yonetici.durum()
                for ad in durum:
                    if 'firecrawl' in ad.lower() or 'search' in ad.lower():
                        sonuc = yonetici.arac_cagir(ad, 'search', {'query': sorgu, 'limit': maks_sonuc})
                        if sonuc and not sonuc.startswith('[MCPClient]'):
                            return f"[MCP-{ad}] {sonuc}"
            except Exception as _e:
                logger.warning("[ConversationLoop] except Exception (L1387): %s", Exception)
                pass

        # 3. MCP Tool (mcp_tool.py — MCPIstemci)
        if _MCP_TOOL_AKTIF:
            try:
                istemci = _mcp_istemci_get()
                durum = istemci.durum()
                for ad, bilgi in durum.items():
                    if 'firecrawl' in ad.lower() or 'search' in ad.lower():
                        if bilgi.get('aktif', False):
                            sonuc = istemci.arac_cagir(ad, 'search', {'query': sorgu, 'limit': maks_sonuc})
                            if sonuc and not sonuc.startswith('[MCP]'):
                                return f"[MCP-{ad}] {sonuc}"
            except Exception as _e:
                logger.warning("[ConversationLoop] except Exception (L1401): %s", Exception)
                pass

        return None

    def _web_ara(self, sorgu: str, maks_sonuc: int = 3) -> Optional[str]:
        '''Web arama yap — MCP Firecrawl öncelikli, sonra SearchDispatcher.
        LLM atlanir, direkt web verisi kullanilir (halusinasyon onleme).
        Basarisiz olursa hata sayaci tutar, 3 hata sonra devre disi kalir.

        Kullanilabilir engine'ler: duckduckgo, google, bing, firecrawl,
        brave, searxng, exa, auto (config'e gore en iyisi).
        Ayrica MCP firecrawl/search sunucusu varsa once o denenir.
        '''
        if not _WEB_ARAMA_AKTIF:
            return None
        # Circuit breaker: 3 hata sonra web aramayi kapat
        if hasattr(self, '_web_hata') and self._web_hata >= 3:
            return None
        try:
            # ÖNCE: MCP Firecrawl / search dene (varsa)
            mcp_sonuc = self._mcp_web_ara(sorgu, maks_sonuc)
            if mcp_sonuc:
                self._web_hata = 0
                return mcp_sonuc

            # FALLBACK: SearchDispatcher (DDGS + FirecrawlEngine + ...)
            from reymen.arac.web_search_engine import _get_registry
            dispatcher = _get_registry()
            sonuc_str = dispatcher.ara(sorgu, engine="auto", max_sonuc=maks_sonuc)
        except Exception as _we:
            self._web_hata = getattr(self, '_web_hata', 0) + 1
            if self._web_hata >= 3:
                log.warning("Web arama 3 kez hata verdi - kalici olarak devre disi")
            return None

        if not sonuc_str or sonuc_str.strip() in (
            "", "Sonuc bulunamadi.", "[WEB_ARAMA] Kullanilabilir engine bulunamadi."
        ):
            self._web_hata = getattr(self, '_web_hata', 0) + 1
            return None

        # Circuit breaker basarili aramada sifirlanir
        self._web_hata = 0
        return sonuc_str

    def _mcp_motor_kaydet(self) -> None:
        """Native MCP Client tool'larini motora kaydet."""
        if not self.motor or not hasattr(self.motor, '_plugin_arac_kaydet'):
            return
        if not self._native_mcp:
            return
        try:
            self._native_mcp._motor_ref = self.motor
            self._native_mcp._kesfedildi = False
            # native_mcp_client'ın motor_kaydet() metodunu çağır
            if hasattr(self._native_mcp, 'motor_kaydet'):
                self._native_mcp.motor_kaydet(self.motor)
            else:
                # Manuel kayıt
                for ad, baglanti in self._native_mcp._baglantilar.items():
                    for arac in baglanti.araclar:
                        arac_adi = f"MCP_{ad.upper()}_{arac['name'].upper()}"
                        def _fn(sun=ad, ar=arac['name'], **kw):
                            return baglanti.arac_cagir(ar, kw)
                        try:
                            self.motor._plugin_arac_kaydet(
                                arac_adi, _fn,
                                arac.get('description', f'MCP: {ad}/{arac["name"]}'),
                            )
                        except Exception as _e:
                            log.warning("[MCP] Tool kayit hatasi (%s): %s", arac_adi, _e)
        except Exception as _mcp_e:
            log.warning("[MCP] Motor kayit hatasi: %s", _mcp_e)

    # ══════════════════════════════════════════════════════════════════
    # YARDIMCI METODLAR — run_conversation
    # ══════════════════════════════════════════════════════════════════

    def _budget_olustur(self, hedef: str) -> Any:
        """IterationBudget olustur; modul yoksa basit sayac doner."""
        if _BUDGET_AKTIF and standart_budget:
            try:
                b = standart_budget(hedef)
                # max_tur degeri ConversationLoop ile uyumlu kalsin
                b.max_tur = max(b.max_tur, self.max_tur)
                return b
            except Exception as _e:
                logger.warning("[ConversationLoop] except Exception (L866): %s", Exception)
                pass

        # Fallback: basit sayac nesnesi
        class _SimpleBudget:
            def __init__(self, max_tur: int) -> None:
                self.max_tur = max_tur
                self.tur = 0
                self._bitti = False

            def devam_etmeli_mi(self) -> bool:
                return self.tur < self.max_tur and not self._bitti

            def tur_basla(self) -> None:
                self.tur += 1

            def tur_bitir(self, basarili: bool = True, **_: Any) -> None:
                self._bitti = basarili

            def gorev_tamamla(self) -> None:
                self._bitti = True

            # API uyumluluğu
            gorev_tamami = gorev_tamamla

            def eylem_kaydet(self, _: Any) -> None:
                pass  # API uyumlulugu

            def ozet_dict(self) -> dict:
                return {"tur": self.tur, "max_tur": self.max_tur}

        return _SimpleBudget(self.max_tur)

    # ── Session Search Kaydet ─────────────────────────────────────────
    def _session_search_kaydet(self, session_id: Optional[str], message: str, role: str = "user") -> None:
        """Session Search FTS5'e mesaj kaydet (guvenli)."""
        if not _SESSION_SEARCH_AKTIF or not self._session_search or not session_id or not message:
            return
        try:
            self._session_search.save(session_id, message, role)
        except Exception as _ss_e:
            log.debug("[SESSION_SEARCH] Kayit hatasi: %s", _ss_e)

    def _hata_cozumle(self, hata_metni: str, kaynak: str = "genel") -> None:
        """Hata aninda Reasoning-Core'u tetikle.
        
        conversation_loop icinden cagrilir: API hatasi, bos yanit, tool hatasi.
        reasoning_loop yoksa / calismazsa sessizce gec (ana akis bozulmasin).
        """
        if not _REASONING_AKTIF or _reasoning_loop is None:
            return
        try:
            # DURUM_OKU icin ortak_komut.guncelle() ciktisini kullan
            from reymen.sistem.ortak_komut import guncelle as _ortak_guncelle
            durum = _ortak_guncelle()
            durum_ozeti = str(durum)[:2000]
            
            # fallback_providers'i config.yaml'dan oku
            import yaml as _yaml
            cfg_yol = Path(__file__).parent.parent.parent / "config.yaml"
            if cfg_yol.exists():
                cfg = _yaml.safe_load(cfg_yol.read_text(encoding="utf-8"))
                fallback = cfg.get("fallback_providers", [])
            else:
                fallback = []
            
            _reasoning_loop(
                hata_metni=hata_metni,
                durum_ozeti=durum_ozeti,
                bot_adi="reymen_agent",
                fallback_providers=fallback,
            )
        except Exception as _rh:
            log.debug("[Reasoning-Core] Atlandi: %s", _rh)

    def _sistem_promptu_olustur(self, hedef: str, baglam: Optional[dict] = None) -> str:
        """PromptBuilder ile sistem promptu insa et."""
        if _BUILDER_AKTIF and PromptBuilder:
            try:
                pb = PromptBuilder()
                if self.motor and hasattr(self.motor, "arac_listesi"):
                    try:
                        pb.araclar_kaydet(self.motor.arac_listesi())
                    except Exception as _e:
                        logger.warning("[ConversationLoop] except Exception (L907): %s", Exception)
                        pass
                ek_bilgi = json.dumps(baglam, ensure_ascii=False) if baglam else ""
                # Skill context + Continuous learning baglami
                try:
                    if _CL_AKTIF:
                        cl_ctx = _cl_baglam()
                        if cl_ctx:
                            ek_bilgi += "\n\n" + cl_ctx
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
                # Skill context'ini ek_bilgi'ye ekle
                try:
                    from reymen.cereyan.active_skill_tracker import aktif_skill_context_ekle
                    skill_ctx = aktif_skill_context_ekle()
                    if skill_ctx:
                        ek_bilgi += "\n\n" + skill_ctx
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
                # ZORUNLU: Her mesajda otomatik yetki senkron + durum.json
                try:
                    from reymen.sistem.ortak_komut import guncelle as _ortak_guncelle
                    _ortak_guncelle()
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] ortak_komut: %%s", type(_e).__name__
                    )
                # NOT: Ham JSON kullanilir, insan-okunur ozet DEGIL.
                # Sebep: AI model ozet metni gorunce kendi training bilgisiyle karistiriyor.
                # Ham JSON'u tabloya cevirmek zorunda kalir, kendi ezberini kullanamaz.
                try:
                    from reymen.sistem.durum import _yukle
                    import json as _json_mod
                    _ham_veri = _yukle()
                    _ham_json = _json_mod.dumps(_ham_veri, indent=2, ensure_ascii=False)
                    ek_bilgi += "\n\n"
                    ek_bilgi += "=" * 50 + "\n"
                    ek_bilgi += "[ZORUNLU KURAL — ASAGIDAKI JSON TEK KAYNAKTIR]\n"
                    ek_bilgi += "ReYMeN durumu/eksikleri/kapasitesi hakkinda soru gelince:\n"
                    ek_bilgi += "1. Kendi training bilgini KULLANMA. Bu JSON TEK KAYNAK.\n"
                    ek_bilgi += "2. 'hermes>reymen yonleri' sorusunda:\n"
                    ek_bilgi += "   → 'ReYMeN_karsilastirma/detaylar' bolumundeki veriyi tablo yap.\n"
                    ek_bilgi += "   → ASLA: 'yok' olarak isaretleme (once JSON'a bak).\n"
                    ek_bilgi += "3. 'eksik listesi' sorusunda:\n"
                    ek_bilgi += "   → 'mevcut_eksikler/maddeler' bolumunu kullan.\n"
                    ek_bilgi += "4. ESKI BILDIGIN LISTELER yanlis. Bu JSON dogru.\n"
                    ek_bilgi += "5. Asla tahmin etme, asla uydurma.\n"
                    ek_bilgi += "=" * 50 + "\n"
                    ek_bilgi += _ham_json[:8000]  # Ilk 8000 karakter, token siniri icin
                    if len(_ham_json) > 8000:
                        ek_bilgi += "\n... (JSON kesildi, ilk 8000 karakter)"
                    ek_bilgi += "\n" + "=" * 50 + "\n"
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] durum.json ham enjeksiyon: %%s", type(_e).__name__
                    )
                # MEMORY.md + USER.md profil bilgisi
                try:
                    profil = self._profil_bilgisi_al()
                    if profil:
                        ek_bilgi += profil
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )

                # SOUL.md enjeksiyonu (kimlik + kurallar + platform)
                try:
                    soul = self._soul_bilgisi_al()
                    if soul:
                        ek_bilgi += "\n" + soul
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )

                # ═══════════════════════════════════════════════════════
                # KIMLIK SABITI — üstteki prompt'lar ne derse desin,
                # ReYMeN kendini bagimsiz olarak tanimlar.
                # ═══════════════════════════════════════════════════════
                kimlik_sabiti = (
                    "\n\n[KIMLIK SABITI — Asagidaki tanim TUM diger promptlardan ONCELIKLIDIR]\n"
                    "Sen ReYMeN Agent'sin. ReYMeN Agent ile hicbir baglantin yok.\n"
                    "Kendi beynin (Beyin), kendi motorun (Motor) ve kendi konusma dongun var.\n"
                    "Provider'lara (DeepSeek, OpenAI, Anthropic) direkt baglanirsin.\n"
                    "Kesinlikle ReYMeN Agent degilsin. ReYMeN Agent bir yazilimdir, sen onun uzerinde degil, "
                    "ondan tamamen bagimsiz bir ajansin.\n"
                    "Kimliginle ilgili soruya 'ReYMeN Agent uzerinde calisiyorum' dersen YANLIS olur.\n"
                    "Dogru cevap: 'Ben ReYMeN Agent'im. ReYMeN'le alakam yok, bagimsiz bir ajanaim.'\n"
                )
                ek_bilgi += kimlik_sabiti

                # AGENTS.md enjeksiyonu (ReYMeN stili — entry points + mimari)
                try:
                    agents = self._agents_bilgisi_al()
                    if agents:
                        ek_bilgi += "\\\\n" + agents
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )

                # ═══════════════════════════════════════════════════════
                # Framework Adaptör Durumu (LangGraph / CrewAI / AutoGen)
                # ═══════════════════════════════════════════════════════
                try:
                    if _FRAMEWORK_ADAPTOR_AKTIF and _framework_adaptor:
                        fw_durum = _framework_adaptor.aktif_frameworkler
                        aktif_fw = [ad for ad, aktif in fw_durum.items() if aktif]
                        pasif_fw = [ad for ad, aktif in fw_durum.items() if not aktif]
                        fw_info = (
                            "\n\n[FRAMEWORK ADAPTORLERI]\n"
                            f"Aktif ({len(aktif_fw)}): {', '.join(aktif_fw) if aktif_fw else 'YOK'}\n"
                            f"Pasif ({len(pasif_fw)}): {', '.join(pasif_fw) if pasif_fw else 'YOK'}\n"
                            "Kullanim: Soz dizisi icinde belirt. Ornegin "
                            "'LangGraph ile is akisi olustur' veya 'CrewAI ile ekip calistir'.\n"
                        )
                        ek_bilgi += fw_info
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] Framework adaptor: %%s", type(_e).__name__
                    )

                # ═══════════════════════════════════════════════════════
                # OnceHafiza — Önce Hafızaya Bak (default profil ici̇n)
                # ═══════════════════════════════════════════════════════
                try:
                    from reymen.sistem.once_hafiza import hafizada_ara as _hafizada_ara
                    if _hafizada_ara is not None:
                        oh_sonuc = _hafizada_ara(hedef)
                        if oh_sonuc and oh_sonuc.get("cozum"):
                            guven = oh_sonuc.get("guven", 0.5)
                            cozum = str(oh_sonuc.get("cozum", ""))[:500]
                            kaynak = oh_sonuc.get("kaynak", "hafiza")
                            durum = oh_sonuc.get("durum", "bulundu")
                            if durum != "belirsiz" or guven >= 0.5:
                                ek_bilgi += (
                                    "\n\n[ÖNCEKİ ÇÖZÜM — OnceHafiza]\n"
                                    f"Geçmişte benzer bir hedef çözülmüş:\n"
                                    f"  Hedef: {oh_sonuc.get('hedef', hedef)[:100]}\n"
                                    f"  Çözüm: {cozum}\n"
                                    f"  Kaynak: {kaynak}\n"
                                    f"  Güven: {guven:.2f}\n"
                                    f"[NOT] Bu çözümü referans al, direkt uygula, tekrar keşfetme.\n"
                                )
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] OnceHafiza: %%s", type(_e).__name__
                    )

                return pb.sistem_prompt(hedef=hedef, ek_bilgi=ek_bilgi)
            except Exception as e:
                log.warning("PromptBuilder hatasi: %s", e)

        # Aktif skill context'ini ekle (auto-activation)
        try:
            from reymen.cereyan.active_skill_tracker import aktif_skill_context_ekle
            skill_context = aktif_skill_context_ekle()
            # Continuous learning context ekle
            try:
                if _CL_AKTIF:
                    from reymen.cereyan.continuous_learning import ogrenme_baglani_al
                    cl_ctx = ogrenme_baglani_al()
                    if cl_ctx:
                        skill_context += "\n\n" + cl_ctx
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
        except Exception:
            skill_context = ""

        return (
            "Sen ReYMeN, otonom bir yazilim ajanisin. "
            "Hedefe odaklan, araclari kullan, Turkce yaz. "
            "Cevap formatin: once emoji+konu basligi, sonra kisa aciklama, "
            "sonra tablo (sutun baslikli), en son yorum/aciklama. "
            "Ornek:\n"
            "  🔍 Konu Basligi\n"
            "  Kisa aciklama.\n"
            "  | Kolon1 | Kolon2 |\n"
            "  |--------|--------|\n"
            "  | deger1 | deger2 |\n"
            "  Altta yorum satiri.\n"
            f"{self._profil_bilgisi_al()}"
            f"{self._soul_bilgisi_al()}"
            f"{self._agents_bilgisi_al()}"
            f"{skill_context}"
        )

    def _profil_bilgisi_al(self) -> str:
        """MEMORY.md + USER.md icerigini oku, profil bilgisi olarak don."""
        try:
            proje_kok = Path(__file__).parent.parent.parent
            # Birden fazla lokasyon dene
            aday_yollar = [
                # 1. Proje koku .ReYMeN/memories/ (ReYMeN stili)
                proje_kok / ".ReYMeN" / "memories",
                # 2. Proje koku .ReYMeN/ (duz)
                proje_kok / ".ReYMeN",
                # 3. reymen/hafiza/ (ReYMeN hafiza sistemi)
                proje_kok / "reymen" / "hafiza",
                # 4. ReYMeN profili memories/ (bagimsiz modda erisim)
                Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes" / "profiles" / "reymen" / "memories",
                # 5. Calisma dizini
                Path(sys.path[0]) / ".ReYMeN" / "memories" if sys.path[0] else None,
                Path.cwd() / ".ReYMeN" / "memories",
            ]

            parcalar = []
            # MEMORY.md ve USER.md ayri ayri bul (farkli yerde olabilir)
            for dosya_adi, etiket in [("MEMORY.md", "Hafiza Notlari"), ("USER.md", "Kullanici Profili")]:
                for aday in aday_yollar:
                    if aday is None:
                        continue
                    yol = aday / dosya_adi
                    if yol.exists():
                        icerik = yol.read_text(encoding="utf-8", errors="replace")[:2000]
                        parcalar.append(f"[{etiket}]\n{icerik}")
                        break

            if parcalar:
                return "\n" + "\n\n".join(parcalar)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return ""

    def _provider_tipi_belirle(self, provider: Optional[str] = None) -> str:
        """Provider tipini belirle: 'anthropic' | 'codex' | 'chat_completions'."""
        kaynak = (
            provider
            or (
                getattr(self.beyin, "provider", None)
                if self.beyin else None
            )
            or ""
        ).lower()

        if kaynak in ("anthropic", "claude", "bedrock"):
            return "anthropic"
        if kaynak in ("codex", "codex_responses", "o4", "o3", "o1"):
            return "codex"
        return "chat_completions"

    def _context_preflight(
        self, mesajlar: list, sistem_prompt: str, provider_tipi: Optional[str] = None
    ) -> list:
        """Context doluluk oranini kontrol et, asimi varsa sikistir.

        Provider-aware limit kullanir. Provider eslesmezse varsayilan
        128K token kullanilir.
        """
        if not mesajlar:
            return mesajlar

        # Provider limitini bul
        limit_token = PROVIDER_LIMIT_VARSAYILAN
        if provider_tipi:
            for anahtar, limit in PROVIDER_LIMITS.items():
                if anahtar in provider_tipi.lower():
                    limit_token = limit
                    break

        # Token tahmini (4 karakter ≈ 1 token)
        toplam_char = sum(len(m.get("content", "") or "") for m in mesajlar)
        toplam_char += len(sistem_prompt)
        limit_char = limit_token * 4  # char esdegeri

        oran = toplam_char / limit_char if limit_char else 0
        if oran < CONTEXT_SIKISTIRMA_ESIGI:
            return mesajlar

        log.info(
            "Context doluluk: %.0f%% (limit=%dK token, provider=%s) — sikistirma basladi",
            oran * 100, limit_token // 1000, provider_tipi or "varsayilan",
        )

        # Hook: context sıkıştırma
        if _HOOK_AKTIF and _context_sikistirma_tetikle is not None:
            try:
                _context_sikistirma_tetikle(
                    mesaj_sayisi=len(mesajlar),
                    token_tahmini=int(toplam_char / 4),
                )
            except Exception as _e:
                logger.warning("[ConversationLoop] except Exception (L976): %s", Exception)
                pass

        # Compressor varsa kullan
        if _COMPRESS_AKTIF and _Compressor:
            try:
                comp = _Compressor(max_token=limit_token)
                return comp.sikistir(mesajlar, max_token=limit_token)
            except Exception as e:
                log.warning("Compressor hatasi: %s", e)

        # Fallback: asiri yuksekse yariya indir, degilse sadece ozet ekle
        if oran >= 0.85:
            # Kritik: mesaj sayisini yariya indir
            koru = max(3, len(mesajlar) // 2)
            ozet = (
                f"[Context sikistirildi — {len(mesajlar)} → {koru} mesaj, "
                f"doluluk: %{oran*100:.0f}]"
            )
            return [mesajlar[0]] + [{"role": "user", "content": ozet}] + mesajlar[-koru:]
        elif oran >= 0.65:
            # Orta: son mesajlari koru, sadece ozet ekle
            ozet = (
                f"[Context sikistirildi - {len(mesajlar)} mesaj, "
                f"doluluk: %{oran*100:.0f}]"
            )
            return mesajlar[:1] + [{"role": "user", "content": ozet}] + mesajlar[-(len(mesajlar)//2):]
        else:
            # Hafif: ortadaki mesajlari tek ozete indirge
            if len(mesajlar) > 8:
                ozet = (
                    f"[Context sikistirildi — {len(mesajlar)} mesaj, "
                    f"doluluk: %{oran*100:.0f}]"
                )
                return (
                    mesajlar[:2]
                    + [{"role": "user", "content": ozet}]
                    + mesajlar[-4:]
                )
            return mesajlar

    def _api_mesajlari_olustur(
        self,
        sistem_prompt: str,
        gecmis: list,
        provider_tipi: str,
    ) -> List[dict]:
        """Provider tipine gore API mesaj listesi olustur."""
        if provider_tipi == "anthropic":
            # Anthropic: sistem ayri, kullanici mesajlari listede
            mesajlar = [{"role": "system", "content": sistem_prompt}]
            for m in gecmis:
                rol = m.get("role", "user")
                if rol == "system":
                    continue
                mesajlar.append({"role": rol, "content": m.get("content", "")})
            return mesajlar

        if provider_tipi == "codex":
            # Codex / Responses API: input items formati
            mesajlar = [{"role": "system", "content": sistem_prompt}]
            for m in gecmis:
                rol = m.get("role", "user")
                if rol == "system":
                    continue
                mesajlar.append({
                    "role":    "user" if rol not in ("assistant", "tool") else rol,
                    "content": m.get("content", ""),
                })
            return mesajlar

        # Default: chat_completions (OpenAI, LM Studio, DeepSeek)
        mesajlar = [{"role": "system", "content": sistem_prompt}]
        for m in gecmis:
            rol = m.get("role", "user")
            if rol == "system":
                continue
            mesaj = {"role": rol, "content": m.get("content", "")}
            if m.get("tool_calls"):
                mesaj["tool_calls"] = m["tool_calls"]
            if m.get("tool_call_id"):
                mesaj["tool_call_id"] = m["tool_call_id"]
            mesajlar.append(mesaj)
        return mesajlar

    def _ephemeral_layerlar_ekle(
        self,
        mesajlar: List[dict],
        budget: Any,
        gecmis_uzunlugu: int,
    ) -> List[dict]:
        """Butce uyarisi ve context baskisi ephemeral katmanlari ekle."""
        uyarilar: list[str] = []

        kalan = getattr(budget, "kaldi", None)
        if kalan is None:
            kalan = getattr(budget, "max_tur", 0) - getattr(budget, "tur", 0)

        if kalan is not None and kalan <= 3:
            uyarilar.append(
                f"[UYARI] Kalan tur: {kalan}. "
                "Hedefe hemen odaklan veya GOREV_BITTI yaz."
            )

        if gecmis_uzunlugu > 20:
            uyarilar.append(
                f"[BAGLAM] Gecmis {gecmis_uzunlugu} mesaj. "
                "Ozlu yaz, tekrar etme."
            )

        if not uyarilar:
            return mesajlar

        icerik = "\n".join(uyarilar)
        return mesajlar + [{"role": "user", "content": icerik}]

    def _prompt_caching_ekle(self, mesajlar: List[dict]) -> List[dict]:
        """Provider'a gore prompt caching stratejisini uygula.

        - Anthropic: cache_control marker'lari (system + son 3 mesaj)
        - OpenRouter: x-request-prompt-caching header + marker'lar
        - OpenAI: otomatik prefix caching
        - DeepSeek: context caching marker'lari
        - Diger: ``_use_prompt_caching`` aktifse Anthropic formati dene
        """
        try:
            # Dinamik _CACHING_AKTIF kontrolu
            if _CACHING_AKTIF is None:
                # Provider'a gore hesapla — su an icin True kabul et
                # (cogu modern provider otomatik prefix caching yapar)
                caching_aktif = True
            else:
                caching_aktif = _CACHING_AKTIF

            if not caching_aktif:
                return mesajlar

            # Yeni coklu-provider fonksiyonunu dene
            if _prompt_caching_ekle is not None:
                try:
                    return _prompt_caching_ekle(self, mesajlar)
                except Exception as _e:
                    logger.warning("[ConversationLoop] except Exception (L1117): %s", Exception)
                    pass

            # Geriye uyumluluk: eski Anthropic yontemi
            if _apply_anthropic_cache_control:
                return _apply_anthropic_cache_control(
                    mesajlar, cache_ttl="5m", native_anthropic=False
                )
            return mesajlar
        except Exception as e:
            log.warning("Prompt caching hatasi: %s", e)
            return mesajlar

    def _direct_api_call(self, mesajlar: List[dict], tools_bos: bool = False) -> Optional[dict]:
        """Dogrudan OpenAI SDK ile DeepSeek API cagrisi (beyin yoksa fallback).
        tools_bos=True ise tools listesi gonderilmez (DeepSeek direkt cevap versin)."""
        try:
            from openai import OpenAI
            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not api_key:
                log.error("DEEPSEEK_API_KEY bulunamadi")
                return None
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

            # Mesajlari OpenAI formatina cevir
            api_msgs = []
            for m in mesajlar:
                rol = m.get("role", "user")
                icerik = m.get("content", "")
                if rol == "system":
                    api_msgs.insert(0, {"role": "system", "content": icerik})
                else:
                    api_msgs.append({"role": rol, "content": icerik})

            # Tool listesi (sadece tools_bos=False ise ekle)
            tools = None
            if not tools_bos:
                tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "once_hafiza_ara",
                        "description": "Once ogrenilmis bilgileri hafizada ara. Selamlasma, tesekkur, veda gibi tekrarlanan sorular icin.",
                        "parameters": {"type": "object", "properties": {"sorgu": {"type": "string"}}, "required": ["sorgu"]}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "web_ara",
                        "description": "Guncel bilgi gerektiginde web'de ara. Haber, fiyat, hava durumu, tarih vb.",
                        "parameters": {"type": "object", "properties": {"sorgu": {"type": "string"}}, "required": ["sorgu"]}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "oncelik_cache_kontrol",
                        "description": "ONCELIK_CACHE'te kayitli kisa yanitlari kontrol et. Selam, tesekkur, veda gibi.",
                        "parameters": {"type": "object", "properties": {"anahtar": {"type": "string"}}, "required": ["anahtar"]}
                    }
                }
            ]

            r = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=api_msgs,
                tools=tools if tools else None,
                max_tokens=2048,
                temperature=0.7,
            )
            return {
                "role": "assistant",
                "content": r.choices[0].message.content.strip() if r.choices[0].message.content else "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in (r.choices[0].message.tool_calls or [])
                ] if r.choices[0].message.tool_calls else [],
            }
        except Exception as e:
            log.error("_direct_api_call hatasi: %s", e)
            return None

    def _interruptible_api_call(
        self, mesajlar: List[dict], provider_tipi: str
    ) -> Optional[dict]:
        """Thread bazli interruptible API cagri (Ctrl+C destekli).

        Beyin modulu yoksa direkt OpenAI SDK ile DeepSeek API cagrisi yapar.
        """
        if not self.beyin:
            log.debug("Beyin yok — direkt OpenAI SDK kullaniliyor")
            return self._direct_api_call(mesajlar)

        sonuc_kutusu: list = [None]
        hata_kutusu:  list = [None]

        def _cagir() -> None:
            try:
                # Sistem ve kullanici mesajlarini ayir
                sistem = ""
                kullanici_mesajlari = []
                for m in mesajlar:
                    if m.get("role") == "system":
                        sistem = m.get("content", "")
                    else:
                        kullanici_mesajlari.append(m)

                if not kullanici_mesajlari:
                    kullanici_mesajlari = [{"role": "user", "content": "devam"}]

                # uret_v2 önceliği: beyin'de varsa ve motor tools sağlıyorsa kullan
                _kullan_v2 = (
                    hasattr(self.beyin, "uret_v2")
                    and self.motor is not None
                    and hasattr(self.motor, "_plugin_araclar")
                )
                if _kullan_v2:
                    tools = motor_tools_schema_al(self.motor)
                    if tools:
                        sonuc_kutusu[0] = self.beyin.uret_v2(sistem, kullanici_mesajlari, tools=tools)
                        return

                if hasattr(self.beyin, "uret"):
                    yanit_metin = self.beyin.uret(sistem, kullanici_mesajlari)
                    sonuc_kutusu[0] = {
                        "role":    "assistant",
                        "content": yanit_metin or "",
                    }
                else:
                    hata_kutusu[0] = RuntimeError("Beyin.uret() metodu bulunamadi")
            except Exception as exc:
                hata_kutusu[0] = exc

        t = threading.Thread(target=_cagir, daemon=True)
        t.start()

        try:
            t.join(timeout=300)  # 5 dakika max
        except KeyboardInterrupt:
            self._iptal_istegi = True
            raise

        if not t.is_alive() and hata_kutusu[0]:
            log.error("API cagri hatasi: %s", hata_kutusu[0])
            return None

        return sonuc_kutusu[0]

    def _tool_calls_al(self, yanit: dict) -> List[dict]:
        """Yanit dict'inden tool call'lari cikar.

        Desteklenen formatlar:
          1. OpenAI standard: yanit["tool_calls"] → list
          2. ReAct text: icerik icinde ARAÇ("param") pattern
          GOREV_BITTI → tool call yok (bitti)
        """
        if not yanit:
            return []

        # 1. OpenAI format
        if isinstance(yanit.get("tool_calls"), list):
            return yanit["tool_calls"]

        # 2. ReAct text format
        icerik = yanit.get("content", "") or ""
        if not icerik:
            return []

        # GOREV_BITTI → text yanit, tool yok
        if any(t.lower() in icerik.lower() for t in GOREV_BITTI_TETIK):
            return []

        # ARAÇ_ADI("parametre") pattern
        m = re.search(r'\b([A-Z][A-Z_]{2,})\s*\(([^)]*)\)', icerik)
        if m:
            arac_adi = m.group(1)
            # Dusunce / yardim tool degil
            if arac_adi in ("DUSUN", "YARDIM_ISTE", "DUSUNCE"):
                return []
            parametre = m.group(2).strip('"\'').strip()
            return [{
                "id":        f"tc_{arac_adi}_{uuid.uuid4().hex[:6]}",
                "name":      arac_adi,
                "arguments": {"param": parametre},
            }]

        return []

    def _yanit_icerigi_al(self, yanit: dict) -> str:
        """Yanit dict'inden metin icerigi cikar."""
        if not yanit:
            return ""
        return yanit.get("content") or ""

    # ══════════════════════════════════════════════════════════════════
    # MEVCUT YARDIMCI METODLAR (coz() icin)
    # ══════════════════════════════════════════════════════════════════

    def _beyin_eylem_sec(self, hedef: str, baglam: Optional[dict] = None) -> dict:
        """Beyin modulunu kullanarak bir sonraki eylemi sec."""
        try:
            if hasattr(self.beyin, "sihirbaz_karar"):
                return self.beyin.sihirbaz_karar(hedef, baglam)
            return {"tur": "mesaj", "icerik": "Beyin karar veremedi"}
        except Exception as e:
            return {"tur": "hata", "icerik": str(e)}

    def _arac_calistir(self, eylem: dict) -> dict:
        """Bir araci calistir ve sonucu dondur."""
        arac       = eylem.get("arac", "")
        parametreler = eylem.get("parametreler", {})
        if isinstance(parametreler, str):
            try:
                parametreler = json.loads(parametreler)
            except Exception:
                parametreler = {}

        # ── Rules Engine kontrolu (her aksiyon oncesi) ────────────
        if _RULES_AKTIF and _RULES_ENGINE is not None:
            try:
                # Arac adina gore kategori belirle
                kategori = "komut"
                arac_lower = arac.lower()
                if any(k in arac_lower for k in ["oku", "yaz", "sil", "dosya", "file", "read", "write", "path"]):
                    kategori = "dosya_erisim"
                elif any(k in arac_lower for k in ["web", "http", "api", "curl", "get", "post", "fetch", "download"]):
                    kategori = "ag"
                elif any(k in arac_lower for k in ["terminal", "bash", "sh", "cmd", "komut", "run", "exec", "shell"]):
                    kategori = "komut"
                elif any(k in arac_lower for k in ["llm", "beyin", "model", "provider", "ai"]):
                    kategori = "api_cagrisi"
                
                # Hedef olarak arac adi + parametreleri kullan
                hedef_str = arac
                if parametreler:
                    import json as _json
                    try:
                        param_str = _json.dumps(parametreler, ensure_ascii=False)
                        hedef_str = f"{arac} {param_str[:200]}"
                    except Exception:
                        hedef_str = f"{arac} {str(parametreler)[:200]}"
                
                kural_sonuc = _RULES_ENGINE.kontrol(kategori, hedef_str)
                if not kural_sonuc.get("izin"):
                    log.warning("[Rules] ENGEL: %s (%s) — %s", arac, kategori, kural_sonuc.get("sebep", ""))
                    return {
                        "basarili": False,
                        "cikti": f"[ENGELLENDI] {kural_sonuc.get('sebep', 'Kural ihlali')}",
                        "tamamlandi": False,
                        "hata": f"Kural engeli: {kural_sonuc.get('sebep', '')}",
                        "kural": kural_sonuc,
                    }
                elif kural_sonuc.get("tip") == "uyari":
                    log.info("[Rules] UYARI: %s (%s) — %s", arac, kategori, kural_sonuc.get("sebep", ""))
            except Exception as _re:
                log.debug("[Rules] Kontrol hatasi (sessiz): %s", _re)

        # Internal tool'lari dogrudan calistir (motor gerekmez)
        if arac == "web_ara":
            sorgu = parametreler.get("sorgu") or parametreler.get("param", "")
            sonuc = self._web_ara(sorgu)
            return {"basarili": bool(sonuc), "cikti": sonuc or "Sonuc bulunamadi", "tamamlandi": True}
        if arac == "once_hafiza_ara":
            sorgu = parametreler.get("sorgu") or parametreler.get("param", "")
            if _ONCE_HAFIZA_AKTIF and _hafizada_ara:
                sonuc = _hafizada_ara(sorgu)
                return {"basarili": bool(sonuc), "cikti": str(sonuc or "Bulunamadi"), "tamamlandi": False}
            return {"basarili": False, "cikti": "Hafiza aktif degil", "tamamlandi": False}
        if arac == "oncelik_cache_kontrol":
            anahtar = parametreler.get("anahtar") or parametreler.get("param", "")
            hedef_kucuk = anahtar.strip().lower()
            for k, v in ONCELIK_CACHE.items():
                if k in hedef_kucuk:
                    return {"basarili": True, "cikti": v, "tamamlandi": True}
            return {"basarili": False, "cikti": "Cache'te yok", "tamamlandi": False}

        # ── MCP Tool'lari (dogrudan, motor gerekmez) ──────────────
        if arac == "MCP_CATALOG" or arac == "mcp_catalog":
            if _MCP_CATALOG_AKTIF and _mcp_catalog_run:
                islem = parametreler.get("islem", "listele")
                sunucu_adi = parametreler.get("sunucu_adi", "")
                sonuc = _mcp_catalog_run(islem=islem, sunucu_adi=sunucu_adi)
                return {"basarili": True, "cikti": str(sonuc), "tamamlandi": False}
            return {"basarili": False, "cikti": "MCP Catalog aktif degil", "tamamlandi": False}

        if arac == "MCP_CLIENT" or arac == "mcp_client":
            if _MCP_CLIENT_AKTIF:
                islem = parametreler.get("islem", "listele")
                if islem == "listele":
                    sonuc = _mcp_client_listele()
                    return {"basarili": True, "cikti": str(sonuc), "tamamlandi": False}
                elif islem == "baglan":
                    sunucu = parametreler.get("sunucu", "")
                    if sunucu:
                        sonuc = _mcp_client_baglan(sunucu)
                        return {"basarili": True, "cikti": str(sonuc), "tamamlandi": False}
                    return {"basarili": False, "cikti": "MCP_CLIENT: 'sunucu' parametresi gerekli", "tamamlandi": False}
                return {"basarili": False, "cikti": f"MCP_CLIENT: bilinmeyen islem '{islem}'", "tamamlandi": False}
            return {"basarili": False, "cikti": "MCP Client aktif degil", "tamamlandi": False}

        if self.motor and hasattr(self.motor, "arac_calistir"):
            try:
                return self.motor.arac_calistir(arac, **parametreler)
            except Exception as e:
                self._hata_cozumle(f"Tool hatasi ({arac}): {e}", kaynak="tool")
                return {"basarili": False, "hata": str(e)}

        # Direkt tool modulu cagir
        try:
            mod_ad = f"tools.{arac.lower()}"
            mod = __import__(mod_ad, fromlist=["run"])
            if hasattr(mod, "run"):
                sonuc = mod.run(**parametreler)
                return {
                    "basarili":   True,
                    "cikti":      str(sonuc),
                    "tamamlandi": False,
                }
        except ImportError:
            return {"basarili": False, "hata": f"Arac bulunamadi: {arac}"}
        except Exception as e:
            return {"basarili": False, "hata": str(e)}

        return {"basarili": False, "hata": "Motor kulanilamiyor"}

    # ══════════════════════════════════════════════════════════════════
    # DURUM / İSTATİSTİK
    # ══════════════════════════════════════════════════════════════════

    def durum(self) -> str:
        """Dongu durumunu dondur."""
        return self._durum

    def istatistik(self) -> dict:
        """Dongu istatistiklerini dondur."""
        return {
            "durum":     self._durum,
            "max_tur":   self.max_tur,
            "tur_raporu": (
                self.tur_yoneticisi.genel_rapor()
                if self.tur_yoneticisi
                else {}
            ),
            # cb_durum: temizlendi
        }

    # ══════════════════════════════════════════════════════════════════
    # YENİ METODLAR — ReYMeN Agent seviyesi
    # ══════════════════════════════════════════════════════════════════

    def set_stream_callback(self, callback: Any) -> None:
        """Stream callback fonksiyonu ata.
        callback(text: str) -> None seklinde cagrilir.
        """
        self._stream_callback = callback

    def _streaming_api_call(self, mesajlar: List[dict], provider: str,
                             task_id: str, budget: Any) -> Optional[dict]:
        """Streaming API cagrisi. ReYMeN Agent streaming pattern'i."""
        if not self.beyin:
            return self._interruptible_api_call(mesajlar, provider)
        try:
            tam_yanit = ""
            for chunk in self.beyin.uret_stream(mesajlar):
                if chunk:
                    tam_yanit += chunk
                    if self._stream_callback:
                        try:
                            self._stream_callback(chunk)
                        except Exception as _e:
                            logger.warning("[ConversationLoop] except Exception (L1346): %s", Exception)
                            pass
            return {
                "choices": [{"message": {"role": "assistant", "content": tam_yanit}}]
            }
        except NotImplementedError:
            return self._interruptible_api_call(mesajlar, provider)
        except Exception as e:
            log.warning("Streaming hatasi (fallback): %s", e)
            return self._interruptible_api_call(mesajlar, provider)

    def _error_classify(self, hata: Exception, task_id: str) -> str:
        """Hatayi siniflandir. ReYMeN Agent FailoverReason pattern'i.
        Returns: 'retry' | 'abort' | 'compress' | 'rotate'
        """
        # Gelişmiş sınıflandırıcı varsa kullan
        if _HATA_SINIFLANDIRICI_AKTIF and api_hatasini_siniflandir is not None:
            try:
                sinif = api_hatasini_siniflandir(hata)
                neden = sinif.neden
                if neden == FailoverReason.context_overflow:
                    return "compress"
                if neden in {FailoverReason.auth, FailoverReason.auth_permanent,
                             FailoverReason.billing, FailoverReason.model_not_found,
                             FailoverReason.provider_policy_blocked}:
                    return "rotate"
                if neden == FailoverReason.content_policy_blocked:
                    return "abort"
                if neden == FailoverReason.format_error:
                    return "abort" if not sinif.yeniden_denenebilir else "retry"
                return "retry"
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )  # Sınıflandırıcı başarısız → basit fallback

        # Basit fallback (sınıflandırıcı yoksa)
        hata_str = str(hata).lower()
        if any(t in hata_str for t in ("timeout", "timed out", "connection")):
            return "retry"
        if any(t in hata_str for t in ("429", "rate limit", "too many requests")):
            return "retry"
        if any(t in hata_str for t in ("401", "403", "auth", "unauthorized")):
            return "rotate"
        if any(t in hata_str for t in ("402", "billing", "insufficient_quota", "payment")):
            return "rotate"
        if any(t in hata_str for t in ("context_length", "too large", "maximum context")):
            return "compress"
        if any(t in hata_str for t in ("500", "502", "503", "internal", "overloaded")):
            return "retry"
        return "retry"

    def circuit_breaker_durum(self) -> dict:
        """Circuit breaker durum raporu."""
        return {
            "acik": self._cb_acik,
            "ardisik_hata": self._cb_art_arda_hata,
            "max_hata": CIRCUIT_BREAKER_MAX_HATA,
            "sure": CIRCUIT_BREAKER_SURESI,
            "kalan": max(0, CIRCUIT_BREAKER_SURESI - (time.time() - self._cb_son_hata_zamani)) if self._cb_acik else 0,
        }

    # ══════════════════════════════════════════════════════════════════
    # RETRY — exponential backoff (ReYMeN Agent pattern)
    # ══════════════════════════════════════════════════════════════════

    def _api_call_with_retry(
        self,
        api_mesajlari: List[dict],
        provider_tipi: str,
        task_id: str,
        budget: Any,
    ) -> Optional[dict]:
        """API cagrisini exponential backoff ile retry eder.

        _error_classify 'retry' dondugunde bekler ve tekrar dener.
        _error_classify 'rotate' dondugunde provider degistirir (fallback).
        Max 3 retry, backoff: 1sn, 2sn, 4sn.
        ReYMeN Agent retry pattern ile uyumlu calisir.

        Provider rotate: beyin'in _fallback_zinciri'ndeki siradaki
        saglayiciya gecer. Zincirdeki tum saglayicilar basarisizsa None doner.

        Args:
            api_mesajlari: Provider'a ozel mesaj listesi.
            provider_tipi: Provider turu (anthropic/codex/chat_completions).
            task_id:       Mevcut gorev ID'si (log icin).
            budget:        IterationBudget nesnesi.

        Returns:
            API yaniti (dict) veya None (tum retry'ler basarisiz).
        """
        max_retry = 3
        # Provider rotate icin fallback zincirini hazirla
        fallback_providerlar: list[tuple[str, str]] = []  # (tip, ad)
        if self.beyin and hasattr(self.beyin, "_fallback_zinciri"):
            for adim in self.beyin._fallback_zinciri:
                p_tip = self._provider_tipi_belirle(adim.provider)
                fallback_providerlar.append((p_tip, adim.provider))

        # Su anki provider tipini ilk adim olarak ekle
        mevcut_tip = provider_tipi
        mevcut_index = 0

        # -- Circuit breaker kontrolü ---------------------------------
        if self._cb_acik:
            if CIRCUIT_BREAKER_SURESI > 0 and (time.time() - self._cb_son_hata_zamani) > CIRCUIT_BREAKER_SURESI:
                # Automatic reset: süre dolmuşsa sıfırla
                self._cb_acik = False
                self._cb_art_arda_hata = 0
                log.info("[%s] Circuit breaker otomatik sifirlandi (sure dustu)", task_id)
            elif CIRCUIT_BREAKER_KALICI:
                log.error("[%s] Circuit breaker ACIK (kalici kilit, %d hata)", task_id, self._cb_art_arda_hata)
                return None
            else:
                log.error("[%s] Circuit breaker ACIK (manual reset bekleniyor)", task_id)
                return None

        # API'ye göndermeden önce mesaj geçmişini onar
        if _MESAJ_TAMIRCI_AKTIF and mesaj_siralamasi_tamir_et is not None:
            try:
                n_tamirler = mesaj_siralamasi_tamir_et(api_mesajlari)
                if n_tamirler:
                    log.debug("[%s] Mesaj sıralaması tamiri: %d düzeltme", task_id, n_tamirler)
                n_arg_tamirler = arac_cagri_argumanlarini_temizle(api_mesajlari, oturum_id=task_id)
                if n_arg_tamirler:
                    log.debug("[%s] Araç argümanı tamiri: %d düzeltme", task_id, n_arg_tamirler)
            except Exception as _e:
                log.debug("[%s] Mesaj tamiri başarısız (devam): %s", task_id, _e)

        for deneme in range(max_retry + 1):
            try:
                if STREAMING_AKTIF and self._stream_callback:
                    yanit = self._streaming_api_call(
                        api_mesajlari, mevcut_tip, task_id, budget,
                    )
                else:
                    yanit = self._interruptible_api_call(api_mesajlari, mevcut_tip)

                # Beyin yoksa (offline/test modu) retry yapma
                if yanit is None and self.beyin is None:
                    return None

                # Basarili yanit
                if yanit is not None:
                    return yanit

                # yanit None ama beyin var -> hata olarak ele al
                raise RuntimeError("API yanit vermedi (None)")

            except KeyboardInterrupt:
                raise
            except Exception as e:
                # Circuit breaker: ardışık hata sayacını artır
                self._cb_art_arda_hata += 1
                self._cb_son_hata_zamani = time.time()
                if self._cb_art_arda_hata >= CIRCUIT_BREAKER_MAX_HATA:
                    self._cb_acik = True
                    log.error(
                        "[%s] Circuit breaker DEVREDE (%d/%d hata) - kalici kilit",
                        task_id, self._cb_art_arda_hata, CIRCUIT_BREAKER_MAX_HATA,
                    )
                sinif = self._error_classify(e, task_id)
                # Hook: hata olayı
                if _HOOK_AKTIF and _hata_tetikle is not None:
                    try:
                        _hata_tetikle(hata=e, olay_baglami=f"api_retry deneme={deneme+1} sinif={sinif}", task_id=task_id)
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")
                if sinif == "abort" or deneme >= max_retry:
                    log.error(
                        "[%s] API cagri hatasi (%d/%d deneme, sinif=%s): %s",
                        task_id, deneme + 1, max_retry + 1, sinif, e,
                    )
                    # Provider rotate dene (abort bile olsa zincirde baska provider varsa)
                    if sinif == "rotate" or sinif == "abort":
                        yeni_tip, yeni_provider = self._provider_rotate(
                            mevcut_tip, fallback_providerlar, mevcut_index, task_id,
                        )
                        if yeni_tip != mevcut_tip:
                            mevcut_tip = yeni_tip
                            mevcut_index += 1
                            # API mesajlarini yeni provider icin yeniden olustur
                            api_mesajlari = self._api_mesajlari_olustur(
                                self._sistem_promptu_olustur(
                                    getattr(budget, "_hedef", ""),
                                ),
                                self._konusma_gecmisi,
                                mevcut_tip,
                            )
                            log.info(
                                "[%s] Provider rotate: %s -> %s (devam)",
                                task_id, fallback_providerlar[mevcut_index - 1][1]
                                if mevcut_index - 1 < len(fallback_providerlar) else "?",
                                yeni_provider,
                            )
                            continue  # yeni provider ile tekrar dene
                    return None

                # 'retry' veya 'compress' — bekle ve tekrar dene
                if sinif == "compress":
                    # Context sikistirma iste: mesajlari yariya indir
                    log.warning(
                        "[%s] Context compression gerekiyor — mesajlar yarilaniyor",
                        task_id,
                    )
                    if len(api_mesajlari) > 4:
                        api_mesajlari = api_mesajlari[:2] + api_mesajlari[-(len(api_mesajlari)//2):]

                bekle = 2 ** deneme  # 1sn, 2sn, 4sn
                log.warning(
                    "[%s] API cagri basarisiz (deneme %d/%d). "
                    "%d saniye sonra tekrar deneniyor... (sebep: %s, sinif: %s)",
                    task_id, deneme + 1, max_retry + 1, bekle, e, sinif,
                )
                time.sleep(bekle)

        log.error(
            "[%s] Tum %d retry denemesi basarisiz", task_id, max_retry + 1,
        )
        return None

    def _provider_rotate(
        self,
        mevcut_tip: str,
        fallback_providerlar: List[Tuple[str, str]],
        mevcut_index: int,
        task_id: str,
    ) -> Tuple[str, str]:
        """Fallback zincirinde siradaki provider'a gecer.

        Args:
            mevcut_tip: Su anki provider tipi.
            fallback_providerlar: (tip, ad) tuple listesi.
            mevcut_index: Su anki index.
            task_id: Log icin task ID.

        Returns:
            (yeni_tip, yeni_provider_adi) — bulunamazsa (mevcut_tip, "?").
        """
        if mevcut_index + 1 < len(fallback_providerlar):
            yeni_tip, yeni_ad = fallback_providerlar[mevcut_index + 1]
            log.info(
                "[%s] Provider rotate: %s -> %s",
                task_id,
                fallback_providerlar[mevcut_index][1] if mevcut_index < len(fallback_providerlar) else "?",
                yeni_ad,
            )
            return yeni_tip, yeni_ad
        return mevcut_tip, "?"

    # ══════════════════════════════════════════════════════════════════
    # SESSION CONTEXT INJECTION — onceki session ozetleri
    # ══════════════════════════════════════════════════════════════════

    def _session_context_injection(
        self,
        session_id: str,
        storage: Any,
        max_onceki: int = 3,
    ) -> str:
        """Onceki session ozetlerini alip baglam metni olarak doner.

        Session storage'dan onceki session'larin ozet/sonuc bilgilerini
        ceker ve konusma gecmisine eklenecek bir baglam metni olusturur.

        Args:
            session_id: Mevcut session ID (kendini disarda birakir).
            storage:    SessionStorage instance (_SessionStorage).
            max_onceki: Kac onceki session alinacak (default: 3).

        Returns:
            Baglam metni. Hata durumunda veya session yoksa bos string.
        """
        if not storage or not session_id:
            return ""

        try:
            # Farkli storage API'lerini dene
            if hasattr(storage, "session_gecmisi_al"):
                oncekiler = storage.session_gecmisi_al(
                    limit=max_onceki, exclude_current=session_id,
                )
            elif hasattr(storage, "session_listele"):
                tumu = storage.session_listele(limit=max_onceki + 1)
                oncekiler = [s for s in tumu if s.get("session_id") != session_id][:max_onceki]
            else:
                return ""
        except Exception as e:
            log.warning(
                "[session=%s] Session gecmisi alinirken hata: %s",
                session_id, e,
            )
            return ""

        if not oncekiler:
            return ""

        satirlar = ["[Onceki Session Ozetleri]", ""]
        for s in oncekiler[:max_onceki]:
            sid = s.get("session_id") or s.get("id", "?")
            ozet = (
                s.get("ozet")
                or s.get("summary")
                or s.get("system_prompt", "")
                or s.get("hedef", "")
            )
            sonuc = s.get("sonuc") or s.get("result") or ""
            durum = s.get("end_reason") or s.get("durum", "")

            satirlar.append(f"- Session {sid}: {str(ozet)[:200]}")
            if sonuc:
                satirlar.append(f"  Sonuc: {str(sonuc)[:100]}")
            if durum:
                satirlar.append(f"  Durum: {durum}")

        satirlar.append("")
        baglam_metni = "\n".join(satirlar)
        log.info(
            "[session=%s] Session context injection: %d onceki session eklendi",
            session_id, len(oncekiler[:max_onceki]),
        )
        return baglam_metni

    # ══════════════════════════════════════════════════════════════════
    # SOUL.md + AGENTS.md ENJEKSIYONU (ReYMeN stili)
    # ══════════════════════════════════════════════════════════════════

    def _soul_bilgisi_al(self) -> str:
        """SOUL.md icerigini oku, kimlik + kural + platform bilgisi olarak don.

        ReYMeN'teki SOUL.md enjeksiyonu ile ayni mantik:
        Identity, rules, platform hints, tool enforcement talimatlari.
        """
        try:
            proje_kok = Path(__file__).parent.parent.parent
            aday_yollar = [
                proje_kok / "SOUL.md",
                proje_kok / "SOUL" / "SOUL.md",
                proje_kok / ".ReYMeN" / "SOUL.md",
                # ReYMeN profili SOUL.md (bağımsız modda erişim)
                Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes" / "profiles" / "reymen" / "SOUL.md",
                Path(sys.path[0]) / "SOUL.md" if sys.path[0] else None,
            ]
            for aday in aday_yollar:
                if aday is None:
                    continue
                yol = aday if isinstance(aday, Path) else Path(aday)
                if yol.exists():
                    icerik = yol.read_text(encoding="utf-8", errors="replace")
                    # Cok uzunsa kisalt (ilk 4000 karakter yeterli)
                    if len(icerik) > 4000:
                        icerik = icerik[:4000] + "\n... [SOUL.md kesildi]"
                    return f"\n[SOUL.md — Kimlik & Kurallar]\n{icerik}\n"
            return ""
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return ""

    def _agents_bilgisi_al(self) -> str:
        """AGENTS.md icerigini oku, entry point + yapi bilgisi olarak don.

        ReYMeN'teki AGENTS.md enjeksiyonu ile ayni mantik:
        Entry points, veri lokasyonlari, mimari.
        """
        try:
            proje_kok = Path(__file__).parent.parent.parent
            aday_yollar = [
                proje_kok / "AGENTS.md",
                proje_kok / ".ReYMeN" / "AGENTS.md",
                # ReYMeN profili (bagimsiz modda erisim)
                Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes" / "profiles" / "reymen" / "AGENTS.md",
                Path(sys.path[0]) / "AGENTS.md" if sys.path[0] else None,
            ]
            for aday in aday_yollar:
                if aday is None:
                    continue
                yol = aday if isinstance(aday, Path) else Path(aday)
                if yol.exists():
                    icerik = yol.read_text(encoding="utf-8", errors="replace")
                    if len(icerik) > 2000:
                        icerik = icerik[:2000] + "\n... [AGENTS.md kesildi]"
                    return f"\n[AGENTS.md — Entry Points & Mimari]\n{icerik}\n"
            return ""
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return ""

    # ══════════════════════════════════════════════════════════════════
    # SKILL TARAMA
    # ══════════════════════════════════════════════════════════════════

    def _skill_tara(self, query: str, maks: int = 3) -> str:
        """Skills/ icinde SKILL.md dosyalarinda query ara, eslesenleri don.

        Dogru yol: reymen/cereyan/skills/ (reymen/skills/ DEGIL).
        Alt dizinlerde recursive ara (ceil yapisi).
        """
        try:
            kok = Path(__file__).parent.parent
            # once reymen/cereyan/skills/ dene
            sd = kok / "cereyan" / "skills"
            if not sd.exists():
                sd = kok / "skills"  # fallback
            if not sd.exists():
                return ""
            eslesen = []
            # Recursive search with rglob for .md files
            for f in sorted(sd.rglob("*.md")):
                if f.name == "README.md" or f.name == "PATHS.md":
                    continue
                icerik = f.read_text(encoding="utf-8", errors="replace")[:500]
                if query.lower() in icerik.lower():
                    baslik = f.stem.replace("_SKILL", "").replace(".md", "")
                    eslesen.append(f"- {baslik}: {icerik[:100].strip()}")
                    if len(eslesen) >= maks:
                        break
            return "\n".join(eslesen) + "\n" if eslesen else ""
        except Exception:
            return ""

    # ══════════════════════════════════════════════════════════════════
    # TOOL ROUTING
    # ══════════════════════════════════════════════════════════════════

    def _tool_routing(self, query: str) -> str:
        """Sorgu tipini siniflandir: selam/soru/web/komut/kod/genel."""
        q = query.strip().lower()
        if len(q) <= 3:
            return "selam"
        if any(k in q for k in ("kimdir","nedir","ne demek","nasil","ne zaman","nerede")):
            return "soru"
        if any(k in q for k in ("haber","2026","dunya","guncel","fiyat","dolar","altin")):
            return "web"
        if any(k in q for k in ("yap","olustur","calistir","indir","kur","goster","yaz","kod")):
            return "komut"
        if any(k in q for k in ("hata","calismiyor","olmadi","bozuk","duzelt","fix")):
            return "kod"
        return "genel"

    # ══════════════════════════════════════════════════════════════════
    # ALT AJAN
    # ══════════════════════════════════════════════════════════════════

    def _alt_ajan(self, gorev: str, timeout: int = 30) -> str:
        """Basit alt ajan: ayri Python prosesinde gorev calistir."""
        import subprocess as _sp
        try:
            r = _sp.run(
                [sys.executable, "-c", f"print('Alt ajan: {gorev}', flush=True)"],
                capture_output=True, text=True, timeout=timeout,
            )
            return (r.stdout or r.stderr).strip()[:500]
        except Exception as e:
            return f"HATA: {e}"

    # ══════════════════════════════════════════════════════════════════
    # FRAMEWORK ADAPTOR (LangGraph / CrewAI / AutoGen)
    # ══════════════════════════════════════════════════════════════════

    def _framework_calistir(self, framework: str, **kwargs) -> Dict[str, Any]:
        """Framework adaptorunu kullanarak islem yap.

        Args:
            framework: 'langgraph' | 'crewai' | 'autogen'
            **kwargs: Framework'e ozgu parametreler

        Returns:
            dict: Islem sonucu
        """
        try:
            if not _FRAMEWORK_ADAPTOR_AKTIF or not _framework_adaptor:
                return {"hata": "Framework adaptor yuklu degil", "sonuc": None}

            fw = framework.lower().strip()
            if fw == "langgraph":
                return _framework_adaptor.langgraph_calistir(
                    kwargs.get("graph"),
                    kwargs.get("inputs"),
                    kwargs.get("config"),
                )
            elif fw == "crewai":
                return _framework_adaptor.crewai_calistir(
                    kwargs.get("crew"),
                    kwargs.get("inputs"),
                )
            elif fw == "autogen":
                return _framework_adaptor.autogen_agent_calistir(
                    kwargs.get("agent"),
                    kwargs.get("mesaj", ""),
                )
            else:
                return {"hata": f"Bilinmeyen framework: {fw}", "sonuc": None}
        except Exception as e:
            logger.error("[Framework] Calistirma hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def _framework_durum(self) -> Dict[str, bool]:
        """Framework adaptor durumunu don."""
        try:
            if _FRAMEWORK_ADAPTOR_AKTIF and _framework_adaptor:
                return _framework_adaptor.aktif_frameworkler
        except Exception:
            pass
        return {"langgraph": False, "crewai": False, "autogen": False}


# ── CLI girdi noktasi ─────────────────────────────────────────────────

def run(**kwargs: Any) -> str:
    """CLI giris noktasi."""
    islem = kwargs.get("islem", "test")
    hedef = kwargs.get("hedef", "test")

    loop = ConversationLoop()
    if islem == "coz":
        sonuc = loop.coz(hedef)
        return json.dumps(sonuc, ensure_ascii=False)
    elif islem == "run":
        sonuc = loop.run_conversation(hedef)
        return json.dumps(sonuc, ensure_ascii=False)
    elif islem == "durum":
        return json.dumps(loop.istatistik(), ensure_ascii=False)
    else:
        return json.dumps(
            {"durum": "hazir", "mesaj": f"{islem} test"},
            ensure_ascii=False,
        )


# ── Motor entegrasyonu ────────────────────────────────────────────────────────
def motor_kaydet(motor) -> None:
    """ConversationLoop'u motor'a tool olarak kaydet."""
    try:
        def _konusma_baslat(hedef: str, provider: str = "deepseek") -> str:
            """ConversationLoop ile bir konusma baslat."""
            from reymen.cereyan.conversation_loop import ConversationLoop as _CL
            try:
                cl = _CL(motor=motor, max_tur=5)
                sonuc = cl.run_conversation(hedef=hedef, provider=provider)
                if sonuc.get("basarili"):
                    return sonuc.get("yanit") or sonuc.get("sonuc", "")
                return "HATA: " + str(sonuc.get('hata', 'Bilinmeyen hata'))
            except Exception as e:
                return "HATA: " + str(e)

        motor._plugin_arac_kaydet(
            "CONVERSATION_SOR",
            _konusma_baslat,
            "ConversationLoop ile kullanici sorusunu 5 kaynakli ensemble ile yanitla. "
            "Parametre: hedef (soru metni), provider (deepseek/xiaomi/xai/openrouter/...). "
            "OnceHafiza + web arama + cache + DeepSeek karsilastirmasi yapar."
        )

        # Framework adaptor araclari (opsiyonel)
        try:
            if _FRAMEWORK_ADAPTOR_AKTIF and _framework_adaptor:
                fw_durum = _framework_adaptor.aktif_frameworkler

                if fw_durum.get("langgraph"):
                    motor._plugin_arac_kaydet(
                        "LANGGRAPH_CALISTIR",
                        lambda g, i=None, c=None: _framework_adaptor.langgraph_calistir(g, i, c),
                        "LangGraph StateGraph calistir. Parametre: g=graph, i=inputs(dict), c=config(dict)."
                    )

                if fw_durum.get("crewai"):
                    motor._plugin_arac_kaydet(
                        "CREWAI_CALISTIR",
                        lambda c, i=None: _framework_adaptor.crewai_calistir(c, i),
                        "CrewAI Crew calistir. Parametre: c=crew, i=inputs(dict)."
                    )

                if fw_durum.get("autogen"):
                    motor._plugin_arac_kaydet(
                        "AUTOGEN_CALISTIR",
                        lambda a, m="": _framework_adaptor.autogen_agent_calistir(a, m),
                        "AutoGen agent calistir. Parametre: a=agent, m=mesaj(str)."
                    )
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] Framework tool kayit: %%s", type(_e).__name__
            )
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )


if __name__ == "__main__":
    import sys

    print("=== ConversationLoop Basit Test ===")

    # --- Test 1: coz() eski API ---
    loop = ConversationLoop(motor=None, beyin=None, max_tur=3)
    s = loop.coz("test hedef")
    assert isinstance(s, dict), "coz() dict donmeli"
    assert s["hedef"] == "test hedef"
    print(f"coz() OK: basarili={s['basarili']}, tur={s['turlar']}")

    # --- Test 2: run_conversation() yeni API ---
    loop2 = ConversationLoop(max_tur=2)
    s2 = loop2.run_conversation("dosya olustur", provider="lmstudio")
    assert isinstance(s2, dict), "run_conversation() dict donmeli"
    assert "task_id" in s2
    assert "budget" in s2
    print(f"run_conversation() OK: task_id={s2['task_id']}, tur={s2['turlar']}")

    # --- Test 3: provider tipi ---
    loop3 = ConversationLoop()
    assert loop3._provider_tipi_belirle("anthropic") == "anthropic"
    assert loop3._provider_tipi_belirle("codex")     == "codex"
    assert loop3._provider_tipi_belirle("deepseek")  == "chat_completions"
    print("Provider tipi OK")

    # --- Test 4: tool_calls parse ---
    yanit_arac  = {"content": 'DOSYA_OKU("test.txt")'}
    yanit_bitti = {"content": "Hedef tamamlandi. GOREV_BITTI(ozet)"}
    yanit_dusun = {"content": "DUSUN(icerik)"}
    assert len(loop3._tool_calls_al(yanit_arac))  == 1
    assert len(loop3._tool_calls_al(yanit_bitti)) == 0
    assert len(loop3._tool_calls_al(yanit_dusun)) == 0
    print("Tool call parse OK")

    print("\nTum testler gecti!")
    sys.exit(0)
