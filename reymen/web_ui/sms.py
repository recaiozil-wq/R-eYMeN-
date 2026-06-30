# -*- coding: utf-8 -*-
"""📱 ReYMeN SMS Modülü — Twilio REST API üzerinden SMS gönderme.

Bağımlılık: twilio kütüphanesi GEREKMEZ, urllib ile direkt REST API.

.env'de:
  TWILIO_ACCOUNT_SID=ACxxxx
  TWILIO_AUTH_TOKEN=xxxx
  TWILIO_FROM_NUMBER=+1xxxxx
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


def _env_oku(anahtar: str, varsayilan: str = "") -> str:
    """.env + ReYMeN env fallback ile değer oku."""
    # Proje .env
    proje_env = Path(__file__).resolve().parent.parent / ".env"
    if proje_env.exists():
        for satir in proje_env.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir.startswith("#") or "=" not in satir:
                continue
            k, v = satir.split("=", 1)
            if k.strip() == anahtar:
                return v.strip().strip('"').strip("'")
    # ReYMeN env fallback
    kiral_env = Path.home() / "AppData" / "Local" / "reymen" / "profiles" / "kiral38" / ".env"
    if kiral_env.exists():
        for satir in kiral_env.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir.startswith("#") or "=" not in satir:
                continue
            k, v = satir.split("=", 1)
            if k.strip() == anahtar:
                return v.strip().strip('"').strip("'")
    return varsayilan


def sms_gonder(
    telefon: str,
    mesaj: str,
    account_sid: Optional[str] = None,
    auth_token: Optional[str] = None,
    from_num: Optional[str] = None,
) -> dict:
    """Twilio REST API ile SMS gönder.

    Args:
        telefon: Hedef telefon numarası (+905551234567)
        mesaj: SMS metni
        account_sid: Twilio Account SID (None=.env'den al)
        auth_token: Twilio Auth Token (None=.env'den al)
        from_num: Gönderen numara (None=.env'den al)

    Returns:
        {"ok": bool, "mesaj_id": str|None, "hata": str|None}
    """
    sid = account_sid or _env_oku("TWILIO_ACCOUNT_SID")
    token = auth_token or _env_oku("TWILIO_AUTH_TOKEN")
    gonderici = from_num or _env_oku("TWILIO_FROM_NUMBER")

    if not sid or not token or not gonderici:
        eksik = []
        if not sid:
            eksik.append("TWILIO_ACCOUNT_SID")
        if not token:
            eksik.append("TWILIO_AUTH_TOKEN")
        if not gonderici:
            eksik.append("TWILIO_FROM_NUMBER")
        return {"ok": False, "hata": f"Eksik: {', '.join(eksik)}", "mesaj_id": None}

    if not mesaj:
        return {"ok": False, "hata": "Mesaj boş", "mesaj_id": None}

    if len(mesaj) > 1600:
        mesaj = mesaj[:1600] + "..."

    # Basic Auth header
    auth_str = f"{sid}:{token}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()

    # POST data
    post_data = urllib.parse.urlencode({
        "From": gonderici,
        "To": telefon,
        "Body": mesaj,
    }).encode()

    url = f"{TWILIO_API_BASE}/Accounts/{sid}/Messages.json"

    try:
        req = urllib.request.Request(
            url,
            data=post_data,
            method="POST",
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            sid_resp = result.get("sid")
            status = result.get("status", "?")
            logger.info("SMS gonderildi: %s -> %s (status=%s)", sid_resp, telefon, status)
            return {"ok": True, "mesaj_id": sid_resp, "durum": status, "hata": None}

    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        hata = f"Twilio HTTP {e.code}: {body}"
        logger.error("SMS hatasi: %s", hata)
        return {"ok": False, "hata": hata, "mesaj_id": None}

    except Exception as e:
        hata = str(e)
        logger.error("SMS hatasi: %s", hata)
        return {"ok": False, "hata": hata, "mesaj_id": None}


def bakiye_kontrol(account_sid: Optional[str] = None, auth_token: Optional[str] = None) -> dict:
    """Twilio hesap bakiyesini kontrol et."""
    sid = account_sid or _env_oku("TWILIO_ACCOUNT_SID")
    token = auth_token or _env_oku("TWILIO_AUTH_TOKEN")

    if not sid or not token:
        return {"ok": False, "hata": "Eksik: TWILIO_ACCOUNT_SID veya TWILIO_AUTH_TOKEN"}

    auth_str = f"{sid}:{token}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()

    url = f"{TWILIO_API_BASE}/Accounts/{sid}.json"

    try:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Basic {auth_b64}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {
                "ok": True,
                "friendly_name": data.get("friendly_name", ""),
                "durum": data.get("status", ""),
                "type": data.get("type", ""),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "hata": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"ok": False, "hata": str(e)}
