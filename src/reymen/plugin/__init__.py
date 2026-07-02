# -*- coding: utf-8 -*-
"""reymen.plugin — Plugin sistemi (lifecycle hooks).

PluginBase:
    Tüm plugin'lerin türetmesi gereken temel sınıf.
    İsteğe bağlı hook metodları:

        on_load()                     — plugin yüklendiğinde
        on_unload()                   — plugin kaldırıldığında
        on_session_start(session_id, user_id) — session başında
        on_session_end(session_id, reason)    — session sonunda
        on_message(message, context)          — kullanıcı mesajı geldiğinde
        pre_llm_call(messages, context)       — LLM çağrısı öncesi mesajları değiştir
        post_llm_call(response, context)      — LLM yanıtı geldikten sonra işle
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PluginBase:
    """Tüm ReYMeN plugin'leri bu sınıftan türetilmelidir.

    Özellikler:
        name (str):    Plugin adı (zorunlu).
        version (str): Plugin versiyonu (zorunlu).

    Tüm hook metodları *opsiyoneldir* — PluginBase varsayılan no-op
    implementasyon sağlar, alt sınıf sadece ihtiyacı olanları override eder.
    """

    name: str = "unnamed"
    version: str = "0.0.1"

    # ── Lifecycle ──────────────────────────────────────────────────────

    def on_load(self) -> None:
        """Plugin yüklendiğinde bir kere çağrılır."""
        pass

    def on_unload(self) -> None:
        """Plugin kaldırıldığında bir kere çağrılır."""
        pass

    # ── Session hooks ──────────────────────────────────────────────────

    def on_session_start(self, session_id: str, user_id: str) -> None:
        """Yeni bir konuşma oturumu başladığında çağrılır."""
        pass

    def on_session_end(self, session_id: str, reason: str) -> None:
        """Konuşma oturumu sonlandığında çağrılır.

        Args:
            session_id: Oturum kimliği.
            reason:     Sonlanma sebebi (örn. "completed", "error", "cancelled").
        """
        pass

    # ── Message hooks ──────────────────────────────────────────────────

    def on_message(self, message: str, context: dict) -> str:
        """Kullanıcı mesajı işlenmeden hemen önce çağrılır.

        Dönen string mesajın yerine kullanılır. Mesajı değiştirmeden
        iletmek için orijinal *message* döndürülmelidir.
        """
        return message

    # ── LLM hooks ──────────────────────────────────────────────────────

    def pre_llm_call(
        self, messages: List[dict], context: dict
    ) -> Tuple[List[dict], dict]:
        """LLM çağrısından hemen önce çağrılır.

        *messages* ve *context* üzerinde değişiklik yapıp (messages, context)
        tuple'ı olarak döndürebilirsiniz.

        Args:
            messages: LLM'e gönderilecek mesaj listesi.
            context:  Plugin bağlamı (her plugin kendi anahtarında saklanır).

        Returns:
            (messages, context) — değiştirilmiş veya orijinal halleri.
        """
        return messages, context

    def post_llm_call(
        self, response: dict, context: dict
    ) -> Dict[str, Any]:
        """LLM yanıtı geldikten hemen sonra çağrılır.

        *response* dict'i üzerinde değişiklik yapıp döndürebilirsiniz.

        Args:
            response: LLM'den gelen yanıt dict'i.
            context:  Plugin bağlamı.

        Returns:
            Değiştirilmiş veya orijinal response dict'i.
        """
        return response


# ── Re-export ──────────────────────────────────────────────────────────
__all__ = ["PluginBase"]
