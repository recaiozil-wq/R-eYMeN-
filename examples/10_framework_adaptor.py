#!/usr/bin/env python3
"""Ornek 10: Framework Adaptoru — LangGraph, CrewAI, AutoGen entegrasyonu."""

try:
    from reymen.arac.framework_adaptor import (
        FrameworkYonetici,
        LangGraphAdaptor,
        CrewAIAdaptor,
        AutoGenAdaptor,
    )

    print("=== Framework Adaptor ===")

    # Ana yonetici
    fy = FrameworkYonetici()
    durum = fy.aktif_frameworkler

    print(f"\nFramework Durumu:")
    for ad, aktif in durum.items():
        ikon = "✅" if aktif else "❌"
        print(f"  {ikon} {ad}: {'Yuklu' if aktif else 'Yuklu Degil'}")

    # ── LangGraph (opsiyonel) ────────────────────────────────────────────
    print(f"\n--- LangGraph Adaptor ---")
    lg = LangGraphAdaptor()
    if lg.aktif:
        # Basit is akisi tanimla
        def node_1(state):
            state["mesaj"] = state.get("mesaj", "") + " [Isleme alindi]"
            return state

        def node_2(state):
            state["mesaj"] = state.get("mesaj", "") + " [Tamamlandi]"
            return state

        sonuc = lg.basit_is_akisi(
            nodes=[node_1, node_2],
            inputs={"mesaj": "ReYMeN LangGraph Test"},
        )
        print(f"  Sonuc: {sonuc}")
    else:
        print(f"  ℹ️  LangGraph yuklu degil. pip install langgraph ile kurulabilir.")

    # ── CrewAI (opsiyonel) ───────────────────────────────────────────────
    print(f"\n--- CrewAI Adaptor ---")
    ca = CrewAIAdaptor()
    if ca.aktif:
        sonuc2 = ca.basit_ekip_calistir(
            agents=[
                {"rol": "Analist", "gorev": "Veriyi analiz et", "model": "gpt-4"},
                {"rol": "Yazar", "gorev": "Rapor yaz", "model": "gpt-4"},
            ],
            tasks=[
                {"aciklama": "Kullanici girdisini analiz et", "beklenen_cikti": "Analiz sonucu"},
            ],
            isim="ReYMeN Ekibi",
        )
        print(f"  Sonuc: {sonuc2}")
    else:
        print(f"  ℹ️  CrewAI yuklu degil. pip install crewai ile kurulabilir.")

    # ── AutoGen (opsiyonel) ─────────────────────────────────────────────
    print(f"\n--- AutoGen (AG2) Adaptor ---")
    ag = AutoGenAdaptor()
    if ag.aktif:
        # ReYMeN fonksiyonunu AutoGen agent'ine sar
        def reymen_yanitla(mesaj):
            return f"ReYMeN yaniti: '{mesaj}' alindi, isleniyor..."

        sarili_agent = ag.reymen_agent_sar(reymen_yanitla, agent_adi="ReYMeN")
        if sarili_agent:
            print(f"  ✅ ReYMeN agenti AutoGen'e sarildi")
    else:
        print(f"  ℹ️  AutoGen yuklu degil. pip install pyautogen ile kurulabilir.")

    print(f"\n=== Adaptor Ozeti ===")
    print(fy.ozet())

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
