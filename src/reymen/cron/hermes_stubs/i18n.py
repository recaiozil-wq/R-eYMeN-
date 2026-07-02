# -*- coding: utf-8 -*-
"""
i18n.py — ReYMeN stub. Basit metin ceviri/sablon sistemi.
Apache 2.0 — inspired by NousResearch/hermes-agent
"""
from __future__ import annotations
import logging
import re
from typing import Any
logger = logging.getLogger(__name__)

# Fallback metinler (Ingilizce -> Turkce ceviri yok, orijinal key'i gosterir)
_FALLBACKS: dict[str, str] = {}


def t(key: str, **kwargs: Any) -> str:
    """Basit ceviri fonksiyonu. Key bulunamazsa '{key}' formatinda doner.
    
    Ornek: t("gateway.usage.label_total", count=42) -> "Total API calls: 42"
    """
    if not key:
        return ""
    
    # Bilinen key'ler icin basit fallback
    known = {
        "gateway.usage.label_model": "Model: {model}",
        "gateway.usage.label_total": "Total tokens: {count:,}",
        "gateway.usage.label_api_calls": "API calls: {count}",
        "gateway.insights.invalid_days": "Invalid value: {value}",
    }
    
    template = known.get(key)
    if template is None:
        # Bilinmeyen key: key'in kendisini goster
        if kwargs:
            parts = [f"{k}={v}" for k, v in kwargs.items()]
            return f"[{key}] ({', '.join(parts)})"
        return f"[{key}]"
    
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError) as e:
        logger.debug("[i18n/stub] Format hatasi '%s': %s", key, e)
        return template
