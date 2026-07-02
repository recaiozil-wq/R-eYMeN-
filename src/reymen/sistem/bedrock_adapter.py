# -*- coding: utf-8 -*-
"""bedrock_adapter.py — AWS Bedrock Provider Adapteri.

AWS Bedrock'a AWS SigV4 imzali istekler gonderir.
OpenAI uyumlu degil, ozel imza gerektirir.
"""

import json
import os
from datetime import datetime
from typing import Optional

# AWS SigV4 imzalama icin
try:
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class BedrockAdapter:
    """AWS Bedrock provider adapteri."""

    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self._hazir = BOTO3_AVAILABLE

    @property
    def hazir_mi(self) -> bool:
        return self._hazir and bool(os.environ.get("AWS_ACCESS_KEY_ID", ""))

    def ping(self) -> bool:
        """Bedrock erisilebilir mi?"""
        if not self.hazir_mi:
            return False
        try:
            client = boto3.client("bedrock-runtime", region_name=self.region)
            client.list_foundation_models()
            return True
        except Exception:
            return False

    def uret(self, model: str, prompt: str, max_tokens: int = 4096) -> str:
        """Bedrock'tan yanit uret.

        Args:
            model: Model ID (ornek: amazon.nova-micro-v1:0)
            prompt: Gonderilecek prompt
            max_tokens: Maksimum token

        Returns:
            Yanit metni
        """
        if not self.hazir_mi:
            return "[Bedrock]: AWS credentials veya boto3 bulunamadi."

        try:
            client = boto3.client("bedrock-runtime", region_name=self.region)

            # Model tipine gore farkli payload formatlari
            if "claude" in model or "anthropic" in model:
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }
            elif "nova" in model:
                payload = {
                    "inferenceConfig": {"max_new_tokens": max_tokens},
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                }
            else:
                payload = {
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }

            response = client.invoke_model(
                modelId=model,
                body=json.dumps(payload),
            )

            sonuc = json.loads(response["body"].read())

            # Model tipine gore yanit ayristir
            if "claude" in model or "anthropic" in model:
                return sonuc["content"][0]["text"]
            elif "nova" in model:
                return sonuc["output"]["message"]["content"][0]["text"]
            return sonuc.get("choices", [{}])[0].get("message", {}).get("content", "")

        except Exception as e:
            return f"[Bedrock]: Hata: {e}"

    def modelleri_listele(self) -> list[str]:
        """Kullanilabilir modelleri listele."""
        if not self.hazir_mi:
            return []
        try:
            client = boto3.client("bedrock-runtime", region_name=self.region)
            response = client.list_foundation_models()
            return [m["modelId"] for m in response.get("modelSummaries", [])[:20]]
        except Exception:
            return []


if __name__ == "__main__":
    b = BedrockAdapter()
    print(f"Bedrock: {'HAZIR' if b.hazir_mi else 'BULUNAMADI (boto3 veya AWS creds gerekli)'}")
    if b.hazir_mi:
        print(f"  Modeller: {b.modelleri_listele()[:5]}")
