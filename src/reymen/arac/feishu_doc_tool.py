# -*- coding: utf-8 -*-
"""feishu_doc_tool.py — Feishu (Lark) Doküman Aracı.

Feishu Docs API v1: döküman oluştur, oku, güncelle, listele.
gateway/feishu.py'den bağımsız; doküman odaklı motor aracı.
ENV: FEISHU_APP_ID, FEISHU_APP_SECRET
"""

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Optional

FEISHU_APP_ID     = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_BASE       = "https://open.feishu.cn/open-apis"

_TOKEN_CACHE: dict = {"token": "", "bitis": 0.0}


def _feishu_token() -> str:
    """Tenant access token al (önbellekli)."""
    if time.time() < _TOKEN_CACHE["bitis"] and _TOKEN_CACHE["token"]:
        return _TOKEN_CACHE["token"]
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return ""
    try:
        govde = json.dumps({
            "app_id":     FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            data=govde,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            yanit = json.loads(r.read().decode("utf-8"))
            _TOKEN_CACHE["token"] = yanit.get("tenant_access_token", "")
            _TOKEN_CACHE["bitis"] = time.time() + yanit.get("expire", 7200) - 120
            return _TOKEN_CACHE["token"]
    except Exception:
        return ""


def _fs_get(yol: str, params: dict = None) -> dict:
    token = _feishu_token()
    if not token:
        return {"error": "Feishu token alınamadı."}
    url = f"{FEISHU_BASE}{yol}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def _fs_post(yol: str, veri: dict) -> dict:
    token = _feishu_token()
    if not token:
        return {"error": "Feishu token alınamadı."}
    try:
        req = urllib.request.Request(
            f"{FEISHU_BASE}{yol}",
            data=json.dumps(veri).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def _fs_patch(yol: str, veri: dict) -> dict:
    token = _feishu_token()
    if not token:
        return {"error": "Feishu token alınamadı."}
    try:
        govde = json.dumps(veri).encode("utf-8")
        req = urllib.request.Request(
            f"{FEISHU_BASE}{yol}",
            data=govde,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


# ── Döküman İşlemleri ─────────────────────────────────────────────────

def dokuman_olustur(baslik: str, klasor_token: str = "") -> str:
    """Yeni Feishu dokümanı oluştur.

    Args:
        baslik:        Döküman başlığı
        klasor_token:  Klasör token'ı (boşsa root)

    Returns:
        Döküman URL veya hata
    """
    veri: dict = {"title": baslik}
    if klasor_token:
        veri["folder_token"] = klasor_token

    yanit = _fs_post("/docx/v1/documents", veri)
    if "error" in yanit:
        return f"[Feishu Döküman]: {yanit['error']}"

    doc_id = yanit.get("data", {}).get("document", {}).get("document_id", "")
    url    = f"https://docs.larksuite.com/docx/{doc_id}" if doc_id else ""
    return f"Döküman oluşturuldu: {doc_id}\nURL: {url}"


def dokuman_oku(document_id: str) -> str:
    """Feishu dökümanı içeriğini oku.

    Args:
        document_id: Döküman ID'si

    Returns:
        Döküman içeriği metin olarak
    """
    yanit = _fs_get(f"/docx/v1/documents/{document_id}/raw_content")
    if "error" in yanit:
        return f"[Feishu Döküman]: {yanit['error']}"

    icerik = yanit.get("data", {}).get("content", "")
    return icerik or "[Boş döküman]"


def dokuman_blok_ekle(document_id: str, metin: str, blok_tipi: str = "text") -> str:
    """Dökümanın sonuna blok ekle.

    Args:
        document_id: Döküman ID'si
        metin:       Eklenecek metin
        blok_tipi:   text | heading1 | heading2 | bullet | ordered

    Returns:
        Sonuç metni
    """
    tip_map = {
        "text":     2,
        "heading1": 3,
        "heading2": 4,
        "heading3": 5,
        "bullet":   12,
        "ordered":  13,
    }
    tip_kodu = tip_map.get(blok_tipi, 2)

    veri = {
        "children": [{
            "block_type": tip_kodu,
            "text": {
                "elements": [{"text_run": {"content": metin}}]
            },
        }]
    }
    yanit = _fs_post(f"/docx/v1/documents/{document_id}/blocks/batch_update", veri)
    if "error" in yanit:
        return f"[Feishu Blok]: {yanit['error']}"
    return f"Blok eklendi: {document_id}"


def dokuman_ara(arama_terimi: str, max_sonuc: int = 10) -> str:
    """Feishu dökümanlarında ara.

    Args:
        arama_terimi: Aranacak kelime/cümle
        max_sonuc:    Kaç sonuç döneceği

    Returns:
        Sonuçlar metin olarak
    """
    yanit = _fs_post("/suite/docs-api/search/object", {
        "search_key": arama_terimi,
        "count":      min(max_sonuc, 50),
        "docs_types": ["docx", "doc", "sheet"],
    })
    if "error" in yanit:
        return f"[Feishu Arama]: {yanit['error']}"

    oge_listesi = yanit.get("data", {}).get("docs_entities", [])
    if not oge_listesi:
        return f"'{arama_terimi}' için sonuç bulunamadı."

    satirlar = [f"Feishu Arama: '{arama_terimi}' — {len(oge_listesi)} sonuç"]
    for oge in oge_listesi:
        satirlar.append(
            f"  [{oge.get('docs_type','?')}] {oge.get('title','İsimsiz')} "
            f"— {oge.get('url','')}"
        )
    return "\n".join(satirlar)


def motor_kaydet(motor):
    """Feishu döküman araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    motor._plugin_arac_kaydet(
        "FEISHU_DOC_OLUSTUR",
        lambda baslik, klasor="": dokuman_olustur(baslik, klasor),
        "Feishu'da yeni döküman oluştur",
    )
    motor._plugin_arac_kaydet(
        "FEISHU_DOC_OKU",
        lambda document_id: dokuman_oku(document_id),
        "Feishu dökümanını oku",
    )
    motor._plugin_arac_kaydet(
        "FEISHU_DOC_BLOK_EKLE",
        lambda document_id, metin, blok_tipi="text": dokuman_blok_ekle(document_id, metin, blok_tipi),
        "Feishu dökümanına içerik ekle",
    )
    motor._plugin_arac_kaydet(
        "FEISHU_DOC_ARA",
        lambda arama_terimi, max_sonuc=10: dokuman_ara(arama_terimi, int(max_sonuc)),
        "Feishu dökümanlarında ara",
    )


if __name__ == "__main__":
    print(f"App ID: {'✓' if FEISHU_APP_ID else '✗'}")
    if FEISHU_APP_ID:
        print(dokuman_ara("test", max_sonuc=3))
