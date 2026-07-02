# -*- coding: utf-8 -*-
"""
account_usage.py — ReYMeN stub. Hermes account_usage API'sini taklit eder.
Apache 2.0 — inspired by NousResearch/hermes-agent
"""
from __future__ import annotations
import logging
from typing import Optional
logger = logging.getLogger(__name__)


class AccountUsageSnapshot:
    """Minimal stub: always returns 'bilgi yok'."""
    def __init__(self):
        self.available = False
        self.total_usage = 0.0
        self.total_limit = None
        self.remaining = 0.0
        self.usage_pct = 0.0
        self.reset_date = None
        self.model_group = None


class CreditsView:
    """Minimal stub."""
    def __init__(self):
        self.lines = []
        self.error = None


def fetch_account_usage(*args, **kwargs) -> Optional[AccountUsageSnapshot]:
    """Stub — Hermes hesap kullanim bilgisi alinamazsa None."""
    logger.debug("[account_usage/stub] fetch_account_usage: stub")
    return None


def render_account_usage_lines(snapshot, *, markdown=False) -> list[str]:
    """Stub — kullanim satirlari."""
    return ["ℹ️ Kullanim bilgisi alinamadi (ReYMeN stub)."]


def build_credits_view(*, markdown=False, timeout=10.0) -> CreditsView:
    """Stub — credits goruntulemesi."""
    view = CreditsView()
    view.lines = ["ℹ️ Kredi bilgisi alinamadi (ReYMeN stub)."]
    return view


def nous_credits_lines(*, markdown=False, timeout=10.0) -> list[str]:
    """Stub — nous credits satirlari."""
    return ["ℹ️ Nous kredi bilgisi alinamadi (ReYMeN stub)."]
