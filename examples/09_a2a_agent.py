#!/usr/bin/env python3
"""Ornek 9: A2A/ACP Protokolu — agent karti, beceri aktarimi, gorev devri."""

try:
    from reymen.a2a_acp import (
        AgentCard,
        AgentCardRegistry,
        SkillPackage,
        SkillTransferProtocol,
        DelegationTask,
        TaskDelegationProtocol,
        AgentCapability,
    )
    import tempfile
    import os

    # ── 1. Agent Card ───────────────────────────────────────────────────
    print("=== 1. Agent Card (Yetkinlik Bildirimi) ===")

    kart = AgentCard(
        agent_id="reymen-001",
        name="ReYMeN",
        version="2026.07.01",
        description="Cok yonlu AI asistani",
        capabilities=[
            AgentCapability.MESSAGING.value,
            AgentCapability.TOOL_EXECUTION.value,
            AgentCapability.SKILL_TRANSFER.value,
            AgentCapability.TASK_DELEGATION.value,
        ],
        skills=["python", "web-arama", "dosya-islemleri"],
        transport="stdio",
    )
    print(f"  Agent: {kart.name} ({kart.agent_id})")
    print(f"  Yetenekler: {', '.join(kart.capabilities)}")
    print(f"  Beceriler: {', '.join(kart.skills)}")

    # ── 2. Agent Card Registry ──────────────────────────────────────────
    print("\n=== 2. Agent Card Registry (Kayit Defteri) ===")

    registry = AgentCardRegistry()
    registry.register(kart)

    # Ikinci bir agent ekle
    kart2 = AgentCard(
        agent_id="asistan-alpha",
        name="Alpha Asistan",
        capabilities=["messaging", "tool_execution"],
        skills=["hesaplama", "veri-analizi"],
    )
    registry.register(kart2)
    print(f"  Kayitli agent: {registry.count()}")
    print(f"  Tool execution yetenegi olanlar: {len(registry.list(capability='tool_execution'))}")

    # ── 3. Skill Transfer ────────────────────────────────────────────────
    print("\n=== 3. Skill Transfer (Beceri Aktarimi) ===")

    gecici_dizin = tempfile.mkdtemp()
    stp = SkillTransferProtocol(skills_dir=gecici_dizin)

    paket = stp.package_skill(
        name="web-scraper",
        content="\"\"\"Web scraping tool using requests + BeautifulSoup.\"\"\"\nimport requests\nfrom bs4 import BeautifulSoup\n\ndef scrape(url):\n    r = requests.get(url)\n    return BeautifulSoup(r.text, 'html.parser').get_text()[:1000]",
        source_agent="reymen-001",
        target_agent="asistan-alpha",
        description="Basit web kazima araci",
        category="arac",
        tags=["web", "scraping"],
    )
    print(f"  Paket olusturuldu: {paket.name} (ID: {paket.skill_id[:8]}...)")

    alinan = stp.receive_skill(paket)
    print(f"  Aktarim: {alinan['status']} -> {alinan.get('path', 'N/A')}")

    # ── 4. Task Delegation ───────────────────────────────────────────────
    print("\n=== 4. Task Delegation (Gorev Devri) ===")

    tdp = TaskDelegationProtocol()

    gorev = DelegationTask(
        source_agent="reymen-001",
        target_agent="asistan-alpha",
        title="Dosya Ozetle",
        description="Verilen dosyayi oku ve 3 cumleyle ozetle",
        context="dosya: /home/user/not.txt",
        priority=7,
    )
    print(f"  Gorev olusturuldu: {gorev.title} (ID: {gorev.task_id[:8]}...)")

    gonder = tdp.delegate(gorev)
    print(f"  Devredildi: {gonder['status']}")

    # Gorev durumunu kontrol et
    durum = tdp.task_status(gorev.task_id)
    print(f"  Durum: {durum['status']}")

    # ── 5. Ozet ─────────────────────────────────────────────────────────
    print(f"\n=== Ozet ===")
    print(f"  Agent Card: {registry.count()} kayitli")
    print(f"  Beceri: '{paket.name}' aktarildi")
    print(f"  Gorev: '{gorev.title}' -> {durum['status']}")

    import shutil
    shutil.rmtree(gecici_dizin, ignore_errors=True)

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
