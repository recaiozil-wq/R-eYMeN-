# -*- coding: utf-8 -*-
"""lmstudio_reasoning.py — LM Studio Reasoning Adaptoru.

LM Studio'nun reasoning/thinking ozelliklerini kullanmak icin
ozel adapter. Chain-of-thought, deep thinking modlari.
"""

import json
import os
import requests
import logging

logger = logging.getLogger(__name__)


class LMStudioReasoning:
    """LM Studio reasoning adapteri."""

    def __init__(self, base_url: str = ""):
        self.base_url = base_url or os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234")

    def ping(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def dusun(self, prompt: str, derinlik: str = "normal", max_tokens: int = 2048) -> dict:
        """LM Studio'da reasoning ile yanit uret.

        Args:
            prompt: Kullanici prompt'u
            derinlik: "normal", "derin", "cok_derin"
            max_tokens: Maksimum token

        Returns:
            {"yanit": str, "thinking": str, "sure": float}
        """
        import time
        baslangic = time.time()

        # Derinlige gore system prompt
        system = {
            "normal": "Adim adim dusun, sonra cevap ver.",
            "derin": "Once problemi analiz et, cozum yollarini degerlendir, en iyisini sec ve uygula.",
            "cok_derin": "Derinlemesine analiz yap. Tum olasiliklari degerlendir. Zincirleme dusunce kullan.",
        }.get(derinlik, "Adim adim dusun.")

        try:
            r = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "llava",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                timeout=120,
            )
            sure = round(time.time() - baslangic, 2)

            if r.status_code == 200:
                yanit = r.json()["choices"][0]["message"]["content"]
                return {"yanit": yanit, "thinking": "", "sure": sure, "basarili": True}
            return {"yanit": "", "thinking": "", "sure": sure, "basarili": False, "hata": str(r.status_code)}

        except Exception as e:
            sure = round(time.time() - baslangic, 2)
            return {"yanit": "", "thinking": "", "sure": sure, "basarili": False, "hata": str(e)}

    def modelleri_listele(self) -> list[str]:
        try:
            r = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data", [])]
        except Exception as _e:
            logger.warning("[LmstudioReasoning] except Exception (L77): %s", Exception)
            pass
        return []


if __name__ == "__main__":
    lm = LMStudioReasoning()
    print(f"LM Studio: {'ERISILEBILIR' if lm.ping() else 'KAPALI'}")
    if lm.ping():
        print(f"Modeller: {lm.modelleri_listele()}")
        sonuc = lm.dusun("2+2 kac eder?", derinlik="normal")
        print(f"Yanit: {sonuc}")
