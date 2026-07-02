"""ReYMeN tools.execute_code_tool shim — Hermes code execution fonksiyonlarını yönlendirir.

Not: ReYMeN kendi code_execution mantığını kullanır.
Bu shim, Hermes import'larının kırılmaması için basit implementasyon sağlar.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def run(kod: str, **kwargs) -> str:
    """Hermes execute_code_tool.run — ReYMeN için basit implementasyon.

    Python kodunu çalıştırır ve sonucu döndürür.
    """
    import io
    import sys
    import traceback

    # stdout'u yakala
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured = io.StringIO()
    sys.stdout = captured
    sys.stderr = captured

    try:
        exec(kod, {"__builtins__": __builtins__})
        output = captured.getvalue()
        if not output:
            output = "[Kod başarıyla çalıştı, çıktı yok]"
        return output
    except Exception:
        return f"[HATA]\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def build_execute_code_schema(
    available_tools: set,
    mode: str = "local",
) -> Dict[str, Any]:
    """Hermes build_execute_code_schema — ReYMeN için basit implementasyon.

    execute_code tool'unun OpenAPI şemasını oluşturur.
    """
    return {
        "name": "execute_code",
        "description": "Python kodunu çalıştırır. Korumalı modda çalışır.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Çalıştırılacak Python kodu",
                }
            },
            "required": ["code"],
        },
    }


def _get_execution_mode() -> str:
    """Hermes _get_execution_mode — ReYMeN için basit implementasyon."""
    return "local"
