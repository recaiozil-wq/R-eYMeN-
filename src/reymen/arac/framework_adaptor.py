# -*- coding: utf-8 -*-
"""
framework_adaptor.py — Harici AI Framework Adaptörleri.

LangGraph, CrewAI ve AutoGen (AG2) framework'lerini ReYMeN'e entegre eder.
Her framework opsiyoneldir (try/except ile yüklenir, bağımlılık yoksa sessiz geç).

Kullanim:
    from reymen.arac.framework_adaptor import framework_adaptor
    sonuc = framework_adaptor.langgraph_calistir(graph, inputs)
    sonuc = framework_adaptor.crewai_calistir(crew)
    sonuc = framework_adaptor.autogen_calistir(agent, message)
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable, Union

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# LangGraph Adaptörü
# ══════════════════════════════════════════════════════════════════════

try:
    from langgraph.graph import StateGraph, StateGraph as LangGraphStateGraph, END
    from langgraph.checkpoint import MemorySaver
    from typing import TypedDict, Annotated
    import langgraph as _lg
    _LANGGRAPH_MEVCUT = True
    logger.debug("[Framework] LangGraph %s yuklu", getattr(_lg, "__version__", "?"))
except ImportError:
    StateGraph = None
    END = None
    MemorySaver = None
    _LANGGRAPH_MEVCUT = False


class LangGraphAdaptor:
    """LangGraph StateGraph calistirma adaptoru.

    Kullanim:
        adaptor = LangGraphAdaptor()
        # Var olan bir StateGraph'i calistir
        sonuc = adaptor.calistir(graph, inputs={"messages": []})
        # Basit bir graph olustur + calistir
        sonuc = adaptor.basit_is_akisi(
            nodes=[islev1, islev2],
            inputs={"messages": []}
        )
    """

    def __init__(self):
        self._mevcut = _LANGGRAPH_MEVCUT

    @property
    def aktif(self) -> bool:
        return self._mevcut

    def calistir(
        self,
        graph: Any,
        inputs: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Var olan bir StateGraph'i calistir.

        Args:
            graph: LangGraph StateGraph nesnesi
            inputs: Graph girdileri (varsayilan: {"messages": []})
            config: Calistirma yapilandirmasi

        Returns:
            dict: Graph sonucu
        """
        if not self._mevcut:
            return {"hata": "LangGraph yuklu degil", "sonuc": None}

        try:
            _inputs = inputs or {"messages": []}
            _config = config or {"recursion_limit": 25}
            sonuc = graph.invoke(_inputs, _config)
            return {"sonuc": sonuc, "hata": None}
        except Exception as e:
            logger.error("[LangGraph] Calistirma hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def basit_is_akisi(
        self,
        nodes: List[Callable],
        inputs: Optional[Dict[str, Any]] = None,
        state_type: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Basit bir StateGraph olusturup calistirir.

        Her node bir oncekinin ciktisini alir.
        Son node'dan END'e gider.

        Args:
            nodes: Sirali calistirilacak fonksiyon listesi
            inputs: Baslangic girdileri
            state_type: Opsiyonel state tipi (TypedDict)

        Returns:
            dict: Graph sonucu
        """
        if not self._mevcut:
            return {"hata": "LangGraph yuklu degil", "sonuc": None}

        try:
            if state_type is None:
                # Dinamik state tipi olustur
                state_type = type("WorkflowState", (dict,), {})

            graph = StateGraph(state_type)

            # Node'lari ekle
            for i, node_fn in enumerate(nodes):
                node_name = getattr(node_fn, "__name__", f"node_{i}")
                graph.add_node(node_name, node_fn)

            # Kenarlari bagla (zincir)
            node_names = [
                getattr(fn, "__name__", f"node_{i}")
                for i, fn in enumerate(nodes)
            ]
            for i in range(len(node_names) - 1):
                graph.add_edge(node_names[i], node_names[i + 1])

            # Son node'dan END'e
            if node_names:
                graph.add_edge(node_names[-1], END)
                graph.set_entry_point(node_names[0])

            _app = graph.compile()
            sonuc = _app.invoke(inputs or {"messages": []})
            return {"sonuc": sonuc, "hata": None}
        except Exception as e:
            logger.error("[LangGraph] Is akisi hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def kullanilabilir_mi(self) -> bool:
        """LangGraph kullanilabilir mi kontrol et."""
        return self._mevcut


# ══════════════════════════════════════════════════════════════════════
# CrewAI Adaptörü
# ══════════════════════════════════════════════════════════════════════

try:
    from crewai import Crew, Agent, Task, Process
    import crewai as _ca
    _CREWAI_MEVCUT = True
    logger.debug("[Framework] CrewAI %s yuklu", getattr(_ca, "__version__", "?"))
except ImportError:
    Crew = None
    Agent = None
    Task = None
    Process = None
    _CREWAI_MEVCUT = False


class CrewAIAdaptor:
    """CrewAI Crew/Agent/Task calistirma adaptoru.

    Kullanim:
        adaptor = CrewAIAdaptor()
        # Var olan bir Crew'i calistir
        sonuc = adaptor.crew_calistir(crew)
        # Agent+Task olustur + calistir
        sonuc = adaptor.basit_ekip_calistir(
            agents=[agent1, agent2],
            tasks=[task1],
            isim="Analiz Ekibi"
        )
    """

    def __init__(self):
        self._mevcut = _CREWAI_MEVCUT

    @property
    def aktif(self) -> bool:
        return self._mevcut

    def crew_calistir(
        self,
        crew: Any,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Var olan bir Crew'i calistir.

        Args:
            crew: CrewAI Crew nesnesi
            inputs: Crew girdileri

        Returns:
            dict: Crew calistirma sonucu
        """
        if not self._mevcut:
            return {"hata": "CrewAI yuklu degil", "sonuc": None}

        try:
            sonuc = crew.kickoff(inputs=inputs)
            return {"sonuc": str(sonuc) if sonuc else "", "hata": None}
        except Exception as e:
            logger.error("[CrewAI] Calistirma hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def basit_ekip_calistir(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        isim: str = "ReYMeN Crew",
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Agent ve Task dict'lerinden Crew olusturup calistirir.

        Args:
            agents: Agent yapilandirma dict'leri
                [{"rol": "...", "gorev": "...", "model": "..."}]
            tasks: Task yapilandirma dict'leri
                [{"aciklama": "...", "beklenen_cikti": "...", "agent": agent_ref}]
            isim: Crew ismi
            verbose: Detayli log

        Returns:
            dict: Crew sonucu
        """
        if not self._mevcut:
            return {"hata": "CrewAI yuklu degil", "sonuc": None}

        try:
            from crewai import Crew, Agent, Task

            # Agent'lari olustur
            crew_agents = []
            for a in agents:
                agent = Agent(
                    role=a.get("rol", "Asistan"),
                    goal=a.get("gorev", "Gorevi tamamla"),
                    backstory=a.get("gecmis", ""),
                    llm=a.get("model"),
                    verbose=verbose,
                    allow_delegation=a.get("yetki_devri", False),
                )
                crew_agents.append(agent)

            # Task'lari olustur
            crew_tasks = []
            for t in tasks:
                task = Task(
                    description=t.get("aciklama", ""),
                    expected_output=t.get("beklenen_cikti", ""),
                    agent=t.get("agent"),  # Agent objesi veya None
                )
                crew_tasks.append(task)

            crew = Crew(
                agents=crew_agents,
                tasks=crew_tasks,
                verbose=verbose,
                process=Process.sequential,
            )

            sonuc = crew.kickoff()
            return {"sonuc": str(sonuc) if sonuc else "", "hata": None}
        except Exception as e:
            logger.error("[CrewAI] Ekip calistirma hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def kullanilabilir_mi(self) -> bool:
        """CrewAI kullanilabilir mi kontrol et."""
        return self._mevcut


# ══════════════════════════════════════════════════════════════════════
# AutoGen (AG2) Adaptörü
# ══════════════════════════════════════════════════════════════════════

try:
    import autogen as _ag
    _AUTOGEN_MEVCUT = True
    logger.debug("[Framework] AutoGen %s yuklu", getattr(_ag, "__version__", "?"))
except ImportError:
    _AUTOGEN_MEVCUT = False


class AutoGenAdaptor:
    """AutoGen (AG2) agent wrapper adaptoru.

    ReYMeN agent'larini AutoGen ortaminda calistirilabilir hale getirir.

    Kullanim:
        adaptor = AutoGenAdaptor()
        # Var olan bir AutoGen agent'i calistir
        sonuc = adaptor.agent_calistir(agent, "merhaba")
        # ReYMeN agent'ini AutoGen agent'ine sar
        reymen_agent = adaptor.reymen_agent_sar(fonksiyon)
        sonuc = adaptor.agent_calistir(reymen_agent, "gorev")
    """

    def __init__(self):
        self._mevcut = _AUTOGEN_MEVCUT

    @property
    def aktif(self) -> bool:
        return self._mevcut

    def agent_calistir(
        self,
        agent: Any,
        mesaj: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        clear_history: bool = True,
    ) -> Dict[str, Any]:
        """AutoGen agent'ini mesajla calistir.

        Args:
            agent: AutoGen ConversableAgent (veya wrapper)
            mesaj: Gonderilecek mesaj (str, dict, veya mesaj listesi)
            clear_history: Islem oncesi gecmisi temizle

        Returns:
            dict: Agent yaniti
        """
        if not self._mevcut:
            return {"hata": "AutoGen yuklu degil", "sonuc": None}

        try:
            from autogen import ConversableAgent

            if isinstance(mesaj, str):
                _mesaj = mesaj
            elif isinstance(mesaj, dict):
                _mesaj = mesaj
            elif isinstance(mesaj, list):
                _mesaj = mesaj
            else:
                _mesaj = str(mesaj)

            # UserProxyAgent olustur (yardimci)
            user = ConversableAgent(
                name="Kullanici",
                llm_config=False,
                human_input_mode="NEVER",
            )

            # Agent'i calistir
            sonuc = user.initiate_chat(
                agent,
                message=_mesaj,
                clear_history=clear_history,
            )

            # Son yaniti bul
            yanit = ""
            if hasattr(sonuc, "chat_history") and sonuc.chat_history:
                for msg in reversed(sonuc.chat_history):
                    if msg.get("role") == "assistant":
                        yanit = msg.get("content", "")
                        break

            return {"sonuc": yanit, "hata": None, "gecmis": sonuc}
        except Exception as e:
            logger.error("[AutoGen] Agent calistirma hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def reymen_agent_sar(
        self,
        fonksiyon: Callable,
        agent_adi: str = "ReYMeN",
        system_message: Optional[str] = None,
    ) -> Any:
        """ReYMeN fonksiyonunu AutoGen ConversableAgent'e sarar.

        Bu sayede ReYMeN yetenekleri AutoGen ortaminda
        diger agent'larla konusabilir.

        Args:
            fonksiyon: ReYMeN agent fonksiyonu (mesaj -> yanit)
            agent_adi: AutoGen'de gorunecek isim
            system_message: Opsiyonel sistem mesaji

        Returns:
            ConversableAgent: AutoGen uyumlu agent wrapper
        """
        if not self._mevcut:
            return None

        try:
            from autogen import ConversableAgent

            agent = ConversableAgent(
                name=agent_adi,
                system_message=system_message or "ReYMeN AI Agent yardimcisi.",
                llm_config=False,  # Harici LLM kullanmayacak
                human_input_mode="NEVER",
                code_execution_config=False,
            )

            # register_reply ile ReYMeN fonksiyonunu bagla
            def _reyimen_reply(receiver, messages, sender, config):
                """ReYMeN fonksiyonunu AutoGen reply handler olarak sar."""
                if not messages:
                    return False, None
                son_mesaj = messages[-1].get("content", "") if isinstance(
                    messages[-1], dict) else str(messages[-1])
                try:
                    yanit = fonksiyon(son_mesaj)
                    return True, {"content": str(yanit), "role": "assistant"}
                except Exception as e:
                    return True, {"content": f"[ReYMeN Hata] {e}", "role": "assistant"}

            agent.register_reply(
                trigger=lambda sender: True,
                reply_func=_reyimen_reply,
                position=0,
                config={},
            )

            return agent
        except Exception as e:
            logger.error("[AutoGen] Agent sarma hatasi: %s", e)
            return None

    def iki_agent_konusma(
        self,
        agent1: Any,
        agent2: Any,
        mesaj: str,
        max_tur: int = 5,
    ) -> Dict[str, Any]:
        """Iki AutoGen agent'i arasinda konusma baslat.

        Args:
            agent1: Birinci agent (genelde Kullanici)
            agent2: Ikinci agent (genelde Asistan)
            mesaj: Baslangic mesaji
            max_tur: Maksimum konusma turu

        Returns:
            dict: Konusma sonucu
        """
        if not self._mevcut:
            return {"hata": "AutoGen yuklu degil", "sonuc": None}

        try:
            sonuc = agent1.initiate_chat(
                agent2,
                message=mesaj,
                max_turns=max_tur,
                clear_history=True,
            )
            return {"sonuc": sonuc, "hata": None}
        except Exception as e:
            logger.error("[AutoGen] Iki agent konusma hatasi: %s", e)
            return {"hata": str(e), "sonuc": None}

    def kullanilabilir_mi(self) -> bool:
        """AutoGen kullanilabilir mi kontrol et."""
        return self._mevcut


# ══════════════════════════════════════════════════════════════════════
# Framework Yoneticisi (Ana Adaptor)
# ══════════════════════════════════════════════════════════════════════

class FrameworkYonetici:
    """Tum framework adaptörlerini birlesik arayuzde yonetir.

    conversation_loop.py'ye entegrasyon icin tek nokta.

    Kullanim:
        fy = FrameworkYonetici()
        fy.aktif_frameworkler  -> {"langgraph": True, "crewai": False, "autogen": True}
        fy.langgraph_calistir(graph, inputs)
        fy.crewai_calistir(crew)
        fy.autogen_calistir(agent, mesaj)
    """

    def __init__(self):
        self.langgraph = LangGraphAdaptor()
        self.crewai = CrewAIAdaptor()
        self.autogen = AutoGenAdaptor()

    @property
    def aktif_frameworkler(self) -> Dict[str, bool]:
        """Kullanilabilir framework'lerin durumu."""
        return {
            "langgraph": self.langgraph.aktif,
            "crewai": self.crewai.aktif,
            "autogen": self.autogen.aktif,
        }

    @property
    def aktif(self) -> bool:
        """En az bir framework kullanilabilir mi?"""
        return any(self.aktif_frameworkler.values())

    def langgraph_calistir(
        self,
        graph: Any,
        inputs: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """LangGraph StateGraph calistir."""
        return self.langgraph.calistir(graph, inputs, config)

    def crewai_calistir(
        self,
        crew: Any,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """CrewAI Crew calistir."""
        return self.crewai.crew_calistir(crew, inputs)

    def autogen_agent_calistir(
        self,
        agent: Any,
        mesaj: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """AutoGen agent calistir."""
        return self.autogen.agent_calistir(agent, mesaj)

    def reymen_agentini_autogen_sar(
        self,
        fonksiyon: Callable,
        agent_adi: str = "ReYMeN",
    ) -> Any:
        """ReYMeN fonksiyonunu AutoGen agent'ine sar."""
        return self.autogen.reymen_agent_sar(fonksiyon, agent_adi)

    def ozet(self) -> str:
        """Framework durum ozeti."""
        durum = self.aktif_frameworkler
        aktif_liste = [ad for ad, aktif in durum.items() if aktif]
        pasif_liste = [ad for ad, aktif in durum.items() if not aktif]
        satirlar = [
            "=== Framework Adaptor Durumu ===",
            f"Aktif ({len(aktif_liste)}): {', '.join(aktif_liste) if aktif_liste else 'YOK'}",
            f"Pasif ({len(pasif_liste)}): {', '.join(pasif_liste) if pasif_liste else 'YOK'}",
        ]
        return "\n".join(satirlar)

    def __repr__(self) -> str:
        return f"<FrameworkYonetici aktif={self.aktif} {self.aktif_frameworkler}>"


# ── Singleton (Tekil Nesne) ─────────────────────────────────────────────
framework_adaptor = FrameworkYonetici()

# ── Kolay kullanim icin fonksiyonlar ────────────────────────────────────


def langgraph_calistir(
    graph: Any,
    inputs: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """LangGraph StateGraph calistir (kolay fonksiyon)."""
    return framework_adaptor.langgraph_calistir(graph, inputs, config)


def crewai_calistir(
    crew: Any,
    inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """CrewAI Crew calistir (kolay fonksiyon)."""
    return framework_adaptor.crewai_calistir(crew, inputs)


def autogen_agent_calistir(
    agent: Any,
    mesaj: Union[str, Dict[str, Any], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """AutoGen agent calistir (kolay fonksiyon)."""
    return framework_adaptor.autogen_agent_calistir(agent, mesaj)


def framework_adaptor_durum() -> Dict[str, bool]:
    """Tum framework adaptorlerinin durumunu don."""
    return framework_adaptor.aktif_frameworkler


__all__ = [
    "FrameworkYonetici",
    "framework_adaptor",
    "LangGraphAdaptor",
    "CrewAIAdaptor",
    "AutoGenAdaptor",
    "langgraph_calistir",
    "crewai_calistir",
    "autogen_agent_calistir",
    "framework_adaptor_durum",
]
