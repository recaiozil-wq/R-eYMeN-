# -*- coding: utf-8 -*-
"""
mcp_server.py — ReYMeN MCP (Model Context Protocol) Sunucusu.

ReYMeN konuşmalarını (session'ları) MCP protokolü üzerinden
dış MCP istemcilerine (Claude Code, VS Code MCP, özel araçlar vb.)
resource ve tool olarak sunar.

Transport: STDIO (stdin / stdout)
Protokol:  JSON-RPC 2.0 tabanlı MCP
Bağımlılık: sadece stdlib (json, sqlite3, sys)

Kullanım:
    python -c "from reymen.ag.mcp_server import main; main()"

MCP İstemci Yapılandırması (claude_desktop_config.json / VS Code MCP):
    {
      "mcpServers": {
        "reymen": {
          "command": "python",
          "args": ["-c", "from reymen.ag.mcp_server import main; main()"]
        }
      }
    }
"""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ── Opsiyonel: Session Storage ───────────────────────────────────────────
try:
    from reymen.hafiza.session_db import (
        AdvancedSessionStorage as _SessionStorage,
    )
    _SESSION_AKTIF = True
except ImportError:
    _SessionStorage = None
    _SESSION_AKTIF = False

# ── Sabitler ──────────────────────────────────────────────────────────────
MCP_VERSION = "2025-03-26"
SERVER_NAME = "reymen-mcp"
SERVER_VERSION = "1.0.0"
RESOURCE_PREFIX = "reymen://"

# ── JSON-RPC / MCP Yardimciları ─────────────────────────────────────────

def _rpc_json(request_id: Any, result: Any = None, error: Optional[dict] = None) -> str:
    """JSON-RPC 2.0 yanıtı oluştur."""
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error:
        msg["error"] = error
    else:
        msg["result"] = result if result is not None else {}
    return json.dumps(msg, ensure_ascii=False)

def _rpc_notification(method: str, params: Optional[dict] = None) -> str:
    """JSON-RPC 2.0 bildirimi (notification, id'siz)."""
    msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params:
        msg["params"] = params
    return json.dumps(msg, ensure_ascii=False)

def _rpc_error(request_id: Any, code: int, message: str, data: Any = None) -> str:
    """JSON-RPC hata yanıtı."""
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return _rpc_json(request_id, error=err)


# ── MCP Sunucu Sinifi ────────────────────────────────────────────────────

class MCPServer:
    """ReYMeN MCP Sunucusu.

    MCP protokolünü uygular:
      - resources/list, resources/read
      - tools/list, tools/call
      - initialize, ping, notifications/initialized

    Session verilerini AdvancedSessionStorage üzerinden okur/yazar.
    """

    def __init__(self, storage: Optional[_SessionStorage] = None) -> None:
        self._storage = storage or (
            _SessionStorage() if _SESSION_AKTIF and _SessionStorage else None
        )
        self._initialized = False
        self._request_handlers: dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "ping": self._handle_ping,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "notifications/initialized": self._handle_notification_initialized,
        }

    # ── Ana Döngü ─────────────────────────────────────────────────────

    def run(self) -> None:
        """STDIN'den JSON-RPC isteklerini oku, STDOUT'a yanıt yaz."""
        logger.info("[MCPServer] ReYMeN MCP sunucusu başlatılıyor...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self._dispatch(request)
                if response:
                    sys.stdout.write(response + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                err = _rpc_error(None, -32700, "Parse error: geçersiz JSON")
                sys.stdout.write(err + "\n")
                sys.stdout.flush()
            except Exception:
                err = _rpc_error(
                    None, -32603, "Internal error",
                    traceback.format_exc(),
                )
                sys.stdout.write(err + "\n")
                sys.stdout.flush()

    def _dispatch(self, request: dict) -> Optional[str]:
        """JSON-RPC isteğini dağıt."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        handler = self._request_handlers.get(method)
        if handler is None:
            return _rpc_error(req_id, -32601, f"Method not found: {method}")

        # Bildirimler (id yok) -> yanıt yok
        if req_id is None:
            try:
                handler(params)
            except Exception:
                logger.error("[MCPServer] Bildirim hatası: %s", traceback.format_exc())
            return None

        try:
            result = handler(params)
            return _rpc_json(req_id, result=result)
        except ValueError as e:
            return _rpc_error(req_id, -32602, str(e))
        except Exception as e:
            return _rpc_error(
                req_id, -32603, str(e),
                traceback.format_exc() if logger.isEnabledFor(logging.DEBUG) else None,
            )

    # ── Initialize ────────────────────────────────────────────────────

    def _handle_initialize(self, params: dict) -> dict:
        """initialize — MCP el sıkışması."""
        client_version = params.get("protocolVersion", "unknown")
        logger.info(
            "[MCPServer] İstemci bağlandı: protocolVersion=%s", client_version
        )
        self._initialized = True
        return {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
            "capabilities": {
                "resources": {
                    "subscribe": False,
                    "listChanged": True,
                },
                "tools": {
                    "listChanged": True,
                },
            },
        }

    def _handle_notification_initialized(self, params: dict) -> None:
        """notifications/initialized — istemci init tamamlandı."""
        self._initialized = True
        logger.info("[MCPServer] İstemci initialized notification gönderdi.")

    def _handle_ping(self, params: dict) -> dict:
        """ping — canlılık kontrolü."""
        return {}

    # ── Resources ─────────────────────────────────────────────────────

    def _handle_resources_list(self, params: dict) -> dict:
        """resources/list — session'ları resource olarak listele."""
        cursor = params.get("cursor")
        resources = []
        sessions = self._get_session_list(cursor)
        for s in sessions:
            sid = s.get("id") or s.get("session_id", "")
            title = s.get("title") or f"Session {sid[:8]}"
            model = s.get("model", "?")
            created = s.get("started_at", 0)
            msg_count = s.get("message_count", 0)
            resources.append({
                "uri": f"{RESOURCE_PREFIX}sessions/{sid}",
                "name": title,
                "description": (
                    f"Model: {model} | Mesaj: {msg_count} | "
                    f"Oluşturulma: {time.strftime('%Y-%m-%d %H:%M', time.localtime(created)) if created else '?'}"
                ),
                "mimeType": "application/json",
            })
        return {
            "resources": resources,
            "nextCursor": None,
        }

    def _handle_resources_read(self, params: dict) -> dict:
        """resources/read — session detayını oku."""
        uri = params.get("uri", "")
        if not uri.startswith(RESOURCE_PREFIX):
            raise ValueError(f"Geçersiz URI: {uri}")

        path = uri[len(RESOURCE_PREFIX):].strip("/")
        parts = path.split("/")

        if len(parts) == 1 and parts[0] == "sessions":
            # Tüm session listesi
            sessions = self._get_session_list()
            content = json.dumps(sessions, ensure_ascii=False, indent=2, default=str)
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": content,
                }]
            }

        if len(parts) >= 2 and parts[0] == "sessions":
            sid = parts[1]
            session = self._get_session(sid)
            if not session:
                raise ValueError(f"Session bulunamadı: {sid}")

            if len(parts) >= 3 and parts[2] == "messages":
                # Session mesajları
                messages = self._get_session_messages(sid)
                session_data = {
                    "session": session,
                    "messages": messages,
                }
            else:
                # Session özeti
                messages = self._get_session_messages(sid)
                session_data = {
                    "session": session,
                    "messages": messages,
                }

            content = json.dumps(session_data, ensure_ascii=False, indent=2, default=str)
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": content,
                }]
            }

        raise ValueError(f"Geçersiz resource yolu: {uri}")

    def _handle_tools_list(self, params: dict) -> dict:
        """tools/list — kullanılabilir araçları listele."""
        cursor = params.get("cursor")
        return {
            "tools": [
                {
                    "name": "list_sessions",
                    "description": "Tüm ReYMeN konuşma oturumlarını listeler.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maksimum session sayısı (varsayılan: 20)",
                                "default": 20,
                            },
                            "source": {
                                "type": "string",
                                "description": "Kaynak filtresi (cli, telegram, discord, vb.)",
                            },
                        },
                    },
                },
                {
                    "name": "get_session",
                    "description": "Belirtilen session'ın detaylarını ve mesajlarını getirir.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID (UUID formatında)",
                            },
                        },
                        "required": ["session_id"],
                    },
                },
                {
                    "name": "create_session",
                    "description": "Yeni bir ReYMeN konuşma oturumu oluşturur.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Kaynak (mcp, cli, telegram, vb.)",
                                "default": "mcp",
                            },
                            "model": {
                                "type": "string",
                                "description": "Kullanılacak model adı",
                            },
                            "title": {
                                "type": "string",
                                "description": "Session başlığı",
                            },
                            "user_id": {
                                "type": "string",
                                "description": "Kullanıcı ID",
                                "default": "mcp-client",
                            },
                        },
                    },
                },
                {
                    "name": "send_message",
                    "description": "Bir session'a mesaj gönderir (user rolüyle).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Hedef session ID",
                            },
                            "content": {
                                "type": "string",
                                "description": "Mesaj içeriği",
                            },
                        },
                        "required": ["session_id", "content"],
                    },
                },
                {
                    "name": "session_stats",
                    "description": "Session istatistiklerini (toplam session, token, maliyet) getirir.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
                {
                    "name": "search_sessions",
                    "description": "Session içeriklerinde tam metin arama yapar.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Arama sorgusu (FTS5 MATCH sözdizimi)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maksimum sonuç sayısı (varsayılan: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                },
            ],
            "nextCursor": None,
        }

    def _handle_tools_call(self, params: dict) -> dict:
        """tools/call — araç çağrısını yürüt."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler_map: dict[str, Callable] = {
            "list_sessions": self._tool_list_sessions,
            "get_session": self._tool_get_session,
            "create_session": self._tool_create_session,
            "send_message": self._tool_send_message,
            "session_stats": self._tool_session_stats,
            "search_sessions": self._tool_search_sessions,
        }

        handler = handler_map.get(name)
        if handler is None:
            raise ValueError(f"Bilinmeyen araç: {name}")

        result = handler(arguments)
        # MCP tool sonuç formatı
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2, default=str),
                }
            ],
        }

    # ── Veri Katmanı ──────────────────────────────────────────────────

    def _check_storage(self) -> None:
        """Storage mevcut değilse hata fırlat."""
        if not self._storage:
            raise RuntimeError(
                "SessionStorage kullanılamıyor. "
                "reymen.hafiza.session_db modülü yüklenememiş olabilir."
            )

    def _get_session_list(self, cursor: Optional[str] = None) -> list[dict]:
        """Session listesini AdvancedSessionStorage'dan al."""
        self._check_storage()
        try:
            # son_sessionlar ile son session'ları al
            return self._storage.son_sessionlar(limit=50)
        except Exception as e:
            logger.error("[MCPServer] Session listesi alınamadı: %s", e)
            return []

    def _get_session(self, session_id: str) -> dict:
        """Tek session detayını al."""
        self._check_storage()
        try:
            return self._storage.session_bul(session_id)
        except Exception as e:
            logger.error("[MCPServer] Session bulunamadı (%s): %s", session_id, e)
            return {}

    def _get_session_messages(self, session_id: str) -> list[dict]:
        """Session mesajlarını al."""
        self._check_storage()
        try:
            # _mesajlari_getir kullan (AdvancedSessionStorage'da private)
            if hasattr(self._storage, "_mesajlari_getir"):
                return self._storage._mesajlari_getir(session_id)
            # Fallback: doğrudan SQLite sorgusu
            import sqlite3
            conn = sqlite3.connect(str(self._storage.db_yolu))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT rol, icerik, created_at FROM session_messages "
                    "WHERE session_id=? ORDER BY created_at ASC",
                    (session_id,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception as e:
            logger.error("[MCPServer] Mesajlar alınamadı (%s): %s", session_id, e)
            return []

    # ── Tool Implementasyonları ───────────────────────────────────────

    def _tool_list_sessions(self, args: dict) -> dict:
        """list_sessions aracı."""
        limit = args.get("limit", 20)
        source = args.get("source")
        self._check_storage()
        sessions = self._storage.son_sessionlar(source=source, limit=limit)
        return {
            "total": len(sessions),
            "sessions": [
                {
                    "session_id": s.get("id"),
                    "source": s.get("source"),
                    "model": s.get("model"),
                    "title": s.get("title"),
                    "message_count": s.get("message_count"),
                    "started_at": s.get("started_at"),
                    "ended_at": s.get("ended_at"),
                    "end_reason": s.get("end_reason"),
                    "input_tokens": s.get("input_tokens"),
                    "output_tokens": s.get("output_tokens"),
                }
                for s in sessions
            ],
        }

    def _tool_get_session(self, args: dict) -> dict:
        """get_session aracı."""
        session_id = args.get("session_id", "")
        if not session_id:
            raise ValueError("session_id parametresi gerekli.")
        session = self._get_session(session_id)
        if not session:
            return {"error": f"Session bulunamadı: {session_id}"}

        messages = self._get_session_messages(session_id)
        return {
            "session": {
                "id": session.get("id"),
                "source": session.get("source"),
                "user_id": session.get("user_id"),
                "model": session.get("model"),
                "title": session.get("title"),
                "system_prompt": session.get("system_prompt"),
                "parent_session_id": session.get("parent_session_id"),
                "started_at": session.get("started_at"),
                "ended_at": session.get("ended_at"),
                "end_reason": session.get("end_reason"),
                "message_count": session.get("message_count"),
                "tool_call_count": session.get("tool_call_count"),
                "input_tokens": session.get("input_tokens"),
                "output_tokens": session.get("output_tokens"),
                "estimated_cost_usd": session.get("estimated_cost_usd"),
            },
            "messages": [
                {
                    "role": m.get("rol"),
                    "content": m.get("icerik"),
                    "created_at": m.get("created_at"),
                }
                for m in messages
            ],
        }

    def _tool_create_session(self, args: dict) -> dict:
        """create_session aracı."""
        self._check_storage()
        source = args.get("source", "mcp")
        model = args.get("model")
        title = args.get("title")
        user_id = args.get("user_id", "mcp-client")

        session_id = self._storage.session_baslat(
            source=source,
            model=model,
            title=title,
            user_id=user_id,
        )
        if not session_id:
            raise RuntimeError("Session oluşturulamadı.")
        return {
            "session_id": session_id,
            "message": f"Session başarıyla oluşturuldu: {session_id}",
        }

    def _tool_send_message(self, args: dict) -> dict:
        """send_message aracı."""
        self._check_storage()
        session_id = args.get("session_id", "")
        content = args.get("content", "")

        if not session_id:
            raise ValueError("session_id parametresi gerekli.")
        if not content:
            raise ValueError("content parametresi gerekli.")

        # Session'ın var olduğunu kontrol et
        session = self._storage.session_bul(session_id)
        if not session:
            raise ValueError(f"Session bulunamadı: {session_id}")

        # Mesajı ekle
        self._storage.mesaj_ekle(session_id, "user", content)
        return {
            "session_id": session_id,
            "role": "user",
            "content_length": len(content),
            "message": "Mesaj başarıyla eklendi.",
        }

    def _tool_session_stats(self, args: dict) -> dict:
        """session_stats aracı."""
        self._check_storage()
        stats = self._storage.istatistik()
        if not stats:
            return {"message": "İstatistik verisi yok."}
        return {
            "total_sessions": stats.get("toplam_session", 0),
            "total_input_tokens": stats.get("toplam_input_token", 0),
            "total_output_tokens": stats.get("toplam_output_token", 0),
            "total_estimated_cost_usd": stats.get("toplam_tahmini_maliyet", 0),
            "total_actual_cost_usd": stats.get("toplam_gercek_maliyet", 0),
            "total_tool_calls": stats.get("toplam_tool_call", 0),
        }

    def _tool_search_sessions(self, args: dict) -> dict:
        """search_sessions aracı."""
        self._check_storage()
        query = args.get("query", "")
        limit = args.get("limit", 10)

        if not query:
            raise ValueError("query parametresi gerekli.")

        results = self._storage.session_search(sorgu=query, limit=limit)
        return {
            "total": len(results),
            "results": [
                {
                    "session_id": r.get("session_id"),
                    "summary": r.get("ozet"),
                    "model": r.get("model"),
                    "started_at": r.get("started_at"),
                    "match_count": r.get("eslesen_mesaj_sayisi"),
                    "sample_messages": [
                        {
                            "role": m.get("rol"),
                            "content": m.get("icerik"),
                        }
                        for m in (r.get("ilgili_mesajlar") or [])
                    ],
                }
                for r in results
            ],
        }


# ── Entry Points ─────────────────────────────────────────────────────────

def main() -> None:
    """MCP sunucusunu başlatır (ana entry point)."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    server = MCPServer()
    server.run()


def create_server(storage: Optional[_SessionStorage] = None) -> MCPServer:
    """Test / entegrasyon amaçlı MCPServer instance'ı oluşturur."""
    return MCPServer(storage=storage)


if __name__ == "__main__":
    main()
