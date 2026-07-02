# -*- coding: utf-8 -*-
"""ReYMeN_cli/webhook.py — Webhook CLI.

List, add, remove, test, log islemleri.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent


def _webhook_dosyasi() -> Path:
    """Webhook kayit dosyasi."""
    return PROJE_KOK / ".ReYMeN" / "webhooks" / "webhooks.json"


def _webhooklari_oku() -> dict:
    """Kayitli webhooklari oku."""
    dosya = _webhook_dosyasi()
    if not dosya.exists():
        return {}
    try:
        with open(str(dosya), "r", encoding="utf-8") as f:
            icerik = f.read().strip()
            return json.loads(icerik) if icerik else {}
    except (json.JSONDecodeError, Exception):
        return {}


def _webhooklari_yaz(webhooklar: dict):
    """Webhooklari dosyaya yaz."""
    dosya = _webhook_dosyasi()
    dosya.parent.mkdir(parents=True, exist_ok=True)
    with open(str(dosya), "w", encoding="utf-8") as f:
        json.dump(webhooklar, f, indent=2, ensure_ascii=False)


def kaydet(alt_parser):
    """Webhook CLI alt komutlarini argparse alt ayristiricisina kaydet.

    Alt komutlar: list, add, remove, test, log
    """
    alt_parser.add_argument("islem", type=str, nargs="?",
                            choices=["list", "add", "remove", "test", "log"],
                            help="Yapilacak islem (list|add|remove|test|log)")
    alt_parser.add_argument("--name", type=str, default=None,
                            help="Webhook adi")
    alt_parser.add_argument("--url", type=str, default=None,
                            help="Webhook URL (add icin)")
    alt_parser.add_argument("--event", type=str, default=None,
                            help="Tetiklenecek olay (add icin)")


def calistir(args):
    """Webhook komutunu calistir."""
    try:
        islem = args.islem or "list"

        if islem == "list":
            webhooklar = _webhooklari_oku()
            if not webhooklar:
                print("[Webhook] Kayitli webhook yok.")
            else:
                print(f"[Webhook] Kayitli webhooklar ({len(webhooklar)} adet):")
                for ad, bilgi in sorted(webhooklar.items()):
                    url = bilgi.get("url", "?")
                    olay = bilgi.get("event", "?")
                    print(f"  + {ad}: {olay} -> {url}")

        elif islem == "add":
            name = args.name
            url = args.url
            event = args.event
            if not name or not url:
                print("[Webhook] Lutfen --name ve --url parametrelerini belirtin.")
                return
            webhooklar = _webhooklari_oku()
            webhooklar[name] = {
                "url": url,
                "event": event or "all",
                "aktif": True,
                "olusturma": datetime.now().isoformat(),
            }
            _webhooklari_yaz(webhooklar)
            print(f"[Webhook] Webhook eklendi: {name}")

        elif islem == "remove":
            name = args.name
            if not name:
                print("[Webhook] Lutfen --name parametresini belirtin.")
                return
            webhooklar = _webhooklari_oku()
            if name not in webhooklar:
                print(f"[Webhook] Webhook bulunamadi: {name}")
                return
            del webhooklar[name]
            _webhooklari_yaz(webhooklar)
            print(f"[Webhook] Webhook silindi: {name}")

        elif islem == "test":
            name = args.name
            if not name:
                print("[Webhook] Lutfen --name parametresini belirtin.")
                return
            webhooklar = _webhooklari_oku()
            if name not in webhooklar:
                print(f"[Webhook] Webhook bulunamadi: {name}")
                return
            bilgi = webhooklar[name]
            print(f"[Webhook] Test ediliyor: {name} -> {bilgi.get('url')}")
            try:
                import urllib.request
                veri = json.dumps({"test": True, "zaman": datetime.now().isoformat()}).encode()
                req = urllib.request.Request(bilgi["url"], data=veri,
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
                print(f"[Webhook] Test basarili.")
            except Exception as ex:
                print(f"[Webhook] Test basarisiz: {ex}")

        elif islem == "log":
            print("[Webhook] Webhook loglari:")
            log_yolu = PROJE_KOK / ".ReYMeN" / "webhooks" / "log.json"
            if log_yolu.exists():
                with open(str(log_yolu), "r", encoding="utf-8") as f:
                    icerik = f.read().strip()
                    if icerik:
                        loglar = json.loads(icerik)
                        for kayit in loglar[-10:]:
                            print(f"  {kayit}")
                    else:
                        print("  (Henuz log yok)")
            else:
                print("  (Henuz log yok)")

    except Exception as e:
        print(f"[Webhook] Beklenmeyen hata: {e}")
