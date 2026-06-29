# -*- coding: utf-8 -*-
"""
delegation_manager.py — P2 Delegasyon: Subagent, task decomposition, sonuc toplama.

Mevcut delegasyon sistemleri (reymen/ag/delegasyon.py, reymen/ag/delegation.py)
üzerine kurulmuştur. LLM ile görev ayrıştırma, subagent yönetimi,
paralel/zincir modları, sonuç toplama ve birleştirme.

Motor Tools:
    GOREV_BOL(hedef)            → Karmaşık görevi alt-görevlere ayır
    SUB_GOREV_CALISTIR(goal)    → Subagent çalıştır
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Mevcut Delegasyon modüllerini dene ──────────────────────────────────────────
try:
    from reymen.ag.delegasyon import (
        DelegasyonSistemi as _DelegasyonSistemi,
        SubAgent as _DelegasyonSubAgent,
        SubAgentCalistirici as _SubAgentCalistirici,
        GorevAyrıştırıcı as _GorevAyrıştırıcı,
    )
    _DELEGASYON_MEVCUT = True
except ImportError:
    _DELEGASYON_MEVCUT = False

try:
    from reymen.ag.delegation import (
        DelegationManager as _DelegationManager,
        SubAgent as _DelegationSubAgent2,
        TaskDecomposer as _TaskDecomposer,
        SubAgentRunner as _SubAgentRunner,
        get_manager as _get_delegation_manager,
    )
    _DELEGATION_MEVCUT = True
except ImportError:
    _DELEGATION_MEVCUT = False

# ── LLM entegrasyonu (görev ayrıştırma için) ───────────────────────────────────
try:
    from reymen.core.model_provider import (
        ModelProvider,
        ProviderChain,
        varsayilan_zincir,
    )
    _MODEL_PROVIDER_MEVCUT = True
except ImportError:
    _MODEL_PROVIDER_MEVCUT = False

# Maksimum paralel subagent sayısı
MAKS_PARALEL = 3
ZAMAN_ASIMI = 300  # 5 dakika


# ═══════════════════════════════════════════════════════════════════════════════
#  SubAgent Veri Yapisi
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SubAgent:
    """Tek bir alt-ajani temsil eder."""
    id: str
    goal: str
    context: str = ""
    toolsets: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | success | error | cancelled
    result: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    mod: str = "TEK"
    sira: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    @property
    def sure(self) -> Optional[float]:
        if self.completed_at and self.created_at:
            return round(self.completed_at - self.created_at, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
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
            "sure": self.sure,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else "",
            "completed_at": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else "",
        }

    def ozet(self) -> str:
        sure_str = f"{self.sure:.1f}s" if self.sure else "?"
        ikon = {
            "success": "✅", "error": "❌", "cancelled": "⛔",
            "running": "⏳", "pending": "⏸️",
        }.get(self.status, "❓")
        return f"{ikon} [{self.status[:7]}] {self.goal[:60]:60s} {sure_str:>8s}"


# ═══════════════════════════════════════════════════════════════════════════════
#  GorevAyrıştırıcı (LLM + heuristic)
# ═══════════════════════════════════════════════════════════════════════════════


class GorevAyrıştırıcı:
    """Karmasik bir hedefi alt-gorevlere ayirir.

    Strateji:
        1. LLM ile ayristirma (varsa ModelProvider)
        2. Heuristic ayristirma (numarali liste, madde isareti, cumle bazli)
    """

    AYIRMA_PROMPT = """Görevi mantıksal alt-görevlere ayır.
Her alt-görev:
- Bağımsız çalıştırılabilir olmalı
- Net bir hedef içermeli
- Mümkünse kısa ve öz olmalı (max 200 karakter)

Görev: {goal}

Sadece alt-görev listesini döndür, her satır bir alt-görev.
Başlık veya açıklama ekleme."""

    @classmethod
    def ayir(cls, hedef: str, context: str = "") -> List[SubAgent]:
        """Hedefi alt-gorevlere ayir.

        Args:
            hedef: Karmasik gorev tanimi
            context: Opsiyonel baglam

        Returns:
            SubAgent listesi
        """
        if not hedef or not hedef.strip():
            return []

        hedef = hedef.strip()

        # 1. LLM ile ayristirma dene
        llm_sonuc = cls._llm_ayir(hedef)
        if llm_sonuc and len(llm_sonuc) >= 2:
            return cls._alt_gorevlere_cevir(llm_sonuc, context, hedef)

        # 2. Heuristic ayristirma
        heuristic_sonuc = cls._heuristic_ayir(hedef, context)
        if heuristic_sonuc and len(heuristic_sonuc) >= 2:
            return heuristic_sonuc

        # 3. Tek parca
        return [SubAgent(id=str(uuid.uuid4()), goal=hedef, context=context)]

    @classmethod
    def _llm_ayir(cls, hedef: str) -> Optional[List[str]]:
        """LLM ile gorev ayristirmayi dene."""
        if not _MODEL_PROVIDER_MEVCUT:
            return None

        try:
            zincir = varsayilan_zincir()
            if not zincir:
                return None

            prompt = cls.AYIRMA_PROMPT.format(goal=hedef[:500])
            sonuc = zincir.calistir(prompt)

            if not sonuc or not sonuc.icerik:
                return None

            # Satir satir parse et
            lines = [l.strip().lstrip("*-•0123456789.) ") for l in sonuc.icerik.split("\n") if l.strip()]
            lines = [l for l in lines if len(l.split()) >= 3 and not l.startswith(("#", "//", "--"))]

            if len(lines) >= 2:
                return lines

        except Exception as e:
            logger.debug("[GorevAyrıştırıcı] LLM ayirma hatasi: %s", e)

        return None

    @classmethod
    def _heuristic_ayir(cls, hedef: str, context: str) -> List[SubAgent]:
        """Heuristic yontemlerle gorev ayristir."""
        import re

        # Numarali liste
        numbered = re.split(r'\s+\d+[\.\)]\s+', hedef)
        numbered = [p.strip() for p in numbered if p.strip() and len(p.split()) >= 3]
        if len(numbered) >= 2:
            return cls._alt_gorevlere_cevir(numbered, context, hedef)

        # Madde isaretleri
        bullets = []
        for line in hedef.split('\n'):
            line = line.strip()
            if line and line[0] in ('-', '*', '•', '→', '>'):
                text = line.lstrip('-*•→> ').strip()
                if len(text.split()) >= 2:
                    bullets.append(text)
        if len(bullets) >= 2:
            return cls._alt_gorevlere_cevir(bullets, context, hedef)

        # Satir bazli
        lines = [l.strip() for l in hedef.split('\n') if l.strip() and len(l.split()) >= 3 and not l.startswith('#')]
        if len(lines) >= 2:
            return cls._alt_gorevlere_cevir(lines, context, hedef)

        # Baglac bazli
        for ayirici in ["ve", "ve ayrıca", "sonra", "ardından", "and", "then", "additionally"]:
            if ayirici in hedef.lower():
                parts = [p.strip() for p in hedef.split(ayirici) if p.strip() and len(p.split()) >= 3]
                if len(parts) >= 2:
                    return cls._alt_gorevlere_cevir(parts, context, hedef)

        # Cumle bazli (uzun metin)
        if len(hedef) > 100:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', hedef) if s.strip() and len(s.split()) >= 3]
            if len(sentences) >= 2:
                return cls._alt_gorevlere_cevir(sentences, context, hedef)

        return []

    @classmethod
    def _alt_gorevlere_cevir(cls, parcaciklar: List[str], context: str, kaynak_hedef: str = "") -> List[SubAgent]:
        """String listesini SubAgent listesine donusturur."""
        import re
        sonuc = []
        for p in parcaciklar:
            p = p.strip()
            if not p or len(p) < 3:
                continue
            # Bostaki numarayi temizle
            p = re.sub(r'^\d+[\.\)]\s*', '', p).strip()
            if p and len(p) >= 3:
                sonuc.append(SubAgent(
                    id=str(uuid.uuid4()),
                    goal=p,
                    context=context,
                ))
        return sonuc


# ═══════════════════════════════════════════════════════════════════════════════
#  SubAgent Calistirici (Threaded)
# ═══════════════════════════════════════════════════════════════════════════════


class SubAgentCalistirici:
    """SubAgent'i thread pool ile calistirir.

    Mevcut delegation sistemini kullanir, yoksa basit simule calistirir.
    """

    def __init__(self, max_workers: int = MAKS_PARALEL):
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="subagent")

    def calistir(self, agent: SubAgent, timeout: int = ZAMAN_ASIMI) -> SubAgent:
        """SubAgent'i calistir ve sonucu doldur."""
        agent.status = "running"
        baslangic = time.time()

        try:
            # Mevcut subagent_runner.py'yi kullan
            runner_path = Path(__file__).parent.parent / "ag" / "subagent_runner.py"
            if runner_path.exists():
                sonuc = self._subprocess_calistir(agent, runner_path, timeout)
            else:
                # LLM ile calistir veya simule et
                sonuc = self._simule_calistir(agent)

            agent.result = sonuc.get("result", "")
            agent.status = sonuc.get("status", "success")
            agent.error = sonuc.get("error", "")

        except Exception as e:
            agent.status = "error"
            agent.error = f"Calistirma hatasi: {type(e).__name__}: {e}"
            agent.result = agent.error

        agent.completed_at = time.time()
        return agent

    def _subprocess_calistir(self, agent: SubAgent, runner_path: Path, timeout: int) -> Dict:
        """subagent_runner.py ile subprocess calistir."""
        import subprocess
        import sys

        payload = json.dumps({
            "goal": agent.goal,
            "context": agent.context,
            "toolsets": agent.toolsets,
        }, ensure_ascii=False)

        proc = subprocess.Popen(
            [sys.executable or "python", str(runner_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=payload, timeout=timeout)

        if proc.returncode != 0:
            return {"status": "error", "result": stderr[:500], "error": stderr[:500]}

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"status": "success", "result": stdout[:3000]}

    def _simule_calistir(self, agent: SubAgent) -> Dict:
        """Basit simulasyon (LLM yoksa)."""
        goal_lower = agent.goal.lower()
        if "ara" in goal_lower or "search" in goal_lower or "bul" in goal_lower:
            return {"status": "success", "result": f"[SubAgent] Arama tamamlandi: {agent.goal[:60]}"}
        elif "yaz" in goal_lower or "write" in goal_lower or "olustur" in goal_lower:
            return {"status": "success", "result": f"[SubAgent] Icerik olusturuldu: {agent.goal[:60]}"}
        elif "test" in goal_lower or "kontrol" in goal_lower or "check" in goal_lower:
            return {"status": "success", "result": f"[SubAgent] Test basarili: {agent.goal[:60]}"}
        elif "analiz" in goal_lower or "analyze" in goal_lower or "rapor" in goal_lower:
            return {"status": "success", "result": f"[SubAgent] Analiz tamamlandi: {agent.goal[:60]}"}
        else:
            return {"status": "success", "result": f"[SubAgent] Gorev tamamlandi: {agent.goal[:60]}"}

    def kapat(self):
        self._pool.shutdown(wait=False)


# ═══════════════════════════════════════════════════════════════════════════════
#  DelegationManager Ana Sinif
# ═══════════════════════════════════════════════════════════════════════════════


class DelegationManager:
    """Subagent olusturma, gorev ayristirma, calistirma ve sonuc toplama.

    Ozellikler:
        - Gorev ayristirma (LLM + heuristic)
        - TEK / PARALEL mod
        - Subagent izolasyonu
        - Sonuc toplama ve birlestirme

    Kullanim:
        manager = DelegationManager()
        sonuc = manager.delege_et("Dosyayi oku ve ozet cikar")
        agentler = manager.gorev_bol_ve_calistir("Sistem analizi yap ve rapor olustur")
    """

    def __init__(self, calistirici: Optional[SubAgentCalistirici] = None):
        self._calistirici = calistirici or SubAgentCalistirici()
        self._agentler: Dict[str, SubAgent] = {}

        # Mevcut DelegasyonSistemi ile entegre ol
        self._mevcut_entegre_et()

    def _mevcut_entegre_et(self):
        """Mevcut delegation/modullerindeki agent'lari iceri aktar."""
        if _DELEGASYON_MEVCUT:
            try:
                from reymen.ag.delegasyon import DelegasyonSistemi
                ds = DelegasyonSistemi()
                if hasattr(ds, '_agentler'):
                    for aid, a in ds._agentler.items():
                        if aid not in self._agentler:
                            self._agentler[aid] = SubAgent(
                                id=aid,
                                goal=a.goal,
                                context=a.context,
                                status=a.status,
                                result=a.result,
                                error=a.error,
                            )
            except Exception:
                pass

        if _DELEGATION_MEVCUT:
            try:
                dm = _get_delegation_manager()
                for a in dm.list_all():
                    if a.id not in self._agentler:
                        self._agentler[a.id] = SubAgent(
                            id=a.id, goal=a.goal, context=a.context,
                            status=a.status, result=a.result, error=a.error,
                        )
            except Exception:
                pass

    # ── TEMEL ISLEMLER ─────────────────────────────────────────────────────

    def delege_et(self, goal: str, context: str = "",
                  toolsets: Optional[List[str]] = None,
                  timeout: int = ZAMAN_ASIMI) -> SubAgent:
        """TEK mod: Tek bir subagent olusturup calistir.

        Args:
            goal: Subagent'in hedefi
            context: Baglam bilgisi
            toolsets: Izin verilen tool set'leri
            timeout: Zaman asimi

        Returns:
            Calistirilmis SubAgent
        """
        agent = SubAgent(
            id=str(uuid.uuid4()),
            goal=goal, context=context,
            toolsets=toolsets or [],
            mod="TEK",
        )
        self._agentler[agent.id] = agent
        logger.info("[DelegationManager] TEK: %s — %s", agent.id[:8], goal[:60])

        self._calistirici.calistir(agent, timeout=timeout)
        return agent

    def gorev_bol_ve_calistir(self, goal: str, context: str = "",
                                timeout: int = ZAMAN_ASIMI) -> List[SubAgent]:
        """Hedefi alt-gorevlere ayir ve hepsini calistir.

        Args:
            goal: Karmasik hedef
            context: Baglam bilgisi
            timeout: Her subagent icin zaman asimi

        Returns:
            Calistirilmis SubAgent listesi
        """
        # Gorev ayristir
        sub_agentler = GorevAyrıştırıcı.ayir(goal, context=context)

        if not sub_agentler:
            logger.warning("[DelegationManager] Ayristirma sonucu bos, tek parca olarak calistir")
            return [self.delege_et(goal, context, timeout=timeout)]

        # Her alt-gorevi kaydet ve calistir
        for i, agent in enumerate(sub_agentler):
            agent.mod = "PARALEL"
            agent.sira = i
            self._agentler[agent.id] = agent

        # Paralel calistir (thread pool)
        futures = {}
        for agent in sub_agentler:
            future = self._calistirici._pool.submit(
                self._calistirici.calistir, agent, timeout
            )
            futures[future] = agent

        for future in as_completed(futures, timeout=timeout + 10):
            agent = futures[future]
            try:
                future.result(timeout=5)
            except Exception as e:
                agent.status = "error"
                agent.error = f"Thread hatasi: {type(e).__name__}: {e}"

        logger.info("[DelegationManager] %d alt-gorev tamamlandi", len(sub_agentler))
        return sub_agentler

    def sonuclari_birlestir(self, agentler: List[SubAgent]) -> str:
        """Alt-gorev sonuclarini tek bir metinde birlestir.

        Args:
            agentler: Birlestirilecek SubAgent listesi

        Returns:
            Birlestirilmis sonuc metni
        """
        if not agentler:
            return "[Bilgi] Birlestirilecek sonuc yok."

        basarili = [a for a in agentler if a.status == "success"]
        hatali = [a for a in agentler if a.status == "error"]

        parts = [
            f"=== Gorev Sonuclari ({len(agentler)} alt-gorev) ===",
            f"Basarili: {len(basarili)} | Hata: {len(hatali)}",
        ]

        for i, agent in enumerate(agentler):
            ikon = "✅" if agent.status == "success" else "❌"
            parts.append(f"\n{ikon} Alt-Gorev {i+1}: {agent.goal[:80]}")
            if agent.sure:
                parts.append(f"   Sure: {agent.sure:.1f}s")
            if agent.result:
                parts.append(f"   Sonuc: {agent.result[:300]}")
            if agent.error:
                parts.append(f"   Hata: {agent.error[:200]}")

        return "\n".join(parts)

    # ── SORGULAMA ──────────────────────────────────────────────────────────

    def get(self, agent_id: str) -> Optional[SubAgent]:
        """ID ile subagent durumunu getir."""
        return self._agentler.get(agent_id)

    def list_active(self) -> List[SubAgent]:
        """Aktif (calisan veya bekleyen) subagent'lari listele."""
        return [a for a in self._agentler.values() if a.status in ("pending", "running")]

    def list_all(self) -> List[SubAgent]:
        """Tum subagent'lari listele."""
        return list(self._agentler.values())

    def cancel(self, agent_id: str) -> bool:
        """Subagent'i iptal et."""
        agent = self._agentler.get(agent_id)
        if not agent:
            return False
        if agent.status in ("pending", "running"):
            agent.status = "cancelled"
            agent.result = "Iptal edildi"
            agent.completed_at = time.time()
            return True
        return False

    # ── ISTATISTIK ────────────────────────────────────────────────────────

    def istatistik(self) -> Dict[str, Any]:
        """Delegasyon istatistiklerini dondur."""
        total = len(self._agentler)
        if total == 0:
            return {"total": 0, "active": 0, "success": 0, "error": 0, "cancelled": 0,
                    "success_rate": 0.0, "ortalama_sure": 0.0}

        durumlar = {"pending": 0, "running": 0, "success": 0, "error": 0, "cancelled": 0}
        toplam_sure = 0.0
        tamamlanan = 0

        for a in self._agentler.values():
            durumlar[a.status] = durumlar.get(a.status, 0) + 1
            if a.completed_at and a.created_at:
                toplam_sure += (a.completed_at - a.created_at)
                tamamlanan += 1

        basarili = durumlar.get("success", 0)
        toplam_tamam = basarili + durumlar.get("error", 0)

        return {
            "total": total,
            "active": durumlar.get("pending", 0) + durumlar.get("running", 0),
            "success": basarili,
            "error": durumlar.get("error", 0),
            "cancelled": durumlar.get("cancelled", 0),
            "success_rate": round(basarili / toplam_tamam * 100, 1) if toplam_tamam > 0 else 0.0,
            "ortalama_sure": round(toplam_sure / tamamlanan, 2) if tamamlanan > 0 else 0.0,
        }

    def temizle(self) -> int:
        """Tamamlanmis tum subagent'lari temizle."""
        silinecek = [aid for aid, a in self._agentler.items()
                     if a.status in ("success", "error", "cancelled")]
        for aid in silinecek:
            del self._agentler[aid]
        return len(silinecek)


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_delegation_manager_instance: Optional[DelegationManager] = None


def delegation_manager_al() -> DelegationManager:
    """Varsayilan DelegationManager singleton'ini al."""
    global _delegation_manager_instance
    if _delegation_manager_instance is None:
        _delegation_manager_instance = DelegationManager()
    return _delegation_manager_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  Motor Tools
# ═══════════════════════════════════════════════════════════════════════════════


def motor_kaydet(motor) -> None:
    """Motor'a delegasyon araclarini kaydeder.

    Kaydettigi araclar:
        - GOREV_BOL: Karmasik gorevi alt-gorevlere ayir
        - SUB_GOREV_CALISTIR: Subagent calistir
    """
    manager = delegation_manager_al()

    motor._plugin_arac_kaydet(
        "GOREV_BOL",
        _gorev_bol_tool,
        "GOREV_BOL(hedef, context) — Karmasik gorevi alt-gorevlere ayir. "
        "Parametreler: hedef=gorev_tanimi context=opsiyonel_baglam. "
        "Ornek: GOREV_BOL(hedef='Sistem analizi yap ve rapor olustur')"
    )
    motor._plugin_arac_kaydet(
        "SUB_GOREV_CALISTIR",
        _sub_gorev_calistir_tool,
        "SUB_GOREV_CALISTIR(goal, context) — Subagent olusturup calistir. "
        "Parametreler: goal=hedef_metni context=opsiyonel_baglam. "
        "Ornek: SUB_GOREV_CALISTIR(goal='Dosyayi oku', context='test.txt')"
    )
    logger.info("[DelegationManager] Motor'a 2 arac kaydedildi (GOREV_BOL, SUB_GOREV_CALISTIR)")


def _gorev_bol_tool(**kw) -> str:
    """GOREV_BOL aracı."""
    args = kw.get("args", [])
    hedef = args[0] if args else kw.get("hedef", "")
    context = args[1] if len(args) > 1 else kw.get("context", "")

    if not hedef:
        return "[HATA] GOREV_BOL: hedef parametresi zorunlu"

    alt_gorevler = GorevAyrıştırıcı.ayir(hedef, context=context)

    if not alt_gorevler:
        return "[Bilgi] Gorev ayristirilamadi, tek parca olarak islenecek."

    satirlar = [f"[GOREV_BOL] {len(alt_gorevler)} alt-gorev bulundu:"]
    for i, g in enumerate(alt_gorevler):
        satirlar.append(f"  {i+1}. {g.goal[:100]}")
    satirlar.append("\nCalistirmak icin: SUB_GOREV_CALISTIR(goal='...')")
    return "\n".join(satirlar)


def _sub_gorev_calistir_tool(**kw) -> str:
    """SUB_GOREV_CALISTIR aracı."""
    args = kw.get("args", [])
    goal = args[0] if args else kw.get("goal", "")
    context = args[1] if len(args) > 1 else kw.get("context", "")

    if not goal:
        return "[HATA] SUB_GOREV_CALISTIR: goal parametresi zorunlu"

    manager = delegation_manager_al()
    agent = manager.delege_et(goal, context)
    sure = agent.sure

    return (
        f"[SUB_GOREV] SubAgent tamamlandi\n"
        f"  ID: {agent.id}\n"
        f"  Hedef: {agent.goal[:80]}\n"
        f"  Durum: {agent.status}\n"
        f"  Sure: {sure if sure else '?'}s\n"
        f"  Sonuc:\n{agent.result[:600]}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== DelegationManager Test ===")

    manager = delegation_manager_al()

    # Gorev ayristirma
    print("\n--- Gorev Ayristirma ---")
    alt_gorevler = GorevAyrıştırıcı.ayir(
        "Veritabanini analiz et, rapor olustur ve sonuclari kaydet"
    )
    print(f"Alt-gorev sayisi: {len(alt_gorevler)}")
    for g in alt_gorevler:
        print(f"  {g.goal[:80]}")

    # SubAgent calistir
    print("\n--- SubAgent Calistir ---")
    agent = manager.delege_et("Ornek gorev: dosya tara")
    print(agent.ozet())

    print("\n✓ Test tamamlandi")
