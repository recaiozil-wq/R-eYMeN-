"""ReYMeN tools.clarify_tool shim — Hermes clarify fonksiyonlarını ReYMeN'e yönlendirir.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def run(
    soru: str,
    secenekler: Optional[List[str]] = None,
    varsayilan: str = "",
) -> str:
    """Hermes clarify_tool.run — ReYMeN için basit implementasyon.

    Kullanıcıya soru sorar ve cevabı döndürür.
    Telegram bot için direkt input() kullanır.
    """
    if secenekler:
        secenek_metni = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(secenekler))
        prompt = f"{soru}\n{secenek_metni}\n"
        if varsayilan:
            prompt += f"Varsayılan: {varsayilan}\n"
        prompt += "Cevabınız: "
    else:
        prompt = f"{soru}: "
        if varsayilan:
            prompt += f" (varsayılan: {varsayilan}) "

    try:
        cevap = input(prompt).strip()
        if not cevap and varsayilan:
            return varsayilan
        return cevap
    except (EOFError, KeyboardInterrupt):
        return varsayilan or "[iptal]"


def ask_user(
    question: str,
    choices: Optional[List[str]] = None,
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """Hermes ask_user — ReYMeN için basit implementasyon."""
    result = run(question, choices, default or "")
    return {"result": result, "cancelled": result == "[iptal]"}
