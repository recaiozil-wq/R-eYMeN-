# -*- coding: utf-8 -*-
"""moonshot_schema.py — Moonshot/Kimi API Adaptörü.

Moonshot AI (Kimi) için OpenAI uyumlu arayüz.
Kimi uzun bağlam (128K+) ve Çince/Türkçe desteği için idealdir.
ENV: MOONSHOT_API_KEY
"""

import json
import os
import urllib.request
from typing import Optional

MOONSHOT_API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
MOONSHOT_BASE    = "https://api.moonshot.cn/v1"


class MoonshotProvider:
    """Moonshot Kimi API sağlayıcısı (OpenAI uyumlu arayüz)."""

    MODELLER = {
        "moonshot-v1-8k":   {"context": 8192,   "max_out": 4096},
        "moonshot-v1-32k":  {"context": 32768,  "max_out": 8192},
        "moonshot-v1-128k": {"context": 131072, "max_out": 16384},
    }

    def __init__(
        self,
        model: str = "moonshot-v1-32k",
        api_key: str = MOONSHOT_API_KEY,
    ):
        self.model   = model
        self.api_key = api_key

    def _istek(self, yol: str, veri: dict) -> dict:
        if not self.api_key:
            return {"error": "MOONSHOT_API_KEY ayarlanmamış."}
        url   = f"{MOONSHOT_BASE}{yol}"
        govde = json.dumps(veri).encode("utf-8")
        try:
            req = urllib.request.Request(
                url, data=govde,
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def uret(
        self,
        sistem: str,
        mesajlar: list[dict],
        max_tokens: int = 4096,
        sicaklik: float = 0.3,
    ) -> str:
        """Moonshot Kimi'den yanıt al."""
        msgs = []
        if sistem:
            msgs.append({"role": "system", "content": sistem})
        msgs.extend(mesajlar)

        yanit = self._istek("/chat/completions", {
            "model":       self.model,
            "messages":    msgs,
            "max_tokens":  max_tokens,
            "temperature": sicaklik,
        })

        if "error" in yanit:
            return f"[Moonshot]: {yanit['error']}"
        choices = yanit.get("choices", [])
        return choices[0]["message"]["content"] if choices else "[Moonshot]: Boş yanıt"

    def dosya_yukle(self, dosya_yolu: str) -> str:
        """Moonshot Files API ile döküman yükle (long context için)."""
        import mimetypes
        mime = mimetypes.guess_type(dosya_yolu)[0] or "text/plain"
        try:
            with open(dosya_yolu, "rb") as f:
                icerik = f.read()
            # multipart/form-data gerektiriyor — basit boundary
            sinir = "----MoonshotBoundary"
            govde = (
                f"--{sinir}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(dosya_yolu)}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode() + icerik + f"\r\n--{sinir}--\r\n".encode()

            req = urllib.request.Request(
                f"{MOONSHOT_BASE}/files",
                data=govde,
                headers={
                    "Authorization":f"Bearer {self.api_key}",
                    "Content-Type": f"multipart/form-data; boundary={sinir}",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8")).get("id", "")
        except Exception as e:
            return f"[Moonshot Dosya Yükleme]: {e}"

    def model_listesi(self) -> list[str]:
        return list(self.MODELLER.keys())

    def saglik_kontrol(self) -> dict:
        if not self.api_key:
            return {"ok": False, "sebep": "API anahtarı yok"}
        yanit = self._istek("/models", {})
        if "error" in yanit:
            return {"ok": False, "sebep": yanit["error"]}
        modeller = [m.get("id") for m in yanit.get("data", [])]
        return {"ok": True, "modeller": modeller}


import os as _os


if __name__ == "__main__":
    p = MoonshotProvider()
    print(f"API Anahtarı: {'✓' if MOONSHOT_API_KEY else '✗'}")
    saglik = p.saglik_kontrol()
    print(f"Sağlık: {saglik}")
