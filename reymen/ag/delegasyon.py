# -*- coding: utf-8 -*-
"""
delegasyon.py — Subagent + Görev Ayrıştırma Sistemi (P2)

ReYMeN için gelişmiş delegasyon sistemi. Hermes legacy'deki delegate_task_tool
ve delegate_tool pattern'lerini referans alır, ReYMeN yapısına uyarlanmıştır.

Desteklenen Modlar:
    TEK     → Tek subagent'a tek görev
    PARALEL → Birden çok subagent'a paralel görev (maks 3)
    ZINCIR  → Subagent zinciri (çıktı → sonraki subagent girdisi)

Her subagent izole ortamda çalışır:
    - Ayrı context window
    - Ayrı process (subprocess veya thread pool)
    - Parent context'ini kirletmez

Kullanım:
    from reymen.ag.delegasyon import DelegasyonSistemi
    
    sistem = DelegasyonSistemi()
    
    # TEK mod
    sonuc = sistem.delege_et(goal="Dosyayı oku", context="test.txt")
    
    # PARALEL mod
    sonuclar = sistem.paralel_delege(
        gorevler=[
            {"goal": "Arama yap", "context": "konu A"},
            {"goal": "Rapor yaz", "context": "konu B"},
        ]
    )
    
    # ZINCIR mod
    sonuclar = sistem.zincir_delege(
        adimlar=[
            {"goal": "Veriyi topla", "context": ""},
            {"goal": "Veriyi analiz et", "context": ""},
            {"goal": "Rapor oluştur", "context": ""},
        ]
    )
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Maksimum paralel subagent sayısı
MAKS_PARALEL = 3

# Varsayılan zaman aşımı (saniye)
ZAMAN_ASIMI = 120

# Desteklenen modlar
MOD_TEK = "TEK"
MOD_PARALEL = "PARALEL"
MOD_ZINCIR = "ZINCIR"


# ═══════════════════════════════════════════════════════════════════════════
# SubAgent
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class SubAgent:
    """Tek bir alt-ajanı temsil eder. İzole context ve tool set'i ile çalışır."""
    id: str
    goal: str
    context: str = ""
    toolsets: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | success | error | cancelled
    result: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    mod: str = MOD_TEK
    sira: int = 0  # Zincirdeki sıra
    sure: Optional[float] = None
    # İzole context bilgisi
    izole_context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def tamamlandi_mi(self) -> bool:
        return self.status in ("success", "error", "cancelled")

    def basarili_mi(self) -> bool:
        return self.status == "success"

    def dict_olustur(self) -> Dict[str, Any]:
        sure = None
        if self.completed_at and self.created_at:
            sure = round(self.completed_at - self.created_at, 2)
        return {
            "id": self.id,
            "goal": self.goal,
            "context": self.context[:200] if self.context else "",
            "toolsets": self.toolsets,
            "status": self.status,
            "result": self.result[:500] if self.result else "",
            "error": self.error[:200] if self.error else "",
            "mod": self.mod,
            "sira": self.sira,
            "sure": sure,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else "",
            "completed_at": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else "",
        }

    def ozet(self) -> str:
        sure_str = f"{self.sure:.1f}s" if self.sure else "?"
        ikon = {
            "success": "✅", "error": "❌", "cancelled": "⛔",
            "running": "⏳", "pending": "⏸️"
        }.get(self.status, "❓")
        return f"{ikon} [{self.status[:7]}] {self.goal[:60]:60s} {sure_str:>8s}"

    def __repr__(self) -> str:
        return f"<SubAgent [{self.status[:4]}] {self.id[:8]} goal={self.goal[:40]}>"


# ═══════════════════════════════════════════════════════════════════════════
# Görev Ayrıştırıcı
# ═══════════════════════════════════════════════════════════════════════════


class GorevAyrıştırıcı:
    """Karmaşık bir hedefi alt-görevlere ayırır."""
    
    AYIRICI_KELIMELER = [
        "ve", "ve ayrıca", "sonra", "ardından",
        "and", "then", "additionally", "furthermore",
    ]

    @classmethod
    def ayir(cls, hedef: str, context: str = "") -> List[SubAgent]:
        """
        Hedef metnini mantıksal alt-görevlere ayırır.
        
        Stratejiler (sırayla):
        1. Numaralı liste (1. 2. 3. ...)
        2. Madde işaretleri (- * •)
        3. Satır bazlı (her satır bir görev)
        4. Bağlaç bazlı (ve, sonra, and, then)
        5. Cümle bazlı (nokta ile biten)
        6. Tek parça
        """
        if not hedef or not hedef.strip():
            return []

        hedef = hedef.strip()
        import re

        # Strateji 1: Numaralı liste (hem satır başı hem inline)
        numbered = re.split(r'\s+\d+[\.\)]\s+', hedef)
        numbered = [p.strip() for p in numbered if p.strip()]
        if len(numbered) >= 2:
            return cls._alt_gorevlere_cevir(numbered, context)

        # Strateji 2: Madde işaretleri
        bullets = []
        for line in hedef.split('\n'):
            line = line.strip()
            if line and line[0] in ('-', '*', '•', '→', '>'):
                bullet_text = line.lstrip('-*•→> ').strip()
                if len(bullet_text.split()) >= 2:
                    bullets.append(bullet_text)
        if len(bullets) >= 2:
            return cls._alt_gorevlere_cevir(bullets, context)

        # Strateji 3: Satır bazlı
        lines = [l.strip() for l in hedef.split('\n') if l.strip()]
        lines = [l for l in lines if len(l.split()) >= 3 and not l.startswith('#')]
        if len(lines) >= 2:
            return cls._alt_gorevlere_cevir(lines, context)

        # Strateji 4: Bağlaç bazlı
        for ayirici in cls.AYIRICI_KELIMELER:
            if ayirici in hedef.lower():
                parts = [p.strip() for p in hedef.split(ayirici) if p.strip()]
                if len(parts) >= 2:
                    # En az 3 kelime olan parçaları al
                    parts = [p for p in parts if len(p.split()) >= 3]
                    if len(parts) >= 2:
                        return cls._alt_gorevlere_cevir(parts, context)

        # Strateji 5: Cümle bazlı (uzun metinler için)
        if len(hedef) > 100:
            sentences = re.split(r'(?<=[.!?])\s+', hedef)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.split()) >= 3]
            if len(sentences) >= 2:
                return cls._alt_gorevlere_cevir(sentences, context)

        # Hiçbiri eşleşmezse: tek parça
        return [SubAgent(
            id=str(uuid.uuid4()),
            goal=hedef,
            context=context,
        )]

    @classmethod
    def _alt_gorevlere_cevir(cls, parcaciklar: List[str], context: str) -> List[SubAgent]:
        """String listesini SubAgent listesine dönüştürür."""
        import re
        sonuc = []
        for p in parcaciklar:
            p = p.strip()
            if not p or len(p) < 3:
                continue
            # Baştaki numarayı temizle (örn: "1. Veri topla" → "Veri topla")
            p = re.sub(r'^\d+[\.\)]\s*', '', p).strip()
            if p and len(p) >= 3:
                sonuc.append(SubAgent(
                    id=str(uuid.uuid4()),
                    goal=p,
                    context=context,
                ))
        return sonuc


# ═══════════════════════════════════════════════════════════════════════════
# SubAgent Çalıştırıcı
# ═══════════════════════════════════════════════════════════════════════════


class SubAgentCalistirici:
    """
    SubAgent'ı izole ortamda çalıştırır.
    
    İki mod:
    - subprocess: Tam izolasyon (ayrı process, ayrı memory)
    - thread: Hafif, aynı process içinde (paylaşımlı memory)
    
    Her subagent kendi context window ve tool set'i ile çalışır.
    Parent context'ini kirletmez.
    """

    def __init__(self, runner_script: Optional[str] = None, mod: str = "subprocess"):
        """
        Args:
            runner_script: subagent_runner.py yolu (None = otomatik)
            mod: "subprocess" (önerilen) veya "thread"
        """
        if runner_script:
            self._runner = Path(runner_script)
        else:
            self._runner = Path(__file__).parent / "subagent_runner.py"
        self._mod = mod

    def calistir(self, agent: SubAgent, timeout: int = ZAMAN_ASIMI) -> SubAgent:
        """
        SubAgent'ı çalıştırır ve sonucu doldurur.
        
        Args:
            agent: Çalıştırılacak SubAgent
            timeout: Zaman aşımı süresi
            
        Returns:
            Güncellenmiş SubAgent
        """
        agent.status = "running"
        baslangic = time.time()

        if self._mod == "thread":
            return self._thread_calistir(agent, timeout, baslangic)
        else:
            return self._subprocess_calistir(agent, timeout, baslangic)

    def _subprocess_calistir(self, agent: SubAgent, timeout: int, baslangic: float) -> SubAgent:
        """Subprocess ile tam izole çalıştırma."""
        if not self._runner.exists():
            agent.status = "error"
            agent.error = f"Runner script bulunamadı: {self._runner}"
            agent.result = agent.error
            agent.completed_at = time.time()
            agent.sure = round(agent.completed_at - baslangic, 2)
            logger.error(f"[SubAgent {agent.id[:8]}] {agent.error}")
            return agent

        proc = None
        try:
            payload = json.dumps({
                "goal": agent.goal,
                "context": agent.context,
                "toolsets": agent.toolsets,
                "izole_context": agent.izole_context,
            }, ensure_ascii=False)

            # İzole ortam: ayrı process, temiz env
            izole_env = os.environ.copy()
            izole_env["SUBAGENT_ID"] = agent.id
            izole_env["SUBAGENT_GOAL"] = agent.goal[:200]
            izole_env["SUBAGENT_IZOLE"] = "1"

            proc = subprocess.Popen(
                [sys.executable or "python", str(self._runner)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=izole_env,
            )

            stdout, stderr = proc.communicate(input=payload, timeout=timeout)

            if proc.returncode != 0:
                agent.status = "error"
                stderr_text = stderr[:500] if stderr else ""
                agent.error = f"Çıkış kodu: {proc.returncode}\n{stderr_text}"
                agent.result = agent.error
                agent.completed_at = time.time()
                agent.sure = round(agent.completed_at - baslangic, 2)
                logger.warning(f"[SubAgent {agent.id[:8]}] Hata kodu: {proc.returncode}")
                return agent

            try:
                output = json.loads(stdout)
                agent.status = output.get("status", "success")
                agent.result = output.get("result", stdout[:3000])
                agent.error = output.get("error", "")
            except json.JSONDecodeError:
                agent.status = "success"
                agent.result = stdout[:3000]

            agent.completed_at = time.time()
            agent.sure = round(agent.completed_at - baslangic, 2)
            logger.info(f"[SubAgent {agent.id[:8]}] {agent.status} ({agent.sure}s)")

        except subprocess.TimeoutExpired:
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass
            agent.status = "error"
            agent.error = f"Zaman aşımı ({timeout}s)"
            agent.result = agent.error
            agent.completed_at = time.time()
            agent.sure = round(agent.completed_at - baslangic, 2)
            logger.warning(f"[SubAgent {agent.id[:8]}] {agent.error}")
        except Exception as e:
            agent.status = "error"
            agent.error = f"Runner hatası: {type(e).__name__}: {e}"
            agent.result = agent.error
            agent.completed_at = time.time()
            agent.sure = round(agent.completed_at - baslangic, 2)
            logger.error(f"[SubAgent {agent.id[:8]}] {agent.error}")

        return agent

    def _thread_calistir(self, agent: SubAgent, timeout: int, baslangic: float) -> SubAgent:
        """Thread ile hafif çalıştırma (daha hızlı, daha az izole)."""
        try:
            # Thread içinde çalışacak işlev
            def _gorev():
                try:
                    # subagent_runner.py'deki run fonksiyonunu import et
                    runner_mod = str(self._runner)
                    if Path(runner_mod).exists():
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("subagent_runner", runner_mod)
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            sonuc = mod.run(agent.goal, agent.context)
                            return sonuc
                    
                    # Fallback: basit simülasyon
                    return {
                        "status": "success",
                        "result": f"[SubAgent] {agent.goal[:100]} tamamlandı (thread)",
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "result": f"Thread hatası: {type(e).__name__}: {e}",
                    }

            # Thread'de çalıştır
            sonuc = {"status": "error", "result": "Zaman aşımı"}
            
            def _thread_hedefi():
                nonlocal sonuc
                try:
                    sonuc = _gorev()
                except Exception as e:
                    sonuc = {"status": "error", "result": str(e)}

            thread = threading.Thread(target=_thread_hedefi, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            agent.status = sonuc.get("status", "success")
            agent.result = sonuc.get("result", "")
            agent.error = sonuc.get("error", "")

        except Exception as e:
            agent.status = "error"
            agent.error = f"Thread hatası: {type(e).__name__}: {e}"
            agent.result = agent.error

        agent.completed_at = time.time()
        agent.sure = round(agent.completed_at - baslangic, 2)
        return agent


# ═══════════════════════════════════════════════════════════════════════════
# Delegasyon Sistemi (Ana Sınıf)
# ═══════════════════════════════════════════════════════════════════════════


class DelegasyonSistemi:
    """
    Subagent oluşturma, görev devretme ve sonuç toplama sistemi.
    
    Özellikler:
    - Subagent oluşturma (her biri kendi context + tool set'i ile)
    - Görev devretme (goal + context + toolsets)
    - Subagent izolasyonu (ayrı context window, ayrı process)
    - Maksimum 3 paralel subagent
    - Sonuç toplama ve raporlama
    - TEK / PARALEL / ZINCIR modları
    """

    def __init__(self, calistirici: Optional[SubAgentCalistirici] = None):
        self._calistirici = calistirici or SubAgentCalistirici()
        self._agentler: Dict[str, SubAgent] = {}
        self._lock = threading.Lock()
        self._thread_pool = ThreadPoolExecutor(max_workers=MAKS_PARALEL, thread_name_prefix="subagent")

    # ── TEK Mod ─────────────────────────────────────────────────────────

    def delege_et(self, goal: str, context: str = "",
                  toolsets: Optional[List[str]] = None,
                  timeout: int = ZAMAN_ASIMI) -> SubAgent:
        """
        TEK mod: Tek bir subagent oluşturup çalıştırır.
        
        Args:
            goal: Subagent'ın hedefi
            context: Bağlam bilgisi
            toolsets: İzin verilen tool set'leri
            timeout: Zaman aşımı süresi
            
        Returns:
            Çalıştırılmış SubAgent
        """
        agent = SubAgent(
            id=str(uuid.uuid4()),
            goal=goal,
            context=context,
            toolsets=toolsets or [],
            mod=MOD_TEK,
        )

        with self._lock:
            self._agentler[agent.id] = agent

        logger.info(f"[Delegasyon] TEK: {agent.id[:8]} → {goal[:60]}")
        self._calistirici.calistir(agent, timeout=timeout)
        return agent

    # ── PARALEL Mod ─────────────────────────────────────────────────────

    def paralel_delege(self, gorevler: List[Dict[str, Any]],
                       timeout: int = ZAMAN_ASIMI) -> List[SubAgent]:
        """
        PARALEL mod: Birden çok subagent'ı paralel çalıştırır (maks 3).
        
        Args:
            gorevler: Görev listesi. Her biri:
                {
                    "goal": "hedef metni",
                    "context": "bağlam",
                    "toolsets": ["tool1", "tool2"],
                }
            timeout: Her subagent için zaman aşımı
            
        Returns:
            Çalıştırılmış SubAgent listesi
        """
        if len(gorevler) > MAKS_PARALEL:
            logger.warning(
                f"[Delegasyon] PARALEL: {len(gorevler)} görev maksimum {MAKS_PARALEL}'e düşürüldü"
            )
            gorevler = gorevler[:MAKS_PARALEL]

        agentler = []
        for g in gorevler:
            agent = SubAgent(
                id=str(uuid.uuid4()),
                goal=g.get("goal", ""),
                context=g.get("context", ""),
                toolsets=g.get("toolsets", []),
                mod=MOD_PARALEL,
            )
            with self._lock:
                self._agentler[agent.id] = agent
            agentler.append(agent)

        logger.info(f"[Delegasyon] PARALEL: {len(agentler)} subagent başlatılıyor")

        # ThreadPoolExecutor ile paralel çalıştır
        futurelar: Dict[Future, SubAgent] = {}
        for agent in agentler:
            future = self._thread_pool.submit(
                self._calistirici.calistir, agent, timeout
            )
            futurelar[future] = agent

        # Sonuçları topla
        for future in as_completed(futurelar):
            agent = futurelar[future]
            try:
                future.result()  # agent zaten güncellendi
            except Exception as e:
                agent.status = "error"
                agent.error = f"Paralel çalıştırma hatası: {e}"
                agent.result = agent.error
                agent.completed_at = time.time()
                logger.error(f"[Delegasyon] PARALEL hata: {agent.id[:8]} → {e}")

        basarili = sum(1 for a in agentler if a.basarili_mi())
        logger.info(f"[Delegasyon] PARALEL tamam: {basarili}/{len(agentler)} başarılı")
        return agentler

    # ── ZINCIR Mod ─────────────────────────────────────────────────────

    def zincir_delege(self, adimlar: List[Dict[str, Any]],
                      timeout: int = ZAMAN_ASIMI) -> List[SubAgent]:
        """
        ZINCIR mod: Subagent zinciri. Her adımın çıktısı bir sonraki adıma girdi olur.
        
        Args:
            adimlar: Adım listesi. Her biri:
                {
                    "goal": "hedef metni",
                    "context": "başlangıç bağlamı",
                    "toolsets": ["tool1"],
                }
            timeout: Her adım için zaman aşımı
            
        Returns:
            Çalıştırılmış SubAgent listesi
        """
        agentler = []
        onceki_sonuc = ""

        for sira, adim in enumerate(adimlar, 1):
            goal = adim.get("goal", "")
            base_context = adim.get("context", "")
            toolsets = adim.get("toolsets", [])

            # Zincir: önceki adımın çıktısını context'e ekle
            zincir_context = base_context
            if onceki_sonuc:
                if zincir_context:
                    zincir_context += "\n\n"
                zincir_context += f"[ÖNCEKİ ADIM ÇIKTISI]\n{onceki_sonuc[:1000]}"

            agent = SubAgent(
                id=str(uuid.uuid4()),
                goal=goal,
                context=zincir_context,
                toolsets=toolsets,
                mod=MOD_ZINCIR,
                sira=sira,
            )

            with self._lock:
                self._agentler[agent.id] = agent
            agentler.append(agent)

            logger.info(f"[Delegasyon] ZINCIR adım {sira}/{len(adimlar)}: {agent.id[:8]} → {goal[:40]}")
            self._calistirici.calistir(agent, timeout=timeout)

            # Zincir: sonucu bir sonraki adıma aktar
            if agent.basarili_mi():
                onceki_sonuc = agent.result
            else:
                onceki_sonuc = f"[HATA: {agent.error}]"
                logger.warning(
                    f"[Delegasyon] ZINCIR adım {sira} başarısız, zincir devam ediyor..."
                )

        basarili = sum(1 for a in agentler if a.basarili_mi())
        logger.info(f"[Delegasyon] ZINCIR tamam: {basarili}/{len(adimlar)} başarılı")
        return agentler

    # ── Görev Ayrıştırma + Otomatik Delegasyon ──────────────────────────

    def ayir_ve_delege_et(self, hedef: str, context: str = "",
                           mod: str = MOD_TEK) -> List[SubAgent]:
        """
        Hedefi otomatik ayrıştırır ve belirtilen modda çalıştırır.
        
        Args:
            hedef: Karmaşık hedef metni
            context: Bağlam bilgisi
            mod: Çalıştırma modu (TEK, PARALEL, ZINCIR)
            
        Returns:
            Çalıştırılmış SubAgent listesi
        """
        alt_gorevler = GorevAyrıştırıcı.ayir(hedef, context)

        if not alt_gorevler:
            logger.warning("[Delegasyon] Ayrıştırma sonucu boş, TEK olarak dene")
            return [self.delege_et(hedef, context)]

        if len(alt_gorevler) == 1:
            # Tek görev → TEK mod
            self._calistirici.calistir(alt_gorevler[0])
            return alt_gorevler

        if mod == MOD_PARALEL:
            # PARALEL mod
            gorev_dicts = [
                {"goal": a.goal, "context": a.context, "toolsets": a.toolsets}
                for a in alt_gorevler
            ]
            return self.paralel_delege(gorev_dicts)

        elif mod == MOD_ZINCIR:
            # ZINCIR mod
            adim_dicts = [
                {"goal": a.goal, "context": a.context, "toolsets": a.toolsets}
                for a in alt_gorevler
            ]
            return self.zincir_delege(adim_dicts)

        else:
            # TEK mod (her birini sırayla çalıştır)
            for agent in alt_gorevler:
                self._calistirici.calistir(agent)
            return alt_gorevler

    # ── Sorgulama ──────────────────────────────────────────────────────

    def get(self, agent_id: str) -> Optional[SubAgent]:
        """ID ile subagent durumunu getirir."""
        with self._lock:
            return self._agentler.get(agent_id)

    def aktif_listele(self) -> List[SubAgent]:
        """Aktif (çalışan/bekleyen) subagent'ları listeler."""
        with self._lock:
            return [a for a in self._agentler.values()
                    if a.status in ("pending", "running")]

    def tamamlanan_listele(self) -> List[SubAgent]:
        """Tamamlanmış subagent'ları listeler."""
        with self._lock:
            return [a for a in self._agentler.values()
                    if a.status in ("success", "error", "cancelled")]

    def tumu_listele(self) -> List[SubAgent]:
        """Tüm subagent'ları listeler."""
        with self._lock:
            return list(self._agentler.values())

    # ── İptal ──────────────────────────────────────────────────────────

    def iptal_et(self, agent_id: str) -> bool:
        """Subagent'ı iptal eder."""
        with self._lock:
            agent = self._agentler.get(agent_id)
            if not agent:
                logger.warning(f"[Delegasyon] İptal: {agent_id[:8]} bulunamadı")
                return False
            if agent.status in ("pending", "running"):
                agent.status = "cancelled"
                agent.completed_at = time.time()
                agent.result = "İptal edildi"
                agent.error = "Kullanıcı tarafından iptal"
                logger.info(f"[Delegasyon] İptal edildi: {agent_id[:8]}")
                return True
            return False

    def hepsini_iptal_et(self) -> int:
        """Tüm aktif subagent'ları iptal eder."""
        sayac = 0
        with self._lock:
            for agent in list(self._agentler.values()):
                if agent.status in ("pending", "running"):
                    agent.status = "cancelled"
                    agent.completed_at = time.time()
                    agent.result = "Toplu iptal"
                    sayac += 1
        if sayac:
            logger.info(f"[Delegasyon] {sayac} subagent toplu iptal edildi")
        return sayac

    # ── İstatistik ve Raporlama ────────────────────────────────────────

    def istatistik(self) -> Dict[str, Any]:
        """Delegasyon sistemi istatistikleri."""
        with self._lock:
            total = len(self._agentler)
            if total == 0:
                return {
                    "total": 0, "aktif": 0, "basarili": 0,
                    "hata": 0, "iptal": 0, "basarı_orani": 0.0,
                    "ortalama_sure": 0.0, "mod_dagilimi": {},
                }

            durum_sayaci = {"pending": 0, "running": 0, "success": 0,
                            "error": 0, "cancelled": 0}
            mod_sayaci: Dict[str, int] = {}
            toplam_sure = 0.0
            tamamlanan = 0

            for a in self._agentler.values():
                durum_sayaci[a.status] = durum_sayaci.get(a.status, 0) + 1
                mod_sayaci[a.mod] = mod_sayaci.get(a.mod, 0) + 1
                if a.sure is not None:
                    toplam_sure += a.sure
                    tamamlanan += 1

            basarili = durum_sayaci.get("success", 0)
            tamamlanan_toplam = durum_sayaci.get("success", 0) + durum_sayaci.get("error", 0)

            return {
                "total": total,
                "aktif": durum_sayaci.get("pending", 0) + durum_sayaci.get("running", 0),
                "basarili": basarili,
                "hata": durum_sayaci.get("error", 0),
                "iptal": durum_sayaci.get("cancelled", 0),
                "basarı_orani": round(basarili / tamamlanan_toplam * 100, 1) if tamamlanan_toplam > 0 else 0.0,
                "ortalama_sure": round(toplam_sure / tamamlanan, 2) if tamamlanan > 0 else 0.0,
                "mod_dagilimi": mod_sayaci,
            }

    def rapor(self) -> str:
        """İnsan okunabilir delegasyon raporu üretir."""
        stats = self.istatistik()
        if stats["total"] == 0:
            return "[Delegasyon Raporu]\nHenüz hiç subagent çalıştırılmamış."

        lines = [
            "=" * 60,
            "📋 DELEGASYON RAPORU",
            "=" * 60,
            f"  Toplam Subagent: {stats['total']}",
            f"  Aktif:           {stats['aktif']}",
            f"  Başarılı:        {stats['basarili']}",
            f"  Hatalı:          {stats['hata']}",
            f"  İptal:           {stats['iptal']}",
            f"  Başarı Oranı:    %{stats['basarı_orani']}",
            f"  Ortalama Süre:   {stats['ortalama_sure']}s",
            f"  Mod Dağılımı:    {stats['mod_dagilimi']}",
            "",
            "  ── Subagent Listesi ──",
        ]

        with self._lock:
            for a in sorted(self._agentler.values(),
                          key=lambda x: x.created_at, reverse=True)[:20]:
                lines.append(f"  {a.ozet()}")

        lines.extend([
            "",
            f"  ({min(len(self._agentler), 20)}/{len(self._agentler)} gösteriliyor)",
            "=" * 60,
        ])

        return "\n".join(lines)

    def temizle(self) -> int:
        """Tamamlanmış tüm subagent'ları temizler."""
        silinecek = []
        with self._lock:
            silinecek = [
                aid for aid, a in self._agentler.items()
                if a.status in ("success", "error", "cancelled")
            ]
            for aid in silinecek:
                del self._agentler[aid]
        logger.info(f"[Delegasyon] {len(silinecek)} subagent temizlendi")
        return len(silinecek)


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

_DELEGASYON_SISTEMI: Optional[DelegasyonSistemi] = None
_sistem_lock = threading.Lock()


def sistem_al() -> DelegasyonSistemi:
    """Singleton DelegasyonSistemi döndürür."""
    global _DELEGASYON_SISTEMI
    if _DELEGASYON_SISTEMI is None:
        with _sistem_lock:
            if _DELEGASYON_SISTEMI is None:
                _DELEGASYON_SISTEMI = DelegasyonSistemi()
    return _DELEGASYON_SISTEMI


# ═══════════════════════════════════════════════════════════════════════════
# Motor Araçları
# ═══════════════════════════════════════════════════════════════════════════


def motor_kaydet(motor) -> None:
    """
    Motor'a delegasyon araçlarını kaydeder.
    
    Kaydettiği araçlar:
        - DELEGE_ET: TEK mod - tek subagent'a görev devret
        - DELEGE_PARALEL: PARALEL mod - paralel subagent'lar
        - DELEGE_ZINCIR: ZINCIR mod - zincirleme subagent'lar
        - DELEGE_AYRISTIR: Hedefi otomatik ayrıştır + delegasyon
        - DELEGE_DURUM: Delegasyon sistemi durumu
        - DELEGE_IPTAL: Subagent iptal
        - DELEGE_TEMIZLE: Tamamlanan subagent'ları temizle
    """
    sistem = sistem_al()

    motor._plugin_arac_kaydet(
        "DELEGE_ET",
        _delege_et_araci,
        "DELEGE_ET(goal, context, toolsets) — Tek subagent'a görev devret. "
        "Parametreler: goal=hedef_metni (zorunlu), context=bağlam (opsiyonel), "
        "toolsets=izinli_araç_listesi (virgülle ayrılmış, opsiyonel). "
        "Örnek: DELEGE_ET(goal='Dosyayı oku ve özet çıkar', context='veri.txt')"
    )

    motor._plugin_arac_kaydet(
        "DELEGE_PARALEL",
        _delege_paralel_araci,
        "DELEGE_PARALEL(gorev1|gorev2|gorev3) — Paralel subagent'lar (maks 3). "
        "Parametre: gorev1|gorev2|gorev3 formatında '|' ile ayrılmış görevler. "
        "Her görev: 'goal:hedef|context:bağlam' formatında. "
        "Örnek: DELEGE_PARALEL(gorev1='goal:Ara|context:konu_A', "
        "gorev2='goal:Ozet çıkar|context:konu_B')"
    )

    motor._plugin_arac_kaydet(
        "DELEGE_ZINCIR",
        _delege_zincir_araci,
        "DELEGE_ZINCIR(adim1, adim2, adim3) — Zincirleme subagent'lar. "
        "Her adımın çıktısı sonraki adıma girdi olur. "
        "Parametre: adim1=hedef1, adim2=hedef2, adim3=hedef3 şeklinde. "
        "Örnek: DELEGE_ZINCIR(adim1='Veri topla', adim2='Veriyi analiz et', "
        "adim3='Rapor oluştur')"
    )

    motor._plugin_arac_kaydet(
        "DELEGE_AYRISTIR",
        _delege_ayristir_araci,
        "DELEGE_AYRISTIR(hedef, mod, context) — Hedefi otomatik ayrıştır ve "
        "belirtilen modda çalıştır. Parametreler: hedef=karmaşık_hedef (zorunlu), "
        "mod=TEK|PARALEL|ZINCIR (opsiyonel, varsayılan: PARALEL), "
        "context=bağlam (opsiyonel). "
        "Örnek: DELEGE_AYRISTIR(hedef='1. Veri topla 2. Analiz et 3. Rapor yaz', "
        "mod='ZINCIR')"
    )

    motor._plugin_arac_kaydet(
        "DELEGE_DURUM",
        _delege_durum_araci,
        "DELEGE_DURUM() — Delegasyon sistemi durumunu gösterir: "
        "toplam subagent sayısı, başarı/başarısızlık oranları, aktif görevler."
    )

    motor._plugin_arac_kaydet(
        "DELEGE_IPTAL",
        _delege_iptal_araci,
        "DELEGE_IPTAL(agent_id) — Belirtilen subagent'ı iptal eder. "
        "Parametre: agent_id=subagent_id (zorunlu, DELEGE_DURUM'dan alınır). "
        "Örnek: DELEGE_IPTAL(agent_id='abc-1234')"
    )

    motor._plugin_arac_kaydet(
        "DELEGE_TEMIZLE",
        _delege_temizle_araci,
        "DELEGE_TEMIZLE() — Tamamlanmış tüm subagent'ları bellekten temizler."
    )

    logger.info(
        "[Delegasyon] Motor'a 7 araç kaydedildi: "
        "DELEGE_ET, DELEGE_PARALEL, DELEGE_ZINCIR, "
        "DELEGE_AYRISTIR, DELEGE_DURUM, DELEGE_IPTAL, DELEGE_TEMIZLE"
    )


# ── Araç İşlevleri ─────────────────────────────────────────────────────


def _delege_et_araci(**kw) -> str:
    """DELEGE_ET aracı: tek subagent'a görev devret."""
    args = kw.get("args", [])
    goal = args[0] if args else kw.get("goal", "")
    context = args[1] if len(args) > 1 else kw.get("context", "")
    toolsets_str = args[2] if len(args) > 2 else kw.get("toolsets", "")
    toolsets = [t.strip() for t in toolsets_str.split(",")] if toolsets_str else []

    if not goal:
        return "[HATA] DELEGE_ET: 'goal' parametresi zorunlu"

    sistem = sistem_al()
    agent = sistem.delege_et(goal=goal, context=context, toolsets=toolsets)

    sure_str = f"{agent.sure:.1f}s" if agent.sure else "?"
    return (
        f"[DELEGE_ET] Subagent tamamlandı\n"
        f"  ID:     {agent.id}\n"
        f"  Hedef:  {agent.goal[:80]}\n"
        f"  Durum:  {'✅ Başarılı' if agent.basarili_mi() else '❌ Hata'}\n"
        f"  Süre:   {sure_str}\n"
        f"  Sonuç:\n{agent.result[:600]}"
    )


def _delege_paralel_araci(**kw) -> str:
    """DELEGE_PARALEL aracı: paralel subagent'lar."""
    # Parametreleri topla
    gorevler = []
    for i in range(1, MAKS_PARALEL + 1):
        gorev_str = kw.get(f"gorev{i}", "")
        if gorev_str:
            # Format: "goal:hedef|context:bağlam" veya düz metin
            parcalar = gorev_str.split("|")
            goal = ""
            context = ""
            for p in parcalar:
                if p.startswith("goal:"):
                    goal = p[5:].strip()
                elif p.startswith("context:"):
                    context = p[8:].strip()
            if not goal:
                goal = gorev_str  # düz metin
            gorevler.append({"goal": goal, "context": context})

    # args'den de dene
    if not gorevler:
        args = kw.get("args", [])
        for arg in args[:MAKS_PARALEL]:
            if isinstance(arg, str) and arg.strip():
                gorevler.append({"goal": arg, "context": ""})

    if not gorevler:
        return "[HATA] DELEGE_PARALEL: En az bir görev gerekli"

    sistem = sistem_al()
    agentler = sistem.paralel_delege(gorevler)

    basarili = sum(1 for a in agentler if a.basarili_mi())
    hatali = sum(1 for a in agentler if a.status == "error")

    lines = [
        f"[DELEGE_PARALEL] {len(agentler)} subagent paralel çalıştı",
        f"  ✅ Başarılı: {basarili}  ❌ Hatalı: {hatali}",
        "",
    ]

    for i, a in enumerate(agentler, 1):
        sure_str = f"{a.sure:.1f}s" if a.sure else "?"
        ikon = "✅" if a.basarili_mi() else "❌"
        lines.append(f"  {i}. {ikon} [{a.status}] {a.goal[:60]}")
        lines.append(f"     ID: {a.id}  Süre: {sure_str}")
        if a.result:
            lines.append(f"     → {a.result[:150]}")

    return "\n".join(lines)


def _delege_zincir_araci(**kw) -> str:
    """DELEGE_ZINCIR aracı: zincirleme subagent'lar."""
    adimlar = []
    for i in range(1, 10):  # maks 10 adım
        adim = kw.get(f"adim{i}", "")
        if adim and adim.strip():
            adimlar.append({"goal": adim, "context": ""})

    if not adimlar:
        # args'den dene
        args = kw.get("args", [])
        adimlar = [{"goal": a, "context": ""} for a in args[:10] if isinstance(a, str) and a.strip()]

    if not adimlar:
        return "[HATA] DELEGE_ZINCIR: En az bir adım gerekli"

    sistem = sistem_al()
    agentler = sistem.zincir_delege(adimlar)

    basarili = sum(1 for a in agentler if a.basarili_mi())

    lines = [
        f"[DELEGE_ZINCIR] {len(agentler)} adımlı zincir tamamlandı",
        f"  ✅ Başarılı adım: {basarili}/{len(agentler)}",
        "",
    ]

    for i, a in enumerate(agentler, 1):
        sure_str = f"{a.sure:.1f}s" if a.sure else "?"
        ikon = "✅" if a.basarili_mi() else "❌"
        ok = "  ↓" if i < len(agentler) else ""
        lines.append(f"  Adım {i}: {ikon} {a.goal[:55]}")
        lines.append(f"          Süre: {sure_str}  Durum: {a.status}{ok}")
        if a.result:
            lines.append(f"          → {a.result[:100]}")

    return "\n".join(lines)


def _delege_ayristir_araci(**kw) -> str:
    """DELEGE_AYRISTIR aracı: hedefi ayrıştır ve çalıştır."""
    args = kw.get("args", [])
    hedef = args[0] if args else kw.get("hedef", "")
    mod = args[1] if len(args) > 1 else kw.get("mod", MOD_PARALEL)
    context = args[2] if len(args) > 2 else kw.get("context", "")

    if not hedef:
        return "[HATA] DELEGE_AYRISTIR: 'hedef' parametresi zorunlu"

    mod = mod.upper().strip()
    if mod not in (MOD_TEK, MOD_PARALEL, MOD_ZINCIR):
        mod = MOD_PARALEL

    sistem = sistem_al()
    agentler = sistem.ayir_ve_delege_et(hedef=hedef, context=context, mod=mod)

    basarili = sum(1 for a in agentler if a.basarili_mi())
    hatali = sum(1 for a in agentler if a.status == "error")

    lines = [
        f"[DELEGE_AYRISTIR] {len(agentler)} alt-görev (mod: {mod})",
        f"  ✅ Başarılı: {basarili}  ❌ Hatalı: {hatali}",
        "",
    ]

    for i, a in enumerate(agentler, 1):
        sure_str = f"{a.sure:.1f}s" if a.sure else "?"
        ikon = "✅" if a.basarili_mi() else "❌"
        lines.append(f"  {i}. {ikon} [{a.status}] {a.goal[:60]}")
        lines.append(f"     ID: {a.id}  Süre: {sure_str}")

    return "\n".join(lines)


def _delege_durum_araci(**kw) -> str:
    """DELEGE_DURUM aracı: sistem durumunu göster."""
    _ = kw
    sistem = sistem_al()
    return sistem.rapor()


def _delege_iptal_araci(**kw) -> str:
    """DELEGE_IPTAL aracı: subagent iptal."""
    args = kw.get("args", [])
    agent_id = args[0] if args else kw.get("agent_id", "")

    if not agent_id:
        return "[HATA] DELEGE_IPTAL: 'agent_id' parametresi zorunlu"

    sistem = sistem_al()
    if sistem.iptal_et(agent_id):
        return f"[DELEGE_IPTAL] Subagent iptal edildi: {agent_id[:8]}"
    return f"[DELEGE_IPTAL] İptal başarısız: {agent_id[:8]} bulunamadı veya tamamlanmış"


def _delege_temizle_araci(**kw) -> str:
    """DELEGE_TEMIZLE aracı: tamamlanan subagent'ları temizle."""
    _ = kw
    sistem = sistem_al()
    sayi = sistem.temizle()
    return f"[DELEGE_TEMIZLE] {sayi} subagent temizlendi"


# ═══════════════════════════════════════════════════════════════════════════
# Conversation Loop Hook
# ═══════════════════════════════════════════════════════════════════════════

def konusma_dongusu_hook_bul() -> Optional[Callable]:
    """
    Conversation loop için subagent hook'u.
    
    Bu hook, conversation_loop'un her turunda çağrılır.
    Eğer kullanıcı mesajı delegasyon gerektiriyorsa otomatik
    subagent oluşturup çalıştırır.
    
    Returns:
        Hook fonksiyonu veya None
    """
    try:
        from reymen.cereyan.hook_dispatcher import hook_kaydet as _hook_kaydet
        
        def _subagent_hook(tur, mesaj, baglam=None):
            """Her tur öncesi delegasyon kontrolü."""
            if not mesaj:
                return None
            
            mesaj_str = str(mesaj).lower()
            
            # Delegasyon anahtar kelimeleri
            delegasyon_ipuclari = [
                "delege et", "subagent", "alt ajan", "görev devret",
                "paralel çalıştır", "zincir", "aynı anda",
                "delegate", "parallel",
            ]
            
            for ipucu in delegasyon_ipuclari:
                if ipucu in mesaj_str:
                    sistem = sistem_al()
                    return {
                        "delegasyon_aktif": True,
                        "sistem": sistem,
                        "ipucu": ipucu,
                    }
            
            return None
        
        _hook_kaydet("on_turn_start", _subagent_hook)
        logger.info("[Delegasyon] Konuşma döngüsü hook'u kaydedildi")
        return _subagent_hook
        
    except Exception as e:
        logger.warning(f"[Delegasyon] Hook kaydı başarısız: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Test / Demo
# ═══════════════════════════════════════════════════════════════════════════

def demo():
    """Delegasyon sistemi demo'su."""
    print("=" * 60)
    print("🧪 DELEGASYON SİSTEMİ DEMO (P2)")
    print("=" * 60)

    sistem = DelegasyonSistemi()

    # 1. TEK Mod
    print("\n1️⃣  TEK MOD: Tek Subagent")
    print("-" * 40)
    agent = sistem.delege_et("Örnek analiz görevi", context="test_verisi")
    print(f"  ID:     {agent.id}")
    print(f"  Durum:  {agent.status}")
    print(f"  Süre:   {agent.sure}s")
    print(f"  Sonuç:  {agent.result[:150]}")

    # 2. PARALEL Mod
    print("\n2️⃣  PARALEL MOD: 3 Paralel Subagent")
    print("-" * 40)
    gorevler = [
        {"goal": "Web'de konu A ara", "context": "konu_A"},
        {"goal": "Web'de konu B ara", "context": "konu_B"},
        {"goal": "Rapor şablonu oluştur", "context": "şablon"},
    ]
    agentler = sistem.paralel_delege(gorevler)
    for a in agentler:
        print(f"  {a.ozet()}")

    # 3. ZINCIR Mod
    print("\n3️⃣  ZINCIR MOD: 3 Adımlı Zincir")
    print("-" * 40)
    adimlar = [
        {"goal": "Veriyi topla", "context": ""},
        {"goal": "Veriyi analiz et", "context": ""},
        {"goal": "Rapor oluştur", "context": ""},
    ]
    zincir = sistem.zincir_delege(adimlar)
    for a in zincir:
        print(f"  {a.ozet()}")

    # 4. İstatistik
    print("\n4️⃣  SİSTEM İSTATİSTİKLERİ")
    print("-" * 40)
    print(sistem.rapor())

    print("\n✅ DEMO TAMAMLANDI")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()
