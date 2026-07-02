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

# ── OnceHafiza (bellegi-oncelikli kontrol) ───────────────────────
try:
    from reymen.sistem.once_hafiza import hafizada_ara as _hafizada_ara
    _ONCE_HAFIZA_AKTIF = True
except ImportError:
    _hafizada_ara = None
    _ONCE_HAFIZA_AKTIF = False

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

                if self.beyin:
                    eylem = self._beyin_eylem_sec(hedef, baglam)
                else:
                    eylem = {"tur": "mesaj", "icerik": "Beyin modulu bulunamadi"}

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
        '''Konusma dongusu - ReYMeN Agent pipeline ile birebir ayni.

        Akis (Ensemble - 7 kaynak):
          1. SORGU (task_id + session + budget)
          2. ONCE HAFIZA KONTROLU (OnceHafiza, guven>0.8 direkt don)
          3. Session search (FTS5 gecmis konusma arama)
          4. Skill tarama (FTS5 skills_index.db arama)
          5. ENSEMBLE KARSILASTIR (7 kaynak):
             a. DeepSeek (toolsuz, oncek kontrolesiz)
             b. OnceHafiza (guven puanli)
             c. Web arama (backend=html)
             d. Gorsel analiz (URL/dosya icin)
             e. Skill tarama (FTS5)
             f. ONCELIK_CACHE (15 entry)
             g. En yuksek puanli sec + dogrula
          6. KAYDET (OnceHafiza ogrenme)
          7. CEVAP (formatli yanit + session kapat)

        Args:
            hedef:    Kullanicinin hedefi.
            baglam:   Ek baglam dicti (opsiyonel).
            provider: Provider override.

        Returns:
            Sonuc dicti (task_id, basarili, turlar, sure, budget, ...).
        '''
        # -- 1. task_id + session + budget -----------------------------
        task_id = str(uuid.uuid4())[:8]
        # Continuous Learning: session baslat
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
                # Hook: session baslangici
                if _HOOK_AKTIF and _oturum_baslat_tetikle is not None:
                    try:
                        _oturum_baslat_tetikle(session_id=session_id, task_id=task_id, agent_adi="reymen")
                    except Exception:
                        logger.warning("[hook] sessiz_except")
            except Exception as _se:
                log.warning("[%s] Session baslatma hatasi: %s", task_id, _se)

        budget = self._budget_olustur(hedef)

        # Hook: tur baslangici
        if _HOOK_AKTIF and _tur_baslat_tetikle is not None:
            try:
                _tur_baslat_tetikle(tur=1, task_id=task_id, hedef=hedef[:100])
            except Exception:
                logger.warning("[hook] sessiz_except")

        # -- A2A mesaj kontrolu (gelen mesaj varsa hedefe ekle)
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

        # -- 2. ONCE HAFIZA KONTROLU (guven>0.8 ise direkt don)
        hafiza_sonuc = None
        if _ONCE_HAFIZA_AKTIF and _hafizada_ara is not None:
            try:
                hafiza_sonuc = _hafizada_ara(hedef)
            except Exception as _he:
                log.warning("[%s] OnceHafiza hatasi: %s", task_id, _he)
                hafiza_sonuc = None

        if hafiza_sonuc:
            guven = hafiza_sonuc.get("guven", 0)
            yanit = hafiza_sonuc.get("yanit") or hafiza_sonuc.get("sonuc", "")
            if guven > 0.8 and yanit:
                sonuc["basarili"] = True
                sonuc["yanit"] = yanit
                sonuc["kaynak"] = "once_hafiza"
                sonuc["tur"] = 0
                sonuc["sure"] = round(time.time() - baslama, 2)
                self._durum = "tamamlandi"
                return sonuc

        # -- 2a. SKILL AUTO-ACTIVATION (sorgudan_aktif_et)
        #    Kullanici sorgusundaki anahtar kelimelere gore ilgili skill'leri
        #    otomatik aktif eder. Sonuclar system prompt'a eklenecek.
        if _SKILL_ACTIVATOR_AKTIF and _SKILL_ACTIVATOR is not None:
            try:
                aktif_edilen = _SKILL_ACTIVATOR.sorgudan_aktif_et(hedef, max_aktif=3, min_skor=0.15)
                if aktif_edilen:
                    log.info("[%s] Skill auto-activation: %d skill aktif edildi: %s",
                             task_id, len(aktif_edilen), aktif_edilen)
                    # Aktif skill'lerin iceriklerini system prompt'a ekle
                    # once active_skill_tracker uzerinden
                    try:
                        from reymen.cereyan.active_skill_tracker import aktif_skill_ayarla, aktif_skill_al
                        # Aktif edilen ilk skill'i tracker'a ekle
                        ilk_id = aktif_edilen[0]
                        ilk_skill = _SKILL_ACTIVATOR._lib.get(ilk_id)
                        if ilk_skill:
                            skill_baslik = ilk_skill.get("baslik", ilk_id)
                            skill_ozet = ilk_skill.get("icerik_ozeti", "")
                            skill_etiket = ", ".join(ilk_skill.get("etiketler", []))
                            tracker_icerik = (
                                f"Skill: {skill_baslik}\n"
                                f"Aciklama: {skill_ozet}\n"
                                f"Etiketler: {skill_etiket}\n"
                                f"Aktif edilen skill'ler: {', '.join(aktif_edilen)}"
                            )
                            aktif_skill_ayarla(ilk_id, tracker_icerik)
                            log.info("[%s] Skill context enjekte edildi: %s", task_id, ilk_id)
                    except Exception as _ste:
                        log.warning("[%s] Skill tracker enjeksiyon hatasi: %s", task_id, _ste)

                    # Ayrica sonuc'a not olarak ekle (loglama)
                    aktif_detaylar = _SKILL_ACTIVATOR.durum()
                    if aktif_detaylar:
                        skill_notlari = []
                        for s in aktif_detaylar:
                            if s.get("id") in aktif_edilen:
                                baslik = s.get("baslik", s["id"])
                                ozet = s.get("icerik_ozeti", "")
                                etiket = ", ".join(s.get("etiketler", []))
                                skill_notlari.append(
                                    f"- {baslik}: {ozet} ({etiket})"
                                )
                        if skill_notlari:
                            sonuc["aktif_skill_notlari"] = skill_notlari
                            log.info("[%s] Skill context: %s", task_id, skill_notlari)
            except Exception as _se:
                log.warning("[%s] Skill auto-activation hatasi: %s", task_id, _se)

        # -- 2b. OGRENME ATLAMA (imza tabanli cozum varsa direkt don)
        try:
            from reymen.core.ogrenme import cozum_bul, imza_uret
            _hata_on = Exception(hedef)
            _imza_on = imza_uret(_hata_on)
            _cozum_on = cozum_bul(_imza_on)
            if _cozum_on:
                sonuc["yanit"] = f"[Kayitli cozum]\n{_cozum_on}"
                sonuc["basarili"] = True
                sonuc["kaynak"] = "ogrenme_atlama"
                sonuc["tur"] = 0
                sonuc["sure"] = round(time.time() - baslama, 2)
                self._durum = "tamamlandi"
                log.info("[%s] Ogrenme atlama: cozum bulundu", task_id)
                return sonuc
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # -- 3. DOGRUDAN LLM + TOOL LOOP (DeepSeek karar verir) ------------
        self._konusma_gecmisi = [dict(m) for m in self._gecmis_mesajlar]
        if baglam:
            baglam_str = json.dumps(baglam, ensure_ascii=False)
            self._konusma_gecmisi.append({
                "role": "user",
                "content": f"[Baglam]\n{baglam_str}",
            })
        self._konusma_gecmisi.append({"role": "user", "content": hedef})

        # -- 3c. DELEGASYON KONTROL (P2) — Subagent gerekli mi? ----------
        try:
            delegasyon_sonuc = self._delegasyon_kontrol(hedef)
            if delegasyon_sonuc and delegasyon_sonuc.get("basarili"):
                sonuc["basarili"] = True
                sonuc["yanit"] = delegasyon_sonuc["yanit"]
                sonuc["kaynak"] = f"delegasyon_{delegasyon_sonuc['mod']}"
                sonuc["delegasyon"] = delegasyon_sonuc
                sonuc["tur"] = 1
                sonuc["sure"] = round(time.time() - baslama, 2)
                self._durum = "tamamlandi"
                log.info(
                    "[%s] Delegasyon basarili: mod=%s",
                    task_id, delegasyon_sonuc["mod"],
                )
                # Session kapat ve dön
                if _storage and session_id:
                    try:
                        _storage.session_bitir(session_id, end_reason="completed")
                    except Exception as _e:
                        __import__("logging").getLogger(__name__).warning(
                            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                        )
                return sonuc
        except Exception as _de:
            log.warning("[%s] Delegasyon kontrol hatasi: %s", task_id, _de)

        # -- 3b. SESSION CONTEXT INJECTION + SEARCH ------------------------
        if _storage and session_id:
            try:
                session_baglam = self._session_context_injection(session_id, _storage)
                if session_baglam:
                    self._konusma_gecmisi.insert(0, {"role": "user", "content": session_baglam})
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
        try:
            from reymen.hafiza.session_db import session_search
            import concurrent.futures as _cf
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                _fut = _ex.submit(session_search, hedef, limit=2)
                oncekiler = _fut.result(timeout=3)
            if oncekiler and len(oncekiler) > 0:
                for s in oncekiler[:2]:
                    ozet = s.get("ozet") or s.get("summary", "") or ""
                    if ozet:
                        self._konusma_gecmisi.append({"role": "user", "content": f"[Onceki: {str(ozet)[:200]}]"})
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # -- 3d. SKILL TARAMA (skills/ icinde query ile eslesen SKILL.md yukle)
        try:
            skill_icerik = self._skill_tara(hedef)
            if skill_icerik:
                self._konusma_gecmisi.append({"role": "user", "content": skill_icerik})
                log.info("[%s] Skill tarama: eslesen skill eklendi", task_id)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        # -- 3e. TOOL ROUTING (sorgu tipini siniflandir, puanlari ayarla)
        try:
            route = self._tool_routing(hedef)
            sonuc["route"] = route
            log.info("[%s] Tool routing: %s", task_id, route)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

        sistem_prompt = self._sistem_promptu_olustur(hedef, baglam)
        provider_tipi = self._provider_tipi_belirle(provider)
        sonuc["provider"] = provider_tipi

        # -- 4. ENSEMBLE: DeepSeek + OnceHafiza + Web + Cache karsilastir
        ensemble = {}

        # 4a. DeepSeek'e direkt sor (toolsuz, oncek kontrolesiz)
        try:
            ds_mesaj = [
                {"role": "system", "content": "Kisa, oz, dogrudan cevap ver."},
                {"role": "user", "content": hedef}
            ]
            ds_yanit = self._direct_api_call(ds_mesaj, tools_bos=True)
            ds_icerik = ""
            if ds_yanit:
                ds_icerik = ds_yanit.get("content", "") or ""
            ensemble["deepseek"] = {
                "yanit": ds_icerik,
                "puan": 6 if len(ds_icerik.strip()) > 10 else 3,
                "kaynak": "deepseek"
            }
        except Exception:
            ensemble["deepseek"] = {"yanit": "", "puan": 0, "kaynak": "deepseek"}

        # 4b. OnceHafiza
        try:
            oh_sonuc = _hafizada_ara(hedef) if _ONCE_HAFIZA_AKTIF and _hafizada_ara else None
            if oh_sonuc:
                oh_yanit = oh_sonuc.get("yanit") or oh_sonuc.get("sonuc") or oh_sonuc.get("cozum", "")
                oh_guven = oh_sonuc.get("guven", 0)
                ensemble["hafiza"] = {
                    "yanit": oh_yanit,
                    "puan": round(oh_guven * 10, 1),
                    "kaynak": "once_hafiza"
                }
            else:
                ensemble["hafiza"] = {"yanit": "", "puan": 0, "kaynak": "once_hafiza"}
        except Exception:
            ensemble["hafiza"] = {"yanit": "", "puan": 0, "kaynak": "once_hafiza"}

        # 4c. Direkt LLM (basit sorular icin web'e gitmeden once dene)
        _basit_yanit = None
        try:
            if len(hedef) < 60:
                _msg = [{"role":"system","content":"Kisa, oz, dogrudan cevap ver. Turkce konus."},
                        {"role":"user","content":hedef}]
                _r = self._direct_api_call(_msg, tools_bos=True)
                if _r and _r.get("content","").strip() and len(_r["content"]) < 200:
                    _basit_yanit = _r["content"].strip()
        except Exception as _e:
            logger.warning("[ConversationLoopRunConversationYedek] except Exception (L814): %s", Exception)
            pass

        # 4d. Web ara (sonucu LLM ile formatla)
        try:
            web_sonuc = self._web_ara(hedef) if _WEB_ARAMA_AKTIF and not _basit_yanit else None
            if web_sonuc and len(web_sonuc) > 30:
                # Web sonucunu LLM'den geçir - formatli cevap uret
                try:
                    _fmt_mesaj = [
                        {"role": "system", "content": "Kisa, oz, dogrudan cevap ver. Turkce konus. Web verisini kullan."},
                        {"role": "user", "content": f"Soru: {hedef}\n\nWeb verisi:\n{web_sonuc[:2000]}\n\nYukaridaki web verisini kullanarak soruya net, duzgun bir cevap ver."}
                    ]
                    _fmt_yanit = self._direct_api_call(_fmt_mesaj, tools_bos=True)
                    _fmt_icerik = _fmt_yanit.get("content", "").strip() if _fmt_yanit else ""
                    if _fmt_icerik and len(_fmt_icerik) > 10:
                        web_sonuc = _fmt_icerik
                except Exception as _e:
                    pass  # formatlama basarisizsa raw sonucu kullan
                ensemble["web"] = {
                    "yanit": web_sonuc,
                    "puan": 8,
                    "kaynak": "web_arama"
                }
            else:
                ensemble["web"] = {"yanit": "", "puan": 0, "kaynak": "web_arama"}
        except Exception:
            ensemble["web"] = {"yanit": "", "puan": 0, "kaynak": "web_arama"}

        # 4d. GORSEL ANALIZ (fotograf/resim varsa)
        try:
            vision_yanit = self._vision_analiz(hedef)
            if vision_yanit and len(vision_yanit.strip()) > 10:
                ensemble["vision"] = {
                    "yanit": vision_yanit,
                    "puan": 7,
                    "kaynak": "vision"
                }
            else:
                ensemble["vision"] = {"yanit": "", "puan": 0, "kaynak": "vision"}
        except Exception:
            ensemble["vision"] = {"yanit": "", "puan": 0, "kaynak": "vision"}

        # 4e. SKILL TARAMA (FTS5 skills_index.db)
        try:
            skill_yanit = self._skill_bul(hedef)
            if skill_yanit:
                ensemble["skill"] = {
                    "yanit": skill_yanit,
                    "puan": 8,
                    "kaynak": "skill"
                }
            else:
                ensemble["skill"] = {"yanit": "", "puan": 0, "kaynak": "skill"}
        except Exception:
            ensemble["skill"] = {"yanit": "", "puan": 0, "kaynak": "skill"}

        # 4e. ONCELIK_CACHE (tam kelime eslesmesi, alt-string degil)
        try:
            import re as _re
            hedef_kucuk = hedef.strip().lower()
            cache_yanit = ""
            for k, v in ONCELIK_CACHE.items():
                if _re.search(r'\b' + _re.escape(k) + r'\b', hedef_kucuk):
                    cache_yanit = v
                    break
            if cache_yanit:
                ensemble["cache"] = {
                    "yanit": cache_yanit,
                    "puan": 9,
                    "kaynak": "oncelik_cache"
                }
            else:
                ensemble["cache"] = {"yanit": "", "puan": 0, "kaynak": "oncelik_cache"}
        except Exception:
            ensemble["cache"] = {"yanit": "", "puan": 0, "kaynak": "oncelik_cache"}

        # 4e. KARSILASTIR + PUANLA - en yuksek puanliyi sec
        en_iyi = max(ensemble.values(), key=lambda x: x["puan"])
        en_iyi_kaynak = en_iyi["kaynak"]
        en_iyi_yanit = en_iyi["yanit"]

        # ReYMeN sorusu => direkt durum.json oku, web/cache'e gerek yok
        _reymen_kw = ("reymen", "reymen ajan", "reymenai")
        hedef_kucuk = hedef.strip().lower()
        _reymen_sorusu = any(kw in hedef_kucuk for kw in _reymen_kw)
        if _reymen_sorusu:
            # Direkt durum.json oku
            try:
                import json as _json
                _djyol = Path(__file__).parent.parent.parent / "durum.json"
                if _djyol.exists():
                    _dj = _json.loads(_djyol.read_text(encoding="utf-8"))
                    _ozet = []
                    for _k, _v in sorted(_dj.items()):
                        if isinstance(_v, dict) and _v.get("durum") == "tamam":
                            _ozet.append(f"- {_k}: {_v.get('detay','')[:120]}")
                    if _ozet:
                        sonuc["basarili"] = True
                        sonuc["yanit"] = "ReYMeN durum.json verisi:\n\n" + "\n".join(_ozet[:30])
                        sonuc["kaynak"] = "durum.json"
                        log.info("[%s] ReYMeN sorusu -> direkt durum.json'dan yanitlandi", task_id)
                        if _storage and session_id:
                            try: _storage.session_bitir(session_id, end_reason="completed")
                            except Exception as _e:
                                __import__("logging").getLogger(__name__).warning(
                                    "[SessizExcept] yedek: %s", _e
                                )
                        return sonuc
            except Exception as _e:
                log.warning("[%s] durum.json okuma hatasi: %s", task_id, _e)
            # durum.json yoksa veya bossa -> normal ensemble'a yonlen
            _reymen_sorusu = False
            log.info("[%s] durum.json bos/yok, ensemble'a yonleniyor", task_id)
        else:
            sonuc["ensemble"] = ensemble
            if en_iyi_yanit and len(en_iyi_yanit.strip()) > 3:
                sonuc["basarili"] = True
                sonuc["yanit"] = en_iyi_yanit
                sonuc["kaynak"] = en_iyi_kaynak
                sonuc["puan"] = en_iyi["puan"]
                log.info(
                    "[%s] Ensemble kazanan: %s (puan=%.1f)",
                    task_id, en_iyi_kaynak, en_iyi["puan"],
                )
            else:
                sonuc["hata"] = "Tum kaynaklar basarisiz"
                log.warning("[%s] Ensemble: tum kaynaklar basarisiz", task_id)
            # -- ONCEKI HATA COZUMUNU ARA (OnceHafiza'da kayitli mi?) ---
            try:
                if _ONCE_HAFIZA_AKTIF and _hafizada_ara is not None:
                    gecmis_cozum = _hafizada_ara(hedef + " [hata]")
                    if gecmis_cozum and gecmis_cozum.get("guven", 0) > 0.5:
                        eski_cozum = gecmis_cozum.get("yanit") or gecmis_cozum.get("sonuc", "")
                        if eski_cozum:
                            sonuc["yanit"] = eski_cozum
                            sonuc["basarili"] = True
                            sonuc["kaynak"] = "once_hafiza_hata"
                            log.info("[%s] Onceki hata cozumu bulundu", task_id)
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
            if not sonuc.get("basarili"):
                # -- OGRENME.cozum_bul (imza tabanli hata cozumu) ----------
                try:
                    from reymen.core.ogrenme import cozum_bul, cozum_kaydet, imza_uret
                    # imza_uret Exception ister, hata yoksa dummy ver
                    _hata = Exception(sonuc.get("hata", "bilinmiyor"))
                    imza = imza_uret(_hata)
                    mevcut = cozum_bul(imza)
                    if mevcut:
                        sonuc["yanit"] = mevcut
                        sonuc["basarili"] = True
                        sonuc["kaynak"] = "ogrenme_hafiza"
                        log.info("[%s] Ogrenme cozumu bulundu: %s", task_id, imza)
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            if not sonuc.get("basarili"):
                # -- HATA ANALIZI + OnceHafiza + Ogrenme'ye kaydet -------
                try:
                    from reymen.hafiza.hata_analiz import hata_analiz_et
                    ha = hata_analiz_et(hedef, sonuc.get("hata", ""))
                    sonuc["hata_analizi"] = ha
                    cozum = ha.get("cozum", "")
                    if cozum:
                        from reymen.core.ogrenme import cozum_kaydet, imza_uret
                        _hata2 = Exception(sonuc.get("hata", "bilinmiyor"))
                        imza2 = imza_uret(_hata2)
                        cozum_kaydet(imza2, hata_tipi=ha.get("sinif","bilinmiyor"),
                                     hata_ozet=sonuc.get("hata","")[:200],
                                     cozum_kodu=cozum,
                                     kaynak_script="conversation_loop",
                                     basarili=False)
                        if _ONCE_HAFIZA_AKTIF:
                            try:
                                from reymen.sistem.once_hafiza import kaydet as _oh_kaydet
                                _oh_kaydet(hedef=hedef+" [hata]", cozum=cozum,
                                           kategori="hata_cozumu", kaynak=f"hata_analiz_{task_id}")
                            except Exception as _e:
                                __import__("logging").getLogger(__name__).warning(
                                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                                )
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )

        sonuc["tur"] = 1
        sonuc["sure"] = round(time.time() - baslama, 2)
        self._durum = "tamamlandi" if sonuc["basarili"] else "hata"

        # Konusma gecmisini guncelle
        if sonuc["basarili"] and (sonuc.get("yanit") or sonuc.get("sonuc")):
            yanit_metin = sonuc.get("yanit") or sonuc.get("sonuc", "")
            # Kanit kontrolu: yanit bos/None mi?
            if not yanit_metin or len(str(yanit_metin).strip()) < 5:
                log.warning(
                    "[%s] DOGRULA: yanit cok kisa (%d char) - basarisiz sayiliyor",
                    task_id, len(str(yanit_metin).strip()),
                )
                sonuc["basarili"] = False
                sonuc["dogrulama_uyarisi"] = "yanit_cok_kisa"
            else:
                log.info("[%s] DOGRULA: basarili (%d char)", task_id, len(str(yanit_metin).strip()))

        # -- 6. KAYDET (OnceHafiza ogrenme kaydi - _gorev_sonrasi_hafiza) ---
        if sonuc["basarili"] and sonuc.get("kaynak") not in ("once_hafiza", "oncelik_cache", "oneri_uret"):
            ogrenilecek_yanit = sonuc.get("yanit") or sonuc.get("sonuc", "")
            if ogrenilecek_yanit and len(str(ogrenilecek_yanit).strip()) > 20:
                try:
                    self._gorev_sonrasi_hafiza(
                        hedef=hedef,
                        yanit=str(ogrenilecek_yanit)[:500],
                        task_id=task_id,
                    )
                    sonuc["kaydedildi"] = True
                except Exception as _ke:
                    log.warning("[%s] KAYDET hatasi: %s", task_id, _ke)
                    sonuc["kaydedildi"] = False

        # -- 6b. KONUSMADAN SKILL CIKAR (basarili gorev sonrasi) ----------
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
            dict(m) for m in self._konusma_gecmisi
            if m.get("role") in ("user", "assistant") and m.get("content")
        ][-self._max_gecmis_mesaj:]

        # Hook: tur bitisi
        if _HOOK_AKTIF and _tur_bitir_tetikle is not None:
            try:
                _tur_bitir_tetikle(
                    tur=1,
                    basarili=sonuc["basarili"],
                    task_id=task_id,
                    kaynak=sonuc.get("kaynak", ""),
                )
            except Exception:
                logger.warning("[hook] sessiz_except")

        # -- A2A: yaniti broadcast et (diger agent'lar gor sunu)
        if self._a2a_agent is not None and sonuc.get("yanit"):
            try:
                yanit_metin = str(sonuc["yanit"])[:200]
                self._a2a_broker.broadcast(
                    "conversation_loop",
                    {"task_id": task_id, "yanit": yanit_metin},
                    exclude={self._a2a_agent.id},
                )
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

        # -- 7. CEVAP (formatli yanit + session kapat)
        if _storage and session_id:
            try:
                end_reason = "completed" if sonuc["basarili"] else (
                    "cancelled" if self._durum == "iptal" else "error"
                )
                _storage.session_bitir(session_id, end_reason=end_reason)
                log.info("[%s] Session kapatildi: %s (%s)", task_id, session_id, end_reason)
                # Hook: session bitisi
                if _HOOK_AKTIF and _oturum_bitir_tetikle is not None:
                    try:
                        _oturum_bitir_tetikle(
                            session_id=session_id,
                            tur_sayisi=budget.tur if hasattr(budget, 'tur') else 1,
                            basarili=sonuc["basarili"],
                            task_id=task_id,
                        )
                    except Exception:
                        logger.warning("[hook] sessiz_except")
            except Exception as _se:
                log.warning("[%s] Session bitirme hatasi: %s", task_id, _se)

        log.info(
            "[%s] run_conversation bitti: basarili=%s, tur=%d, sure=%.1fs",
            task_id, sonuc["basarili"], budget.tur, sonuc["sure"],
        )

        # -- Self-improvement kalite kaydı
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

        return sonuc

    # ══════════════════════════════════════════════════════════════════
    # ONERI + DOGRULA + KAYDET + TAKILMA — yardimci metodlar
    # ══════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════
    # HATA COZME + OGRENME + ANALIZ — yardimci metodlar
    # ══════════════════════════════════════════════════════════════════

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
            gorsel_kelimeler = ["foto", "resim", "gorsel", "goruntu", "ekran", "ss", "screenshot", "image", "photo", "picture"]
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

    def _web_ara(self, sorgu: str, maks_sonuc: int = 3) -> Optional[str]:
        '''Web arama yap — SearchDispatcher uzerinden (coklu back-end).
        LLM atlanir, direkt web verisi kullanilir (halusinasyon onleme).
        Basarisiz olursa hata sayaci tutar, 3 hata sonra devre disi kalir.

        Kullanilabilir engine'ler: duckduckgo, google, bing, firecrawl,
        brave, searxng, exa, auto (config'e gore en iyisi).
        '''
        if not _WEB_ARAMA_AKTIF:
            return None
        # Circuit breaker: 3 hata sonra web aramayi kapat
        if hasattr(self, '_web_hata') and self._web_hata >= 3:
            return None
        try:
            # Lazy import — circular import ihtimaline karsi
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
                # ZORUNLU: Her mesajda guncel durum.json verisini ekle
                try:
                    from reymen.sistem.durum import durum_oku
                    durum = durum_oku()
                    # Baslik ve tarih kismini ekle, detay atla
                    ek_bilgi += "\n\n📊 GUNCEL DURUM (durum.json):\n"
                    ek_bilgi += durum
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
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
                # 4. Calisma dizini
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

        if self.motor and hasattr(self.motor, "arac_calistir"):
            try:
                return self.motor.arac_calistir(arac, **parametreler)
            except Exception as e:
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
    # SKILL TARAMA
    # ══════════════════════════════════════════════════════════════════

    def _skill_tara(self, query: str, maks: int = 3) -> str:
        """Skills/ icinde SKILL.md dosyalarinda query ara, eslesenleri don."""
        try:
            kok = Path(__file__).parent.parent
            sd = kok / "skills"
            if not sd.exists():
                return ""
            eslesen = []
            for f in sd.iterdir():
                if not f.name.endswith(("_SKILL.md", ".md")) or f.name == "README.md":
                    continue
                icerik = f.read_text(encoding="utf-8", errors="replace")[:500]
                if query.lower() in icerik.lower():
                    baslik = f.name.replace("_SKILL.md", "").replace(".md", "")
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
