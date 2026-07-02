# -*- coding: utf-8 -*-
"""🌐 A2A Transport — HTTP/WebSocket ile ağ üzerinden mesajlaşma.

A2A agent'larının farklı makineler/process'ler arasında iletişim kurmasını
sağlar. Mevcut bellek-içi Broker'i ağa taşır.

Kullanim:
    # Sunucu (Node 1)
    from reymen.a2a_transport import A2ANode
    node = A2ANode(broker, port=9100)
    node.baslat()

    # İstemci (Node 2)
    from reymen.a2a_transport import A2ARemote
    remote = A2ARemote("http://192.168.1.100:9100")
    remote.baglan()
    remote.send("agent_x", "merhaba")
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# ── HTTP Transport (FastAPI + httpx) ──────────────────────────────────────

_HTTP_SERVER = None
_HTTP_THREAD = None


def _create_app(broker):
    """FastAPI uygulamasi olustur."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse

    app = FastAPI(title="ReYMeN A2A Transport", version="1.0.0")

    @app.get("/api/a2a/health")
    async def health():
        return {"durum": "ok", "zaman": time.time()}

    @app.post("/api/a2a/send")
    async def send(data: dict):
        """Mesaj gonder.

        Body: {sender, receiver, content, type?, reply_to?, metadata?}
        """
        from reymen.a2a import Message, MessageType
        try:
            msg = Message(
                sender=data["sender"],
                receiver=data["receiver"],
                content=data["content"],
                type=MessageType(data.get("type", "text")),
                reply_to=data.get("reply_to"),
                metadata=data.get("metadata", {}),
            )
            broker.send(msg)
            return {"id": msg.id, "durum": "iletildi"}
        except KeyError as e:
            raise HTTPException(400, f"Eksik alan: {e}")
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/api/a2a/receive/{agent_id}")
    async def receive(agent_id: str, timeout: float = 1.0):
        """Agent'in inbox'ındaki ilk mesaji al (silerek)."""
        try:
            msg = broker.receive(agent_id, block=True, timeout=timeout)
            if msg is None:
                return {"durum": "bos"}
            return {
                "id": msg.id,
                "sender": msg.sender,
                "receiver": msg.receiver,
                "content": msg.content,
                "type": msg.type.value,
                "reply_to": msg.reply_to,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata,
            }
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/api/a2a/peek/{agent_id}")
    async def peek(agent_id: str):
        """Inbox'a silmeden bak."""
        try:
            msg = broker.peek(agent_id)
            if msg is None:
                return {"durum": "bos"}
            return {
                "id": msg.id,
                "sender": msg.sender,
                "content": msg.content[:200] if msg.content else "",
                "type": msg.type.value,
            }
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/api/a2a/inbox_size/{agent_id}")
    async def inbox_size(agent_id: str):
        try:
            return {"agent_id": agent_id, "size": broker.inbox_size(agent_id)}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/api/a2a/stats")
    async def stats():
        return broker.stats()

    @app.post("/api/a2a/register")
    async def register(data: dict):
        """Uzak agent kaydet."""
        try:
            broker.register(data["agent_id"])
            return {"durum": "kaydedildi", "agent_id": data["agent_id"]}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post("/api/a2a/unregister")
    async def unregister(data: dict):
        try:
            broker.unregister(data["agent_id"])
            return {"durum": "silindi", "agent_id": data["agent_id"]}
        except Exception as e:
            raise HTTPException(500, str(e))

    # ── WebSocket endpoint ──
    @app.websocket("/ws/a2a/{agent_id}")
    async def websocket_endpoint(websocket, agent_id: str):
        from reymen.a2a import MessageType
        await websocket.accept()
        try:
            broker.register(agent_id)
            logger.info("[A2A-WS] %s baglandi", agent_id)

            async def _dinle():
                """Gelen WS mesajlarini broker'a ilet."""
                while True:
                    try:
                        data = await websocket.receive_json()
                        from reymen.a2a import Message
                        msg = Message(
                            sender=data.get("sender", agent_id),
                            receiver=data["receiver"],
                            content=data["content"],
                            type=MessageType(data.get("type", "text")),
                            reply_to=data.get("reply_to"),
                            metadata=data.get("metadata", {}),
                        )
                        broker.send(msg)
                    except Exception:
                        break

            async def _gonder():
                """Broker'dan gelen mesajlari WS'ye ilet."""
                while True:
                    msg = broker.receive(agent_id, block=True, timeout=1.0)
                    if msg:
                        await websocket.send_json(msg.as_dict())

            await asyncio.gather(_dinle(), _gonder())
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        finally:
            broker.unregister(agent_id)
            logger.info("[A2A-WS] %s ayrildi", agent_id)

    return app


class A2ANode:
    """A2A ag sunucusu — Broker'i HTTP/WS uzerinden yayinlar.

    Ornek:
        node = A2ANode(broker, port=9100)
        node.baslat()
    """

    def __init__(self, broker, port: int = 9100, host: str = "0.0.0.0"):
        self.broker = broker
        self.port = port
        self.host = host
        self._app = _create_app(broker)
        self._thread: threading.Thread | None = None
        self._calisiyor = False

    def baslat(self, background: bool = True) -> str:
        """Sunucuyu baslat.

        Args:
            background: True ise ayri thread'de baslat.

        Returns:
            Durum mesaji.
        """
        import uvicorn
        if background:
            self._thread = threading.Thread(
                target=lambda: uvicorn.run(
                    self._app,
                    host=self.host,
                    port=self.port,
                    log_level="error",
                ),
                daemon=True,
            )
            self._thread.start()
            self._calisiyor = True
            return f"[A2A] Node baslatildi: http://{self.host}:{self.port}"
        else:
            uvicorn.run(self._app, host=self.host, port=self.port, log_level="error")
            return "[A2A] Node durdu."

    def durdur(self) -> str:
        """Sunucuyu durdur."""
        self._calisiyor = False
        if self._thread and self._thread.is_alive():
            import os
            os._exit(0)
        return "[A2A] Node durduruldu."

    def durum(self) -> str:
        """Sunucu durumu."""
        if self._thread and self._thread.is_alive():
            return f"  A2A Node: AKTIF (http://{self.host}:{self.port})"
        return "  A2A Node: PASIF"


class A2ARemote:
    """Uzak bir A2A node'una HTTP ile baglanan istemci.

    Ornek:
        remote = A2ARemote("http://192.168.1.100:9100")
        remote.send("agent_x", "selam")
        msgs = remote.receive("agent_y")
    """

    def __init__(self, base_url: str, local_agent_id: str = "remote"):
        self.base_url = base_url.rstrip("/")
        self.local_agent_id = local_agent_id
        self._session = None

    def _get_session(self):
        if self._session is None:
            import httpx
            self._session = httpx.Client(timeout=10.0)
        return self._session

    def baglan(self) -> str:
        """Uzak node'a baglan (health check + register)."""
        try:
            s = self._get_session()
            r = s.get(f"{self.base_url}/api/a2a/health", timeout=5)
            r.raise_for_status()
            # Kendini kaydettir
            s.post(f"{self.base_url}/api/a2a/register",
                   json={"agent_id": self.local_agent_id})
            return f"[A2A] Baglanti basarili: {self.base_url}"
        except Exception as e:
            return f"[A2A] Baglanti hatasi: {e}"

    def send(self, receiver: str, content: str, msg_type: str = "text",
             reply_to: str | None = None) -> str:
        """Uzak node uzerinden mesaj gonder."""
        try:
            s = self._get_session()
            r = s.post(f"{self.base_url}/api/a2a/send", json={
                "sender": self.local_agent_id,
                "receiver": receiver,
                "content": content,
                "type": msg_type,
                "reply_to": reply_to,
            })
            r.raise_for_status()
            data = r.json()
            return f"[A2A] Gonderildi: id={data.get('id', '?')}"
        except Exception as e:
            return f"[A2A] Gonderme hatasi: {e}"

    def receive(self, agent_id: str | None = None,
                timeout: float = 1.0) -> dict | None:
        """Uzak node'dan mesaj al."""
        aid = agent_id or self.local_agent_id
        try:
            s = self._get_session()
            r = s.get(
                f"{self.base_url}/api/a2a/receive/{aid}",
                params={"timeout": timeout},
                timeout=timeout + 2,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("durum") == "bos":
                return None
            return data
        except Exception:
            return None

    def inbox_size(self, agent_id: str | None = None) -> int:
        aid = agent_id or self.local_agent_id
        try:
            s = self._get_session()
            r = s.get(f"{self.base_url}/api/a2a/inbox_size/{aid}")
            return r.json().get("size", 0)
        except Exception:
            return -1

    def kapat(self):
        if self._session:
            self._session.close()
            self._session = None


# ── NetworkBroker — Hibrit: yerel + uzak ─────────────────────────────────

class NetworkBroker:
    """Yerel Broker + uzak node'lara yonlendirme yapabilen hibrit broker.

    Yerel agent'lar direkt broker'a gider. Uzak agent'lar icin
    A2ARemote uzerinden HTTP cagrisi yapilir.

    Ornek:
        nb = NetworkBroker()
        nb.uzak_ekle("node1", A2ARemote("http://192.168.1.100:9100"))
        nb.send("agent_x", "merhaba")  # otomatik yonlendirir
    """

    def __init__(self, broker=None):
        from reymen.a2a import Broker
        self.broker = broker or Broker()
        self._uzaklar: dict[str, A2ARemote] = {}
        self._agent_uzak: dict[str, str] = {}  # agent_id -> node_adi

    def uzak_ekle(self, node_adi: str, remote: A2ARemote) -> str:
        """Uzak bir node ekle."""
        self._uzaklar[node_adi] = remote
        return f"[A2A] Uzak node eklendi: {node_adi} -> {remote.base_url}"

    def uzak_cikar(self, node_adi: str) -> str:
        self._uzaklar.pop(node_adi, None)
        # Bu node'a ait agent kayitlarini temizle
        self._agent_uzak = {k: v for k, v in self._agent_uzak.items()
                            if v != node_adi}
        return f"[A2A] Uzak node cikarildi: {node_adi}"

    def register(self, agent_id: str, node_adi: str | None = None) -> None:
        """Agent kaydet. node_adi verilirse uzak olarak isaretlenir."""
        if node_adi:
            self._agent_uzak[agent_id] = node_adi
        else:
            self.broker.register(agent_id)

    def unregister(self, agent_id: str) -> None:
        self._agent_uzak.pop(agent_id, None)
        try:
            self.broker.unregister(agent_id)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

    def send(self, message) -> None:
        """Mesaj gonder — otomatik yerel/uzak yonlendirme."""
        from reymen.a2a import Message
        receiver = message.receiver

        # Uzak mi?
        node_adi = self._agent_uzak.get(receiver)
        if node_adi and node_adi in self._uzaklar:
            remote = self._uzaklar[node_adi]
            remote.send(receiver, message.content,
                        msg_type=message.type.value,
                        reply_to=message.reply_to)
            return

        # Yerel
        self.broker.send(message)

    def receive(self, agent_id: str, **kw):
        return self.broker.receive(agent_id, **kw)

    def stats(self) -> dict:
        s = self.broker.stats()
        s["remote_nodes"] = len(self._uzaklar)
        s["remote_agents"] = len(self._agent_uzak)
        return s

    def message_log(self):
        return self.broker.message_log()


# ── Motor Entegrasyonu ───────────────────────────────────────────────────

_A2A_NODE = None
_A2A_MOTOR = None


def motor_kaydet(motor) -> None:
    """Motor'a A2A Transport araclarini kaydet."""
    global _A2A_MOTOR
    _A2A_MOTOR = motor
    motor._plugin_arac_kaydet(
        "A2A_NODE_BASLAT", _node_baslat,
        "A2A HTTP/WS sunucusunu baslat. Parametreler: port=9100 host=0.0.0.0"
    )
    motor._plugin_arac_kaydet(
        "A2A_NODE_DURUM", _node_durum,
        "A2A sunucu durumunu goster."
    )
    motor._plugin_arac_kaydet(
        "A2A_NODE_DURDUR", _node_durdur,
        "A2A sunucuyu durdur."
    )
    motor._plugin_arac_kaydet(
        "A2A_UZAK_BAGLAN", _uzak_baglan,
        "Uzak bir A2A node'una baglan. Parametreler: url, agent_id"
    )
    motor._plugin_arac_kaydet(
        "A2A_UZAK_GONDER", _uzak_gonder,
        "Uzak node uzerinden mesaj gonder. Parametreler: receiver, content, type?"
    )
    motor._plugin_arac_kaydet(
        "A2A_UZAK_AL", _uzak_al,
        "Uzak node'dan mesaj al. Parametre: timeout=1.0"
    )
    logger.info("[A2A-TRANSPORT] Motor'a 6 arac kaydedildi")


def _node_baslat(**kw) -> str:
    """A2A HTTP/WS sunucusunu baslat."""
    global _A2A_NODE
    if _A2A_NODE and _A2A_NODE._calisiyor:
        return _node_durum(**kw) + " (zaten calisiyor)"

    from reymen.a2a import Broker
    port = int(kw.get("args", [9100])[0]) if kw.get("args") else 9100
    broker = Broker()
    _A2A_NODE = A2ANode(broker, port=port)
    return _A2A_NODE.baslat()


def _node_durum(**kw) -> str:
    """A2A sunucu durumu."""
    if _A2A_NODE:
        return _A2A_NODE.durum()
    return "  A2A Node: PASIF"


def _node_durdur(**kw) -> str:
    """A2A sunucuyu durdur."""
    global _A2A_NODE
    if _A2A_NODE:
        s = _A2A_NODE.durdur()
        _A2A_NODE = None
        return s
    return "[A2A] Node zaten kapali"


_UZAKLAR: dict[str, A2ARemote] = {}


def _uzak_baglan(**kw) -> str:
    """Uzak A2A node'una baglan."""
    args = kw.get("args", [])
    if len(args) < 1:
        return "[A2A] Kullanim: A2A_UZAK_BAGLAN <url> [agent_id]"
    url = args[0]
    agent_id = args[1] if len(args) > 1 else "remote"
    remote = A2ARemote(url, agent_id)
    sonuc = remote.baglan()
    key = f"{url}/{agent_id}"
    _UZAKLAR[key] = remote
    return sonuc


def _uzak_gonder(**kw) -> str:
    """Uzak node'a mesaj gonder."""
    args = kw.get("args", [])
    if len(args) < 2:
        return "[A2A] Kullanim: A2A_UZAK_GONDER <receiver> <content> [msg_type]"
    if not _UZAKLAR:
        return "[A2A] Bagli uzak node yok. Once A2A_UZAK_BAGLAN"
    receiver, content = args[0], args[1]
    msg_type = args[2] if len(args) > 2 else "text"
    sonuclar = []
    for key, remote in _UZAKLAR.items():
        s = remote.send(receiver, content, msg_type)
        sonuclar.append(f"  {key}: {s}")
    return "\n".join(sonuclar)


def _uzak_al(**kw) -> str:
    """Uzak node'dan mesaj al."""
    args = kw.get("args", [])
    timeout = float(args[0]) if args else 1.0
    if not _UZAKLAR:
        return "[A2A] Bagli uzak node yok"
    for key, remote in _UZAKLAR.items():
        msg = remote.receive(timeout=timeout)
        if msg:
            return f"[A2A] {key}'den mesaj:\n  {json.dumps(msg, ensure_ascii=False)[:500]}"
    return "[A2A] Bekleyen mesaj yok"
