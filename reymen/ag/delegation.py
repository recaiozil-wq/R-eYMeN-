# -*- coding: utf-8 -*-
"""
delegation.py — Delegasyon sistemi: alt-ajan oluşturma, görev ayrıştırma ve yönetim.

SubAgent      → Tek bir alt-ajanı temsil eder (id, goal, context, status, result)
TaskDecomposer→ Karmaşık hedefleri alt-görevlere böler (basit sezgisel yaklaşım)
DelegationManager→ Alt-ajanları yönetir, çalıştırır, durumlarını izler
SubAgentRunner→ Alt-ajan görevini subprocess ile çalıştırır

Kullanım:
    manager = DelegationManager()
    sonuc = manager.delegate("Dosyayı oku ve özet çıkar", context="dosya.txt")
    agentler = manager.decompose_and_delegate("Sistem analizi yap ve rapor oluştur")
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SubAgent
# ---------------------------------------------------------------------------


@dataclass
class SubAgent:
    """Tek bir alt-ajanı temsil eder."""
    id: str
    goal: str
    context: str = ""
    status: str = "pending"  # pending | running | success | error | cancelled
    result: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "context": self.context,
            "status": self.status,
            "result": self.result[:500] if self.result else "",
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else "",
            "completed_at_iso": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else "",
            "sure": round(self.completed_at - self.created_at, 2) if self.completed_at and self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<SubAgent [{self.status[:4]}] {self.id[:8]}... goal={self.goal[:40]}>"


# ---------------------------------------------------------------------------
# TaskDecomposer
# ---------------------------------------------------------------------------


class TaskDecomposer:
    """Karmaşık bir hedefi alt-görevlere böler (sezgisel yaklaşım)."""

    @staticmethod
    def decompose(goal: str, base_context: str = "") -> List[SubAgent]:
        """
        Bir hedef metnini alt-görevlere ayırır.

        Stratejiler (sırayla dene):
        1. "and" / "ve" ile ayrılmış cümleler
        2. "then" / "sonra" ile ayrılmış adımlar
        3. Numaralı listeler (1. 2. 3. ...)
        4. Madde işaretleri (- / * / •)
        5. Tek bir alt-görev olarak döndür
        """
        if not goal or not goal.strip():
            return []

        goal = goal.strip()

        # Strateji 1: "and" / "ve" ile ayrılmış cümleler
        parts = TaskDecomposer._split_by_connector(goal, [" and ", ", and "], case_sensitive=False)
        parts_v2 = TaskDecomposer._split_by_connector(goal, [" ve ", ", ve "], case_sensitive=False)
        if len(parts) > 1:
            sub_goals = [p.strip() for p in parts if p.strip()]
            return TaskDecomposer._to_subagents(sub_goals, base_context)
        if len(parts_v2) > 1:
            sub_goals = [p.strip() for p in parts_v2 if p.strip()]
            return TaskDecomposer._to_subagents(sub_goals, base_context)

        # Strateji 2: "then" / "sonra" ile ayrılmış adımlar
        parts = TaskDecomposer._split_by_connector(goal, [" then ", ". then "], case_sensitive=False)
        if len(parts) <= 1:
            parts = TaskDecomposer._split_by_connector(goal, [". sonra ", " sonra "], case_sensitive=False)
        if len(parts) > 1:
            sub_goals = [p.strip().rstrip(".") + "." for p in parts if p.strip()]
            return TaskDecomposer._to_subagents(sub_goals, base_context)

        # Strateji 3: Numaralı listeler (1. 2. 3. veya 1) 2) 3))
        import re
        numbered = re.split(r'\n\s*(?:\d+[\.\)]\s*)', goal)
        if len(numbered) > 2:  # En az 2 gerçek öğe
            sub_goals = [p.strip() for p in numbered if p.strip()]
            return TaskDecomposer._to_subagents(sub_goals, base_context)

        # Strateji 4: Satır bazlı — her satır ayrı bir görev
        lines = [l.strip() for l in goal.split("\n") if l.strip()]
        # Sadece uzun (>5 kelime) ve anlamlı satırları al
        sub_goals = [l for l in lines if len(l.split()) > 3 and not l.startswith("#")]
        if len(sub_goals) >= 2:
            return TaskDecomposer._to_subagents(sub_goals, base_context)

        # Strateji 5: Madde işaretleri (- / * / •)
        bullet = [l.strip().lstrip("-*• ").strip() for l in goal.split("\n")
                  if l.strip() and l.strip()[0] in ("-", "*", "•")]
        bullet = [b for b in bullet if len(b.split()) >= 2]
        if len(bullet) >= 2:
            return TaskDecomposer._to_subagents(bullet, base_context)

        # Strateji 6: Nokta ile biten cümlelere böl (eğer >80 karakter)
        if len(goal) > 80:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', goal) if s.strip()]
            if len(sentences) >= 2:
                return TaskDecomposer._to_subagents(sentences, base_context)

        # Hiçbir strateji eşleşmezse: tek bir alt-görev döndür
        return [SubAgent(
            id=str(uuid.uuid4()),
            goal=goal,
            context=base_context,
        )]

    @staticmethod
    def _split_by_connector(text: str, connectors: List[str], case_sensitive: bool = True) -> List[str]:
        """Metni verilen bağlaçlardan bölmeyi dener."""
        for conn in connectors:
            if case_sensitive:
                if conn in text:
                    return text.split(conn)
            else:
                idx = text.lower().find(conn.lower())
                if idx != -1:
                    return [text[:idx], text[idx + len(conn):]]
        return [text]

    @staticmethod
    def _to_subagents(sub_goals: List[str], base_context: str) -> List[SubAgent]:
        """String listesini SubAgent listesine dönüştür."""
        return [
            SubAgent(
                id=str(uuid.uuid4()),
                goal=g,
                context=base_context,
            )
            for g in sub_goals
            if g
        ]


# ---------------------------------------------------------------------------
# SubAgentRunner
# ---------------------------------------------------------------------------


class SubAgentRunner:
    """
    Alt-ajan görevini subprocess ile çalıştırır.
    subagent_runner.py script'ini python ile çağırır ve
    stdin'den JSON goal/context gönderir.
    """

    def __init__(self, runner_script: Optional[str] = None):
        """
        Args:
            runner_script: subagent_runner.py'nin tam yolu.
                          Varsayılan: bu modülün yanındaki subagent_runner.py
        """
        if runner_script:
            self._runner = Path(runner_script)
        else:
            self._runner = Path(__file__).parent / "subagent_runner.py"

    def run(self, agent: SubAgent, timeout: int = 60) -> SubAgent:
        """
        Alt-ajanı çalıştırır ve sonucu SubAgent nesnesine yazar.
        
        Args:
            agent: Çalıştırılacak SubAgent
            timeout: Maksimum bekleme süresi (saniye)
            
        Returns:
            Güncellenmiş SubAgent (status + result dolu)
        """
        agent.status = "running"

        if not self._runner.exists():
            agent.status = "error"
            agent.result = f"Runner script bulunamadı: {self._runner}"
            agent.completed_at = time.time()
            logger.error(agent.result)
            return agent

        try:
            payload = json.dumps({
                "goal": agent.goal,
                "context": agent.context,
            }, ensure_ascii=False)

            proc = subprocess.Popen(
                [sys.executable or "python", str(self._runner)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = proc.communicate(input=payload, timeout=timeout)

            if proc.returncode != 0:
                agent.status = "error"
                agent.result = f"Subprocess çıkış kodu: {proc.returncode}\n{stderr[:500]}"
                agent.completed_at = time.time()
                logger.warning(f"[SubAgent {agent.id[:8]}] Subprocess hata kodu: {proc.returncode}")
                return agent

            # JSON çıktıyı ayrıştır
            try:
                output = json.loads(stdout)
                agent.status = output.get("status", "success")
                agent.result = output.get("result", stdout[:2000])
            except json.JSONDecodeError:
                # JSON değilse ham stdout'u sonuç olarak al
                agent.status = "success"
                agent.result = stdout[:2000]

            agent.completed_at = time.time()
            logger.info(f"[SubAgent {agent.id[:8]}] Tamamlandı: {agent.status} ({round(agent.completed_at - agent.created_at, 2)}s)")

        except subprocess.TimeoutExpired:
            proc.kill()
            agent.status = "error"
            agent.result = f"Zaman aşımı ({timeout}s)"
            agent.completed_at = time.time()
            logger.warning(f"[SubAgent {agent.id[:8]}] Zaman aşımı")
        except Exception as e:
            agent.status = "error"
            agent.result = f"Runner hatası: {type(e).__name__}: {e}"
            agent.completed_at = time.time()
            logger.error(f"[SubAgent {agent.id[:8]}] Runner hatası: {e}")

        return agent


# ---------------------------------------------------------------------------
# DelegationManager
# ---------------------------------------------------------------------------


class DelegationManager:
    """
    Alt-ajanları yönetir, oluşturur, çalıştırır ve durumlarını izler.
    """

    def __init__(self, runner: Optional[SubAgentRunner] = None):
        self._agents: Dict[str, SubAgent] = {}
        self._runner = runner or SubAgentRunner()

    # ── Temel İşlemler ───────────────────────────────────────────

    def delegate(self, goal: str, context: str = "") -> SubAgent:
        """
        Tek bir alt-ajan oluşturup çalıştırır.
        
        Args:
            goal: Alt-ajanın hedefi
            context: Bağlam bilgisi (isteğe bağlı)
            
        Returns:
            Çalıştırılmış SubAgent
        """
        agent = SubAgent(
            id=str(uuid.uuid4()),
            goal=goal,
            context=context,
        )
        self._agents[agent.id] = agent
        logger.info(f"[Delegation] Yeni alt-ajan: {agent.id[:8]} — {goal[:60]}")

        # Runner ile çalıştır
        self._runner.run(agent)

        return agent

    def decompose_and_delegate(self, goal: str, context: str = "") -> List[SubAgent]:
        """
        Hedefi alt-görevlere ayırır ve her birini çalıştırır.
        
        Args:
            goal: Ayrıştırılacak karmaşık hedef
            context: Bağlam bilgisi
            
        Returns:
            Çalıştırılmış SubAgent listesi
        """
        sub_agents = TaskDecomposer.decompose(goal, base_context=context)

        if not sub_agents:
            logger.warning("[Delegation] Ayrıştırma sonucu boş, tek parça olarak dene")
            return [self.delegate(goal, context)]

        results = []
        for agent in sub_agents:
            self._agents[agent.id] = agent
            self._runner.run(agent)
            results.append(agent)

        logger.info(f"[Delegation] {len(sub_agents)} alt-görev ayrıştırıldı ve çalıştırıldı")
        return results

    # ── Sorgulama ─────────────────────────────────────────────────

    def get(self, agent_id: str) -> Optional[SubAgent]:
        """ID ile alt-ajan durumunu getir."""
        return self._agents.get(agent_id)

    def list_active(self) -> List[SubAgent]:
        """Aktif (çalışan veya bekleyen) alt-ajanları listele."""
        return [a for a in self._agents.values() if a.status in ("pending", "running")]

    def list_all(self) -> List[SubAgent]:
        """Tüm alt-ajanları listele."""
        return list(self._agents.values())

    # ── İptal ─────────────────────────────────────────────────────

    def cancel(self, agent_id: str) -> bool:
        """Alt-ajanı iptal et (sadece pending veya running ise)."""
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning(f"[Delegation] İptal: {agent_id[:8]} bulunamadı")
            return False
        if agent.status in ("pending", "running"):
            agent.status = "cancelled"
            agent.completed_at = time.time()
            agent.result = "İptal edildi (kullanıcı tarafından)"
            logger.info(f"[Delegation] Alt-ajan iptal edildi: {agent_id[:8]}")
            return True
        logger.info(f"[Delegation] İptal reddedildi: {agent_id[:8]} durum={agent.status}")
        return False

    # ── İstatistik ────────────────────────────────────────────────

    def results(self) -> Dict[str, Any]:
        """Delegasyon istatistiklerini döndürür."""
        total = len(self._agents)
        if total == 0:
            return {
                "total": 0,
                "active": 0,
                "completed": 0,
                "error": 0,
                "cancelled": 0,
                "success_rate": 0.0,
                "ortalama_sure": 0.0,
            }

        durumlar = {"pending": 0, "running": 0, "success": 0, "error": 0, "cancelled": 0}
        toplam_sure = 0.0
        tamamlanan = 0

        for a in self._agents.values():
            durumlar[a.status] = durumlar.get(a.status, 0) + 1
            if a.completed_at and a.created_at:
                toplam_sure += (a.completed_at - a.created_at)
                tamamlanan += 1

        basarili = durumlar.get("success", 0)
        toplam_tamam = durumlar.get("success", 0) + durumlar.get("error", 0)

        return {
            "total": total,
            "active": durumlar.get("pending", 0) + durumlar.get("running", 0),
            "completed": toplam_tamam,
            "success": basarili,
            "error": durumlar.get("error", 0),
            "cancelled": durumlar.get("cancelled", 0),
            "success_rate": round(basarili / toplam_tamam * 100, 1) if toplam_tamam > 0 else 0.0,
            "ortalama_sure": round(toplam_sure / tamamlanan, 2) if tamamlanan > 0 else 0.0,
            "agents": [a.to_dict() for a in self._agents.values()],
        }

    def temizle(self) -> int:
        """Tamamlanmış tüm alt-ajanları temizle."""
        silinen_ids = [
            aid for aid, a in self._agents.items()
            if a.status in ("success", "error", "cancelled")
        ]
        for aid in silinen_ids:
            del self._agents[aid]
        logger.info(f"[Delegation] {len(silinen_ids)} alt-ajan temizlendi")
        return len(silinen_ids)


# ---------------------------------------------------------------------------
# Singleton Manager (motor_kaydet için)
# ---------------------------------------------------------------------------

_DELEGATION_MANAGER: Optional[DelegationManager] = None


def get_manager() -> DelegationManager:
    """Singleton DelegationManager döndürür."""
    global _DELEGATION_MANAGER
    if _DELEGATION_MANAGER is None:
        _DELEGATION_MANAGER = DelegationManager()
    return _DELEGATION_MANAGER


# ---------------------------------------------------------------------------
# Motor Araçları
# ---------------------------------------------------------------------------


def motor_kaydet(motor) -> None:
    """
    Motor'a delegasyon araçlarını kaydeder.
    
    Kaydettiği araçlar:
        - DELEGATE: Tek bir alt-ajan oluşturup çalıştır
        - TASK_DECOMPOSE: Hedefi alt-görevlere ayır
        - DELEGATION_DURUM: Delegasyon sistem durumu
    """
    manager = get_manager()

    motor._plugin_arac_kaydet(
        "DELEGATE",
        _delegate_tool,
        "DELEGATE(goal, context) — Alt-ajan oluşturup çalıştır. "
        "Parametre: goal=hedef_metni context=opsiyonel_bağlam. "
        "Örnek: DELEGATE(goal='Dosyayı oku', context='test.txt')"
    )
    motor._plugin_arac_kaydet(
        "TASK_DECOMPOSE",
        _task_decompose_tool,
        "TASK_DECOMPOSE(goal, context) — Hedefi alt-görevlere ayır ve hepsini çalıştır. "
        "Parametre: goal=karmaşık_hedef context=opsiyonel_bağlam. "
        "Örnek: TASK_DECOMPOSE(goal='Analiz yap ve rapor yaz')"
    )
    motor._plugin_arac_kaydet(
        "DELEGATION_DURUM",
        _delegation_durum_tool,
        "DELEGATION_DURUM() — Delegasyon sistemi durumunu göster: "
        "toplam alt-ajan sayısı, başarı/başarısızlık oranları, aktif görevler"
    )
    logger.info("[Delegation] Motor'a 3 araç kaydedildi (DELEGATE, TASK_DECOMPOSE, DELEGATION_DURUM)")


def _delegate_tool(**kw) -> str:
    """DELEGATE aracı: tek alt-ajan oluşturup çalıştır."""
    args = kw.get("args", [])
    goal = args[0] if args else kw.get("goal", "")
    context = args[1] if len(args) > 1 else kw.get("context", "")

    if not goal:
        return "[HATA] DELEGATE: goal parametresi zorunlu"

    manager = get_manager()
    agent = manager.delegate(goal, context)

    sure = round(agent.completed_at - agent.created_at, 2) if agent.completed_at else "?"
    return (
        f"[DELEGATE] Alt-ajan tamamlandı\n"
        f"  ID: {agent.id}\n"
        f"  Hedef: {agent.goal[:80]}\n"
        f"  Durum: {agent.status}\n"
        f"  Süre: {sure}s\n"
        f"  Sonuç:\n{agent.result[:600]}"
    )


def _task_decompose_tool(**kw) -> str:
    """TASK_DECOMPOSE aracı: hedefi alt-görevlere ayır ve çalıştır."""
    args = kw.get("args", [])
    goal = args[0] if args else kw.get("goal", "")
    context = args[1] if len(args) > 1 else kw.get("context", "")

    if not goal:
        return "[HATA] TASK_DECOMPOSE: goal parametresi zorunlu"

    manager = get_manager()
    agents = manager.decompose_and_delegate(goal, context)

    basarili = sum(1 for a in agents if a.status == "success")
    hatali = sum(1 for a in agents if a.status == "error")

    lines = [
        f"[TASK_DECOMPOSE] {len(agents)} alt-görev ayrıştırıldı ve çalıştırıldı",
        f"  Başarılı: {basarili}  Hatalı: {hatali}",
        "",
    ]

    for i, a in enumerate(agents, 1):
        sure = round(a.completed_at - a.created_at, 2) if a.completed_at else "?"
        ikon = "✅" if a.status == "success" else "❌" if a.status == "error" else "⏳"
        lines.append(f"  {i}. {ikon} [{a.status}] {a.goal[:60]}")
        lines.append(f"     ID: {a.id}  Süre: {sure}s")
        if a.result:
            lines.append(f"     → {a.result[:200]}")

    return "\n".join(lines)


def _delegation_durum_tool(**kw) -> str:
    """DELEGATION_DURUM aracı: sistem durumunu göster."""
    _ = kw  # parametre yok
    manager = get_manager()
    stats = manager.results()

    if stats["total"] == 0:
        return "[DELEGATION_DURUM] Hiç alt-ajan kaydı yok"

    lines = [
        "[DELEGATION_DURUM]",
        f"  Toplam: {stats['total']} alt-ajan",
        f"  Aktif:  {stats['active']}",
        f"  Başarı: {stats['success']}  Hata: {stats['error']}  İptal: {stats['cancelled']}",
        f"  Başarı Oranı: %{stats['success_rate']}",
        f"  Ortalama Süre: {stats['ortalama_sure']}s",
        "",
        "  ── Son 10 Kayıt ──",
    ]

    for a in sorted(stats["agents"], key=lambda x: x["created_at"], reverse=True)[:10]:
        ikon = {"success": "✅", "error": "❌", "cancelled": "⛔", "running": "⏳", "pending": "⏸️"}.get(a["status"], "❓")
        sure_str = f"{a['sure']}s" if a["sure"] else "?"
        lines.append(f"  {ikon} [{a['status'][:8]}] {a['goal'][:55]:55s} {sure_str:>8s}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test / Demo
# ---------------------------------------------------------------------------


def demo():
    """Basit bir demo çalıştırır."""
    print("=" * 60)
    print("🧪 DELEGASYON SİSTEMİ DEMO")
    print("=" * 60)

    manager = DelegationManager()

    # 1. Tekli delegasyon
    print("\n1️⃣  TEKLİ DELEGASYON")
    print("-" * 40)
    agent = manager.delegate("Örnek bir analiz görevi gerçekleştir", context="test_verisi")
    print(f"  ID: {agent.id}")
    print(f"  Durum: {agent.status}")
    print(f"  Sonuç: {agent.result[:150]}...")

    # 2. Ayrıştırma ve delegasyon
    print("\n2️⃣  AYRIŞTIRMA + DELEGASYON")
    print("-" * 40)
    karmaşık_hedef = "Sistem durumunu kontrol et ve rapor oluştur"
    agents = manager.decompose_and_delegate(karmaşık_hedef)
    for a in agents:
        ikon = "✅" if a.status == "success" else "❌"
        print(f"  {ikon} {a.goal[:50]:50s} → {a.status}")

    # 3. İstatistikler
    print("\n3️⃣  İSTATİSTİKLER")
    print("-" * 40)
    stats = manager.results()
    print(f"  Toplam: {stats['total']}")
    print(f"  Başarı: {stats['success']}")
    print(f"  Başarı Oranı: %{stats['success_rate']}")

    # 4. Aktif listeleme
    print("\n4️⃣  AKTİF ALT-AJANLAR")
    print("-" * 40)
    aktif = manager.list_active()
    print(f"  Aktif sayısı: {len(aktif)}")

    print("\n✅ DEMO TAMAMLANDI")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()
