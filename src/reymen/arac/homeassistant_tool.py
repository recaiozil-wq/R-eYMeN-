# -*- coding: utf-8 -*-
"""homeassistant_tool.py — Home Assistant Akıllı Ev Aracı.

Home Assistant REST API üzerinden entitiy sorgulama, servis çağırma
ve otomasyon tetikleme. gateway/homeassistant.py'den bağımsız, doğrudan motor aracı.
ENV: HA_URL, HA_TOKEN
"""

import json
import os
import urllib.request
from typing import Optional

HA_URL   = os.environ.get("HA_URL",   "http://homeassistant.local:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "")


def _ha_get(yol: str) -> dict | list:
    if not HA_TOKEN:
        return {"error": "HA_TOKEN ayarlanmamış."}
    try:
        req = urllib.request.Request(
            f"{HA_URL.rstrip('/')}{yol}",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def _ha_post(yol: str, veri: dict) -> dict:
    if not HA_TOKEN:
        return {"error": "HA_TOKEN ayarlanmamış."}
    try:
        req = urllib.request.Request(
            f"{HA_URL.rstrip('/')}{yol}",
            data=json.dumps(veri).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def durum_oku(entity_id: str) -> str:
    """Bir entity'nin durumunu oku.

    Args:
        entity_id: HA entity ID'si (ör. light.salon, sensor.sicaklik)

    Returns:
        Durum ve özellikler metin olarak
    """
    yanit = _ha_get(f"/api/states/{entity_id}")
    if isinstance(yanit, dict) and "error" in yanit:
        return f"[HA]: {yanit['error']}"
    if isinstance(yanit, dict):
        durum = yanit.get("state", "bilinmiyor")
        nit   = yanit.get("attributes", {})
        return f"{entity_id}: {durum} | {json.dumps(nit, ensure_ascii=False)}"
    return str(yanit)


def tum_durumlar(domain: str = "") -> str:
    """Tüm entity durumlarını listele.

    Args:
        domain: Filtre (ör. light, switch, sensor) — boşsa hepsi

    Returns:
        Entity listesi metin olarak
    """
    yanit = _ha_get("/api/states")
    if isinstance(yanit, dict) and "error" in yanit:
        return f"[HA]: {yanit['error']}"

    entitiler = yanit if isinstance(yanit, list) else []
    if domain:
        entitiler = [e for e in entitiler if e.get("entity_id", "").startswith(domain + ".")]

    if not entitiler:
        return f"Domain '{domain}' için entity bulunamadı." if domain else "Hiç entity yok."

    satirlar = [f"Home Assistant Entity'leri ({len(entitiler)}):"]
    for e in entitiler[:50]:
        satirlar.append(f"  {e.get('entity_id')}: {e.get('state')}")
    if len(entitiler) > 50:
        satirlar.append(f"  ... ve {len(entitiler)-50} daha")
    return "\n".join(satirlar)


def servis_cagir(domain: str, servis: str, entity_id: str = "", **kwargs) -> str:
    """Home Assistant servisi çağır.

    Args:
        domain:    Servis domain'i (ör. light, switch, script)
        servis:    Servis adı (ör. turn_on, turn_off, toggle)
        entity_id: Hedef entity (boşsa tüm domain)

    Returns:
        Sonuç metni
    """
    veri: dict = {}
    if entity_id:
        veri["entity_id"] = entity_id
    veri.update(kwargs)

    yanit = _ha_post(f"/api/services/{domain}/{servis}", veri)
    if isinstance(yanit, dict) and "error" in yanit:
        return f"[HA Servis]: {yanit['error']}"
    return f"OK: {domain}.{servis} çağrıldı."


def isik_ac(entity_id: str, parlaklik: Optional[int] = None) -> str:
    """Işık aç."""
    kw = {"brightness": parlaklik} if parlaklik is not None else {}
    return servis_cagir("light", "turn_on", entity_id, **kw)


def isik_kapat(entity_id: str) -> str:
    """Işık kapat."""
    return servis_cagir("light", "turn_off", entity_id)


def switch_toglle(entity_id: str) -> str:
    """Switch'i aç/kapat."""
    return servis_cagir("switch", "toggle", entity_id)


def otomasyon_calistir(otomasyon_id: str) -> str:
    """Otomasyon tetikle."""
    return servis_cagir("automation", "trigger", otomasyon_id)


def motor_kaydet(motor):
    """HA araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    motor._plugin_arac_kaydet(
        "HA_DURUM",
        lambda entity_id: durum_oku(entity_id),
        "Home Assistant entity durumunu oku",
    )
    motor._plugin_arac_kaydet(
        "HA_TUM_DURUMLAR",
        lambda domain="": tum_durumlar(domain),
        "Tüm HA entity'lerini listele",
    )
    motor._plugin_arac_kaydet(
        "HA_SERVIS",
        lambda domain, servis, entity_id="": servis_cagir(domain, servis, entity_id),
        "Home Assistant servisi çağır",
    )
    motor._plugin_arac_kaydet(
        "HA_ISIK_AC",
        lambda entity_id, parlaklik="": isik_ac(entity_id, int(parlaklik) if parlaklik else None),
        "Işık aç",
    )
    motor._plugin_arac_kaydet(
        "HA_ISIK_KAPAT",
        lambda entity_id: isik_kapat(entity_id),
        "Işık kapat",
    )
    motor._plugin_arac_kaydet(
        "HA_SWITCH",
        lambda entity_id: switch_toglle(entity_id),
        "Switch'i aç/kapat",
    )
    motor._plugin_arac_kaydet(
        "HA_OTOMASYON",
        lambda otomasyon_id: otomasyon_calistir(otomasyon_id),
        "HA otomasyonunu tetikle",
    )


if __name__ == "__main__":
    print(f"HA URL: {HA_URL}")
    print(f"Token: {'✓' if HA_TOKEN else '✗'}")
    if HA_TOKEN:
        print(tum_durumlar("light"))
