# -*- coding: utf-8 -*-
"""gemini_cloudcode_adapter.py — Gemini Cloud Code Adaptörü.

Google Cloud Vertex AI üzerinden Gemini modellerine erişim.
Standart Gemini API'den farkı: proje+lokasyon kimlik doğrulaması kullanır.
ENV: GCP_PROJECT_ID, GCP_LOCATION, GOOGLE_APPLICATION_CREDENTIALS
"""

import json
import os
import subprocess
import urllib.request
from typing import Optional
import logging

logger = logging.getLogger(__name__)

GCP_PROJECT  = os.environ.get("GCP_PROJECT_ID", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
VERTEX_BASE  = f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1"

_TOKEN_CACHE: dict = {"token": "", "bitis": 0.0}


def _gcp_token() -> str:
    """GCP erişim token'ı al (Application Default Credentials)."""
    import time
    if time.time() < _TOKEN_CACHE["bitis"] and _TOKEN_CACHE["token"]:
        return _TOKEN_CACHE["token"]

    # 1. Servis hesabı JSON yolu tanımlıysa
    cred_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if cred_json and os.path.exists(cred_json):
        try:
            with open(cred_json, encoding="utf-8") as f:
                creds = json.load(f)
            if creds.get("type") == "service_account":
                from _gcp_sa_token import sa_token_al  # type: ignore
                token = sa_token_al(creds)
                _TOKEN_CACHE["token"] = token
                _TOKEN_CACHE["bitis"] = time.time() + 3500
                return token
        except ImportError as _e:
            logger.warning("[GeminiCloudcodeAdapter] Modul yuklenemedi (L40): %s", ImportError)
            pass

    # 2. gcloud CLI ile token al
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            _TOKEN_CACHE["token"] = token
            _TOKEN_CACHE["bitis"] = time.time() + 3500
            return token
    except Exception as _e:
        logger.warning("[GeminiCloudcodeAdapter] except Exception (L54): %s", Exception)
        pass

    # 3. GCE metadata sunucusu
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            token = data.get("access_token", "")
            _TOKEN_CACHE["token"] = token
            _TOKEN_CACHE["bitis"] = time.time() + data.get("expires_in", 3600) - 60
            return token
    except Exception as _e:
        logger.warning("[GeminiCloudcodeAdapter] except Exception (L69): %s", Exception)
        pass

    return ""


class GeminiCloudCodeAdapter:
    """Vertex AI üzerinden Gemini modeli."""

    DEFAULT_MODEL = "gemini-1.5-pro"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        project: str = GCP_PROJECT,
        location: str = GCP_LOCATION,
    ):
        self.model    = model
        self.project  = project
        self.location = location

    def _endpoint(self) -> str:
        return (
            f"https://{self.location}-aiplatform.googleapis.com/v1"
            f"/projects/{self.project}/locations/{self.location}"
            f"/publishers/google/models/{self.model}:generateContent"
        )

    def _openai_to_vertex(self, sistem: str, mesajlar: list[dict]) -> dict:
        """OpenAI formatını Vertex AI Gemini formatına dönüştür."""
        icerikler = []
        if sistem:
            icerikler.append({
                "role": "user",
                "parts": [{"text": f"[SİSTEM]\n{sistem}\n[/SİSTEM]"}],
            })
            icerikler.append({"role": "model", "parts": [{"text": "Anladım."}]})

        for msg in mesajlar:
            rol = "user" if msg["role"] == "user" else "model"
            icerikler.append({"role": rol, "parts": [{"text": msg["content"]}]})

        return {
            "contents":          icerikler,
            "generationConfig":  {"maxOutputTokens": 4096, "temperature": 0.7},
        }

    def tamamla(self, sistem: str, mesajlar: list[dict], **kwargs) -> dict:
        token = _gcp_token()
        if not token:
            return {"error": "GCP token alınamadı. gcloud auth login yapın."}
        if not self.project:
            return {"error": "GCP_PROJECT_ID ayarlanmamış."}

        govde = self._openai_to_vertex(sistem, mesajlar)
        govde["generationConfig"].update(kwargs)

        try:
            req = urllib.request.Request(
                self._endpoint(),
                data=json.dumps(govde).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def uret(self, sistem: str, mesajlar: list[dict], **kwargs) -> str:
        yanit = self.tamamla(sistem, mesajlar, **kwargs)
        if "error" in yanit:
            return f"[Gemini Vertex]: {yanit['error']}"

        adaylar = yanit.get("candidates", [])
        if adaylar:
            parcalar = adaylar[0].get("content", {}).get("parts", [])
            metin    = " ".join(p.get("text", "") for p in parcalar)
            return metin.strip() if metin.strip() else "[Gemini Vertex]: Boş yanıt"
        return f"[Gemini Vertex]: {yanit}"

    def yapilandirildi_mi(self) -> bool:
        return bool(self.project and _gcp_token())

    def saglik_kontrol(self) -> dict:
        if not self.project:
            return {"ok": False, "sebep": "GCP_PROJECT_ID eksik"}
        token = _gcp_token()
        if not token:
            return {"ok": False, "sebep": "GCP token alınamadı"}
        yanit = self.tamamla("test", [{"role": "user", "content": "hi"}],
                              maxOutputTokens=5)
        if "error" in yanit:
            return {"ok": False, "sebep": yanit["error"]}
        return {"ok": True, "model": self.model, "project": self.project}


if __name__ == "__main__":
    adapter = GeminiCloudCodeAdapter()
    print(f"Proje: {GCP_PROJECT or '(ayarlanmamış)'}")
    print(f"Yapılandırıldı: {adapter.yapilandirildi_mi()}")
