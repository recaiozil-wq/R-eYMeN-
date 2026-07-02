# -*- coding: utf-8 -*-
"""dispatcher.py — Tool dispatch orkestratoru.

Uc bileseni birlestirir:
  - ToolRegistry   (tool_registry)        : ad -> {module, callable} cozumleme
  - ToolGuardrails (tool_guardrails)       : guvenlik kapisi
  - ToolExecutor   (tool_executor)         : retry/timeout'lu calistirma

Akis:
  dispatch(name) -> registry.resolve(name)
                 -> guardrails.kontrolet(module)
                 -> callable=='run' ? executor.calistir_tool(...) : _execute_function(...)

Tum dispatch sonuclari ortak sozlesme dondurur:
  {'ok': bool, 'tool': str, ...}  (basarisizlikta 'error', guard reddinde 'guard')
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Optional

from src.reymen.arac.tool_registry import ToolRegistry
from src.reymen.guvenlik.tool_guardrails import ToolGuardrails
from src.reymen.arac.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class ToolDispatcher:
    """Registry + guardrails + executor uzerinden tool cagrilarini yonetir."""

    def __init__(self, varsayilan_timeout: int = 30):
        """Bilesenleri olustur.

        Args:
            varsayilan_timeout: dispatch icin varsayilan zaman asimi (saniye).
        """
        self.registry = ToolRegistry()
        self.guardrails = ToolGuardrails()
        self.executor = ToolExecutor()
        self._varsayilan_timeout = varsayilan_timeout

    # ── dispatch ──────────────────────────────────────────────────────
    def dispatch(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Bir tool'u cozumle, guvenlik kapisindan gecir ve calistir.

        Args:
            name: Mantiksal tool adi.
            args: Tool parametreleri (None -> {}).
            context: Cagri baglami (None -> {}).
            timeout: Zaman asimi saniyesi.

        Returns:
            dict: {'ok': bool, 'tool': str, ...}.
                  Basarisizlikta 'error', guard reddinde ayrica 'guard'.
        """
        args = args or {}
        context = context or {}

        # 1) Cozumle
        kayit = self.registry.resolve(name)
        if not kayit:
            return {"ok": False, "tool": name, "error": f"Bilinmeyen tool: {name}"}

        module_name = kayit["module"]
        callable_adi = kayit["callable"]

        # 2) Guvenlik kapisi — modul adi ile
        guard = self.guardrails.kontrolet(module_name)
        if not guard.get("guvenli", False):
            return {
                "ok": False,
                "tool": name,
                "error": guard.get("sebep") or "Guardrails reddetti",
                "guard": guard,
            }

        # 3) Calistir
        if callable_adi == "run":
            return self.executor.calistir_tool(module_name, timeout=timeout, **args)
        return self._execute_function(module_name, callable_adi, args, timeout)

    # ── alias fonksiyon calistirma ────────────────────────────────────
    def _execute_function(
        self,
        module_name: str,
        fonksiyon_adi: str,
        args: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """callable != 'run' oldugunda modulden ozel fonksiyonu cagirir.

        Returns:
            dict: {'ok': bool, ...} — hata durumunda 'error' icerir.
        """
        try:
            mod = importlib.import_module(f"tools.{module_name}")
        except Exception as exc:  # ImportError dahil
            return {"ok": False, "error": f"Modul yuklenemedi (tools.{module_name}): {exc}"}

        fn = getattr(mod, fonksiyon_adi, None)
        if not callable(fn):
            return {"ok": False, "error": f"Fonksiyon bulunamadi: tools.{module_name}.{fonksiyon_adi}"}

        return self.executor.calistir_guvenli(fn, timeout=timeout, **(args or {}))

    # ── yardimci sorgular ─────────────────────────────────────────────
    def list_tools(self) -> Any:
        """Kayitli tool adlarinin listesi (registry.liste())."""
        return self.registry.liste()

    def tool_schema(self, name: str) -> Dict[str, Any]:
        """Bir tool'un SCHEMA tanimini dondurur.

        Returns:
            dict: {'tool', 'schema'} veya {'error'}.
                  Modulde SCHEMA yoksa schema='yok'.
        """
        kayit = self.registry.resolve(name)
        if not kayit:
            return {"error": f"Bilinmeyen tool: {name}"}

        module_name = kayit["module"]
        try:
            mod = importlib.import_module(f"tools.{module_name}")
        except Exception as exc:  # ImportError dahil
            return {"error": f"Modul yuklenemedi (tools.{module_name}): {exc}"}

        schema = getattr(mod, "SCHEMA", None)
        return {"tool": name, "schema": schema if schema is not None else "yok"}


if __name__ == "__main__":
    d = ToolDispatcher()
    print(d.dispatch("shell", {"komut": "echo merhaba"}))
