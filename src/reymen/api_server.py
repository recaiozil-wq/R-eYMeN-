# -*- coding: utf-8 -*-
"""
api_server.py — OpenAI-uyumlu REST API sunucusu.

ReYMeN altyapýsýný (Beyin) FastAPI üzerinden OpenAI uyumlu bir API
olarak sunar. Streaming (SSE) ve non-streaming chat completions,
model listeleme ve saðlýk kontrolü endpoint'leri içerir.

Kullaným:
    python -m reymen.api_server --port 8000
    python -m reymen.api_server --port 8000 --host 0.0.0.0 --no-auth

Baðýmlýlýklar:
    fastapi>=0.110.0
    uvicorn[standard]>=0.29.0
    pyyaml>=6.0
    python-dotenv>=1.0.0
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger("reymen.api_server")

# ── Proje kökü (config.yaml ve .env'nin bulunduðu yer) ──────────────────────
_PROJE_KOKU = Path(__file__).resolve().parent.parent
_CONFIG_YOLU = _PROJE_KOKU / "config.yaml"
_ENV_YOLU = _PROJE_KOKU / ".env"


# ── FastAPI ve Starlette içe aktar ──────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

# ── Pydantic þemalarý ────────────────────────────────────────────────────────
from pydantic import BaseModel, Field


class ChatCompletionRequest(BaseModel):
    """OpenAI /v1/chat/completions istek þemasý."""
    model: Optional[str] = None
    messages: list[dict] = Field(..., description="Konuþma mesajlarý")
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[list[str] | str] = None
    user: Optional[str] = None


class ChatCompletionMessage(BaseModel):
    """OpenAI yanýt mesajý."""
    role: str = "assistant"
    content: str = ""


class ChatCompletionChoice(BaseModel):
    """OpenAI yanýt seçeneði."""
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    """OpenAI kullaným istatistiði."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI /v1/chat/completions yanýt þemasý."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage = ChatCompletionUsage()


class ModelPermission(BaseModel):
    """Model izin þemasý (OpenAI uyumluluðu için)."""
    id: str = ""
    object: str = "model_permission"
    created: int = 0
    allow_create_engine: bool = False
    allow_sampling: bool = True
    allow_logprobs: bool = False
    allow_search_indices: bool = False
    allow_view: bool = True
    allow_fine_tuning: bool = False
    organization: str = "*"
    group: Optional[str] = None
    is_blocking: bool = False


class ModelObject(BaseModel):
    """OpenAI model nesnesi."""
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "reymen"
    permission: list[ModelPermission] = []


class ModelList(BaseModel):
    """GET /v1/models yanýtý."""
    object: str = "list"
    data: list[ModelObject]


# ── Varsayýlan modeller (Beyin'den çek) ────────────────────────────────────
try:
    from reymen.cereyan.beyin import _VARSAYILAN_MODELLER as _BEYIN_VARSAYILAN_MODELLER
except ImportError:
    _BEYIN_VARSAYILAN_MODELLER = {}


# ── Config yükleyici ────────────────────────────────────────────────────────
def _config_yukle() -> dict[str, Any]:
    """config.yaml'i okuyup Beyin için uygun formata çevirir.

    config.yaml'deki ``fallback_providers`` listesini
    ``providers`` sözlüðüne dönüþtürür.
    """
    try:
        import yaml as _yaml
    except ImportError:
        raise ImportError("pyyaml kurulu deðil. 'pip install pyyaml' ile kur.")

    if not _CONFIG_YOLU.exists():
        logger.warning("config.yaml bulunamadý: %s — varsayýlan config kullanýlýyor.", _CONFIG_YOLU)
        return {
            "default_provider": "deepseek",
            "default_model": "deepseek-v4-flash",
            "providers": {},
        }

    with open(_CONFIG_YOLU, "r", encoding="utf-8") as f:
        raw: dict = _yaml.safe_load(f) or {}

    # Ana config'den provider/default model
    provider = raw.get("model", {}).get("provider") or raw.get("provider", "deepseek")
    model = raw.get("model", {}).get("default") or raw.get("general", {}).get("default_model", "deepseek-v4-flash")

    # fallback_providers → providers dict
    providers: dict[str, dict[str, str]] = {}
    for fb in raw.get("fallback_providers", []):
        pname = fb.get("provider", "")
        if pname:
            providers[pname] = {
                "base_url": fb.get("base_url", ""),
                "api_key": "",  # runtime'da env'den okunur
            }

    # providers varsa üstüne yaz
    providers.update(raw.get("providers", {}))

    return {
        "default_provider": provider,
        "default_model": model,
        "providers": providers,
        "fallback_model": raw.get("fallback_model"),
        "general": raw.get("general", {}),
    }


# ── .env yükleyici ──────────────────────────────────────────────────────────
def _env_yukle() -> None:
    """.env dosyasýný ortam deðiþkenlerine yükle."""
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_YOLU, override=True)
        logger.info(".env yüklendi: %s", _ENV_YOLU)
    except ImportError:
        logger.debug("python-dotenv yok, .env yüklenmedi.")
    except Exception as e:
        logger.warning(".env yüklenirken hata: %s", e)


# ── API anahtarý doðrulayýcý ───────────────────────────────────────────────
def _api_key_kontrol(request: Request) -> str | None:
    """Ýstekten API anahtarýný çýkar; doðrulama kapalýysa None döndür.

    Sýrasýyla: Authorization header → X-API-Key header → query param.
    """
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    x_key = request.headers.get("X-API-Key", "")
    if x_key:
        return x_key.strip()
    query_key = request.query_params.get("api_key", "")
    if query_key:
        return query_key.strip()
    return None


# ── API Sunucusu Sýnýfý ─────────────────────────────────────────────────────
class APIServer:
    """OpenAI-uyumlu REST API sunucusu.

    ReYMeN'in :class:`reymen.cereyan.beyin.Beyin` altyapýsýný
    FastAPI üzerinden OpenAI uyumlu bir arayüzle dýþarýya açar.

    Özellikler:
        * GET /v1/models — modelleri listele
        * POST /v1/chat/completions — chat tamamlama (streaming + non-streaming)
        * GET /health — saðlýk kontrolü
        * CORS desteði
        * Ýsteðe baðlý API anahtarý korumasý (Authorization: Bearer)
        * SSE streaming (Server-Sent Events)

    Kullaným:
        >>> server = APIServer(port=8000, host="127.0.0.1")
        >>> server.run()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        api_key_required: bool = True,
        log_level: str = "INFO",
    ) -> None:
        """API sunucusunu baþlat.

        Args:
            host: Dinlenecek að arayüzü.
            port: Dinlenecek port.
            api_key_required: True ise .env'deki API_KEY ile koru.
            log_level: Log seviyesi (DEBUG, INFO, WARNING, ERROR).
        """
        self.host = host
        self.port = port
        self.api_key_required = api_key_required
        # .env'yi önceden yükle ki API_KEY okunabilsin
        _env_yukle()
        self._api_key = os.environ.get("API_KEY", "")

        # Loglama
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Config yükle
        self._beyin_config = _config_yukle()

        # Beyin örneði (lazy)
        self._beyin: Any = None

        # FastAPI uygulamasý
        self.app = FastAPI(
            title="ReYMeN API",
            description="ReYMeN AI Asistaný — OpenAI-uyumlu REST API",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        self._kayit_et()

    def _beyin_al(self) -> Any:
        """Beyin örneðini lazy-load ile al.

        Thread-safe deðildir; tek thread'li uvicorn için yeterlidir.
        """
        if self._beyin is None:
            try:
                from reymen.cereyan.beyin import Beyin
                self._beyin = Beyin(config=self._beyin_config)
                logger.info(
                    "Beyin baþlatýldý: provider=%s model=%s",
                    self._beyin.provider, self._beyin.model,
                )
            except Exception as e:
                logger.error("Beyin baþlatýlamadý: %s", e)
                raise RuntimeError(f"Beyin baþlatýlamadý: {e}") from e
        return self._beyin

    def _dogrula(self, request: Request) -> None:
        """API anahtarý doðrulamasý yap (isteðe baðlý).

        Raises:
            HTTPException: Anahtar geçersiz veya eksikse 401.
        """
        if not self.api_key_required or not self._api_key:
            return

        gelen = _api_key_kontrol(request)
        if not gelen:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="API anahtarý gerekli. Authorization: Bearer *** kullanýn.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if gelen != self._api_key:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="API anahtarý geçersiz.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _kayit_et(self) -> None:
        """Tüm endpoint'leri FastAPI uygulamasýna kaydet."""

        # ── Saðlýk kontrolü ─────────────────────────────────────────────
        @self.app.get("/health")
        async def health(request: Request) -> dict:
            """Saðlýk kontrolü endpoint'i.

            Beyin örneðinin canlý olup olmadýðýný kontrol eder.

            Returns:
                {"status": "ok", "provider": ..., "model": ...}
            """
            try:
                beyin = self._beyin_al()
                return {
                    "status": "ok",
                    "provider": beyin.provider,
                    "model": beyin.model,
                    "timestamp": int(time.time()),
                }
            except Exception as e:
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Saðlýk kontrolü baþarýsýz: {e}",
                )

        # ── Modelleri listele ─────────────────────────────────────────────
        @self.app.get("/v1/models")
        async def list_models(request: Request) -> ModelList:
            """Kullanýlabilir modelleri listele.

            Config'deki tüm saðlayýcý/modelleri OpenAI formatýnda döndürür.
            """
            self._dogrula(request)
            modeller: list[ModelObject] = []
            suan = int(time.time())

            cfg = self._beyin_config
            birincil_provider = cfg.get("default_provider", "deepseek")
            birincil_model = cfg.get("default_model", "deepseek-v4-flash")

            # Birincil model
            modeller.append(ModelObject(
                id=f"{birincil_provider}/{birincil_model}",
                created=suan,
                owned_by=birincil_provider,
            ))

            # Fallback provider'lardaki modeller
            for pname in cfg.get("providers", {}):
                # Varsayýlan model
                pmid = _BEYIN_VARSAYILAN_MODELLER.get(pname, f"{pname}/default")
                mid = f"{pname}/{pmid}"
                if mid not in {m.id for m in modeller}:
                    modeller.append(ModelObject(
                        id=mid,
                        created=suan,
                        owned_by=pname,
                    ))

            return ModelList(data=modeller)

        # ── Chat Completions ──────────────────────────────────────────────
        @self.app.post("/v1/chat/completions")
        async def chat_completions(
            request: Request,
            body: ChatCompletionRequest,
        ) -> Any:
            """OpenAI-uyumlu chat completions endpoint'i.

            Streaming (SSE) ve non-streaming modlarý destekler.

            Args:
                body: OpenAI uyumlu istek gövdesi.

            Returns:
                StreamingResponse (SSE) veya ChatCompletionResponse (JSON).
            """
            self._dogrula(request)
            beyin = self._beyin_al()

            # Model/provider seçimi
            model_adi = body.model or beyin.model
            provider_adi: str | None = None

            # "provider/model" formatýný çöz
            if "/" in model_adi:
                parts = model_adi.split("/", 1)
                provider_adi = parts[0]
                model_adi = parts[1]
                logger.debug("Çözümlenen: provider=%s model=%s", provider_adi, model_adi)

            # Mesajlarý ayýr: sistem prompt'u ayrý
            sistem_prompt = ""
            mesajlar: list[dict] = []
            for msg in body.messages:
                if msg.get("role") == "system":
                    sistem_prompt = msg.get("content", "")
                else:
                    mesajlar.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    })

            # OpenAI-uyumlu yanýt ID'si
            yanit_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
            suan = int(time.time())

            # ── Streaming mod ─────────────────────────────────────────
            if body.stream:
                async def _stream_generator() -> AsyncGenerator[str, None]:
                    """SSE akýþý üretir."""
                    try:
                        # Ýlk chunk: rol
                        ilk_chunk = {
                            "id": yanit_id,
                            "object": "chat.completion.chunk",
                            "created": suan,
                            "model": model_adi,
                            "choices": [{
                                "index": 0,
                                "delta": {"role": "assistant", "content": ""},
                                "finish_reason": None,
                            }],
                        }
                        yield f"data: {json.dumps(ilk_chunk, ensure_ascii=False)}\n\n"

                        # Token akýþý
                        for token in beyin.dusun_stream(
                            sistem_prompt=sistem_prompt,
                            mesajlar=mesajlar,
                            model=model_adi if not provider_adi else None,
                        ):
                            chunk = {
                                "id": yanit_id,
                                "object": "chat.completion.chunk",
                                "created": suan,
                                "model": model_adi,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": token},
                                    "finish_reason": None,
                                }],
                            }
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                        # Bitiþ chunk'ý
                        son_chunk = {
                            "id": yanit_id,
                            "object": "chat.completion.chunk",
                            "created": suan,
                            "model": model_adi,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }],
                        }
                        yield f"data: {json.dumps(son_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"

                    except Exception as e:
                        logger.error("Streaming hatasý: %s", e)
                        hata_chunk = {
                            "id": yanit_id,
                            "object": "chat.completion.chunk",
                            "created": suan,
                            "model": model_adi,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "error",
                            }],
                        }
                        yield f"data: {json.dumps(hata_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"

                return StreamingResponse(
                    _stream_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )

            # ── Non-streaming mod ─────────────────────────────────────
            try:
                yanit_metni = beyin.dusun(
                    sistem_prompt=sistem_prompt,
                    mesajlar=mesajlar,
                    model=model_adi if not provider_adi else None,
                    provider=provider_adi,
                )

                # Token sayýsý tahmini
                prompt_token = len(sistem_prompt.split()) + sum(
                    len(m.get("content", "").split()) for m in mesajlar
                )
                completion_token = len(yanit_metni.split())

                return ChatCompletionResponse(
                    id=yanit_id,
                    created=suan,
                    model=model_adi,
                    choices=[
                        ChatCompletionChoice(
                            index=0,
                            message=ChatCompletionMessage(
                                role="assistant",
                                content=yanit_metni,
                            ),
                            finish_reason="stop",
                        )
                    ],
                    usage=ChatCompletionUsage(
                        prompt_tokens=prompt_token,
                        completion_tokens=completion_token,
                        total_tokens=prompt_token + completion_token,
                    ),
                )

            except Exception as e:
                logger.error("Chat completions hatasý: %s", e)
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Yanýt üretilemedi: {e}",
                )

    # ── CORS middleware ──────────────────────────────────────────────────
    def _cors_ekle(self) -> None:
        """Tüm origin'lere izin veren CORS middleware'i ekle."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def run(self) -> None:
        """Sunucuyu baþlat (blocking call)."""
        import uvicorn

        self._cors_ekle()

        logger.info(
            "ReYMeN API sunucusu baþlatýlýyor → http://%s:%s",
            self.host, self.port,
        )
        logger.info(
            "Beyin: provider=%s model=%s",
            self._beyin_config.get("default_provider", "?"),
            self._beyin_config.get("default_model", "?"),
        )
        if self.api_key_required and self._api_key:
            logger.info("API anahtarý korumasý: AÇIK")
        else:
            logger.info("API anahtarý korumasý: KAPALI")

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )


# ── CLI entry point ──────────────────────────────────────────────────────────
def main() -> None:
    """Komut satýrý giriþ noktasý.

    Kullaným::

        python -m reymen.api_server --port 8000
        python -m reymen.api_server --port 8000 --host 0.0.0.0 --no-auth
        python -m reymen.api_server --port 8000 --log DEBUG
    """
    parser = argparse.ArgumentParser(
        prog="python -m reymen.api_server",
        description="ReYMeN API Sunucusu — OpenAI-uyumlu REST API",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.environ.get("API_PORT", "8000")),
        help="Dinlenecek port (ortam: API_PORT, varsayýlan: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("API_HOST", "127.0.0.1"),
        help="Dinlenecek host (ortam: API_HOST, varsayýlan: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="API anahtarý korumasýný kapat (.env'deki API_KEY gerekmez)",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=os.environ.get("API_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log seviyesi (varsayýlan: INFO)",
    )

    args = parser.parse_args()

    server = APIServer(
        host=args.host,
        port=args.port,
        api_key_required=not args.no_auth,
        log_level=args.log,
    )
    server.run()


if __name__ == "__main__":
    main()
