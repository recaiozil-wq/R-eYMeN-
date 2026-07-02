# -*- coding: utf-8 -*-
"""main.py — ReYMeN Otonom Ajan. Ana ReAct dongusu.

Entegre moduller:
- iteration_budget: adaptif tur yonetimi, circuit breaker
- prompt_builder: SOUL.md + MEMORY + skills ile prompt insasi
- trajectory: adim gecmisi kaydi
- conversation_compression: konusma sikistirma
- prompt_caching: LLM onbellegi
- credential_pool: API anahtari yonetimi
"""

import io
import json as _json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor as _TPool, as_completed as _as_completed
from pathlib import Path
from dotenv import load_dotenv

# NOT: UTF-8 wrapping yalnizca __main__ olarak calistirildikta yapilmali.
# Modul import edildiginde (reymen/__init__.py uzerinden) calisirsa
# runpy.run_path + __init__ circular import nedeniyle wrapper iki kez olusur,
# birinci wrapper GC'lenince ortak buffer kapanir → ValueError: I/O on closed file.

DOT_ENV = Path(__file__).parent / ".env"
if DOT_ENV.exists():
    load_dotenv(DOT_ENV, override=True)

# ── ERKEN LOG SUSTURMA: tüm import'lardan ÖNCE ──────────────────────────────
# Hem standart logging hem loguru, modül importu sırasında plugin logları üretir.
# Bu blok, import öncesi her ikisini de susturur.
import logging as _startup_log
_startup_log.disable(_startup_log.CRITICAL)
_LOGURU_KALDIRILDI = False
try:
    from loguru import logger as _loguru_inst
    _loguru_inst.remove()          # tüm loguru handler'larını kaldır
    _LOGURU_KALDIRILDI = True
except Exception as _e:
    logger.warning("[Main] except Exception (L41): %s", Exception)
    pass
# ─────────────────────────────────────────────────────────────────────────────

# --- CORE ---
# DOGRUDAN paket ici yollardan import et (root-level shim'ler
# cirkuler import'a sebep olur)
from src.reymen.cereyan.beyin import Beyin as RuntimeProvider
from src.reymen.hafiza.context_manager import AdvancedContextCompressor as ContextCompressor
from src.reymen.cereyan.prompt_assembly import PromptAssemblyEngine
from src.reymen.hafiza.bounded_memory import BoundedMemory
from src.reymen.hafiza.session_db import AdvancedSessionStorage
from src.reymen.cereyan.closed_learning_loop import ClosedLearningLoop
from src.reymen.cereyan.motor import Motor
from src.reymen.cereyan.planlayici import Planlayici
from src.reymen.cereyan.robust_execution import RobustExecutionEngine
from src.reymen.cereyan.insan_arayuzu import InsanArayuzu
from src.reymen.hafiza.vektorel_hafiza import (
    vektorel_hafiza_sistemini_kur,
    tecrube_kaydet,
    anlamsal_hafiza_ara,
)
from src.reymen.sistem.once_hafiza import OnceHafiza, _get_once_hafiza
import logging

logger = logging.getLogger(__name__)

# --- OPSIYONEL MODULLER ---
try:
    from reymen.cereyan.iteration_budget import IterationBudget
except ImportError:
    IterationBudget = None

try:
    import ReYMeN_cli
    _REYMEN_CLI = ReYMeN_cli
except Exception:
    _REYMEN_CLI = None

try:
    import gateway
    _GATEWAY = gateway
except Exception:
    _GATEWAY = None

try:
    import plugins
    _PLUGINS = plugins
except Exception:
    _PLUGINS = None

try:
    import cron
    _CRON = cron
except Exception:
    _CRON = None

try:
    from reymen.arac.prompt_builder import PromptBuilder
except ImportError:
    PromptBuilder = None

try:
    from reymen.windows.trajectory import Trajectory
except ImportError:
    Trajectory = None

try:
    from reymen.hafiza.conversation_compression import ConversationCompressor
except ImportError:
    ConversationCompressor = None

try:
    from reymen.arac.prompt_caching import cache_ile_uret
except ImportError:
    cache_ile_uret = None

try:
    from reymen.hafiza.semantic_cache import global_cache_al as _semantic_cache_al
    _sem_cache = _semantic_cache_al()
except Exception:
    _sem_cache = None

try:
    from reymen.cereyan.adaptif_ogrenme import AdaptifOgrenme, adaptif_ogrenme_sistemi_kur
except ImportError:
    AdaptifOgrenme = None
    adaptif_ogrenme_sistemi_kur = None

try:
    from reymen.guvenlik.guardrails import HallucinationFiltresi, HITLSikistirici, motor_hitl_yamas_uygula
    _GUARDRAILS_VAR = True
except ImportError:
    HallucinationFiltresi = None
    HITLSikistirici = None
    motor_hitl_yamas_uygula = None
    _GUARDRAILS_VAR = False

try:
    from reymen.sistem.credential_pool import CredentialPool
    _cred_pool = CredentialPool()
except ImportError:
    _cred_pool = None

# ─── FAZ 6 Modulleri ─────────────────────────────────────────────────────────
try:
    from reymen.cereyan.beceri_kutuphanesi import BeceriKutuphanesi as _BeceriKutuphanesi
except ImportError:
    _BeceriKutuphanesi = None

try:
    from reymen.cereyan.ajan_suru import AjanSurusu as _AjanSurusu
except ImportError:
    _AjanSurusu = None

try:
    from reymen.cereyan.oz_yansima import OzYansima as _OzYansima
except ImportError:
    _OzYansima = None

# ─── LLM Self-Improvement Modulleri ──────────────────────────────────────────
try:
    from reymen.cereyan.reflexion_motoru import ReflexionMotoru as _ReflexionMotoru
except ImportError:
    _ReflexionMotoru = None

try:
    from reymen.guvenlik.anayasa_denetci import AnayasaDenetci as _AnayasaDenetci
except ImportError:
    _AnayasaDenetci = None

try:
    from reymen.cereyan.oz_tutarlilik import OzTutarlilikDenetci as _OzTutarlilikDenetci
except ImportError:
    _OzTutarlilikDenetci = None

try:
    from reymen.cereyan.meta_prompt_optimizer import MetaPromptOptimizer as _MetaPromptOptimizer
except ImportError:
    _MetaPromptOptimizer = None

# ─── ReYMeN KOPYASI MODULLER ────────────────────────────────────────────────
try:
    import tui_gateway
    _TUI_GATEWAY = tui_gateway
except Exception:
    _TUI_GATEWAY = None

try:
    import acp_adapter
    _ACP_ADAPTER = acp_adapter
except Exception:
    _ACP_ADAPTER = None

try:
    import llm_provider
    _LLM_PROVIDER = llm_provider
except Exception:
    _LLM_PROVIDER = None

try:
    import notion_writer
    _NOTION_WRITER = notion_writer
except Exception:
    _NOTION_WRITER = None

try:
    from reymen.ag import telegram_bot
    _TELEGRAM_BOT = telegram_bot
except Exception:
    _TELEGRAM_BOT = None

try:
    from dashboard.app import app as _dashboard_app
    _DASHBOARD = _dashboard_app
except Exception:
    _DASHBOARD = None

IC_GOZLEM_ARALIK = 5


def _reymen_env_yolu() -> Path:
    """Platform-bagimsiz .env dosyasi yolu. Windows ve Linux/macOS destegi."""
    import platform
    ev = Path.home()
    if platform.system() == "Windows":
        # Windows: %APPDATA%\..\Local\ReYMeN\.env
        return ev / "AppData" / "Local" / "reymen" / ".env"
    # Linux / macOS: ~/.config/reymen/.env
    return ev / ".config" / "reymen" / ".env"


def _env_anahtar(anahtar, varsayilan=""):
    """API anahtari al — once credential_pool, sonra .env."""
    if _cred_pool:
        deger = _cred_pool.al(anahtar)
        if deger:
            os.environ[anahtar] = deger
            return deger

    deger = os.environ.get(anahtar, "").strip()
    if not deger or deger.startswith("***") or deger == "...":
        ReYMeN_env = _reymen_env_yolu()
        if ReYMeN_env.exists():
            with open(ReYMeN_env, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{anahtar}="):
                        val = line.split("=", 1)[1].strip()
                        if val and not val.startswith("***"):
                            os.environ[anahtar] = val
                            return val
        return varsayilan
    return deger


CONFIG = {
    "default_model":    _env_anahtar("ReYMeN_DEFAULT_MODEL", "deepseek-v4-flash"),
    "default_provider": _env_anahtar("ReYMeN_DEFAULT_PROVIDER", "deepseek"),
    "secure_binding": True,
    "providers": {
        "lmstudio":     {"base_url": _env_anahtar("LMSTUDIO_BASE_URL", "http://localhost:1234"), "api_key": "not-needed"},
        "deepseek":     {"base_url": "https://api.deepseek.com",  "api_key": _env_anahtar("DEEPSEEK_API_KEY")},
        "anthropic":    {"base_url": "https://api.anthropic.com", "api_key": _env_anahtar("ANTHROPIC_API_KEY")},
        "openai":       {"base_url": "https://api.openai.com",    "api_key": _env_anahtar("OPENAI_API_KEY")},
        "groq":         {"base_url": "https://api.groq.com/openai/v1", "api_key": _env_anahtar("GROQ_API_KEY")},
        "moonshot":     {"base_url": _env_anahtar("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"), "api_key": _env_anahtar("MOONSHOT_API_KEY")},
        "azure":        {"base_url": _env_anahtar("AZURE_OPENAI_ENDPOINT", ""),   "api_key": _env_anahtar("AZURE_OPENAI_API_KEY")},
        "bedrock":      {"base_url": "", "api_key": _env_anahtar("AWS_ACCESS_KEY_ID")},
        "gemini_cloud": {"base_url": "", "api_key": _env_anahtar("GOOGLE_CLOUD_PROJECT")},
    },
    "fallback_model": {
        "provider": "deepseek", "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key": _env_anahtar("DEEPSEEK_API_KEY"),
    } if _env_anahtar("DEEPSEEK_API_KEY") else None,
    "auxiliary": {
        "vision":      {"model": _env_anahtar("LMSTUDIO_MODEL", "llava-v1.6-mistral-7b"),
                        "provider": "lmstudio",
                        "base_url": _env_anahtar("LMSTUDIO_BASE_URL", "http://localhost:1234"),
                        "api_key": "not-needed"},
        "compression": {"model": _env_anahtar("LMSTUDIO_MODEL", "cognitivecomputations.dolphin3.0-llama3.1-8b"),
                        "provider": "lmstudio",
                        "base_url": _env_anahtar("LMSTUDIO_BASE_URL", "http://localhost:1234"),
                        "api_key": "not-needed"},
    },
    "telegram": {
        "token":   _env_anahtar("TELEGRAM_BOT_TOKEN"),
        "chat_id": _env_anahtar("TELEGRAM_CHAT_ID", "6328823909"),
    },
    "skills_dir": ".ReYMeN/skills",
}


class AIAgentOrchestrator:
    def __init__(self, config=CONFIG, backend_mode="local", max_tur=15, onay_iste=False):
        self.config = config
        self.backend_mode = backend_mode
        self.max_tur = max_tur
        self.onay_iste = onay_iste

        self._cekirdekleri_baslat()
        self._opsiyonel_modulleri_yukle()
        self._guvenligi_baslat()
        self._eklentileri_yukle()

        if onay_iste:
            self.motor.onay_fonksiyonu = self._onay_iste

    # ── Baslatma yardimcilari ─────────────────────────────────────────

    def _cekirdekleri_baslat(self):
        """Zorunlu cekirdek modulleri baslat."""
        self.provider = RuntimeProvider(self.config)
        self.compressor = ContextCompressor()
        self.bounded_memory = BoundedMemory()
        self.learning = ClosedLearningLoop()
        self.prompt_engine = PromptAssemblyEngine(
            bounded_memory=self.bounded_memory,
            learning_loop=self.learning,
        )
        self.session = AdvancedSessionStorage()
        self.hafiza = vektorel_hafiza_sistemini_kur()
        self.motor = Motor(
            backend_mode=self.backend_mode,
            hafiza_collection=self.hafiza,
            config=self.config,
        )
        self.planlayici = Planlayici(self.provider)
        self.insan = InsanArayuzu()
        # FAZ 6: motor'a provider referansini ver (ARAC_URET icin)
        self.motor._provider_ref = self.provider
        # FC modu: None=bilinmiyor, True=native FC, False=metin-parse fallback
        self._fc_mod: Optional[bool] = None

    def _opsiyonel_modulleri_yukle(self):
        """Opsiyonel modulleri try/except ile yukle."""
        self.budget = IterationBudget(max_tur=self.max_tur) if IterationBudget else None
        self.prompt_builder = PromptBuilder() if PromptBuilder else None
        self.trajectory = None
        self.adaptif_ogrenme = adaptif_ogrenme_sistemi_kur() if adaptif_ogrenme_sistemi_kur else None
        self.halucination_filtresi = HallucinationFiltresi() if HallucinationFiltresi else None
        self.hitl_sikistirici = None  # ihtiyaca gore _eklentileri_yukle'de devreye girer
        self.conv_compressor = ConversationCompressor(
            provider=self.provider, pencere_boyutu=6, esik_token=3500
        ) if ConversationCompressor else None

        # FAZ 6: Beceri kutuphanesi + Oz yansima + Swarm
        self.beceri_kb = _BeceriKutuphanesi() if _BeceriKutuphanesi else None
        self.oz_yansima = _OzYansima(session=self.session, provider=self.provider) if _OzYansima else None
        self.ajan_suru = _AjanSurusu(provider=self.provider) if _AjanSurusu else None

        # LLM Self-Improvement modulleri
        self.reflexion = _ReflexionMotoru(provider=self.provider, hafiza=self.hafiza) if _ReflexionMotoru else None
        self.anayasa = _AnayasaDenetci(provider=self.provider) if _AnayasaDenetci else None
        self.oz_tutarlilik_denetci = _OzTutarlilikDenetci(provider=self.provider) if _OzTutarlilikDenetci else None
        self.meta_prompt = _MetaPromptOptimizer(provider=self.provider, session_db=self.session) if _MetaPromptOptimizer else None

        try:
            from sistem_talimati import sistem_talimatini_insa_et
            self._sistem_talimati_fn = sistem_talimatini_insa_et
        except ImportError:
            self._sistem_talimati_fn = None

        try:
            from reymen.hafiza.context_references import ReferansYoneticisi
            self.referanslar = ReferansYoneticisi()
        except ImportError:
            self.referanslar = None

        try:
            from reymen.sistem.credential_persistence import CredentialPersistence
            for k, v in CredentialPersistence().dosya_oku().items():
                if v and not os.environ.get(k):
                    os.environ[k] = v
        except ImportError as _e:
            logger.warning("[Main] Modul yuklenemedi (L373): %s", ImportError)
            pass

        # ── Windows Otomasyon Entegrasyonu (event bus) ────────────────────
        self.windows_entegrasyon = None
        if self.motor:
            try:
                from reymen.windows.windows_entegrasyon import windows_entegrasyonu_baslat
                bus = windows_entegrasyonu_baslat()
                if bus:
                    self.windows_entegrasyon = bus
            except Exception as _win_e:
                _modul_uyar("Windows Entegrasyon", _win_e)

    def _guvenligi_baslat(self):
        """Guvenlik motorlarini yukle."""
        try:
            from reymen.guvenlik.tirith_security import TirithSecurity
            self.guvenlik = TirithSecurity()
        except ImportError:
            self.guvenlik = None

        try:
            from reymen.guvenlik.security_engine import AdvancedMemorySecurityEngine
            self.mem_guvenlik = AdvancedMemorySecurityEngine()
        except ImportError:
            self.mem_guvenlik = None

        try:
            from reymen.ag.salted_gateway import SaltedGatewaySecurityGate
            self.salted_gate = SaltedGatewaySecurityGate()
        except ImportError:
            self.salted_gate = None

    def _eklentileri_yukle(self):
        """Motor hook + plugin sistemi + hafiza plugin + persistence loglamasi."""
        try:
            from reymen.sistem.persistence import guvenlik_kalicilik
            _gk = guvenlik_kalicilik()
            self.motor.hook_kaydet(
                "TOOL_ERROR",
                lambda arac="", params=None, sonuc="": _gk.olay_kaydet(
                    "tool_error", f"{arac}: {sonuc[:100]}", seviye="WARN", kaynak="motor"
                ),
            )
        except Exception as _e:
            logger.warning("[Main] except Exception (L418): %s", Exception)
            pass

        # ── Araç plugin'leri ───────────────────────────────────────────
        self._plugin_yukleyici = None
        try:
            from reymen.sistem.plugin_loader import PluginYukleyici
            yukleyici = PluginYukleyici()
            yuklu = yukleyici.hepsini_yukle()
            if yuklu:
                yukleyici.motora_kaydet(self.motor)
                print(f"[Plugin] {len(yuklu)} arac eklentisi yuklendi: {yuklu}")
            self._plugin_yukleyici = yukleyici
        except Exception as _e:
            logger.warning("[Main] except Exception (L431): %s", Exception)
            pass

        # ── Hafıza plugin sistemi (ReYMeN Memory Provider Plugin uyumlu) ──
        self.aktif_hafiza_plugin = None
        try:
            if self._plugin_yukleyici:
                import json as _json
                import uuid
                oturum_id = str(uuid.uuid4())[:8]
                reymen_dizin = Path(__file__).parent / ".ReYMeN"
                aktif = self._plugin_yukleyici.hafiza_pluginlerini_yukle(
                    oturum_id=oturum_id,
                    tercih=os.environ.get("REYMEN_HAFIZA_PLUGIN", None),
                    reymen_dizin=str(reymen_dizin),
                    ozet_saglayici=self.provider,
                )
                if aktif:
                    self.aktif_hafiza_plugin = aktif
                    print(f"[HafızaPlugin] Aktif saglayici: {aktif.ad}")
                    # Aktif saglayicinin araclarini motor._plugin_arac_kaydet ile kaydet
                    for sema in aktif.arac_sema_al():
                        arac_adi = sema.get("ad", "")
                        if not arac_adi:
                            continue

                        def _olustur_handler(p, a):
                            def _handler(params):
                                try:
                                    arg_str = params[0] if params else "{}"
                                    try:
                                        args = _json.loads(arg_str) if arg_str.strip().startswith("{") else {"sorgu": arg_str}
                                    except Exception:
                                        args = {"sorgu": arg_str}
                                    return p.arac_cagri_isle(a, args)
                                except Exception as e:
                                    return f"Hafiza arac hatasi [{a}]: {e}"
                            return _handler

                        self.motor._plugin_arac_kaydet(
                            arac_adi,
                            _olustur_handler(aktif, arac_adi),
                            sema.get("aciklama", ""),
                        )
        except Exception as e:
            print(f"[HafızaPlugin] Yuklenemedi: {e}")

        # HITL sıkılaştırma + motor yaması
        if _GUARDRAILS_VAR and HITLSikistirici and motor_hitl_yamas_uygula:
            try:
                motor_hitl_yamas_uygula(self.motor)
                self.hitl_sikistirici = HITLSikistirici(self.motor)
                self.hitl_sikistirici.sikilas()
            except Exception as _e:
                logger.warning("[Main] except Exception (L484): %s", Exception)
                pass

    # ── HITL onay ─────────────────────────────────────────────────────

    def _onay_iste(self, arac, ozet):
        return self.insan.onay_iste("ReYMeN Onay", f"{arac} calistirilsin mi?\n{ozet}")

    # ── Ana ReAct dongusu ─────────────────────────────────────────────

    def run_conversation(self, hedef):
        print("[TEST] burası çalışıyor")
        import time as _time
        _t_baslat = _time.time()

        hedef = self._giris_temizle(hedef)

        # ── ÖNCE HAFIZAYA BAK ────────────────────────────────────────────
        # OnceHafiza: daha önce çözülmüş mü?
        _oh = _get_once_hafiza()
        _hafiza_kayit = _oh.hafizada_ara(hedef)
        if _hafiza_kayit:
            cozum = _hafiza_kayit["cozum"]
            kaynak = _hafiza_kayit.get("kaynak", "hafiza")
            print(f"[OnceHafiza] ✅ Hafizada bulundu: {hedef[:50]} (kaynak: {kaynak})")
            return {
                "output": cozum,
                "exit_code": 0,
                "once_hafiza": True,
                "kaynak": kaynak,
            }
        # ──────────────────────────────────────────────────────────────────

        # Iteration budget — once karmasiklik belirle, sonra goruntu karar ver
        if self.budget:
            analiz = self.budget.analiz_et(hedef)
            _karmasiklik_raw = analiz.get("karmasiklik", 1) if isinstance(analiz, dict) else 1
            # Karmaşıklığa göre ölçeklendir: k1=15, k2=25, k3=40, k4=60, k5=90
            _tur_tablosu = {1: 15, 2: 25, 3: 40, 4: 60, 5: 90}
            _base = getattr(self.budget, "max_total", None) or self.max_tur
            max_tur = max(_base, _tur_tablosu.get(_karmasiklik_raw, _base))
        else:
            analiz = {"karmasiklik": 1, "ipuclari": []}
            _karmasiklik_raw = 1
            max_tur = self.max_tur

        _karmasiklik = analiz.get("karmasiklik", 1) if isinstance(analiz, dict) else 1
        _verbose = _karmasiklik >= 2   # 1=sohbet(sessiz), 2+=teknik(ayrintili)

        # ReYMeN-style ayirici — her zaman goster
        _B, _R, _D = "\033[1m", "\033[0m", "\033[2m"
        _G = "\033[92m"
        _SEP = _D + "─" * 68 + _R
        sys.stdout.write(f"\n{_SEP}\n")

        if _verbose:
            sys.stdout.write(f"{_B}▶ {hedef}{_R}  {_D}[k:{_karmasiklik}/5]{_R}\n")

        # Basit sohbet: ic mesajlari gizle — sadece yanit goster
        if _verbose:
            print(f"[Budget] Karmasiklik: {_karmasiklik}/5, Max tur: {max_tur}")
        else:
            pass
        if Trajectory:
            self.trajectory = Trajectory(hedef)

        # RAG: gecmis tecrube ara
        gecmis = anlamsal_hafiza_ara(self.hafiza, hedef)
        if gecmis and "bulunamadi" not in gecmis:
            print("[Hafiza] Ilgili gecmis tecrube bulundu.")
            self.bounded_memory.kaydet(f"[Gecmis]: {gecmis}", "MEMORY.md")

        # Hafıza Plugin: onceden_getir — API çağrısı öncesi bağlam zenginleştirme
        _hafiza_plugin_baglam = ""
        if self.aktif_hafiza_plugin:
            try:
                _hafiza_plugin_baglam = self.aktif_hafiza_plugin.onceden_getir(hedef)
                if _hafiza_plugin_baglam:
                    print(f"[HafızaPlugin/{self.aktif_hafiza_plugin.ad}] Önceki bağlam yüklendi.")
            except Exception as _e:
                logger.warning("[Main] except Exception (L565): %s", Exception)
                pass

        # FAZ 6 — Beceri kutuphanesi: benzer gecmis beceri varsa rehber enjekte et
        if self.beceri_kb:
            kb_sablon = self.beceri_kb.benzer_bul(hedef)
            if kb_sablon:
                kb_rehber = self.beceri_kb.rehber_metni(kb_sablon)
                print(f"[BeceriKB] Rehber bulundu: {kb_sablon.get('ad', '?')}")
            else:
                kb_rehber = ""
        else:
            kb_rehber = ""

        # FAZ 6 — Swarm: karmasiklik >= 4 ise coklu ajan devreye gir
        suru_kullan = analiz.get("karmasiklik", 1) >= 4 and self.ajan_suru
        if suru_kullan:
            print("[AjanSuru] Karmasiklik >= 4 — swarm aktive ediliyor...")
            try:
                suru_sonuc = self.ajan_suru.calistir(hedef)
                print(f"[AjanSuru]\n{suru_sonuc[:600]}")
                self.bounded_memory.kaydet(f"[Suru Analizi]: {suru_sonuc[:500]}", "MEMORY.md")
            except Exception as _suru_hata:
                print(f"[AjanSuru] Hata: {_suru_hata}")

        # Planlama — karmasiklik >= 3 ise Tree-of-Thought
        self.planlayici.sifirla()
        tot_kullan = analiz.get("karmasiklik", 1) >= 3
        plan = self.planlayici.plani_uret(hedef, tot=tot_kullan)
        if len(plan) > 1:
            print(f"[Plan] {len(plan)} adim:")
            for i, adim in enumerate(plan, 1):
                risk = " [RISK]" if self.planlayici.riskli_mi(adim) else ""
                print(f"  {i}. {adim}{risk}")
            plan_metni = "\n".join(f"{i}. {a}" for i, a in enumerate(plan, 1))
            hedef_ile_plan = f"{hedef}\n\nPLAN:\n{plan_metni}"
        else:
            hedef_ile_plan = hedef

        # Meta-prompt: gecmis analiz kayitlarından sistem eki yukle
        _meta_ek = ""
        if self.meta_prompt:
            try:
                _meta_ek = self.meta_prompt.mevcut_ekleri_yukle()
            except Exception as _e:
                logger.warning("[Main] except Exception (L609): %s", Exception)
                pass

        # Reflexion: benzer gecmis basarisizlik dersleri
        _reflexion_ek = ""
        if self.reflexion:
            try:
                _reflexion_ek = self.reflexion.ilgili_dersleri_al(hedef, adet=2)
            except Exception as _e:
                logger.warning("[Main] except Exception (L617): %s", Exception)
                pass

        # ── SABİT PROMPT BLOĞU: döngü dışında bir kez hesapla ──────────────
        _sabit_beceri_baglami = ""
        try:
            _sb = self.learning.beceri_baglamini_al(hedef, adet=3)
            if _sb:
                _sabit_beceri_baglami = _sb
        except Exception as _e:
            logger.warning("[Main] except Exception (L626): %s", Exception)
            pass

        _sabit_skill_ozet = ""
        try:
            from reymen.arac.skill_utils import skill_ara as _skill_ara
            _sk = _skill_ara(hedef, limit=3)
            if _sk:
                _sabit_skill_ozet = "\n== ILGILI SKILL'LER (SKILL_AKTIVAT ile detay al) ==\n"
                for s in _sk:
                    _sabit_skill_ozet += f"- {s['ad']}: {s['aciklama'][:80]}\n"
        except Exception as _e:
            logger.warning("[Main] except Exception (L637): %s", Exception)
            pass

        _sabit_tercih_blok = ""
        if self.adaptif_ogrenme:
            try:
                _sabit_tercih_blok = self.adaptif_ogrenme.tercih_blogu_al() or ""
            except Exception as _e:
                logger.warning("[Main] except Exception (L644): %s", Exception)
                pass

        _sabit_hafiza_plugin_blok = ""
        if self.aktif_hafiza_plugin:
            try:
                _spb = self.aktif_hafiza_plugin.sistem_prompt_bloku()
                _sabit_hafiza_plugin_blok = (_spb or "") + (
                    f"\n\n{_hafiza_plugin_baglam}" if _hafiza_plugin_baglam else ""
                )
            except Exception as _e:
                logger.warning("[Main] except Exception (L654): %s", Exception)
                pass
        # ────────────────────────────────────────────────────────────────────

        mesajlar = [{"role": "user", "content": hedef_ile_plan}]
        son_gozlem = ""
        adim_gecmisi = []
        ardisik_hata = 0
        yeniden_planlamalar = 0
        onceki_eylem = None
        onceki_param = None
        aktif_ajan_id = "genel_cozucu"
        ajan_degisti = False

        for tur in range(1, max_tur + 1):
            if self.budget:
                self.budget.tur_basla()
                if not self.budget.devam_etmeli_mi():
                    print(f"\n[Budget] {self.budget.durum_raporu()} — durduruldu.")
                    break

            print(f"\n--- TUR {tur}/{max_tur} ---")

            # Ajan seviyesi sikistirma: tur % 4 (50% esigi, normal yonetim)
            if self.conv_compressor and tur > 1 and tur % 4 == 0:
                onceki_len = len(mesajlar)
                mesajlar = self.conv_compressor.sikistir(mesajlar)
                if len(mesajlar) < onceki_len:
                    print(f"[SlidingWindow] {onceki_len} -> {len(mesajlar)} mesaj "
                          f"(#{self.conv_compressor.sikistirma_sayisi()} sikistirma)")

            # Gateway guvenlik agi: %85 esigi — ajan sikistirmayi kaciran uzun sessionlar icin
            # (ReYMeN dual-compression: gateway 85%, agent 50%)
            elif self.conv_compressor and tur > 1:
                _mesaj_tahmini = sum(len(str(m.get("content", ""))) for m in mesajlar) // 4
                if _mesaj_tahmini > 8192 * 0.85:  # 8192 token penceresi varsayimi
                    onceki_len = len(mesajlar)
                    mesajlar = self.conv_compressor.sikistir(mesajlar)
                    if len(mesajlar) < onceki_len:
                        print(f"[GatewaySikistirma] %85 esigi — {onceki_len} -> {len(mesajlar)} mesaj")

            ic_gozlem_modu = (IC_GOZLEM_ARALIK > 0 and tur > 1 and tur % IC_GOZLEM_ARALIK == 0)
            if ic_gozlem_modu:
                print("[Oz-Yansima] Ilerleme degerlendiriliyor...")

            sistem_prompt = self._sistem_promptu_insa_et(
                hedef, analiz, son_gozlem, tur, max_tur, ic_gozlem_modu, gecmis
            )
            if tur == 1:
                self._son_sistem_prompt = sistem_prompt

            # ── SABİT BLOKLAR: döngü dışında hesaplandı, buraya ekle ───────
            sistem_prompt += _sabit_beceri_baglami
            sistem_prompt += _sabit_skill_ozet
            sistem_prompt += _sabit_tercih_blok

            if tur == 1:
                sistem_prompt += _sabit_hafiza_plugin_blok
                if kb_rehber:
                    sistem_prompt += kb_rehber
                if _meta_ek:
                    sistem_prompt += f"\n\n{_meta_ek}"
                if _reflexion_ek:
                    sistem_prompt += _reflexion_ek
            # ─────────────────────────────────────────────────────────────────

            mesajlar = self.compressor.compress(mesajlar, context_length=8192)

            # Ephemeral budget uyarisi (ReYMeN pattern):
            # LLM'e gecici baskı bildirisi — history'ye YAZILMAZ, cache bozmaz
            _ephemeral_ek = ""
            if self.budget:
                kalan_oran = 1.0 - (tur / max(max_tur, 1))
                if kalan_oran <= 0.25:
                    _ephemeral_ek = (
                        f"\n\n[KRITIK]: Tur {tur}/{max_tur}. "
                        f"Yalnizca {max_tur - tur} tur kaldi — hemen GOREV_BITTI kullan."
                    )
                elif kalan_oran <= 0.45:
                    _ephemeral_ek = (
                        f"\n[BILGI]: Tur {tur}/{max_tur}. "
                        "Kalan adimlarini verimli kullan."
                    )
            _efektif_sistem = sistem_prompt + _ephemeral_ek

            # ══════════════════════════════════════════════════════════════════
            # NATIVE FC HİBRİT MOTOR
            # Öncelik: native function calling → paralel araç çalıştırma → continue
            # Fallback: text-parse → eylemi_ayristir → mevcut dispatch
            # ══════════════════════════════════════════════════════════════════

            # 1. Semantic cache (hem FC hem metin modu için)
            cevap = None
            if _sem_cache and tur > 1:
                cevap = _sem_cache.ara(_efektif_sistem, mesajlar)
                if cevap:
                    print("[SemanticCache] Önbellekten yanıt.")

            # 2. FC MODU: uret_v2() ile native tool_calls dene
            _fc_araclari_calistirildi = False
            if cevap is None and self._fc_mod is not False and hasattr(self.provider, "uret_v2"):
                _fc_schema = self.motor.tools_schema_al() if self.motor else []
                if _fc_schema:
                    try:
                        _fc_yanit = self.provider.uret_v2(_efektif_sistem, mesajlar, tools=_fc_schema)
                        _fc_tc    = _fc_yanit.get("tool_calls") or []
                        _fc_metin = _fc_yanit.get("content") or ""
                        self._fc_mod = True

                        if _fc_tc:
                            # ── GOREV_BITTI native tool kontrolü ────────────
                            _gb_tc = next(
                                (tc for tc in _fc_tc
                                 if tc.get("function", {}).get("name") == "GOREV_BITTI"),
                                None,
                            )
                            if _gb_tc:
                                try:
                                    _gb_args = _json.loads(
                                        _gb_tc.get("function", {}).get("arguments", "{}") or "{}"
                                    )
                                except Exception:
                                    _gb_args = {}
                                _gb_ozet = _gb_args.get("ozet", _fc_metin or "Görev tamamlandı.")
                                _gb_esc  = _gb_ozet.replace("\\", "\\\\").replace('"', '\\"')
                                cevap    = f'GOREV_BITTI("{_gb_esc}")'
                                # cevap set edildi → aşağıdaki GOREV_BITTI bloğu handle eder
                            else:
                                # ── Paralel araç çalıştırma ─────────────────
                                mesajlar.append({
                                    "role": "assistant",
                                    "content": _fc_metin,
                                    "tool_calls": _fc_tc,
                                })

                                def _calistir_tc(tc):
                                    _fn     = tc.get("function", {}).get("name", "")
                                    _astr   = tc.get("function", {}).get("arguments", "{}") or "{}"
                                    _tcid   = tc.get("id", _fn)
                                    try:
                                        _tca = _json.loads(_astr)
                                    except Exception:
                                        _tca = {}
                                    _r = self.motor.calistir_fc(_fn, _tca)
                                    return _tcid, _fn, str(_r)

                                _non_gb = [
                                    tc for tc in _fc_tc
                                    if tc.get("function", {}).get("name") != "GOREV_BITTI"
                                ]
                                _sonuclar = []
                                with _TPool(max_workers=min(len(_non_gb), 4)) as _px:
                                    _futs = [_px.submit(_calistir_tc, tc) for tc in _non_gb]
                                    for _ftr in _as_completed(_futs):
                                        _tcid, _fn, _sonuc = _ftr.result()
                                        mesajlar.append({
                                            "role": "tool",
                                            "tool_call_id": _tcid,
                                            "content": _sonuc,
                                        })
                                        adim_gecmisi.append(f"FC/{_fn}: {_sonuc[:80]}")
                                        son_gozlem = _sonuc
                                        _sonuclar.append(_sonuc)
                                        print(f"[FC] {_fn} → {_sonuc[:120]}")

                                # Budget: tek çağrı başına bir tur (paralel araçlar = 1 tur)
                                if self.budget:
                                    _hata_var = any("[Hata]" in s for s in _sonuclar)
                                    self.budget.tur_bitir(
                                        basarili=not _hata_var,
                                        hata_tipi="" if not _hata_var else "tool_error",
                                    )

                                # Trajectory kaydı
                                if self.trajectory:
                                    try:
                                        _isimler = [tc.get("function", {}).get("name") for tc in _non_gb]
                                        self.trajectory.adim_ekle(
                                            tur, f"FC:{len(_non_gb)}araç", str(_isimler), son_gozlem
                                        )
                                    except Exception as _e:
                                        logger.warning("[Main] except Exception (L834): %s", Exception)
                                        pass

                                # Plan ilerlemesi
                                try:
                                    if plan and adim_gecmisi:
                                        self.planlayici.tamamlanan_adim_isaretle(
                                            plan[len(adim_gecmisi) - 1]
                                        )
                                except (IndexError, AttributeError) as _e:
                                    logger.warning("[Main] Indeks disi (L843): %s", IndexError)
                                    pass

                                _fc_araclari_calistirildi = True

                        else:
                            # tool_calls yok → LLM görevi bitirdi (ReYMeN davranışı)
                            if _fc_metin:
                                _fc_esc = _fc_metin.replace("\\", "\\\\").replace('"', '\\"')
                                cevap = f'GOREV_BITTI("{_fc_esc}")'
                            else:
                                cevap = ""  # boş yanıt → metin moduna

                    except Exception as _fc_err:
                        print(f"[FC] Hata ({type(_fc_err).__name__}): {_fc_err} → metin moduna geçildi.")
                        self._fc_mod = False

            # FC araçları paralel çalıştırıldı → yeni tura geç (assistant+tool eklendi)
            if _fc_araclari_calistirildi:
                continue

            # 3. METİN MODU FALLBACK (FC yoksa veya devre dışı)
            if cevap is None:
                if cache_ile_uret and tur > 1:
                    cevap = cache_ile_uret(_efektif_sistem, mesajlar, self.provider.uret)
                else:
                    cevap = self.provider.uret(_efektif_sistem, mesajlar)
                if _sem_cache and cevap and "[Beyin Hatasi]" not in cevap:
                    _sem_cache.kaydet(sistem_prompt, mesajlar, cevap)

            # 4. Hallucination filtresi (hem FC hem metin yanıtları için)
            if self.halucination_filtresi and cevap:
                _temiz_cevap, uyarilar = self.halucination_filtresi.filtrele(
                    cevap, hedef=hedef
                )
                if uyarilar:
                    _uyari_metni = "\n".join(uyarilar)
                    print(_uyari_metni)
                    _kritik = sum(
                        1 for u in uyarilar
                        if "halusinasyon" in u.lower()
                        or "yanlis versiyon" in u.lower()
                        or "internet/disk" in u.lower()
                    )
                    if _kritik >= 1:
                        print("[Guardrail] Kritik hallusinasyon — LLM'e geri bildiriliyor.")
                        mesajlar.append({"role": "user", "content": (
                            f"Önceki yanıtında şu sorunlar tespit edildi:\n{_uyari_metni}\n\n"
                            "Lütfen yalnızca doğrulayabildiğin bilgileri kullan ve "
                            "aynı eylemi tekrar dene."
                        )})
                        son_gozlem = f"[Guardrail]: {_uyari_metni[:200]}"
                        adim_gecmisi.append(f"GUARDRAIL: {uyarilar[0][:80]}")
                        continue

            # 5. Düşünce/Eylem logu ve mesajlara ekle
            _karmasiklik_now = analiz.get("karmasiklik", 1) if isinstance(analiz, dict) else 1
            if _karmasiklik_now >= 2:
                print(f"[Dusunce/Eylem]\n{cevap}")
            mesajlar.append({"role": "assistant", "content": cevap})

            # 6. Eylem ayrıştırma (metin modu: ARAC_ADI(...) pattern'i)
            arac, ham = self.motor.eylemi_ayristir(cevap)

            if arac == "IC_GOZLEM":
                m = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
                analiz_m = m[0] if m else ham
                print(f"[IC GOZLEM]: {analiz_m}")
                mesajlar.append({"role": "user", "content": f"Gozlem: [Oz-Yansima]: {analiz_m}"})
                son_gozlem = f"[Oz-Yansima]: {analiz_m}"
                adim_gecmisi.append(f"IC_GOZLEM: {analiz_m[:80]}")
                continue

            if not arac:
                print("[Uyari] Eylem ayristirilamadi.")
                break

            # Tekrar korumasi
            if tur >= 2 and arac == onceki_eylem and ham == onceki_param:
                print(f"[TEKRAR KORUMASI] {arac} tekrarlandi — bitiriliyor.")
                self._ogren(hedef, adim_gecmisi, f"{arac}: {ham}")
                return f"{arac}: {ham}"
            onceki_eylem = arac
            onceki_param = ham

            if arac == "GOREV_BITTI":
                ozet = self._param_oku(ham)

                # Anayasa denetimi: yalnizca teknik/riskli gorevlerde (karmasiklik >= 3)
                _karmasiklik = analiz.get("karmasiklik", 1) if isinstance(analiz, dict) else 1
                if self.anayasa and _karmasiklik >= 3:
                    try:
                        _gecti, _son_ozet = self.anayasa.denetle(hedef, ozet, adim_gecmisi)
                        if not _gecti:
                            ozet = _son_ozet[:500] if _son_ozet else ozet
                    except Exception as _e:
                        logger.warning("[Main] except Exception (L938): %s", Exception)
                        pass

                # Yaniti yaz (real stdout'a)
                _sure_sn = _time.time() - _t_baslat
                _model_adi = (
                    getattr(self.provider, "model", None)
                    or self.config.get("default_model", "?")
                )
                _prov_adi = self.config.get("default_provider", "")
                _token_str = ""
                try:
                    _mesaj_uzunluk = sum(len(str(m.get("content", ""))) for m in mesajlar)
                    _token_tahmini = _mesaj_uzunluk // 4
                    _token_str = f" │ ~{_token_tahmini // 1000:.0f}K ctx"
                except Exception as _e:
                    logger.warning("[Main] except Exception (L953): %s", Exception)
                    pass
                _SEPR = _D + "─" * 68 + _R
                sys.stdout.write(f"\n{_SEPR}\n")
                sys.stdout.write(f" {_D}─{_R}  {_G}⚕ ReYMeN{_R}\n")
                sys.stdout.write(f"     {ozet}\n")
                sys.stdout.write(f"{_SEPR}\n")
                sys.stdout.write(
                    f" {_D}⚕ {_model_adi}{_R}"
                    f"{_D} │ {_prov_adi}{_R}"
                    f"{_token_str}"
                    f"  {_D}⏲ {_sure_sn:.1f}s{_R}"
                    f"  {_D}✓ tur {tur}/{max_tur}{_R}\n"
                )
                sys.stdout.write(f"{_SEPR}\n\n")
                sys.stdout.flush()
                # Post-processing loglarini gizle ([Ogrenme], [OzGelistirme] vb.)
                try:
                    self._gorev_tamamla(hedef, adim_gecmisi, ozet)
                finally:
                    pass
                return ozet

            # Self-correction: PYTHON_CALISTIR hata alirsa LLM ile duzelt
            if arac == "PYTHON_CALISTIR" and self.adaptif_ogrenme:
                params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
                kod = params[0] if params else ham
                gozlem = self.adaptif_ogrenme.python_duzelt_ve_calistir(
                    kod, self.motor, provider=self.provider, max_deneme=1
                )
            else:
                gozlem = self.motor.calistir(arac, ham)
            print(f"[Gozlem]\n{gozlem}")
            son_gozlem = gozlem
            adim_gecmisi.append(f"{arac}: {ham}")

            if self.trajectory:
                self.trajectory.adim_ekle(
                    tur, cevap.split("\n")[0] if cevap else "",
                    f"{arac}(\"{ham}\")", gozlem
                )

            if self.budget:
                basarili = "[Hata]" not in gozlem and "Hatasi]" not in gozlem
                hata_tipi = self._hata_tipi_bul(gozlem, basarili)
                if not self.budget.tur_bitir(basarili=basarili, hata_tipi=hata_tipi):
                    print(f"\n[Budget] {self.budget.durum_raporu()} — devam edilmiyor.")
                    self._ogren(hedef, adim_gecmisi, "Basarisiz: budget siniri")
                    return None

            if plan and adim_gecmisi and len(adim_gecmisi) <= len(plan):
                self.planlayici.tamamlanan_adim_isaretle(plan[len(adim_gecmisi) - 1])

            # Hafıza Plugin: tur_senkronize (non-blocking, daemon thread)
            if self.aktif_hafiza_plugin:
                try:
                    self.aktif_hafiza_plugin.tur_senkronize(mesajlar)
                except Exception as _e:
                    logger.warning("[Main] except Exception (L1011): %s", Exception)
                    pass

            # Circuit breaker
            if "[Hata]" in gozlem or "Hatasi]" in gozlem:
                ardisik_hata += 1
                print(f"[Hata Sayaci] {ardisik_hata}/3")

                # Stratejik ajan gecisi: hata tipine gore persona degistir
                try:
                    from reymen.cereyan.akilli_yonlendirici import stratejik_ajan_sec, ajan_talimatini_getir
                    yeni_ajan = stratejik_ajan_sec(aktif_ajan_id, gozlem)
                    if yeni_ajan != aktif_ajan_id:
                        aktif_ajan_id = yeni_ajan
                        ajan_degisti = True
                        _persona_talimati = ajan_talimatini_getir(aktif_ajan_id)
                        print(f"[Ajan Gecisi] -> {aktif_ajan_id}")
                        mesajlar.append({
                            "role": "user",
                            "content": f"[SISTEM]: Ajan degisti. Yeni rol:\n{_persona_talimati}\n\nBu yeni rolle cozume devam et."
                        })
                        ardisik_hata = 1  # Yeni ajanla sifirdan basla
                        continue
                except Exception as _aj_hata:
                    print(f"[AjanSecici] Hata: {_aj_hata}")

                if ardisik_hata >= 3:
                    # Reflexion: hata pattern'ini kaydet, ders olustur
                    if self.reflexion:
                        try:
                            self.reflexion.yansima_kaydet(hedef, adim_gecmisi, gozlem)
                        except Exception as _rf_hata:
                            print(f"[Reflexion] Hata: {_rf_hata}")

                    if yeniden_planlamalar < 2:
                        yeni_plan = self.planlayici.yeniden_planla(
                            hedef, self.planlayici.tamamlananlar(), gozlem
                        )
                        if yeni_plan:
                            yeni_metni = "\n".join(f"{i}. {a}" for i, a in enumerate(yeni_plan, 1))
                            mesajlar.append({"role": "user",
                                             "content": f"Hata: {gozlem}\n\nYeni strateji:\n{yeni_metni}"})
                            yeniden_planlamalar += 1
                            ardisik_hata = 0
                            continue
                    print("[Circuit Breaker] Durduruluyor.")
                    self._ogren(hedef, adim_gecmisi, "Basarisiz: tekrarli hata")
                    return None
            else:
                ardisik_hata = 0

            mesajlar.append({"role": "user", "content": f"Gozlem: {gozlem}"})
            self.session.gunluge_yaz(hedef, f"{arac}({ham})", gozlem[:200])


        _sure_toplam = _time.time() - _t_baslat
        _SEPR2 = _D + "─" * 68 + _R
        sys.stdout.write(f"\n{_SEPR2}\n")
        sys.stdout.write(
            f" {_D}─{_R}  {_G}⚕ ReYMeN{_R}  "
            f"{_D}[TUR SINIRI: {max_tur}/{max_tur}  ⏲ {_sure_toplam:.0f}s]{_R}\n"
        )
        sys.stdout.write(
            f"     Gorev {max_tur} turda tamamlanamadi.\n"
            f"     Ipucu: Gorevi parcalara ayir — ornegin once analiz, sonra duzelt.\n"
        )
        sys.stdout.write(f"{_SEPR2}\n\n")
        sys.stdout.flush()
        # Post-processing loglarini gizle
        try:
            print("\n[MAKSIMUM TUR ASILDI]")
            try:
                from reymen.cereyan.cokus_raporlayici import cokus_raporu_uret
                _hata_gecmisi = [f"{a}" for a in adim_gecmisi[-10:]]
                cokus_raporu_uret(
                    gorev=hedef,
                    deneme_sayisi=max_tur,
                    hata_gecmisi=_hata_gecmisi,
                    denenen_ajanlar=["genel_cozucu"],
                    tiklanma_nedeni=f"Son gozlem: {son_gozlem[:200] if son_gozlem else 'Bilinmiyor'}"
                )
            except Exception as _e:
                logger.warning("[Main] except Exception (L1093): %s", Exception)
                pass
            self._ogren(hedef, adim_gecmisi, "Tamamlanamadi: tur asimi")
        finally:
            pass
        if self.trajectory:
            self.trajectory.kaydet()
        return None

    # ── Yardimci metodlar ─────────────────────────────────────────────

    def _giris_temizle(self, hedef: str) -> str:
        """Kullanici girisini guvenlik katmanindan gecir."""
        try:
            from reymen.guvenlik.message_sanitization import giris_temizle
            hedef_temiz, san_rapor = giris_temizle(hedef, maks_uzunluk=8000)
            if san_rapor.get("bulgular"):
                print(f"[Guvenlik] Injection engellendi: {san_rapor['bulgular']}")
                try:
                    from reymen.sistem.persistence import guvenlik_kalicilik
                    guvenlik_kalicilik().tehdit_kaydet(
                        "prompt_injection",
                        f"Girdi temizlendi: {san_rapor['bulgular']}",
                        kaynak="kullanici",
                    )
                except Exception as _e:
                    logger.warning("[Main] except Exception (L1118): %s", Exception)
                    pass
            hedef = hedef_temiz
        except ImportError as _e:
            logger.warning("[Main] Modul yuklenemedi (L1121): %s", ImportError)
            pass

        if self.guvenlik:
            guvenli, neden = self.guvenlik.prompt_guvenli_mi(hedef)
            if not guvenli:
                print(f"[TirithSecurity] Tehdit: {neden}")
        else:
            try:
                from reymen.guvenlik.threat_patterns import prompt_guvenli_mi
                if not prompt_guvenli_mi(hedef):
                    print("[Guvenlik] Tehdit kalıbi tespit edildi.")
            except ImportError as _e:
                logger.warning("[Main] Modul yuklenemedi (L1133): %s", ImportError)
                pass

        if self.mem_guvenlik:
            if self.mem_guvenlik.injection_var_mi(hedef):
                print("[MemSecurity] Injection kalıbi tespit edildi.")
            hedef = self.mem_guvenlik.redact(hedef)

        if self.referanslar:
            ref_ozet = self.referanslar.context_ozeti()
            if ref_ozet:
                hedef = f"{hedef}\n\n{ref_ozet}"

        return hedef

    def _sistem_promptu_insa_et(self, hedef, analiz, son_gozlem,
                                 tur, max_tur, ic_gozlem_modu, gecmis):
        """Tur icin sistem promptunu uret — uc yontemden birini kullan."""
        if self.prompt_builder:
            ek_bilgi = f"Tur: {tur}/{max_tur}, Karmasiklik: {analiz['karmasiklik']}/5"
            if self.budget:
                ek_bilgi += f", {self.budget.durum_raporu()}"
            sistem_prompt, _ = self.prompt_builder.insa(
                hedef,
                gorev_tipi=self._gorev_tipi_bul(hedef, analiz),
                ek_bilgi=ek_bilgi,
                onceki_gozlem=son_gozlem,
                tur=tur,
            )
            return sistem_prompt

        if self._sistem_talimati_fn:
            hafiza_ozeti = gecmis[:500] if gecmis and "bulunamadi" not in str(gecmis).lower() else ""
            return self._sistem_talimati_fn(
                hedef,
                hafiza_ozeti=hafiza_ozeti,
                son_gozlem=son_gozlem,
                tur=tur,
                toplam_tur=max_tur,
                ic_gozlem_modu=ic_gozlem_modu,
            )

        return self.prompt_engine.insa_et(
            hedef, son_gozlem,
            tur=tur, toplam_tur=max_tur, ic_gozlem_modu=ic_gozlem_modu,
        )

    def _gorev_tipi_bul(self, hedef, analiz):
        ipuclari = analiz.get("ipuclari", [])
        if "dosya_islemi" in ipuclari:
            return "dosya"
        if "kod_islemi" in ipuclari:
            return "kod"
        if "web_islemi" in ipuclari:
            return "web"
        return "genel"

    def _param_oku(self, ham):
        m = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        return m[0] if m else ham

    def _hata_tipi_bul(self, gozlem: str, basarili: bool) -> str:
        if basarili:
            return ""
        try:
            from reymen.ag.agent_runtime import HataSiniflandirici
            return HataSiniflandirici.siniflandir(gozlem)
        except ImportError as _e:
            logger.warning("[Main] Modul yuklenemedi (L1200): %s", ImportError)
            pass
        gozlem_lower = gozlem.lower()
        if "baglanti" in gozlem_lower or "timeout" in gozlem_lower:
            return "ag"
        if "izin" in gozlem_lower or "permission" in gozlem_lower:
            return "izin"
        if "module" in gozlem_lower or "import" in gozlem_lower:
            return "modul"
        return "genel"

    def _gorev_tamamla(self, hedef, adim_gecmisi, ozet):
        if self.trajectory:
            self.trajectory.tamamla()
            self.trajectory.kaydet()
            try:
                self.trajectory.sharegpt_kaydet(
                    sistem_prompt=getattr(self, "_son_sistem_prompt", "")
                )
            except Exception as _e:
                logger.warning("[Main] except Exception (L1219): %s", Exception)
                pass
            try:
                from reymen.windows.trajectory_compressor import TrajectoryCompressor
                comp = TrajectoryCompressor(self.provider)
                traj_ozet = comp.ozetle(self.trajectory.adimlar, 1)
                if traj_ozet:
                    self.bounded_memory.kaydet(f"[OZET]: {traj_ozet}", "MEMORY.md")
            except Exception as _e:
                logger.warning("[Main] except Exception (L1227): %s", Exception)
                pass

        self._ogren(hedef, adim_gecmisi, ozet)

        if self.budget:
            self.budget.gorev_tamami()

        # Hafıza Plugin: oturum_bitti kancası
        if self.aktif_hafiza_plugin:
            try:
                self.aktif_hafiza_plugin.oturum_bitti()
            except Exception as _e:
                logger.warning("[Main] except Exception (L1239): %s", Exception)
                pass

    def _ogren(self, hedef, adim_gecmisi, ozet):
        try:
            kayit_id = f"tecrube-{abs(hash(hedef)) % 100000}"
            tecrube_kaydet(self.hafiza, kayit_id, f"{hedef} -> {ozet}", {"hedef": hedef})
            if adim_gecmisi:
                self.learning.beceri_kristallestir(hedef[:40], ozet, "\n".join(adim_gecmisi))
            print("[Ogrenme] Tecrube ve beceri kaydedildi.")
        except Exception as e:
            print(f"[Ogrenme Hatasi] {e}")

        # FAZ 6 — Beceri kutuphanesi JSON kaydı
        if self.beceri_kb and adim_gecmisi:
            try:
                basarili = "Tamamlanamadi" not in ozet and "Basarisiz" not in ozet
                self.beceri_kb.kaydet(
                    hedef[:50],
                    tetikleyiciler=hedef.lower().split()[:6],
                    adimlar=[a.split(":")[0].strip() for a in adim_gecmisi[:8]],
                    basari_kriteri=ozet[:80],
                )
                self.beceri_kb.basari_guncelle(hedef[:50], basarili=basarili)
            except Exception as _kb_hata:
                print(f"[BeceriKB] Kayit hatasi: {_kb_hata}")

        try:
            from reymen.cereyan.self_improvement import OzGelistirmeMotoru
            ogm = OzGelistirmeMotoru(provider=self.provider)
            analiz = ogm.hata_analizi_yap()
            if analiz.get("hata_sayisi", 0) > 5:
                print(f"[OzGelistirme] {analiz['hata_sayisi']} hata bulundu.")
        except Exception as _e:
            logger.warning("[Main] except Exception (L1272): %s", Exception)
            pass


if __name__ == "__main__":
    # Windows konsolunda UTF-8 karakterlerin dogru yazilmasi icin.
    # Burada yapilmali: modul import edildiginde (reymen/__init__ uzerinden) degil.
    import io as _io
    if sys.stdout and hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, _io.TextIOWrapper):
        try:
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception as _e:
            logger.warning("[Main] except Exception (L1283): %s", Exception)
            pass
    if sys.stderr and hasattr(sys.stderr, "buffer") and not isinstance(sys.stderr, _io.TextIOWrapper):
        try:
            sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception as _e:
            logger.warning("[Main] except Exception (L1288): %s", Exception)
            pass

    # 0. Kurulum kontrolu — ilk calistirma ise sihirbaz acilir, sonrakinde atlanir
    try:
        from setup_wizard import kurulum_kontrol_et_ve_calistir
        kurulum_kontrol_et_ve_calistir()
    except Exception as _wizard_hata:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_wizard_hata).__name__, _wizard_hata
        )  # Wizard hatasi ana akisi durdurmasin

    import contextlib as _contextlib

    # Agent init ciktisini yakala (stdout/stderr print'leri icin)
    _buf = _io.StringIO()
    agent = None

    try:
        with _contextlib.redirect_stdout(_buf), _contextlib.redirect_stderr(_buf):
            # 1. Config yükle
            try:
                from setup import config_yukle
                kayitli = config_yukle()
            except Exception:
                kayitli = None
            aktif_config = kayitli or CONFIG

            # 2. Başlangıç kontrolü (API / Ollama / llava)
            try:
                from reymen.sistem.baslangic_kontrol import baslangic_kontrolu, model_degistir
                aktif_config = baslangic_kontrolu(aktif_config)
            except Exception as _e:
                logger.warning("[Main] except Exception (L1318): %s", Exception)
                pass

            # 3. Agent başlat
            mod     = aktif_config.get("backend_mode", _env_anahtar("ReYMeN_BACKEND_MODE", "local"))
            max_tur = int(_env_anahtar("ReYMeN_MAX_TURNS", "15"))
            onay    = _env_anahtar("ReYMeN_ONAY_ISTE", "false").lower() == "true"
            agent   = AIAgentOrchestrator(config=aktif_config, backend_mode=mod, max_tur=max_tur, onay_iste=onay)

            # Oz yansima arkaplan thread
            if hasattr(agent, "oz_yansima") and agent.oz_yansima:
                agent.oz_yansima.baslat_arkaplan(gecikme_sn=5)

    except Exception as _baslama_hatasi:
        _icerik = _buf.getvalue()
        if _icerik:
            sys.stdout.write(_icerik)
        raise _baslama_hatasi

    # 4. Skill tarama (gorkem ekrani icin, susturulmus ciktiyla)
    _skill_veri: dict = {}
    try:
        from startup_ekrani import skill_tara
        _skill_veri = skill_tara(Path(__file__).parent)
    except Exception as _e:
        logger.warning("[Main] except Exception (L1342): %s", Exception)
        pass

    # 5. Gorkem ekrani
    try:
        from startup_ekrani import gorkem_ekranu, model_sec
        gorkem_ekranu(agent=agent, config=aktif_config, skill_veri=_skill_veri)
        model_sec(agent=agent)
    except Exception:
        _hafiza_bilgi = ""
        if agent and agent.aktif_hafiza_plugin:
            _hafiza_bilgi = f"  Hafıza: {agent.aktif_hafiza_plugin.ad}"
        print(f"Komutlar: /model  /guncelle  /yansima  /hafiza  /cikis{_hafiza_bilgi}\n")

    # 5b. Startup bitti — logging'i ac ama gürültülü logger'lari WARNING'de tut
    _startup_log.disable(_startup_log.NOTSET)
    # Root logger'i WARNING'e al → INFO seviyesi artık terminale yazılmaz
    _startup_log.getLogger().setLevel(_startup_log.WARNING)
    # Spesifik gürültülü logger'lar
    for _noisy_logger in ("CUA", "cua_motor_araci", "tools.mcp_tool",
                          "agent.personalities", "plugin_loader", "plugins"):
        _startup_log.getLogger(_noisy_logger).setLevel(_startup_log.WARNING)
    # Loguru: terminale yazmasin (handler ekleme — remove() durumu korunsun)

    # 6. Telegram Gateway'i otomatik baslat (arka planda) - AI bot
    _gateway_thread = None
    try:
        from dotenv import load_dotenv
        env_dosya = Path(__file__).parent / ".env"
        if env_dosya.exists():
            load_dotenv(env_dosya)
        _token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if _token and not _token.startswith("***"):
            _ai_bot = Path(__file__).parent / "telegram_bot" / "ai_bot.py"
            if _ai_bot.exists():
                import threading as _th
                def _gateway_baslat():
                    try:
                        import subprocess as _sp
                        _env = {**os.environ, "TELEGRAM_BOT_TOKEN": _token}
                        _proc = _sp.Popen(
                            [sys.executable, str(_ai_bot)],
                            cwd=str(_ai_bot.parent.parent),
                            env=_env,
                            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                        )
                        _proc.wait()
                    except Exception as _e:
                        logger.warning("[Main] except Exception (L1389): %s", Exception)
                        pass
                _gateway_thread = _th.Thread(target=_gateway_baslat, daemon=True)
                _gateway_thread.start()
                _bot_adi = os.environ.get("TELEGRAM_BOT_ADI", "ReYMeN_ReYMeNbot")
                print(f"  \033[92m[Telegram]\033[0m @{_bot_adi} baslatildi \033[2m(arka plan)\033[0m")
    except Exception as _e:
        logger.warning("[Main] except Exception (L1395): %s", Exception)
        pass

    # 7. İnteraktif döngü

    try:
        from reymen.sistem.guncelle import guncelleme_bildirimi, komut_isle as guncelle_komut
        _guncelle_yuklu = True
    except ImportError:
        _guncelle_yuklu = False

    _bildirim_gosterildi = False

    while True:
        # Arka plan güncelleme kontrolü bittiyse bir kez bildirim göster
        if _guncelle_yuklu and not _bildirim_gosterildi:
            bildirim = guncelleme_bildirimi()
            if bildirim:
                print(bildirim)
                _bildirim_gosterildi = True

        # FAZ 6 — Oz yansima: bildirim kontrol (thread onceden baslatildi)
        if hasattr(agent, "oz_yansima") and agent.oz_yansima:
            _oz_bildirim = agent.oz_yansima.bildirim_al()
            if _oz_bildirim:
                print(_oz_bildirim)

        try:
            hedef = input("ReYMeN > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[ReYMeN] Görüşürüz.")
            break

        if not hedef:
            continue

        # Kullanici duzeltmesini kaydet (adaptif ogrenme)
        if hasattr(agent, "adaptif_ogrenme") and agent.adaptif_ogrenme:
            agent.adaptif_ogrenme.kullanici_mesaji_isle(hedef)

        if hedef.lower() in ("/cikis", "/q", "exit", "quit"):
            print("[ReYMeN] Görüşürüz.")
            break

        if hedef.lower().startswith("/model"):
            try:
                model_degistir(agent)
            except Exception as e:
                print(f"[/model] Hata: {e}")
            continue

        # FAZ 6 — /yansima komutu: oz yansima logunu goster
        if hedef.lower() == "/yansima":
            if hasattr(agent, "oz_yansima") and agent.oz_yansima:
                print(agent.oz_yansima.log_oku())
            else:
                print("[/yansima] OzYansima modulu yuklu degil.")
            continue

        # LLM Self-Improvement — /optimize: meta-prompt analizi calistir
        if hedef.lower() == "/optimize":
            if hasattr(agent, "meta_prompt") and agent.meta_prompt:
                print("[MetaPromptOptimizer] Hata analizi yapiliyor...")
                oneri = agent.meta_prompt.analiz_et_ve_oner()
                if oneri:
                    print(f"[MetaPromptOptimizer] Sistem eki eklendi:\n{oneri[:300]}")
                else:
                    print("[MetaPromptOptimizer] Yeterli hata verisi yok veya iyilestirme gerekmedi.")
            else:
                print("[/optimize] MetaPromptOptimizer modulu yuklu degil.")
            continue

        if hedef.lower().startswith("/guncelle"):
            if _guncelle_yuklu:
                # "/guncelle kapat", "/guncelle ac", "/guncelle durum" veya sadece "/guncelle"
                args = hedef[len("/guncelle"):].strip()
                yeniden_baslat = guncelle_komut(args)
                if yeniden_baslat:
                    print("\n  Programı kapatıp 'python main.py' ile yeniden başlatın.")
            else:
                print("[/guncelle] guncelle.py bulunamadı.")
            continue

        # ── /hafiza komutu ────────────────────────────────────────────────
        if hedef.lower().startswith("/hafiza"):
            _hafiza_arg = hedef[len("/hafiza"):].strip()
            hp = getattr(agent, "aktif_hafiza_plugin", None)
            if not hp:
                print("[Hafıza] Aktif hafıza plugin'i yok.")
                continue

            if not _hafiza_arg or _hafiza_arg == "durum":
                # Durum bilgisi
                blok = hp.sistem_prompt_bloku()
                araclar = [s.get("ad", "") for s in hp.arac_sema_al()]
                print(f"\n[Hafıza Plugin] {hp.ad}")
                print(blok)
                print(f"Araçlar: {', '.join(araclar)}")
                saglayicilar = getattr(agent, "_plugin_yukleyici", None)
                if saglayicilar:
                    liste = saglayicilar.hafiza_saglayici_listele()
                    print(f"Kayıtlı: {', '.join(liste)}")

            elif _hafiza_arg.startswith("ara "):
                sorgu = _hafiza_arg[4:].strip()
                if sorgu:
                    sonuc = hp.onceden_getir(sorgu) or hp.arac_cagri_isle(
                        "HAFIZA_ARA", {"sorgu": sorgu}
                    ) if hasattr(hp, "arac_cagri_isle") else ""
                    print(sonuc or "Sonuç bulunamadı.")
                else:
                    print("Kullanım: /hafiza ara <sorgu>")

            elif _hafiza_arg.startswith("kaydet "):
                metin = _hafiza_arg[7:].strip()
                if metin:
                    arac_adi = "HAFIZA_KAYDET" if hp.ad == "sqlite_fts" else "VEKTOR_KAYDET"
                    sonuc = hp.arac_cagri_isle(arac_adi, {"icerik": metin})
                    print(sonuc)
                else:
                    print("Kullanım: /hafiza kaydet <metin>")

            elif _hafiza_arg == "listele":
                arac_adi = "HAFIZA_LISTELE" if hp.ad == "sqlite_fts" else "OTURUM_LISTELE"
                if any(s.get("ad") == arac_adi for s in hp.arac_sema_al()):
                    print(hp.arac_cagri_isle(arac_adi, {"limit": 10}))
                else:
                    print(hp.arac_cagri_isle(list(hp.arac_sema_al())[0].get("ad", ""), {}))

            elif _hafiza_arg.startswith("degistir "):
                yeni_ad = _hafiza_arg[9:].strip()
                yl = getattr(agent, "_plugin_yukleyici", None)
                if yl:
                    import uuid
                    ok = yl._hafiza_yoneticisi.aktif_saglayici_sec(
                        yeni_ad, str(uuid.uuid4())[:8],
                        reymen_dizin=str(Path(__file__).parent / ".ReYMeN"),
                    ) if yl._hafiza_yoneticisi else False
                    if ok:
                        agent.aktif_hafiza_plugin = yl.aktif_hafiza_saglayici()
                        print(f"[Hafıza] Aktif: {agent.aktif_hafiza_plugin.ad}")
                    else:
                        kayitli = yl.hafiza_saglayici_listele()
                        print(f"Değiştirilemedi. Kayıtlı: {kayitli}")
                else:
                    print("[Hafıza] Plugin yöneticisi bulunamadı.")

            else:
                print(
                    "Kullanım:\n"
                    "  /hafiza durum           — aktif plugin ve araçlar\n"
                    "  /hafiza ara <sorgu>      — hafızada ara\n"
                    "  /hafiza kaydet <metin>   — hafızaya yaz\n"
                    "  /hafiza listele          — son girişleri listele\n"
                    "  /hafiza degistir <ad>    — farklı provider'a geç"
                )
            continue

        agent.run_conversation(hedef)
