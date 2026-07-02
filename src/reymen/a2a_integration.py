"""A2A entegrasyonu — motor + conversation_loop için bağlantı.

Bu modül, a2a.py'deki altyapıyı kullanarak ReYMeN motoruna
A2A mesajlaşma araçlarını ekler.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Global broker singleton ────────────────────────────────────────────────

_A2A_BROKER = None
_A2A_AGENT = None

def _get_broker():
    """Global A2A Broker singleton'ını döndür."""
    global _A2A_BROKER
    if _A2A_BROKER is None:
        from reymen.a2a import Broker
        _A2A_BROKER = Broker()
    return _A2A_BROKER


def _get_agent():
    """Global ReYMeN A2A Agent singleton'ını döndür."""
    global _A2A_AGENT
    if _A2A_AGENT is None:
        from reymen.a2a import Agent
        _A2A_AGENT = Agent("reymen", _get_broker())
    return _A2A_AGENT


# ── Tool fonksiyonları (motor._plugin_arac_kaydet ile kaydedilir) ──────────

def a2a_gonder(receiver: str, content: str, msg_type: str = "text") -> str:
    """A2A mesajı gönder.

    Args:
        receiver: Hedef agent ID.
        content: Mesaj içeriği.
        msg_type: Mesaj tipi (text/task/query/result/error/broadcast).

    Returns:
        Gönderilen mesaj ID'si.
    """
    from reymen.a2a import MessageType
    try:
        tip = MessageType(msg_type)
    except ValueError:
        tip = MessageType.TEXT
    agent = _get_agent()
    msg = agent.send(receiver, content, msg_type=tip)
    return f"[A2A] Mesaj gonderildi: id={msg.id}, receiver={receiver}, tip={tip.value}"


def a2a_al(timeout: float = 1.0) -> str:
    """Gelen A2A mesajlarını kontrol et.

    Args:
        timeout: Maksimum bekleme süresi (saniye).

    Returns:
        Mesaj varsa içeriği, yoksa "[A2A] Bekleyen mesaj yok".
    """
    agent = _get_agent()
    msg = agent.receive(timeout=timeout)
    if msg is None:
        return "[A2A] Bekleyen mesaj yok"
    return (
        f"[A2A] Mesaj alindi:\n"
        f"  id: {msg.id}\n"
        f"  sender: {msg.sender}\n"
        f"  tip: {msg.type.value}\n"
        f"  icerik: {msg.content}"
    )


def a2a_agent_kaydet(agent_id: str) -> str:
    """Yeni bir A2A agent'ı kaydet.

    Args:
        agent_id: Kaydedilecek agent ID'si.

    Returns:
        İşlem sonucu.
    """
    broker = _get_broker()
    if broker.is_registered(agent_id):
        return f"[A2A] '{agent_id}' zaten kayitli"
    broker.register(agent_id)
    return f"[A2A] '{agent_id}' kaydedildi"


def a2a_durum() -> str:
    """A2A broker durumunu göster.

    Returns:
        Broker istatistikleri metni.
    """
    broker = _get_broker()
    stats = broker.stats()
    return (
        f"[A2A] Broker durumu:\n"
        f"  kayitli agent: {stats['agents']}\n"
        f"  toplam mesaj: {stats['total_messages']}\n"
        f"  bekleyen mesaj: {json.dumps(stats['pending'], ensure_ascii=False)}"
    )


def a2a_agent_listele() -> str:
    """Kayıtlı tüm A2A agent'larını listele.

    Returns:
        Agent listesi.
    """
    broker = _get_broker()
    stats = broker.stats()
    if stats['agents'] == 0:
        return "[A2A] Kayitli agent yok"
    liste = [f"[A2A] Kayitli agent'lar ({stats['agents']}):"]
    for aid, pending in stats['pending'].items():
        liste.append(f"  - {aid} ({pending} bekleyen)")
    return "\n".join(liste)


# ── Motor kayıt ────────────────────────────────────────────────────────────

def motor_kaydet(motor: Any) -> None:
    """Motor'a A2A araçlarını kaydet.

    Args:
        motor: Motor instance'ı (self).
    """
    import json as _json
    # _a2a_durum içinde json kullanılıyor — global'e yaz
    global json
    json = _json

    motor._plugin_arac_kaydet(
        "A2A_GONDER", a2a_gonder,
        "A2A mesaji gonder. Parametreler: receiver (str), content (str), msg_type (str: text/task/query/result)",
    )
    motor._plugin_arac_kaydet(
        "A2A_AL", a2a_al,
        "A2A mesaji al. Parametre: timeout (float, varsayilan 1.0)",
    )
    motor._plugin_arac_kaydet(
        "A2A_AGENT_KAYDET", a2a_agent_kaydet,
        "A2A agent'i kaydet. Parametre: agent_id (str)",
    )
    motor._plugin_arac_kaydet(
        "A2A_DURUM", a2a_durum,
        "A2A broker durumunu goster",
    )
    motor._plugin_arac_kaydet(
        "A2A_AGENT_LISTELE", a2a_agent_listele,
        "Kayitli A2A agent'larini listele",
    )
    logger.info("[A2A] Motor'a 5 arac kaydedildi")


# ── Conversation loop entegrasyonu ─────────────────────────────────────────

class A2ABridge:
    """conversation_loop içinde A2A mesajlaşma köprüsü.

    Kullanım::

        bridge = A2ABridge(broker)
        bridge.agent_kaydet("kullanici_123")
        bridge.mesaj_isle(hedef, yanit)
    """

    def __init__(self, broker=None):
        from reymen.a2a import Agent
        self.broker = broker or _get_broker()
        self.agent = Agent("reymen_loop", self.broker)

    def agent_kaydet(self, agent_id: str) -> None:
        """Bir agent'ı kaydet (yoksa)."""
        if not self.broker.is_registered(agent_id):
            self.broker.register(agent_id)

    def mesaj_gonder(self, receiver: str, content: str, msg_type: str = "text") -> str:
        """Agent'a mesaj gönder."""
        from reymen.a2a import MessageType
        try:
            tip = MessageType(msg_type)
        except ValueError:
            tip = MessageType.TEXT
        msg = self.agent.send(receiver, content, msg_type=tip)
        return f"[A2A] Gonderildi: {msg.id} -> {receiver}"

    def mesaj_kontrol(self, timeout: float = 0.1) -> str | None:
        """Gelen mesaj var mı kontrol et. Varsa içeriğini döndür."""
        msg = self.agent.receive(timeout=timeout)
        if msg is None:
            return None
        return msg.content

    def kapat(self) -> None:
        """Agent kaydını temizle."""
        self.agent.close()
