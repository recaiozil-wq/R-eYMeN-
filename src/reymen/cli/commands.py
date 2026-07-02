# -*- coding: utf-8 -*-
"""Stub: commands.py — Slash komutlari. Henuz tam tasinmadi."""

from typing import Any


class SlashCommandCompleter:
    """Slash komut tamamlayici (stub)."""

    def __init__(self, *args, **kwargs):
        pass

    def get_completions(self, document, complete_event):
        return []


class SlashCommandAutoSuggest:
    """Slash komut auto-suggest (stub)."""

    def __init__(self, *args, **kwargs):
        pass

    def get_suggestion(self, buffer, document):
        return None
