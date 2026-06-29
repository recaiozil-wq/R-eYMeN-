"""🌐 ReYMeN Web UI — FastAPI + Jinja2 + HTMX + WebSocket yönetim paneli.

Kullanim:
    python -c "from reymen.web_ui import baslat; baslat()"
    # http://localhost:5000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, Cookie, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Web UI modülleri
from reymen.web_ui.auth import (
    AuthConfig, UserManager, TokenManager, Session,
    user_manager, token_manager,
    get_provider, list_providers,
    Role, ROLE_PERMISSIONS,
    audit_log, AuditEvent,
    InvalidCredentialsError, ProviderError,
)
from reymen.web_ui.module_discovery import ModulTarayici, modul_kategorileri
from reymen.web_ui.process_manager import ProcessManager
from reymen.web_ui.log_stream import LogStreamer, log_kuyrugu_oku

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
PLUGIN_DIZIN = PROJE_KOK / "reymen" / "sistem" / "plugins"
TEMPLATE_DIZIN = Path(__file__).parent / "templates"
STATIC_DIZIN = Path(__file__).parent / "static"
LOG_DOSYASI = PROJE_KOK / "reymen.log"

# ---------------------------------------------------------------------------
# Uygulama
# ---------------------------------------------------------------------------

app = FastAPI(title="ReYMeN Web UI", version="2.0.0")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATE_DIZIN))

# Jinja2 context processor: request.state → template değişkenleri
async def jinja_context(request: Request) -> dict:
    return {
        "user": getattr(request.state, "user", None),
        "role": getattr(request.state, "role", None),
        "tema": "dark",
    }

templates.env.globals["kullanici"] = lambda req: getattr(req.state, "user", None)
# Her TemplateResponse'a otomatik context ekle
_original_render = templates.TemplateResponse

def _render_with_context(name, context, *args, **kwargs):
    request = kwargs.get("request") or context.get("request")
    if request:
        context.setdefault("user", getattr(request.state, "user", None))
        context.setdefault("role", getattr(request.state, "role", None))
    return _original_render(name, context, *args, **kwargs)

templates.TemplateResponse = _render_with_context

# Static files
if STATIC_DIZIN.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIZIN)), name="static")

# Singleton servisler
modul_tarayici = ModulTarayici()
process_manager = ProcessManager()
log_streamer = LogStreamer(LOG_DOSYASI)

# ---------------------------------------------------------------------------
# Middleware — auth kontrolü (Hermes pattern: provider registry + refresh token)
# ---------------------------------------------------------------------------

AUTH_ATLANACAK = {"/auth/", "/login", "/static", "/ws/logs",
                  "/api/health", "/docs", "/openapi.json", "/redoc",
                  "/api/auth/providers", "/api/cron"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(a) for a in AUTH_ATLANACAK):
        return await call_next(request)

    # Hermes pattern: once access token, yoksa refresh token dene
    at = request.cookies.get("hermes_session_at")
    rt = request.cookies.get("hermes_session_rt")

    session = None
    if at:
        for provider in list_providers():
            try:
                session = provider.verify_session(access_token=at)
            except ProviderError:
                continue
            if session is not None:
                break

    # Access token gecersizse refresh token dene (Hermes transparent refresh)
    if session is None and rt:
        for provider in list_providers():
            try:
                session = provider.refresh_session(refresh_token=rt)
            except (ProviderError, InvalidCredentialsError):
                continue
            if session is not None:
                response = await call_next(request)
                response.set_cookie(
                    "hermes_session_at", session.access_token,
                    max_age=token_manager.expires_in(session.access_token),
                    httponly=True, samesite="lax",
                )
                if session.refresh_token:
                    response.set_cookie(
                        "hermes_session_rt", session.refresh_token,
                        max_age=604800, httponly=True, samesite="lax",
                    )
                return response

    if not session:
        if path.startswith("/api/"):
            return JSONResponse({"hata": "Yetkisiz", "error": "unauthenticated"}, status_code=401)
        return RedirectResponse(url="/login")

    request.state.user = session.user_id
    request.state.role = session.role
    request.state.session = session

    # Role-based API izin kontrolü
    if path.startswith("/api/"):
        if request.method in ("POST", "PUT", "DELETE"):
            if session.role not in ("admin", "operator"):
                return JSONResponse(
                    {"hata": "Bu islem icin yetkiniz yok (operator/admin gerekli)"},
                    status_code=403,
                )
        if "gateway" in path and request.method == "POST":
            if not user_manager.has_permission(session.user_id, "gateway.baslat"):
                return JSONResponse({"hata": "Gateway yonetim yetkiniz yok"}, status_code=403)
        if "plugin" in path and request.method == "POST":
            if not user_manager.has_permission(session.user_id, "plugin.aktif_et"):
                return JSONResponse({"hata": "Plugin yonetim yetkiniz yok"}, status_code=403)
        if "user" in path:
            if not user_manager.has_permission(session.user_id, "user.ekle"):
                return JSONResponse({"hata": "Kullanici yonetim yetkiniz yok"}, status_code=403)

    return await call_next(request)


# ── Rol bazlı yetki yardımcısı ────────────────────────────────────

def yetki_kontrol(session, gerekli_roller: list[str], izin: str = "") -> bool:
    if not session:
        return False
    if session.role in gerekli_roller:
        return True
    if izin:
        return user_manager.has_permission(session.user_id, izin)
    return False


def admin_gerekli(session) -> bool:
    return bool(session and session.role == "admin")


def operator_ustu(session) -> bool:
    return bool(session and session.role in ("admin", "operator"))


# ---------------------------------------------------------------------------
# Routes — Sayfalar
# ---------------------------------------------------------------------------


@app.get("/login", response_class=HTMLResponse)
async def login_sayfasi(request: Request, hata: str = ""):
    return templates.TemplateResponse(
        request, "login.html", {"hata": hata}
    )


@app.post("/login")
async def login_post(request: Request):
    """Hermes pattern: PasswordAuthProvider ile giris + audit log + refresh token."""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    provider = get_provider("password")
    if not provider:
        audit_log(AuditEvent.LOGIN_FAILURE, reason="no_provider", ip=request.client.host if request.client else "")
        return templates.TemplateResponse(
            request, "login.html",
            {"hata": "Giris sistemi hazir degil"},
        )

    try:
        session = provider.complete_password_login(username, password)
    except InvalidCredentialsError:
        audit_log(AuditEvent.LOGIN_FAILURE, user_id=username, provider="password",
                  ip=request.client.host if request.client else "", reason="invalid_credentials")
        return templates.TemplateResponse(
            request, "login.html",
            {"hata": "Hatalı kullanıcı adı veya şifre"},
        )

    audit_log(AuditEvent.LOGIN_SUCCESS, user_id=session.user_id, provider="password",
              ip=request.client.host if request.client else "")

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        "hermes_session_at", session.access_token,
        max_age=token_manager.expires_in(session.access_token),
        httponly=True, samesite="lax",
    )
    if session.refresh_token:
        response.set_cookie(
            "hermes_session_rt", session.refresh_token,
            max_age=604800, httponly=True, samesite="lax",
        )
    return response


@app.get("/logout")
async def logout(request: Request):
    """Hermes pattern: cookie temizle + audit log."""
    user = getattr(request.state, "user", "?")
    audit_log(AuditEvent.LOGOUT, user_id=user,
              ip=request.client.host if request.client else "")
    response = RedirectResponse(url="/login")
    response.delete_cookie("hermes_session_at", path="/")
    response.delete_cookie("hermes_session_rt", path="/")
    return response


# ---------------------------------------------------------------------------
# API — Auth (Hermes pattern: /api/auth/me + /api/auth/providers)
# ---------------------------------------------------------------------------


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    """Hermes'teki /api/auth/me — mevcut Session bilgisi."""
    session: Session | None = getattr(request.state, "session", None)
    if not session:
        return JSONResponse({
            "authenticated": False,
            "error": "unauthenticated",
            "login_url": "/login",
        }, status_code=401)
    return JSONResponse({
        "authenticated": True,
        "user_id": session.user_id,
        "display_name": session.display_name,
        "role": session.role,
        "provider": session.provider,
        "expires_at": session.expires_at,
    })


@app.get("/api/auth/providers")
async def api_auth_providers():
    """Hermes'teki /api/auth/providers — kayitli auth provider'lari listele."""
    providers = list_providers()
    return JSONResponse({
        "providers": [
            {
                "name": p.name,
                "display_name": p.display_name,
            }
            for p in providers
        ],
    })


@app.get("/", response_class=HTMLResponse)
async def ana_sayfa(request: Request):
    return templates.TemplateResponse(
        request, "dashboard.html", {}
    )


@app.get("/plugins", response_class=HTMLResponse)
async def plugins_sayfasi(request: Request):
    """Plugin yonetimi (admin)."""
    if not admin_gerekli(getattr(request.state, "session", None)):
        return HTMLResponse(
            content='<div class="container"><h1>🔒 Yetkisiz</h1><p>Bu sayfa icin admin yetkisi gerekli.</p></div>',
            status_code=403,
        )
    return templates.TemplateResponse(
        request, "plugins.html", {}
    )


@app.get("/gateway", response_class=HTMLResponse)
async def gateway_sayfasi(request: Request):
    """Gateway yonetimi (operator+)."""
    if not operator_ustu(getattr(request.state, "session", None)):
        return HTMLResponse(
            content='<div class="container"><h1>🔒 Yetkisiz</h1><p>Bu sayfa icin operator yetkisi gerekli.</p></div>',
            status_code=403,
        )
    return templates.TemplateResponse(
        request, "gateway.html", {}
    )


@app.get("/logs", response_class=HTMLResponse)
async def logs_sayfasi(request: Request):
    return templates.TemplateResponse(
        request, "logs.html", {}
    )


@app.get("/users", response_class=HTMLResponse)
async def users_sayfasi(request: Request):
    """Kullanici yonetimi (admin)."""
    if not admin_gerekli(getattr(request.state, "session", None)):
        return HTMLResponse(
            content='<div class="container"><h1>🔒 Yetkisiz</h1><p>Bu sayfa icin admin yetkisi gerekli.</p></div>',
            status_code=403,
        )
    return templates.TemplateResponse(
        request, "users.html", {}
    )


@app.get("/sandbox", response_class=HTMLResponse)
async def sandbox_sayfasi(request: Request):
    return templates.TemplateResponse(
        request, "sandbox.html", {}
    )


@app.get("/security", response_class=HTMLResponse)
async def security_sayfasi(request: Request):
    """Guvenlik yonetim sayfasi — sandbox, firewall, karantina."""
    return templates.TemplateResponse(
        request, "security.html", {}
    )


# ---------------------------------------------------------------------------
# API — Security (Guvenlik)
# ---------------------------------------------------------------------------


@app.get("/api/security/durum")
async def api_security_durum():
    """Guvenlik genel durum HTML karti."""
    html = []

    try:
        from reymen.guvenlik.docker_sandbox import (
            sandbox_durum, DOCKER_MEVCUT, IMAGE_MEVCUT,
            SUBPROCESS_SANDBOX_OK, NETWORK_RESTRICTION_OK,
        )

        durum = sandbox_durum()
        docker = durum.get("docker", {})

        # Docker Sandbox
        d_ikon = "🟢" if docker.get("docker_mevcut") else "🔴"
        i_ikon = "🟢" if docker.get("image_mevcut") else "🟡"
        sp_ikon = "🟢" if SUBPROCESS_SANDBOX_OK else "🔴"

        html.append(f'<div class="card"><h3>🏖️ Docker Sandbox</h3>')
        html.append(f'<div class="flex">{d_ikon} Docker: {"mevcut" if docker.get("docker_mevcut") else "yok"}</div>')
        html.append(f'<div class="flex">{i_ikon} Image: {"build edilmis" if docker.get("image_mevcut") else "build edilmemis"}</div>')
        html.append(f'<div class="flex">{sp_ikon} Subprocess: {"hazir" if SUBPROCESS_SANDBOX_OK else "yok"}</div>')
        html.append('</div>')

    except ImportError:
        html.append('<div class="card"><h3>🏖️ Docker Sandbox</h3><div class="gri">Sandbox modulu yuklu degil</div></div>')
    except Exception as e:
        html.append(f'<div class="card"><h3>🏖️ Docker Sandbox</h3><div class="tag-no">Hata: {e}</div></div>')

    try:
        from reymen.guvenlik.network_restriction import _VARSAYILAN_NETWORK as nr

        durum = nr.durum
        aktif_ikon = "🟢" if durum['aktif'] else "🔴"
        html.append(f'<div class="card"><h3>🛡️ Network Restriction</h3>')
        html.append(f'<div class="flex">{aktif_ikon} Durum: {"AKTIF" if durum["aktif"] else "PASIF"}</div>')
        html.append(f'<div class="flex">🖥️ Sistem: {durum["sistem"]}</div>')
        html.append(f'<div class="flex">🏠 Izinli: {", ".join(durum["her_zaman_izinli"])}</div>')
        html.append(f'<div class="flex">📋 Kural: {durum["eklenen_kurallar"]}</div>')
        html.append(f'<div class="flex">🌐 Domain: {durum["eklenen_domainler"]} adet</div>')
        if durum["baslangic"]:
            html.append(f'<div class="flex gri">⏰ Baslangic: {durum["baslangic"]}</div>')
        html.append('</div>')

    except ImportError:
        html.append('<div class="card"><h3>🛡️ Network Restriction</h3><div class="gri">Modul yuklu degil</div></div>')
    except Exception as e:
        html.append(f'<div class="card"><h3>🛡️ Network Restriction</h3><div class="tag-no">Hata: {e}</div></div>')

    try:
        from reymen_cli.quarantine import KARANTINA_DIZIN
        if KARANTINA_DIZIN.exists():
            karantina_liste = [f.name for f in KARANTINA_DIZIN.iterdir()]
            karantina_say = len(karantina_liste)
        else:
            karantina_say = 0
        html.append(f'<div class="card"><h3>📦 Karantina</h3>')
        q_ikon = "🟢" if karantina_say == 0 else "🟡"
        html.append(f'<div class="flex">{q_ikon} Dosya Sayisi: {karantina_say}</div>')
        html.append(f'<div class="flex">📁 Dizin: {KARANTINA_DIZIN}</div>')
        html.append('</div>')
    except Exception:
        html.append('<div class="card"><h3>📦 Karantina</h3><div class="gri">Bilgi alinamadi</div></div>')

    return HTMLResponse(content="\n".join(html))


@app.get("/api/security/sandbox/status")
async def api_security_sandbox_status():
    """Docker sandbox ozel durum HTML."""
    try:
        from reymen.guvenlik.docker_sandbox import (
            sandbox_durum_text, DOCKER_MEVCUT, IMAGE_MEVCUT,
        )
        return HTMLResponse(content=f"<pre>{sandbox_durum_text()}</pre>")
    except ImportError:
        return HTMLResponse(content='<div class="gri">Sandbox modulu yuklu degil</div>')


@app.post("/api/security/sandbox/build")
async def api_security_sandbox_build():
    """Docker sandbox image build et."""
    try:
        from reymen.guvenlik.docker_sandbox import docker_image_build, DOCKER_MEVCUT
        if not DOCKER_MEVCUT:
            return HTMLResponse(content='<div class="alert alert-error">❌ Docker yuklu degil</div>')
        sonuc = docker_image_build(zorla=True)
        if "build edildi" in sonuc:
            return HTMLResponse(content=f'<div class="alert alert-success">{sonuc}</div>')
        return HTMLResponse(content=f'<div class="alert alert-warning">{sonuc}</div>')
    except ImportError:
        return HTMLResponse(content='<div class="alert alert-error">❌ Sandbox modulu yuklu degil</div>')
    except Exception as e:
        return HTMLResponse(content=f'<div class="alert alert-error">❌ {e}</div>')


@app.get("/api/security/firewall/status")
async def api_security_firewall_status():
    """Firewall durum HTML."""
    try:
        from reymen.guvenlik.network_restriction import _VARSAYILAN_NETWORK as nr
        durum = nr.durum
        html = []
        aktif_ikon = "🟢" if durum['aktif'] else "🔴"
        html.append(f'<div class="flex">{aktif_ikon} <b>Durum:</b> {"AKTIF" if durum["aktif"] else "PASIF"}</div>')
        html.append(f'<div class="flex">🖥️ <b>Sistem:</b> {durum["sistem"]}</div>')
        html.append(f'<div class="flex">🏠 <b>Izinli IP:</b> {", ".join(durum["her_zaman_izinli"])}</div>')
        html.append(f'<div class="flex">📋 <b>Kural Sayisi:</b> {durum["eklenen_kurallar"]}</div>')
        html.append(f'<div class="flex">🌐 <b>Domain Engelleme:</b> {durum["eklenen_domainler"]} adet</div>')
        if durum["baslangic"]:
            html.append(f'<div class="flex gri"><b>Baslangic:</b> {durum["baslangic"]}</div>')
        return HTMLResponse(content="\n".join(html))
    except ImportError:
        return HTMLResponse(content='<div class="gri">Firewall modulu yuklu degil</div>')
    except Exception as e:
        return HTMLResponse(content=f'<div class="gri">Hata: {e}</div>')


@app.post("/api/security/firewall/apply")
async def api_security_firewall_apply(request: Request):
    """Firewall kisitlamasini uygula."""
    form = await request.form()
    allowlist_str = form.get("allowlist", "").strip()
    block_domains = form.get("block_domains", "false").strip() == "true"

    allowlist = [x.strip() for x in allowlist_str.split(",") if x.strip()]
    allowlist.append("127.0.0.1")

    try:
        from reymen.guvenlik.network_restriction import _VARSAYILAN_NETWORK as nr
        sonuc = nr.apply(allowlist=allowlist, block_domainler=block_domains)
        if sonuc.get("basarili"):
            return HTMLResponse(content=f'<div class="alert alert-success">✅ {sonuc["mesaj"]}</div>')
        return HTMLResponse(content=f'<div class="alert alert-warning">⚠️ {sonuc["mesaj"]}</div>')
    except ImportError:
        return HTMLResponse(content='<div class="alert alert-error">❌ Firewall modulu yuklu degil</div>')
    except Exception as e:
        return HTMLResponse(content=f'<div class="alert alert-error">❌ {e}</div>')


@app.post("/api/security/firewall/remove")
async def api_security_firewall_remove():
    """Firewall kisitlamasini kaldir."""
    try:
        from reymen.guvenlik.network_restriction import _VARSAYILAN_NETWORK as nr
        sonuc = nr.remove()
        if sonuc.get("basarili"):
            return HTMLResponse(content=f'<div class="alert alert-success">✅ {sonuc["mesaj"]}</div>')
        return HTMLResponse(content=f'<div class="alert alert-warning">⚠️ {sonuc["mesaj"]}</div>')
    except ImportError:
        return HTMLResponse(content='<div class="alert alert-error">❌ Firewall modulu yuklu degil</div>')
    except Exception as e:
        return HTMLResponse(content=f'<div class="alert alert-error">❌ {e}</div>')


@app.get("/api/security/quarantine")
async def api_security_quarantine():
    """Karantina listesi HTML."""
    try:
        from reymen_cli.quarantine import KARANTINA_DIZIN
        if not KARANTINA_DIZIN.exists():
            return HTMLResponse(content='<div class="gri">📦 Karantina bos</div>')

        kayitlar = list(KARANTINA_DIZIN.iterdir())
        if not kayitlar:
            return HTMLResponse(content='<div class="gri">📦 Karantina bos</div>')

        html = ['<table class="table"><tr><th>#</th><th>Dosya</th><th>Boyut</th><th>Tarih</th></tr>']
        for i, f in enumerate(sorted(kayitlar, reverse=True)[:50], 1):
            boyut = f.stat().st_size
            tarih = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            html.append(f"<tr><td>{i}</td><td>{f.name}</td><td>{boyut}B</td><td class='gri'>{tarih}</td></tr>")
        html.append("</table>")
        return HTMLResponse(content="\n".join(html))
    except ImportError:
        return HTMLResponse(content='<div class="gri">Karantina modulu yuklu degil</div>')
    except Exception as e:
        return HTMLResponse(content=f'<div class="gri">Hata: {e}</div>')


@app.post("/api/security/quarantine/clean")
async def api_security_quarantine_clean():
    """Karantinayi temizle."""
    try:
        from reymen_cli.quarantine import KARANTINA_DIZIN
        import shutil
        if KARANTINA_DIZIN.exists():
            shutil.rmtree(str(KARANTINA_DIZIN))
            return HTMLResponse(content='<div class="alert alert-success">🧹 Karantina temizlendi</div>')
        return HTMLResponse(content='<div class="gri">Karantina zaten bos</div>')
    except ImportError:
        return HTMLResponse(content='<div class="alert alert-error">❌ Karantina modulu yuklu degil</div>')
    except Exception as e:
        return HTMLResponse(content=f'<div class="alert alert-error">❌ {e}</div>')


@app.get("/kalite", response_class=HTMLResponse)
async def kalite_sayfasi(request: Request):
    return templates.TemplateResponse(
        request, "quality.html", {}
    )


@app.get("/coverage", response_class=HTMLResponse)
async def coverage_sayfasi(request: Request):
    """Coverage rapor sayfası."""
    return templates.TemplateResponse(
        request, "coverage.html", {}
    )


@app.get("/api/coverage/ozet")
async def api_coverage_ozet():
    """Coverage özet kartları HTML."""
    from reymen.sistem.coverage_report import statik_analiz, gecmis_getir
    sonuc = statik_analiz()
    gecmis = gecmis_getir(5)

    yuzde = sonuc.get("yuzde", 0)
    renk = "green" if yuzde >= 70 else "orange" if yuzde >= 40 else "red"

    # Trend oku
    trend = "—"
    if len(gecmis) >= 2:
        onceki = gecmis[-2].get("yuzde", 0)
        fark = yuzde - onceki
        trend = f"📈 +{fark}%" if fark > 0 else f"📉 {fark}%" if fark < 0 else "➡️ ±0"

    son = gecmis[-1].get("tarih", "—")[:16] if gecmis else "Henüz yok"

    html = [
        '<div class="cards" style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.5rem;">',
        f'<div class="card" style="text-align:center;"><h3 style="color:{renk}">{yuzde}%</h3>'
        f'<div class="gri">Kapsama</div><small>{trend}</small></div>',
        f'<div class="card" style="text-align:center;"><h3>{sonuc.get("toplam_modul", 0)}</h3>'
        f'<div class="gri">Modül</div></div>',
        f'<div class="card" style="text-align:center;"><h3>{sonuc.get("toplam_satir", 0):,}</h3>'
        f'<div class="gri">Satır</div></div>',
        f'<div class="card" style="text-align:center;"><h3>{sonuc.get("import_edilebilen", 0)} / {sonuc.get("import_edilemeyen", 0)}</h3>'
        f'<div class="gri">İçe Aktarma</div></div>',
        f'<div class="card" style="text-align:center;"><h3 style="font-size:1rem;">{son}</h3>'
        f'<div class="gri">Son Ölçüm</div></div>',
        '</div>',
    ]
    return HTMLResponse(content="\n".join(html))


@app.get("/api/coverage/gecmis")
async def api_coverage_gecmis():
    """Coverage geçmiş tablosu HTML."""
    from reymen.sistem.coverage_report import gecmis_getir
    gecmis = gecmis_getir(30)

    if not gecmis:
        return HTMLResponse(content='<div class="gri">Henüz coverage verisi yok. "Tam Tarama" yapın.</div>')

    html = ['<table class="table"><thead><tr>']
    html.append('<th>Tarih</th><th>Coverage</th><th>Satır</th><th>Süre</th><th>Tür</th>')
    html.append('</tr></thead><tbody>')

    for k in reversed(gecmis):
        tarih = k.get("tarih", "")[:16]
        yuzde = k.get("yuzde", 0)
        renk = "green" if yuzde >= 70 else "orange" if yuzde >= 40 else "red"
        satir = f"{k.get('toplam_satir', 0):,}" if k.get("toplam_satir") else "—"
        sure = f'{k.get("sure", 0)}s' if k.get("sure") else "—"
        tur = {"coverage": "🎯", "statik": "📊"}.get(k.get("tur", ""), "—")
        html.append(f'<tr><td>{tarih}</td>'
                    f'<td><b style="color:{renk}">{yuzde}%</b></td>'
                    f'<td>{satir}</td><td>{sure}</td><td>{tur}</td></tr>')

    html.append('</tbody></table>')
    return HTMLResponse(content="\n".join(html))


@app.get("/api/coverage/gecmis-json")
async def api_coverage_gecmis_json():
    """Coverage geçmişi JSON (Chart.js için)."""
    from reymen.sistem.coverage_report import gecmis_getir
    return gecmis_getir(50)


@app.post("/api/coverage/calistir")
async def api_coverage_calistir(hizli: bool = False):
    """Coverage çalıştır."""
    from reymen.sistem.coverage_report import calistir, statik_analiz

    if hizli:
        sonuc = calistir(hizli=True)
    else:
        # Tam: statik analiz (güvenilir)
        sonuc = statik_analiz()

    if sonuc.get("basari"):
        yuzde = sonuc.get("yuzde", 0)
        renk = "green" if yuzde >= 70 else "orange" if yuzde >= 40 else "red"
        html = [
            '<div style="display:flex;gap:1rem;align-items:center;">',
            f'<div style="font-size:3rem;font-weight:bold;color:{renk};">{yuzde}%</div>',
            '<div>',
            f'<div>Toplam: {sonuc.get("toplam_satir", 0):,} satır</div>',
            f'<div>Modül: {sonuc.get("toplam_modul", 0)}</div>',
            f'<div>Süre: {sonuc.get("sure", 0)}s</div>',
            '</div></div>',
        ]
        return HTMLResponse(content="\n".join(html))
    return HTMLResponse(
        content=f'<div class="alert alert-error">❌ Hata: {sonuc.get("hata", "?")}</div>'
    )


@app.get("/maliyet", response_class=HTMLResponse)
async def maliyet_sayfasi(request: Request):
    return templates.TemplateResponse(
        request, "cost.html", {}
    )


@app.get("/kanban", response_class=HTMLResponse)
async def kanban_sayfasi(request: Request):
    return templates.TemplateResponse(
        request, "kanban.html", {}
    )


@app.get("/sistem", response_class=HTMLResponse)
async def sistem_sayfasi(request: Request):
    """Sistem yonetimi (admin)."""
    if not admin_gerekli(getattr(request.state, "session", None)):
        return HTMLResponse(
            content='<div class="container"><h1>🔒 Yetkisiz</h1><p>Bu sayfa icin admin yetkisi gerekli.</p></div>',
            status_code=403,
        )
    return templates.TemplateResponse(
        request, "sistem.html", {}
    )


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# API — Görsel Üretim JSON (/api/hermes/media)
# ---------------------------------------------------------------------------


@app.get("/api/hermes/media/backends")
async def api_media_backends():
    """JSON: Kayıtlı görsel üretim backend'leri."""
    try:
        from reymen.arac.image_gen_engine import image_gen_engine_listele
        durum_text = image_gen_engine_listele()
        backends = []
        for line in durum_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            hazir = "hazir" in line
            backends.append({
                "text": line,
                "ready": hazir,
            })
        return JSONResponse({"backends": backends})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/hermes/media/generate")
async def api_media_generate(request: Request):
    """JSON: Görsel üret."""
    try:
        data = await request.json()
    except Exception:
        data = await request.form()

    prompt = data.get("prompt", "").strip() if isinstance(data, dict) else ""
    en = str(data.get("en", "1024")) if isinstance(data, dict) else "1024"
    boy = str(data.get("boy", "1024")) if isinstance(data, dict) else "1024"
    backend = str(data.get("backend", "")) if isinstance(data, dict) else ""

    if not prompt:
        return JSONResponse({"error": "Prompt boş olamaz"}, status_code=400)

    try:
        from reymen.arac.image_gen_engine import resim_olustur
        sonuc = resim_olustur(prompt=prompt, en=en, boy=boy, backend=backend)

        # Parse MEDIA blok
        import re
        img_url = ""
        aciklama = ""
        hata = sonuc if ("Hata" in sonuc) else ""

        src_match = re.search(r'src="([^\"]+)"', sonuc)
        if src_match:
            img_url = src_match.group(1)
        aciklama_match = re.search(r'\[MEDIA[^\]]*\][\s\S]*?\n(.+?)\n\[/MEDIA\]', sonuc)
        if aciklama_match:
            aciklama = aciklama_match.group(1)

        return JSONResponse({
            "success": bool(img_url),
            "image_url": img_url,
            "description": aciklama,
            "raw": sonuc[:500],
            "error": hata if not img_url else "",
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Routes — Görsel Üretim (/media)
# ---------------------------------------------------------------------------


@app.get("/media", response_class=HTMLResponse)
async def media_sayfasi(request: Request):
    """Görsel üretim sayfası — prompt gir + backend seç."""
    return templates.TemplateResponse(
        request, "media.html", {}
    )


@app.post("/media/generate")
async def media_generate(request: Request):
    """Görsel üretim isteği — image_gen_engine.py resim_olustur() çağırır."""
    form = await request.form()
    prompt = form.get("prompt", "").strip()
    en = form.get("en", "1024").strip()
    boy = form.get("boy", "1024").strip()
    backend = form.get("backend", "").strip()

    if not prompt:
        return HTMLResponse(
            content='<div class="alert alert-error">❌ Prompt boş olamaz.</div>'
        )

    try:
        from reymen.arac.image_gen_engine import resim_olustur

        sonuc = resim_olustur(prompt=prompt, en=en, boy=boy, backend=backend)

        # [MEDIA] bloklu sonucu güzel göster
        if sonuc.startswith("[RESIM_OLUSTUR") and "Hata" in sonuc:
            css = "alert alert-error"
        elif sonuc.startswith("[RESIM_OLUSTUR") and "Uyari" in sonuc:
            css = "alert alert-warning"
        elif "[MEDIA" in sonuc:
            # Görsel URL'sini çıkar
            import re
            src_match = re.search(r'src="([^"]+)"', sonuc)
            aciklama_match = re.search(r'\[MEDIA[^\]]*\][\s\S]*?\n(.+?)\n\[/MEDIA\]', sonuc)
            media_html = '<div class="alert alert-success">✅ Görsel başarıyla üretildi!</div>'
            if src_match:
                img_url = src_match.group(1)
                media_html += '<div style="margin-top:1rem;text-align:center;">'
                media_html += f'<img src="{img_url}" alt="Üretilen görsel" style="max-width:100%;max-height:500px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);">'
                media_html += '<div style="margin-top:0.5rem;">'
                media_html += f'<a href="{img_url}" target="_blank" class="btn btn-sm">🔗 Aç</a> '
                media_html += f'<button class="btn btn-sm" onclick="navigator.clipboard.writeText(\'{img_url}\')">📋 Kopyala</button>'
                media_html += '</div></div>'
            if aciklama_match:
                media_html += f'<div class="gri" style="margin-top:0.5rem;font-size:0.85rem;">{aciklama_match.group(1)}</div>'
            return HTMLResponse(content=media_html)
        else:
            css = "alert"
        return HTMLResponse(
            content=f'<div class="{css}"><pre style="white-space:pre-wrap;margin:0;">{sonuc}</pre></div>'
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.exception("[media/generate] Görsel üretim hatasi:")
        return HTMLResponse(
            content=f'<div class="alert alert-error">❌ Görsel üretim hatası: {e}<br><pre style="font-size:0.75rem;margin-top:0.5rem;">{tb[:500]}</pre></div>'
        )


@app.get("/media/generate/list-backends")
async def media_list_backends():
    """Kayıtlı backend'lerin durumunu listele."""
    try:
        from reymen.arac.image_gen_engine import image_gen_engine_listele
        durum = image_gen_engine_listele()
        html_lines = []
        for line in durum.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "hazir" in line:
                html_lines.append(f'<div class="flex"><span>🟢 {line}</span></div>')
            elif "eksik" in line or "Hata" in line:
                html_lines.append(f'<div class="flex"><span>🔴 {line}</span></div>')
            else:
                html_lines.append(f'<div class="flex"><span>{line}</span></div>')
        return HTMLResponse(content="\n".join(html_lines))
    except Exception as e:
        return HTMLResponse(
            content=f'<div class="alert alert-error">❌ {e}</div>'
        )


# ---------------------------------------------------------------------------
# Migration / Alembic
# ---------------------------------------------------------------------------


@app.get("/migration", response_class=HTMLResponse)
async def migration_sayfasi(request: Request):
    """Alembic migration yönetim sayfası (admin)."""
    if not admin_gerekli(getattr(request.state, "session", None)):
        return HTMLResponse(
            content='<div class="container"><h1>🔒 Yetkisiz</h1><p>Bu sayfa icin admin yetkisi gerekli.</p></div>',
            status_code=403,
        )
    return templates.TemplateResponse(
        request, "migration.html", {}
    )


def _alembic_cmd(*args: str) -> str:
    """Alembic komutunu subprocess ile çalıştır, HTML çıktı döndür."""
    import subprocess
    cmd = [
        sys.executable, "-m", "alembic", "--config",
        str(PROJE_KOK / "alembic.ini"),
        *args,
    ]
    try:
        result = subprocess.run(
            cmd, cwd=str(PROJE_KOK),
            capture_output=True, text=True, timeout=120,
        )
        output = result.stdout or ""
        if result.stderr:
            # Alembic log'ları stderr'e yazar, onları da ekle
            output += "\n" + result.stderr
        if result.returncode != 0:
            return f'<div class="alert alert-error">❌ Hata (exit: {result.returncode})</div><pre style="max-height:400px;overflow:auto;">{output}</pre>'
        return f'<pre style="max-height:400px;overflow:auto;">{output.strip()}</pre>'
    except subprocess.TimeoutExpired:
        return '<div class="alert alert-error">❌ Zaman aşımı (120s)</div>'
    except FileNotFoundError:
        return '<div class="alert alert-error">❌ Alembic bulunamadı. <code>pip install alembic</code></div>'
    except Exception as e:
        return f'<div class="alert alert-error">❌ {e}</div>'


@app.get("/api/migration/status")
async def api_migration_status():
    """Migration durumu: current revision + history."""
    cur = _alembic_cmd("current")
    hist = _alembic_cmd("history", "--verbose")
    return HTMLResponse(
        content=f"<h4>📌 Current Revision</h4>{cur}<hr><h4>📜 History</h4>{hist}"
    )


@app.get("/api/migration/history")
async def api_migration_history():
    """Migration geçmişi."""
    return HTMLResponse(content=_alembic_cmd("history", "--verbose"))


@app.get("/api/migration/check")
async def api_migration_check():
    """Bekleyen migrasyon kontrolü."""
    cur_result = _alembic_cmd("current")
    heads_result = _alembic_cmd("heads")
    return HTMLResponse(
        content=f"<h4>📌 Current</h4>{cur_result}<hr><h4>🔍 Heads</h4>{heads_result}"
    )


@app.post("/api/migration/upgrade")
async def api_migration_upgrade(request: Request):
    """Migrasyon yükselt. Varsayılan: head."""
    form = await request.form()
    revision = form.get("revision", "head").strip() or "head"
    result = _alembic_cmd("upgrade", revision)
    return HTMLResponse(
        content=f"<h4>🔼 Upgrade: {revision}</h4>{result}"
    )


@app.post("/api/migration/downgrade")
async def api_migration_downgrade(request: Request):
    """Migrasyon geri al. Varsayılan: -1."""
    form = await request.form()
    revision = form.get("revision", "-1").strip() or "-1"
    result = _alembic_cmd("downgrade", revision)
    return HTMLResponse(
        content=f"<h4>🔽 Downgrade: {revision}</h4>{result}"
    )


@app.post("/api/migration/create")
async def api_migration_create(request: Request):
    """Yeni migrasyon dosyası oluştur (--autogenerate)."""
    form = await request.form()
    message = form.get("message", "").strip()
    if not message:
        return HTMLResponse(
            content='<div class="alert alert-error">❌ Mesaj gerekli</div>'
        )
    result = _alembic_cmd("revision", "--autogenerate", "-m", message)
    return HTMLResponse(
        content=f"<h4>🆕 Yeni Migrasyon: {message}</h4>{result}"
    )


# ---------------------------------------------------------------------------
# API — Dashboard
# ---------------------------------------------------------------------------


@app.get("/api/durum")
async def api_durum(request: Request):
    """Sistem durumu HTML snippet."""
    satirlar = []
    
    # Process durumları
    tumu = process_manager.tumu()
    for p in tumu:
        dot = "🟢" if p.get("durum") == "calisiyor" else "🔴"
        satirlar.append(f"<div class='flex'><span>{dot} <b>{p['ad']}</b> — {p['durum']}</span></div>")

    if not tumu:
        satirlar.append("<div class='flex gri'>Aktif process yok</div>")

    # Log son satır
    son = log_streamer.son_satir
    satirlar.append(f"<div class='flex gri' style='margin-top:8px;font-size:0.8rem'>📋 {son[:100]}</div>")
    
    satirlar.append(f"<div class='flex gri' style='font-size:0.75rem'>Son: {datetime.now().strftime('%H:%M:%S')}</div>")
    
    return HTMLResponse(content="\n".join(satirlar))


@app.get("/api/moduller/ozet")
async def api_moduller_ozet():
    """Modül özet bilgisi."""
    try:
        moduller = modul_tarayici.tara()
        kategoriler = modul_kategorileri(moduller)
        toplam = len(moduller)
        yuklu = sum(1 for m in moduller if m.yuklu)
        kat_sayisi = len(kategoriler)
        return HTMLResponse(
            content=f"<div><b>{toplam}</b> modül (<b>{yuklu}</b> yüklü, <b>{kat_sayisi}</b> kategori)</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='tag-no'>Hata: {e}</div>")


@app.get("/api/log/son")
async def api_log_son():
    """Son log satırı."""
    son = log_streamer.son_satir
    if len(son) > 150:
        son = son[:150] + "..."
    return HTMLResponse(content=f"<pre class='gri' style='font-size:0.8rem'>{son}</pre>")


@app.get("/api/log/tail")
async def api_log_tail(n: int = 50):
    """Son N log satırı."""
    satirlar = log_streamer.tail(n)
    return HTMLResponse(
        content="<pre>" + "\n".join(satirlar) + "</pre>"
    )

# ---------------------------------------------------------------------------
# API — Pluginler
# ---------------------------------------------------------------------------


@app.get("/api/plugins")
async def api_plugins():
    """Plugin listesi HTML tablosu."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        pluginler = yonetici.list_plugins()
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Plugin sistemi yüklenemedi: {e}</div>")

    if not pluginler:
        return HTMLResponse(content="<div class='gri'>Henüz plugin yok</div>")

    satirlar = ["<table><tr><th>Plugin</th><th>Açıklama</th><th>Durum</th><th>İşlem</th></tr>"]
    for p in pluginler:
        ad = p.get("ad", p.get("name", "?"))
        aciklama = p.get("aciklama", p.get("description", ""))[:60]
        aktif = p.get("aktif", p.get("enabled", False))
        tag = "tag-yes" if aktif else "tag-no"
        durum_text = "Aktif" if aktif else "Pasif"
        toggle_action = "devre_disina_al" if aktif else "aktif_et"
        toggle_text = "🔴 Devre Dışı" if aktif else "🟢 Aktif Et"
        satirlar.append(
            f"<tr>"
            f"<td>{ad}</td>"
            f"<td class='gri'>{aciklama}</td>"
            f"<td><span class='tag {tag}'>{durum_text}</span></td>"
            f"<td><button class='btn btn-sm' hx-post='/api/plugins/{toggle_action}/{ad}' "
            f"hx-target='#plugin-sonuc'>{toggle_text}</button></td>"
            f"</tr>"
        )
    satirlar.append("</table>")
    return HTMLResponse(content="\n".join(satirlar))


@app.get("/api/plugins/ozet")
async def api_plugins_ozet():
    """Plugin özet bilgisi."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        pluginler = yonetici.list_plugins()
        toplam = len(pluginler)
        aktif = sum(1 for p in pluginler if p.get("aktif", p.get("enabled", False)))
        return HTMLResponse(
            content=f"<div><b>{toplam}</b> plugin, <b>{aktif}</b> aktif</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='gri'>Plugin sistemi: {e}</div>")


@app.post("/api/plugins/aktif_et/{ad}")
async def api_plugin_aktif_et(ad: str):
    """Plugin'i aktif et."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        yonetici.enable_plugin(ad)
        return HTMLResponse(content=f"<div class='alert alert-success'>✅ {ad} aktif edildi</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ {e}</div>")


@app.post("/api/plugins/devre_disina_al/{ad}")
async def api_plugin_devre_disina_al(ad: str):
    """Plugin'i devre dışı bırak."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        yonetici.disable_plugin(ad)
        return HTMLResponse(content=f"<div class='alert alert-success'>✅ {ad} devre dışı</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ {e}</div>")


@app.get("/api/plugins/tazele")
async def api_plugins_tazele():
    """Plugin listesini yenile."""
    return await api_plugins()


@app.post("/api/plugins/export/{ad}")
async def api_plugin_export(ad: str):
    """Plugin'i .reyplugin paketine dışa aktar."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        cikti = PROJE_KOK / f"{ad}.reyplugin"
        sonuc = yonetici.export_plugin(ad, str(cikti))
        if sonuc.startswith("[OK]"):
            # Dosyayı oku ve indirilebilir olarak döndür
            icerik = cikti.read_bytes()
            cikti.unlink(missing_ok=True)  # geçici dosyayı temizle
            from fastapi.responses import Response
            return Response(
                content=icerik,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{ad}.reyplugin"',
                },
            )
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ {sonuc}</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Export hatasi: {e}</div>")


@app.post("/api/plugins/import")
async def api_plugin_import(request: Request):
    """.reyplugin paketini içe aktar (multipart form-data ile dosya yükleme)."""
    try:
        form = await request.form()
        dosya = form.get("dosya")
        if not dosya:
            return HTMLResponse(content="<div class='alert alert-error'>❌ Dosya gerekli</div>")
        
        # Dosyayı geçici konuma yaz
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / dosya.filename
        with open(str(tmp), "wb") as f:
            f.write(await dosya.read())
        
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        sonuc = yonetici.import_plugin(str(tmp))
        
        # Geçici dosyayı temizle
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()
        
        css = "success" if sonuc.startswith("[OK]") else "error"
        return HTMLResponse(content=f"<div class='alert alert-{css}'>{'✅' if sonuc.startswith('[OK]') else '❌'} {sonuc}</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Import hatasi: {e}</div>")

# ---------------------------------------------------------------------------
# API — Kullanıcı Yönetimi
# ---------------------------------------------------------------------------


@app.get("/api/users")
async def api_users():
    """Kullanıcı listesi HTML tablosu."""
    kullanicilar = user_manager.list_users()
    satirlar = ['<table><tr><th>#</th><th>Kullanıcı</th><th>Rol</th><th>İşlem</th></tr>']
    for i, u in enumerate(kullanicilar, 1):
        username = u.get("username", "?")
        role = u.get("role", "viewer")
        satirlar.append(
            f"<tr><td>{i}</td><td>{username}</td><td>{role}</td>"
            f"<td><button class='btn btn-sm btn-danger' "
            f"hx-post='/api/users/sil/{username}' hx-target='#sonuc' "
            f"hx-confirm='{username} silinsin mi?'>🗙 Sil</button></td></tr>"
        )
    satirlar.append("</table>")
    return HTMLResponse(content="\n".join(satirlar))


@app.post("/api/users/ekle")
async def api_users_ekle(request: Request):
    """Yeni kullanıcı ekle (admin/operator/viewer rolleriyle)."""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()
    role = form.get("role", "viewer").strip().lower()
    if not username or not password:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Boş alan bırakma</div>")
    if len(password) < 4:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Şifre en az 4 karakter</div>")
    ok, msg = user_manager.kullanici_ekle(username, password, role=role)
    css = "success" if ok else "error"
    return HTMLResponse(content=f"<div class='alert alert-{css}'>{'✅' if ok else '❌'} {msg}</div>")


@app.post("/api/users/sifre")
async def api_users_sifre(request: Request):
    """Şifre değiştir."""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()
    if not username or not password:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Boş alan bırakma</div>")
    ok, msg = user_manager.set_password(username, password)
    css = "success" if ok else "error"
    return HTMLResponse(content=f"<div class='alert alert-{css}'>{'✅' if ok else '❌'} {msg}</div>")


@app.post("/api/users/sil/{username}")
async def api_users_sil(username: str):
    """Kullanıcı sil."""
    try:
        dosya = user_manager.config.users_file
        if not dosya.exists():
            return HTMLResponse(content="<div class='alert alert-error'>❌ users.json yok</div>")
        import json
        users = json.loads(dosya.read_text(encoding="utf-8"))
        if username in users:
            del users[username]
            dosya.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")
            user_manager._users = users
            return HTMLResponse(content=f"<div class='alert alert-success'>✅ {username} silindi</div>")
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ {username} bulunamadı</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ {e}</div>")

# ---------------------------------------------------------------------------
# API — Gateway
# ---------------------------------------------------------------------------


@app.get("/api/gateway")
async def api_gateway():
    """Gateway servis durumları."""
    tumu = process_manager.tumu()
    if not tumu:
        return HTMLResponse(content="<div class='gri'>Aktif gateway servisi yok</div>")

    satirlar = ["<table><tr><th>Servis</th><th>Durum</th><th>PID</th><th>Port</th></tr>"]
    for p in tumu:
        durum = p.get("durum", "?")
        dot = "🟢" if durum == "calisiyor" else "🔴"
        satirlar.append(
            f"<tr><td>{p.get('ad', '?')}</td>"
            f"<td>{dot} {durum}</td>"
            f"<td>{p.get('pid', '-') or '-'}</td>"
            f"<td>{p.get('port', '-')}</td></tr>"
        )
    satirlar.append("</table>")
    return HTMLResponse(content="\n".join(satirlar))


@app.get("/api/gateway/ozet")
async def api_gateway_ozet():
    """Gateway özet."""
    tumu = process_manager.tumu()
    calisan = sum(1 for p in tumu if p.get("durum") == "calisiyor")
    return HTMLResponse(
        content=f"<div><b>{calisan}</b>/<b>{len(tumu)}</b> servis çalışıyor</div>"
    )


@app.get("/api/gateway/ayarlar")
async def api_gateway_ayarlar():
    """Gateway ayarları."""
    env_yolu = PROJE_KOK / ".env"
    ayarlar = {}
    if env_yolu.exists():
        with open(str(env_yolu), encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if satir and not satir.startswith("#") and "=" in satir:
                    k, v = satir.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
                        # Maskele
                        ayarlar[k] = v[:6] + "..." + v[-4:] if len(v) > 12 else "***"
                    elif k in ("WEB_UI_SECRET",):
                        ayarlar[k] = "***"
                    else:
                        ayarlar[k] = v

    if not ayarlar:
        return HTMLResponse(content="<div class='gri'>.env dosyası bulunamadı</div>")

    satirlar = ["<table><tr><th>Anahtar</th><th>Değer</th></tr>"]
    for k, v in ayarlar.items():
        satirlar.append(f"<tr><td>{k}</td><td class='gri'>{v}</td></tr>")
    satirlar.append("</table>")
    return HTMLResponse(content="\n".join(satirlar))


@app.post("/api/gateway/restart")
async def api_gateway_restart():
    """Gateway yeniden başlat."""
    try:
        process_manager.durdur("gateway")
        # Kısa bekle
        await asyncio.sleep(0.5)
        ok = process_manager.baslat(
            "gateway",
            [sys.executable, "-m", "reymen.web_ui"],
            port=5000,
        )
        if ok:
            return HTMLResponse(content="<div class='alert alert-success'>✅ Gateway yeniden başlatıldı</div>")
        return HTMLResponse(content="<div class='alert alert-error'>❌ Başlatılamadı</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


@app.post("/api/gateway/baslat")
async def api_gateway_baslat():
    """Gateway başlat."""
    try:
        durum = process_manager.durum("gateway")
        if durum.get("durum") == "calisiyor":
            return HTMLResponse(content="<div class='alert alert-success'>✅ Zaten çalışıyor</div>")
        ok = process_manager.baslat(
            "gateway",
            [sys.executable, "-m", "reymen.web_ui"],
            port=5000,
        )
        if ok:
            return HTMLResponse(content="<div class='alert alert-success'>✅ Gateway başlatıldı</div>")
        return HTMLResponse(content="<div class='alert alert-error'>❌ Başlatılamadı</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


@app.post("/api/gateway/durdur")
async def api_gateway_durdur():
    """Gateway durdur."""
    try:
        process_manager.durdur("gateway", force=True)
        return HTMLResponse(content="<div class='alert alert-success'>✅ Gateway durduruldu</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


@app.post("/api/bot/test")
async def api_bot_test():
    """Bot bağlantı testi."""
    try:
        import urllib.request
        import urllib.error
        env_yolu = PROJE_KOK / ".env"
        token = ""
        if env_yolu.exists():
            for satir in env_yolu.read_text(encoding="utf-8").splitlines():
                if satir.strip().startswith("TELEGRAM_BOT_TOKEN"):
                    token = satir.split("=", 1)[1].strip().strip('"').strip("'")

        if not token:
            return HTMLResponse(content="<div class='tag-no'>❌ TELEGRAM_BOT_TOKEN yok</div>")

        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                bot_info = data.get("result", {})
                return HTMLResponse(
                    content=f"<div class='alert alert-success'>✅ @{bot_info.get('username', '?')} bağlantı başarılı</div>"
                )
        return HTMLResponse(content="<div class='alert alert-error'>❌ API hatası</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


# ---------------------------------------------------------------------------
# API — Telegram Özel
# ---------------------------------------------------------------------------


@app.get("/api/gateway/telegram")
async def api_gateway_telegram():
    """Telegram bot durumu + bilgisi."""
    # Token var mı?
    token = _env_oku("TELEGRAM_BOT_TOKEN", "")
    chat_id = _env_oku("TELEGRAM_CHAT_ID", "")

    if not token:
        return HTMLResponse(content="<div class='alert alert-error'>❌ TELEGRAM_BOT_TOKEN yok</div>")

    # Bot bilgisi al (getMe)
    bot_username = "?"
    bot_online = False
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/getMe")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            if data.get("ok"):
                bot_username = data["result"].get("username", "?")
                bot_online = True
    except Exception:
        bot_online = False

    # Process kontrol
    durum = process_manager.durum("telegram_bot")

    satirlar = [
        f"<div class='flex'><span>{'🟢' if bot_online else '🔴'} <b>@{bot_username}</b></span></div>",
        f"<div class='flex gri' style='font-size:0.85rem'>Token: {'✅' if token else '❌'} mevcut</div>",
    ]
    if chat_id:
        satirlar.append(f"<div class='flex gri' style='font-size:0.85rem'>Hedef Chat ID: {chat_id}</div>")
    else:
        satirlar.append("<div class='flex gri' style='font-size:0.85rem'>Hedef Chat ID: Herkese açık</div>")

    bot_durum = durum.get("durum", "durduruldu")
    dot = "🟢" if bot_durum == "calisiyor" else "🔴"
    satirlar.append(f"<div class='flex' style='margin-top:8px'><span>{dot} Bot process: {bot_durum}</span></div>")

    return HTMLResponse(content="\n".join(satirlar))


@app.post("/api/gateway/telegram/baslat")
async def api_gateway_telegram_baslat():
    """Telegram bot process'ini başlat."""
    tg_yolu = PROJE_KOK / "reymen" / "ag" / "telegram_bot.py"
    if not tg_yolu.exists():
        return HTMLResponse(content="<div class='alert alert-error'>❌ telegram_bot.py bulunamadı</div>")

    ok = process_manager.baslat(
        "telegram_bot",
        [sys.executable, str(tg_yolu)],
        port=0,  # Telegram botu için port gerekmez
        log_dosyasi=PROJE_KOK / "logs" / "telegram_bot.log",
    )
    if ok:
        return HTMLResponse(content="<div class='alert alert-success'>✅ Telegram bot başlatıldı</div>")
    return HTMLResponse(content="<div class='alert alert-error'>❌ Başlatılamadı</div>")


@app.post("/api/gateway/telegram/durdur")
async def api_gateway_telegram_durdur():
    """Telegram bot process'ini durdur."""
    process_manager.durdur("telegram_bot", force=True)
    return HTMLResponse(content="<div class='alert alert-success'>✅ Telegram bot durduruldu</div>")


@app.post("/api/gateway/telegram/mesaj")
async def api_gateway_telegram_mesaj(request: Request):
    """Telegram üzerinden mesaj gönder."""
    form = await request.form()
    metin = form.get("metin", "").strip()
    hedef = form.get("chat_id", "").strip()

    if not metin:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Mesaj boş</div>")

    token = _env_oku("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return HTMLResponse(content="<div class='alert alert-error'>❌ TELEGRAM_BOT_TOKEN yok</div>")

    chat_id = hedef or _env_oku("TELEGRAM_CHAT_ID", "")
    if not chat_id:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Hedef Chat ID yok</div>")

    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": metin}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            if resp.get("ok"):
                return HTMLResponse(content=f"<div class='alert alert-success'>✅ Mesaj gönderildi → {chat_id}</div>")
            return HTMLResponse(content=f"<div class='alert alert-error'>❌ Telegram hatası: {resp.get('description', '?')}</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


@app.post("/api/gateway/test-mesaj")
async def api_gateway_test_mesaj():
    """Varsayılan chat_id'e test mesajı gönder."""
    token = _env_oku("TELEGRAM_BOT_TOKEN", "")
    chat_id = _env_oku("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Token veya Chat ID yok</div>")

    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": "🧪 Test mesajı — ReYMeN Web UI",
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return HTMLResponse(content="<div class='alert alert-success'>✅ Test mesajı gönderildi 📨</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


# _env_oku helper
def _env_oku(anahtar: str, varsayilan: str = "") -> str:
    """.env dosyasından değer oku."""
    env_yolu = PROJE_KOK / ".env"
    if not env_yolu.exists():
        return varsayilan
    for satir in env_yolu.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if satir.startswith("#") or "=" not in satir:
            continue
        k, v = satir.split("=", 1)
        if k.strip() == anahtar:
            return v.strip().strip('"').strip("'")
    # Hermes env'de de ara
    hermes_env = Path.home() / "AppData" / "Local" / "hermes" / "profiles" / "kiral38" / ".env"
    if hermes_env.exists():
        for satir in hermes_env.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir.startswith("#") or "=" not in satir:
                continue
            k, v = satir.split("=", 1)
            if k.strip() == anahtar:
                return v.strip().strip('"').strip("'")
    return varsayilan


# ---------------------------------------------------------------------------
# API — Discord
# ---------------------------------------------------------------------------


@app.get("/api/gateway/discord")
async def api_gateway_discord():
    """Discord bot durumu + bilgisi."""
    token = _env_oku("DISCORD_BOT_TOKEN", "")

    if not token:
        return HTMLResponse(content="<div class='alert alert-error'>❌ DISCORD_BOT_TOKEN yok</div>")

    # Token doğrulama (Discord API /users/@me)
    bot_username = "?"
    bot_online = False
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            bot_username = data.get("username", "?") + "#" + data.get("discriminator", "0")
            bot_online = True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return HTMLResponse(content="<div class='alert alert-error'>❌ Token geçersiz (401)</div>")
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Discord API: {e.code}</div>")
    except Exception:
        bot_online = False

    # Process kontrol
    durum = process_manager.durum("discord_bot")
    bot_durum = durum.get("durum", "durduruldu")

    satirlar = [
        f"<div class='flex'><span>{'🟢' if bot_online else '🔴'} <b>{bot_username}</b></span></div>",
        f"<div class='flex gri' style='font-size:0.85rem'>Token: {'✅' if token else '❌'} mevcut</div>",
    ]

    dot = "🟢" if bot_durum == "calisiyor" else "🔴"
    satirlar.append(f"<div class='flex' style='margin-top:8px'><span>{dot} Bot process: {bot_durum}</span></div>")

    return HTMLResponse(content="\n".join(satirlar))


@app.post("/api/gateway/discord/baslat")
async def api_gateway_discord_baslat():
    """Discord bot process'ini başlat."""
    bot_yolu = PROJE_KOK / "reymen" / "ag" / "discord_bot.py"
    if not bot_yolu.exists():
        return HTMLResponse(content="<div class='alert alert-error'>❌ discord_bot.py bulunamadı</div>")

    ok = process_manager.baslat(
        "discord_bot",
        [sys.executable, str(bot_yolu)],
        port=0,
        log_dosyasi=PROJE_KOK / "logs" / "discord_bot.log",
    )
    if ok:
        return HTMLResponse(content="<div class='alert alert-success'>✅ Discord bot başlatıldı</div>")
    return HTMLResponse(content="<div class='alert alert-error'>❌ Başlatılamadı</div>")


@app.post("/api/gateway/discord/durdur")
async def api_gateway_discord_durdur():
    """Discord bot process'ini durdur."""
    process_manager.durdur("discord_bot", force=True)
    return HTMLResponse(content="<div class='alert alert-success'>✅ Discord bot durduruldu</div>")


@app.post("/api/gateway/discord/mesaj")
async def api_gateway_discord_mesaj(request: Request):
    """Discord kanalına REST ile mesaj gönder."""
    form = await request.form()
    kanal_id = form.get("kanal_id", "").strip()
    metin = form.get("metin", "").strip()

    if not metin or not kanal_id:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Kanal ID ve mesaj gerekli</div>")

    token = _env_oku("DISCORD_BOT_TOKEN", "")
    if not token:
        return HTMLResponse(content="<div class='alert alert-error'>❌ DISCORD_BOT_TOKEN yok</div>")

    try:
        data = json.dumps({"content": metin}).encode()
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{kanal_id}/messages",
            data=data, method="POST",
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            return HTMLResponse(
                content=f"<div class='alert alert-success'>✅ Mesaj gönderildi → {kanal_id}</div>"
            )
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Discord {e.code}: {body}</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


# ---------------------------------------------------------------------------
# API — SMS (Twilio)
# ---------------------------------------------------------------------------

from reymen.web_ui.sms import sms_gonder, bakiye_kontrol


@app.get("/api/gateway/sms")
async def api_gateway_sms():
    """SMS durumu — Twilio hesap bilgisi."""
    sid = _env_oku("TWILIO_ACCOUNT_SID", "")
    from_num = _env_oku("TWILIO_FROM_NUMBER", "")

    if not sid and not from_num:
        return HTMLResponse(
            content="<div class='alert alert-error'>❌ Twilio ayarları yok</div>"
        )

    satirlar = [
        f"<div class='flex gri' style='font-size:0.85rem'>Account SID: {'✅' if sid else '❌'}</div>",
        f"<div class='flex gri' style='font-size:0.85rem'>Gönderen No: {from_num or '❌'}</div>",
    ]

    # Bakiye kontrol (opsiyonel)
    if sid:
        try:
            bakiye = bakiye_kontrol()
            if bakiye.get("ok"):
                satirlar.append(
                    f"<div class='flex' style='margin-top:8px'>"
                    f"🟢 Hesap: <b>{bakiye.get('friendly_name', '?')}</b></div>"
                )
        except Exception:
            pass

    return HTMLResponse(content="\n".join(satirlar))


@app.post("/api/gateway/sms/gonder")
async def api_gateway_sms_gonder(request: Request):
    """SMS gönder."""
    form = await request.form()
    telefon = form.get("telefon", "").strip()
    mesaj = form.get("mesaj", "").strip()

    if not telefon or not mesaj:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Telefon ve mesaj gerekli</div>")

    # Telefon numarası temizleme
    telefon = telefon.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not telefon.startswith("+"):
        telefon = "+" + telefon

    try:
        sonuc = sms_gonder(telefon, mesaj)
        if sonuc.get("ok"):
            return HTMLResponse(
                content=f"<div class='alert alert-success'>✅ SMS gönderildi → {telefon} (ID: {sonuc.get('mesaj_id', '?')[:12]}...)</div>"
            )
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ {sonuc.get('hata', '?')}</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Hata: {e}</div>")


# ---------------------------------------------------------------------------
# API — Sandbox
# ---------------------------------------------------------------------------

from reymen.web_ui.sandbox import yonetici as sandbox_yoneticisi


@app.get("/api/sandbox")
async def api_sandbox():
    """Sandbox listesi HTML tablosu."""
    sandboxlar = sandbox_yoneticisi.listele(limit=30)
    if not sandboxlar:
        return HTMLResponse(content="<div class='gri'>Henüz sandbox yok</div>")

    satirlar = ["<table><tr><th>ID</th><th>Durum</th><th>Exit</th><th>Süre</th><th>İşlem</th></tr>"]
    for sb in sandboxlar:
        durum = sb["durum"]
        dot = "🟢" if durum == "basarili" else "🔴" if durum in ("hata", "zamanasimi") else "🟡"
        satirlar.append(
            f"<tr><td>{sb['id']}</td>"
            f"<td>{dot} {durum}</td>"
            f"<td>{sb['exit_code']}</td>"
            f"<td>{sb['sure_sn']}s</td>"
            f"<td><button class='btn btn-sm' hx-get='/api/sandbox/{sb['id']}' "
            f"hx-target='#sandbox-detay'>🔍</button></td></tr>"
        )
    satirlar.append("</table>")
    return HTMLResponse(content="\n".join(satirlar))


@app.get("/api/sandbox/{sandbox_id}")
async def api_sandbox_detay(sandbox_id: str):
    """Tek sandbox detayi."""
    sb = sandbox_yoneticisi.get(sandbox_id)
    if not sb:
        return HTMLResponse(content="<div class='alert alert-error'>Sandbox bulunamadi</div>")
    r = sb.rapor()
    satirlar = [
        f"<div class='kart'><table>"
        f"<tr><td>ID</td><td>{r['id']}</td></tr>"
        f"<tr><td>Durum</td><td>{r['durum']}</td></tr>"
        f"<tr><td>Exit Code</td><td>{r['exit_code']}</td></tr>"
        f"<tr><td>Süre</td><td>{r['sure_sn']}s</td></tr>"
        f"<tr><td>Dizin</td><td class='gri'>{r['dizin']}</td></tr>"
        f"<tr><td>Çıktı</td><td><pre style='max-height:200px'>{r.get('cikti', '')[:1000]}</pre></td></tr>"
    ]
    if r.get("hata"):
        satirlar.append(f"<tr><td>Hata</td><td><pre class='tag-no'>{r['hata'][:500]}</pre></td></tr>")
    satirlar.append("</table></div>")
    return HTMLResponse(content="\n".join(satirlar))


@app.post("/api/sandbox/calistir")
async def api_sandbox_calistir(request: Request):
    """Sandbox'da komut çalıştır."""
    form = await request.form()
    dil = form.get("dil", "python")
    kod = form.get("kod", "").strip()

    if not kod:
        return HTMLResponse(content="<div class='alert alert-error'>❌ Kod gerekli</div>")

    sb = sandbox_yoneticisi.yeni()

    if dil == "python":
        sb.dosya_yaz("script.py", kod)
        sonuc = sb.calistir([sys.executable, "script.py"])
    elif dil == "shell":
        sb.dosya_yaz("script.sh", kod)
        # Windows'da bash yoksa cmd ile dene
        shell_komut = ["bash", "script.sh"] if sys.platform != "win32" else ["cmd", "/c", kod]
        sonuc = sb.calistir(shell_komut)
    else:
        return HTMLResponse(content=f"<div class='alert alert-error'>❌ Bilinmeyen dil: {dil}</div>")

    cikti = sonuc.get("cikti", "")[:2000]
    hata = sonuc.get("hata", "")[:500]
    durum = sonuc["durum"]
    dot = "🟢" if durum == "basarili" else "🔴"
    sure = sonuc["sure_sn"]

    html = [
        f"<div class='alert alert-{'success' if durum == 'basarili' else 'error'}'>"
        f"{dot} {durum} (exit: {sonuc['exit_code']}, {sure}s) — ID: {sb.id}</div>",
    ]
    if cikti:
        html.append(f"<pre style='max-height:300px'>{cikti}</pre>")
    if hata:
        html.append(f"<pre class='tag-no'>{hata}</pre>")

    return HTMLResponse(content="\n".join(html))


@app.post("/api/sandbox/temizle")
async def api_sandbox_temizle():
    """Tüm sandbox'lari temizle."""
    say = sandbox_yoneticisi.temizle_hepsi()
    return HTMLResponse(content=f"<div class='alert alert-success'>🧹 {say} sandbox temizlendi</div>")


# ═══════════════════════════════════════════════════════════════════
# API — Cron Yönetimi
# ═══════════════════════════════════════════════════════════════════

@app.get("/cron", response_class=HTMLResponse)
async def cron_sayfasi(request: Request):
    """Cron yönetim sayfası (admin)."""
    if not admin_gerekli(getattr(request.state, "session", None)):
        return HTMLResponse(
            content='<div class="container"><h1>🔒 Yetkisiz</h1><p>Bu sayfa icin admin yetkisi gerekli.</p></div>',
            status_code=403,
        )
    return templates.TemplateResponse(request, "cron.html", {})


@app.get("/api/cron")
async def api_cron_liste():
    """Cron job listesi HTML tablosu."""
    try:
        jobs_path = Path.home() / ".hermes" / "cron" / "jobs.json"
        if jobs_path.exists():
            with open(jobs_path) as f:
                data = json.load(f)
            jobs = data if isinstance(data, list) else data.get("jobs", [])
        else:
            jobs = []
    except Exception:
        jobs = []

    if not jobs:
        return HTMLResponse(content='<div id="cron-liste"><div class="gri">⏰ Zamanlanmış görev yok</div></div>')

    html = ['<div id="cron-liste">']
    html.append('<table class="table"><thead><tr>')
    html.append('<th>Ad</th><th>Schedule</th><th>Son Çalışma</th><th>Durum</th><th>İşlem</th>')
    html.append('</tr></thead><tbody>')

    now = datetime.now().isoformat()[:19]
    for j in jobs:
        if isinstance(j, dict):
            durum_raw = j.get("last_status", "")
            active = j.get("enabled", True)
            durum = "✅" if active and durum_raw == "ok" else \
                    "❌" if durum_raw == "error" else "⏸️" if not active else "🔄"
            son = (j.get("last_run_at") or "-")[:16]
            html.append("<tr>")
            html.append(f"<td><b>{j.get('name', '?')}</b></td>")
            html.append(f"<td><code>{j.get('schedule', '-')}</code></td>")
            html.append(f"<td>{son}</td>")
            html.append(f"<td>{durum}</td>")
            html.append(f"<td class='islem'>")
            job_id = j.get("job_id", j.get("id", ""))
            if active:
                html.append(f"<button class='btn btn-sm' onclick='cronDurdur(\"{job_id}\")'>⏸️</button>")
            else:
                html.append(f"<button class='btn btn-sm' onclick='cronDevam(\"{job_id}\")'>▶️</button>")
            html.append(f"<button class='btn btn-sm' onclick='cronSil(\"{job_id}\")'>🗑️</button>")
            html.append("</td></tr>")

    html.append('</tbody></table></div>')
    return HTMLResponse(content="\n".join(html))


@app.post("/api/cron/ekle")
async def api_cron_ekle(request: Request):
    """Yeni cron job ekle."""
    data = await request.form()
    ad = data.get("ad", "").strip()
    zaman = data.get("zaman", "").strip()
    komut = data.get("komut", "").strip()

    if not ad or not zaman or not komut:
        return HTMLResponse(content='<div id="cron-liste" class="alert alert-error">Eksik alanlar var</div>')

    try:
        import uuid
        jobs_path = Path.home() / ".hermes" / "cron" / "jobs.json"
        jobs_path.parent.mkdir(parents=True, exist_ok=True)

        jobs = []
        if jobs_path.exists():
            with open(jobs_path) as f:
                jobs = json.load(f)

        new_job = {
            "job_id": uuid.uuid4().hex[:12],
            "name": ad,
            "schedule": zaman,
            "prompt": komut,
            "enabled": True,
            "last_status": "",
            "repeat": "forever",
            "created_at": datetime.now().isoformat(),
        }
        if isinstance(jobs, list):
            jobs.append(new_job)
        else:
            jobs = [new_job]

        with open(jobs_path, "w") as f:
            json.dump(jobs, f, indent=2)

        return HTMLResponse(
            content=f'<div id="cron-liste" hx-get="/api/cron" hx-trigger="load" hx-swap="outerHTML">'
                    f'<div class="alert alert-success">✅ {ad} eklendi</div></div>'
        )
    except Exception as e:
        return HTMLResponse(content=f'<div id="cron-liste" class="alert alert-error">{e}</div>')


@app.post("/api/cron/sil/{job_id}")
async def api_cron_sil(job_id: str):
    """Cron job sil."""
    try:
        jobs_path = Path.home() / ".hermes" / "cron" / "jobs.json"
        if not jobs_path.exists():
            return HTMLResponse(content='<div id="cron-liste" class="alert alert-error">Cron dosyası yok</div>')

        with open(jobs_path) as f:
            jobs = json.load(f)

        if isinstance(jobs, list):
            jobs = [j for j in jobs if j.get("job_id") != job_id and j.get("id") != job_id]
        elif isinstance(jobs, dict) and "jobs" in jobs:
            jobs["jobs"] = [j for j in jobs["jobs"] if j.get("job_id") != job_id and j.get("id") != job_id]

        with open(jobs_path, "w") as f:
            json.dump(jobs, f, indent=2)

        return HTMLResponse(
            content=f'<div id="cron-liste" hx-get="/api/cron" hx-trigger="load" hx-swap="outerHTML">'
                    f'<div class="alert alert-success">🗑️ Silindi</div></div>'
        )
    except Exception as e:
        return HTMLResponse(content=f'<div id="cron-liste" class="alert alert-error">{e}</div>')


@app.post("/api/cron/durdur/{job_id}")
async def api_cron_durdur(job_id: str):
    """Cron job durdur."""
    try:
        jobs_path = Path.home() / ".hermes" / "cron" / "jobs.json"
        if jobs_path.exists():
            with open(jobs_path) as f:
                jobs = json.load(f)

            def _toggle(j):
                if j.get("job_id") == job_id or j.get("id") == job_id:
                    j["enabled"] = False
                return j

            if isinstance(jobs, list):
                jobs = [_toggle(j) for j in jobs]
            elif isinstance(jobs, dict) and "jobs" in jobs:
                jobs["jobs"] = [_toggle(j) for j in jobs["jobs"]]

            with open(jobs_path, "w") as f:
                json.dump(jobs, f, indent=2)

        return HTMLResponse(
            content=f'<div id="cron-liste" hx-get="/api/cron" hx-trigger="load" hx-swap="outerHTML">'
                    f'<div class="alert alert-info">⏸️ Durduruldu</div></div>'
        )
    except Exception as e:
        return HTMLResponse(content=f'<div id="cron-liste" class="alert alert-error">{e}</div>')


@app.post("/api/cron/devam/{job_id}")
async def api_cron_devam(job_id: str):
    """Cron job devam ettir."""
    try:
        jobs_path = Path.home() / ".hermes" / "cron" / "jobs.json"
        if jobs_path.exists():
            with open(jobs_path) as f:
                jobs = json.load(f)

            def _toggle(j):
                if j.get("job_id") == job_id or j.get("id") == job_id:
                    j["enabled"] = True
                return j

            if isinstance(jobs, list):
                jobs = [_toggle(j) for j in jobs]
            elif isinstance(jobs, dict) and "jobs" in jobs:
                jobs["jobs"] = [_toggle(j) for j in jobs["jobs"]]

            with open(jobs_path, "w") as f:
                json.dump(jobs, f, indent=2)

        return HTMLResponse(
            content=f'<div id="cron-liste" hx-get="/api/cron" hx-trigger="load" hx-swap="outerHTML">'
                    f'<div class="alert alert-info">▶️ Devam ediyor</div></div>'
        )
    except Exception as e:
        return HTMLResponse(content=f'<div id="cron-liste" class="alert alert-error">{e}</div>')


@app.post("/api/cron/calistir/{job_id}")
async def api_cron_calistir(job_id: str):
    """Cron job'u hemen çalıştır."""
    return HTMLResponse(
        content=f'<div id="cron-liste" hx-get="/api/cron" hx-trigger="load" hx-swap="outerHTML">'
                f'<div class="alert alert-info">🔁 Komut gönderildi (scheduler değerlendirecek)</div></div>'
    )


# ═══════════════════════════════════════════════════════════════════
# API — Hata Yönetimi
# ═══════════════════════════════════════════════════════════════════

@app.get("/hatalar", response_class=HTMLResponse)
async def hatalar_sayfasi(request: Request):
    """Hata yönetim sayfası."""
    return templates.TemplateResponse(request, "hatalar.html", {})


@app.get("/api/hatalar")
async def api_hatalar_liste(
    limit: int = 50,
    offset: int = 0,
    seviye: str = "",
    kaynak: str = "",
):
    """Hata listesi HTML."""
    from reymen.sistem.hata_topla import hata_topla
    depo = hata_topla().depo
    kayitlar = depo.listele(limit=limit, offset=offset, seviye=seviye, kaynak=kaynak)

    if not kayitlar:
        return HTMLResponse(content='<div id="hata-liste"><div class="gri">✅ Hata kaydı yok</div></div>')

    html = ['<div id="hata-liste">']
    html.append('<table class="table"><thead><tr>')
    html.append('<th>Zaman</th><th>Seviye</th><th>Kaynak</th><th>Mesaj</th><th>Detay</th>')
    html.append('</tr></thead><tbody>')

    for i, k in enumerate(kayitlar):
        sev = k.get("seviye", "INFO")
        ikon = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡", "INFO": "🔵"}.get(sev, "⚪")
        sinif = {"CRITICAL": "tag-critical", "ERROR": "tag-error",
                 "WARNING": "tag-warning"}.get(sev, "")
        trace = k.get("traceback", "")
        tid = f"t{i}"

        html.append(f"<tr class='{sinif}'>")
        html.append(f"<td class='cizgi'>{k.get('zaman', '?')[:19]}</td>")
        html.append(f"<td><b>{ikon} {sev}</b></td>")
        html.append(f"<td class='cizgi'>{k.get('kaynak', '?')}</td>")
        html.append(f"<td>{k.get('mesaj', '')[:100]}</td>")
        html.append(f"<td>")
        if trace:
            html.append(f"<button class='btn btn-sm' onclick='traceToggle(\"{tid}\")'>📋</button>")
        html.append(f"</td></tr>")
        if trace:
            html.append(f"<tr id='trace-{tid}' class='gizli'><td colspan='5'>"
                        f"<pre style='max-height:200px;font-size:11px;'>{trace[:2000]}</pre></td></tr>")

    html.append('</tbody></table>')
    html.append(f'<div class="gri" style="text-align:center;padding:0.5rem;">'
                f'Toplam {len(kayitlar)} kayıt</div>')
    html.append('</div>')
    return HTMLResponse(content="\n".join(html))


@app.get("/api/hatalar/ozet")
async def api_hatalar_ozet():
    """Hata özet kartları HTML."""
    from reymen.sistem.hata_topla import hata_topla
    ozet = hata_topla().depo.ozet()

    html = [
        '<div class="cards" style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.5rem;">',
        f'<div class="card" style="text-align:center;"><h3>{ozet["toplam"]}</h3><div class="gri">Toplam</div></div>',
        f'<div class="card" style="text-align:center;border-left:3px solid #ef4444;">'
        f'<h3 style="color:#ef4444;">{ozet["CRITICAL"]}</h3><div class="gri">Kritik</div></div>',
        f'<div class="card" style="text-align:center;border-left:3px solid #f97316;">'
        f'<h3 style="color:#f97316;">{ozet["ERROR"]}</h3><div class="gri">Hata</div></div>',
        f'<div class="card" style="text-align:center;border-left:3px solid #eab308;">'
        f'<h3 style="color:#eab308;">{ozet["WARNING"]}</h3><div class="gri">Uyarı</div></div>',
        f'<div class="card" style="text-align:center;border-left:3px solid #3b82f6;">'
        f'<h3 style="color:#3b82f6;">{ozet["INFO"]}</h3><div class="gri">Bilgi</div></div>',
        '</div>',
    ]
    return HTMLResponse(content="\n".join(html))


@app.post("/api/hatalar/temizle")
async def api_hatalar_temizle():
    """Tüm hata kayıtlarını temizle."""
    from reymen.sistem.hata_topla import hata_topla
    say = hata_topla().depo.temizle()
    return HTMLResponse(
        content=f'<div id="hata-liste"><div class="alert alert-success">🧹 {say} kayıt silindi</div></div>'
    )


@app.post("/api/hatalar/test-bildirim")
async def api_hatalar_test_bildirim():
    """Test bildirimi gönder."""
    from reymen.sistem.hata_topla import hata_topla
    kayit = hata_topla().manuel_kaydet(
        seviye="ERROR",
        kaynak="web_ui.test",
        mesaj="Bu bir test hata bildirimidir",
    )
    # Toast için HTML
    html = (
        '<div class="toast toast-success" hx-trigger="load delay:3s" '
        'hx-swap="delete" hx-target="closest .toast">'
        '✅ Test bildirimi gönderildi</div>'
    )
    return HTMLResponse(content=html)


@app.post("/api/hatalar/bildirim-ayarla")
async def api_hatalar_bildirim_ayarla(request: Request):
    """Bildirim kanalı ayarla."""
    data = await request.form()
    tur = data.get("tur", "")
    hedef = data.get("hedef", "")
    esik = data.get("esik", "ERROR")

    from reymen.sistem.hata_topla import bildirim_kanal_ekle
    bildirim_kanal_ekle(tur, hedef, esik)

    return HTMLResponse(content='<div class="alert alert-success">✅ Bildirim kanalı eklendi</div>')


# ---------------------------------------------------------------------------
# API — Plugin JSON
# ---------------------------------------------------------------------------


@app.get("/api/plugin/liste")
async def api_plugin_liste():
    """Plugin listesi JSON."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        pluginler = yonetici.list_plugins()
        istatistik = yonetici.plugin_sayisi()
        if not pluginler:
            return HTMLResponse(content="<div class='gri'>Henüz plugin yok</div>")
        satirlar = [
            "<table><tr><th>#</th><th>Plugin</th><th>Tür</th><th>Versiyon</th><th>Durum</th><th>Araç</th><th>Açıklama</th></tr>"
        ]
        for i, p in enumerate(pluginler, 1):
            ad = p.get("name", "?")
            tur = p.get("kind", "?")
            versiyon = p.get("version", "")
            aktif = p.get("enabled", False)
            tag = "tag-yes" if aktif else "tag-no"
            durum_text = "Aktif" if aktif else "Pasif"
            arac_sayisi = p.get("tools", 0)
            aciklama = (p.get("description", "") or "")[:60]
            satirlar.append(
                f"<tr><td>{i}</td><td><b>{ad}</b></td>"
                f"<td><span class='tag tag-info'>{tur}</span></td>"
                f"<td>{versiyon}</td>"
                f"<td><span class='tag {tag}'>{durum_text}</span></td>"
                f"<td>{arac_sayisi}</td>"
                f"<td class='gri'>{aciklama}</td></tr>"
            )
        satirlar.append("</table>")
        satirlar.append(
            f"<div class='gri' style='margin-top:8px'>"
            f"Toplam: {istatistik.get('toplam', 0)} plugin, "
            f"{istatistik.get('aktif', 0)} aktif, "
            f"{istatistik.get('devre_disi', 0)} pasif"
            f"</div>"
        )
        return HTMLResponse(content="\n".join(satirlar))
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Plugin listesi hatası: {e}</div>")


@app.get("/api/plugin/bilgi/{ad}")
async def api_plugin_bilgi(ad: str):
    """Plugin detay bilgisi."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.sistem.plugin_manager import PluginYoneticisi
        yonetici = PluginYoneticisi(str(PLUGIN_DIZIN))
        bilgi = yonetici.plugin_info(ad)
        satirlar = [
            f"<div class='kart'><table>"
            f"<tr><td>Adı</td><td><b>{bilgi.get('adi', '?')}</b></td></tr>"
            f"<tr><td>Klasör</td><td>{bilgi.get('klasor', '?')}</td></tr>"
            f"<tr><td>Versiyon</td><td>{bilgi.get('versiyon', '-')}</td></tr>"
            f"<tr><td>Tür</td><td><span class='tag tag-info'>{bilgi.get('kind', '?')}</span></td></tr>"
            f"<tr><td>Açıklama</td><td>{bilgi.get('aciklama', '-')}</td></tr>"
            f"<tr><td>Yazar</td><td>{bilgi.get('yazar', '-')}</td></tr>"
            f"<tr><td>Durum</td><td><span class='tag {'tag-yes' if bilgi.get('aktif') else 'tag-no'}'>{'Aktif' if bilgi.get('aktif') else 'Pasif'}</span></td></tr>"
            f"<tr><td>Yüklü</td><td>{'✅' if bilgi.get('yuklu') else '❌'}</td></tr>"
            f"<tr><td>Klasör Var</td><td>{'✅' if bilgi.get('klasor_var') else '❌'}</td></tr>"
            f"<tr><td>Araç Sayısı</td><td>{len(bilgi.get('araclar', []))}</td></tr>"
            f"</table></div>"
        ]
        return HTMLResponse(content="\n".join(satirlar))
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Plugin bilgisi alınamadı: {e}</div>")


# ---------------------------------------------------------------------------
# API — Kalite / Self-Improve
# ---------------------------------------------------------------------------


@app.get("/api/kalite")
async def api_kalite():
    """Self-improve trend raporu HTML."""
    try:
        from reymen.self_improve import report as si_report
        rapor = si_report()
        ortalama = rapor.get("ortalama_skor", 0)
        gecme = rapor.get("gecme_orani", 0)
        toplam = rapor.get("toplam_adim", 0)
        dusuk = rapor.get("dusuk_kalite", 0)
        notlar = rapor.get("not_dagilimi", {})
        haftalik = rapor.get("haftalik_ilerleme", [])
        hedefler = rapor.get("aktif_hedefler", [])
        not_str = " ".join(f"<span class='tag tag-info'>{k}: {v}</span>" for k, v in sorted(notlar.items()))
        hafta_str = ""
        for h in haftalik:
            bar = "█" * max(1, int(h["ortalama"] * 20))
            hafta_str += f"<div>{h['hafta']}: {bar} <span class='gri'>({h['ortalama']:.2f}, {h['adim']} adım)</span></div>"
        hedef_str = ""
        if hedefler:
            for h in hedefler[:5]:
                hedef_str += f"<div>🎯 {h.get('metric_name', '?')}: {h.get('current_val', 0):.1f} → {h.get('target_val', 0):.1f}</div>"
        return HTMLResponse(
            content=f"<div class='flex' style='flex-direction:column;gap:8px'>"
            f"<div><b>Ortalama Skor:</b> {ortalama:.3f}</div>"
            f"<div><b>Geçme Oranı:</b> %{gecme*100:.1f}</div>"
            f"<div><b>Toplam Adım:</b> {toplam} (<span class='tag-no'>{dusuk} düşük</span>)</div>"
            f"<div><b>Not Dağılımı:</b> {not_str}</div>"
            f"<hr><div><b>Haftalık İlerleme:</b></div>{hafta_str}"
            f"{'<hr><div><b>Aktif Hedefler:</b></div>' + hedef_str if hedef_str else ''}"
            f"</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Kalite raporu: {e}</div>")


@app.get("/api/kalite/analiz")
async def api_kalite_analiz():
    """Kod kalite analizi HTML."""
    try:
        from reymen.self_improve import kod_kalite_analizi
        sonuc = kod_kalite_analizi()
        satirlar = [
            f"<table>"
            f"<tr><td>Toplam Dosya</td><td><b>{sonuc.get('toplam_dosya', 0)}</b></td></tr>"
            f"<tr><td>Toplam Satır</td><td><b>{sonuc.get('toplam_satir', 0):,}</b></td></tr>"
            f"<tr><td>Sınıf Sayısı</td><td>{sonuc.get('sinif_sayisi', 0)}</td></tr>"
            f"<tr><td>Fonksiyon Sayısı</td><td>{sonuc.get('fonk_sayisi', 0)}</td></tr>"
            f"<tr><td>Test Dosyası</td><td>{sonuc.get('test_dosyasi', 0)}</td></tr>"
            f"<tr><td>Test Satır Oranı</td><td>%{sonuc.get('test_orani', 0)*100:.1f}</td></tr>"
            f"<tr><td>📝 TODO</td><td><span class='tag tag-info'>{sonuc.get('todo', 0)}</span></td></tr>"
            f"<tr><td>⚠️ FIXME</td><td><span class='tag tag-no'>{sonuc.get('fixme', 0)}</span></td></tr>"
            f"<tr><td>🔴 except:pass</td><td><span class='tag tag-no'>{sonuc.get('except_pass', 0)}</span></td></tr>"
            f"</table>"
        ]
        return HTMLResponse(content="\n".join(satirlar))
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Kod kalite analizi: {e}</div>")


@app.get("/api/kalite/ozet")
async def api_kalite_ozet():
    """Kalite özet bilgisi (dashboard)."""
    try:
        from reymen.self_improve import report as si_report
        rapor = si_report()
        ortalama = rapor.get("ortalama_skor", 0)
        toplam = rapor.get("toplam_adim", 0)
        not_str = " ".join(
            f"<span class='tag tag-info'>{k}: {v}</span>"
            for k, v in sorted(rapor.get("not_dagilimi", {}).items())
        )
        return HTMLResponse(
            content=f"<div><b>{toplam}</b> adım, skor: <b>{ortalama:.3f}</b><br>{not_str}</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='gri'>Kalite: {e}</div>")


# ---------------------------------------------------------------------------
# API — Maliyet / Cost Tracker
# ---------------------------------------------------------------------------


@app.get("/api/maliyet")
async def api_maliyet():
    """Cost tracker özet HTML."""
    try:
        from reymen.cost_tracker import summary as ct_summary
        ozet = ct_summary()
        toplam_maliyet = ozet.get("total_cost_usd", 0)
        toplam_cagri = ozet.get("total_calls", 0)
        toplam_token = ozet.get("total_tokens", 0)
        by_model = ozet.get("by_model", {})
        satirlar = [
            f"<div class='flex' style='flex-direction:column;gap:6px'>"
            f"<div><b>💵 Toplam Maliyet:</b> ${toplam_maliyet:.6f}</div>"
            f"<div><b>📞 Toplam Çağrı:</b> {toplam_cagri}</div>"
            f"<div><b>🔤 Toplam Token:</b> {toplam_token:,}</div>"
            f"<hr><div><b>Modele Göre:</b></div>"
        ]
        if by_model:
            satirlar.append("<table><tr><th>Model</th><th>Çağrı</th><th>Maliyet</th></tr>")
            for model, m_data in sorted(by_model.items(), key=lambda x: x[1]["cost_usd"], reverse=True):
                satirlar.append(
                    f"<tr><td>{model}</td><td>{m_data['calls']}</td>"
                    f"<td>${m_data['cost_usd']:.6f}</td></tr>"
                )
            satirlar.append("</table>")
        satirlar.append("</div>")
        return HTMLResponse(content="\n".join(satirlar))
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Maliyet raporu: {e}</div>")


@app.get("/api/maliyet/detay")
async def api_maliyet_detay(n: int = 20):
    """Cost tracker detay HTML."""
    try:
        from reymen.cost_tracker import dump_log
        kayitlar = dump_log(limit=n)
        if not kayitlar:
            return HTMLResponse(content="<div class='gri'>Henüz kayıt yok</div>")
        satirlar = ["<table><tr><th>#</th><th>Zaman</th><th>Model</th><th>Prompt</th><th>Completion</th><th>Maliyet</th></tr>"]
        for i, r in enumerate(kayitlar, 1):
            ts = r.get("timestamp", 0)
            from datetime import datetime as dt
            zaman = dt.fromtimestamp(ts).strftime("%d.%m %H:%M") if ts else "?"
            satirlar.append(
                f"<tr><td>{i}</td><td class='gri'>{zaman}</td>"
                f"<td>{r.get('model', '?')}</td>"
                f"<td>{r.get('prompt_tokens', 0):,}</td>"
                f"<td>{r.get('completion_tokens', 0):,}</td>"
                f"<td>${r.get('cost_usd', 0):.6f}</td></tr>"
            )
        satirlar.append("</table>")
        return HTMLResponse(content="\n".join(satirlar))
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Maliyet detay: {e}</div>")


@app.get("/api/maliyet/ozet")
async def api_maliyet_ozet():
    """Maliyet özet (dashboard)."""
    try:
        from reymen.cost_tracker import summary as ct_summary
        ozet = ct_summary()
        toplam = ozet.get("total_cost_usd", 0)
        cagri = ozet.get("total_calls", 0)
        return HTMLResponse(
            content=f"<div><b>${toplam:.4f}</b> harcama, <b>{cagri}</b> çağrı</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='gri'>Maliyet: {e}</div>")


# ---------------------------------------------------------------------------
# API — Kanban
# ---------------------------------------------------------------------------


@app.get("/api/kanban")
async def api_kanban():
    """Kanban pano durumu HTML."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.kanban import Board
        board = Board.load(str(PROJE_KOK / ".ReYMeN" / "board.json"))
        tum_kartlar = board.all_cards()
        toplam = len(tum_kartlar)
        done = sum(1 for c in tum_kartlar if c.status == "done")
        in_progress = sum(1 for c in tum_kartlar if c.status == "in_progress")
        blocked = sum(1 for c in tum_kartlar if c.status == "blocked")
        backlog = sum(1 for c in tum_kartlar if c.status in ("backlog", "todo", "ready"))
        geciken = len(board.overdue_cards())
        satirlar = [
            f"<div class='flex' style='flex-direction:column;gap:6px'>"
            f"<div>📊 <b>{toplam}</b> kart toplam</div>"
            f"<div class='flex'>"
            f"<span class='tag tag-yes'>✅ {done} tamam</span>"
            f"<span class='tag tag-info'>🔄 {in_progress} devam</span>"
            f"<span class='tag tag-no'>🚫 {blocked} bloke</span>"
            f"<span class='tag'>📥 {backlog} sırada</span>"
            f"</div>"
            f"<div>{'⚠️ <b>' + str(geciken) + '</b> geciken kart' if geciken else '✅ Geciken kart yok'}</div>"
            f"</div>"
        ]
        # Kolon özeti
        for col in board.columns:
            satirlar.append(
                f"<div><b>{col.name}</b>: {len(col.cards)} kart"
                f"{' (WIP: ' + str(col.wip_limit) + ')' if col.wip_limit else ''}</div>"
            )
        return HTMLResponse(content="\n".join(satirlar))
    except FileNotFoundError:
        return HTMLResponse(
            content="<div class='gri'>Kanban panosu henüz oluşturulmamış. <code>.ReYMeN/board.json</code> dosyası gerekli.</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Kanban: {e}</div>")


@app.get("/api/kanban/kartlar")
async def api_kanban_kartlar():
    """Kanban kart listesi HTML."""
    try:
        sys.path.insert(0, str(PROJE_KOK))
        from reymen.kanban import Board
        board = Board.load(str(PROJE_KOK / ".ReYMeN" / "board.json"))
        tum_kartlar = board.all_cards()
        if not tum_kartlar:
            return HTMLResponse(content="<div class='gri'>Henüz kart yok</div>")
        satirlar = [
            "<table><tr><th>Kart</th><th>Durum</th><th>Öncelik</th><th>Atanan</th><th>Teslim</th></tr>"
        ]
        for c in tum_kartlar[:50]:
            prio_map = {0: "🔴 Kritik", 1: "🟠 Yüksek", 2: "🟡 Orta", 3: "🟢 Düşük"}
            durum_map = {
                "backlog": "📥", "todo": "📋", "ready": "✅",
                "in_progress": "🔄", "blocked": "🚫", "review": "👁️", "done": "✔️"
            }
            prio = prio_map.get(c.priority, str(c.priority))
            durum_icon = durum_map.get(c.status, "❓")
            deadline = c.deadline[:10] if c.deadline else "-"
            assignee = c.assignee or "-"
            baslik = c.title[:50]
            satirlar.append(
                f"<tr><td><b>{baslik}</b></td>"
                f"<td>{durum_icon} {c.status}</td>"
                f"<td><span class='gri'>{prio}</span></td>"
                f"<td>{assignee}</td>"
                f"<td class='gri'>{deadline}</td></tr>"
            )
        satirlar.append("</table>")
        return HTMLResponse(content="\n".join(satirlar))
    except FileNotFoundError:
        return HTMLResponse(content="<div class='gri'>Board dosyası bulunamadı</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Kanban kartları: {e}</div>")


# ---------------------------------------------------------------------------
# API — Sistem / Sağlık
# ---------------------------------------------------------------------------


@app.get("/api/sistem/saglik")
async def api_sistem_saglik():
    """Sistem sağlık kontrolü HTML."""
    try:
        import platform
        import psutil
        satirlar = [
            "<table>"
            f"<tr><td>🖥️ CPU Kullanımı</td><td><b>{psutil.cpu_percent(interval=0.1):.1f}%</b></td></tr>"
            f"<tr><td>💾 RAM Kullanımı</td><td><b>{psutil.virtual_memory().percent:.1f}%</b> "
            f"({psutil.virtual_memory().used // (1024**3)}GB / {psutil.virtual_memory().total // (1024**3)}GB)</td></tr>"
            f"<tr><td>💿 Disk Kullanımı</td><td><b>{psutil.disk_usage('/').percent:.1f}%</b></td></tr>"
        ]
        # Process durumu
        calisan = 0
        tumu = process_manager.tumu()
        for p in tumu:
            if p.get("durum") == "calisiyor":
                calisan += 1
        satirlar.append(
            f"<tr><td>⚙️ Process</td><td><b>{calisan}/{len(tumu)}</b> çalışıyor</td></tr>"
        )
        satirlar.append("</table>")
        return HTMLResponse(content="\n".join(satirlar))
    except ImportError:
        return HTMLResponse(
            content="<div class='gri'>psutil yüklü değil. <code>pip install psutil</code> ile kurabilirsiniz.</div>"
        )
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Sistem sağlığı: {e}</div>")


@app.get("/api/sistem/saglik/ozet")
async def api_sistem_saglik_ozet():
    """Sistem sağlık özet (dashboard)."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.05)
        ram = psutil.virtual_memory().percent
        cpu_tag = "tag-yes" if cpu < 70 else ("tag-info" if cpu < 90 else "tag-no")
        ram_tag = "tag-yes" if ram < 70 else ("tag-info" if ram < 90 else "tag-no")
        return HTMLResponse(
            content=f"<div class='flex'>"
            f"<span class='tag {cpu_tag}'>🖥️ CPU: %{cpu:.0f}</span>"
            f"<span class='tag {ram_tag}'>💾 RAM: %{ram:.0f}</span>"
            f"</div>"
        )
    except ImportError:
        return HTMLResponse(content="<div class='gri'>psutil gerekli</div>")
    except Exception as e:
        return HTMLResponse(content=f"<div class='gri'>Sistem: {e}</div>")


@app.get("/api/sistem/bilgi")
async def api_sistem_bilgi():
    """Sistem bilgisi HTML."""
    try:
        import platform
        import sys
        satirlar = [
            "<table>"
            f"<tr><td>💻 İşletim Sistemi</td><td><b>{platform.system()} {platform.release()}</b></td></tr>"
            f"<tr><td>🐍 Python</td><td><b>{sys.version.split()[0]}</b></td></tr>"
            f"<tr><td>🏠 Makine</td><td>{platform.node()}</td></tr>"
            f"<tr><td>📐 Mimarî</td><td>{platform.machine()}</td></tr>"
            f"<tr><td>📁 Proje Kökü</td><td class='gri'>{PROJE_KOK}</td></tr>"
            f"<tr><td>📦 FastAPI</td><td>{getattr(__import__('fastapi'), '__version__', '?')}</td></tr>"
            f"</table>"
        ]
        return HTMLResponse(content="\n".join(satirlar))
    except Exception as e:
        return HTMLResponse(content=f"<div class='alert alert-error'>Sistem bilgisi: {e}</div>")


# ---------------------------------------------------------------------------
# WebSocket — Canlı Log
# ---------------------------------------------------------------------------


@app.websocket("/ws/logs")
async def ws_loglar(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket log abonesi bağlandı")
    try:
        while True:
            satir = await log_kuyrugu_oku()
            try:
                await websocket.send_text(satir)
            except WebSocketDisconnect:
                break
            except Exception:
                break
    except WebSocketDisconnect:
        logger.info("WebSocket log abonesi ayrıldı")
    except Exception as e:
        logger.warning("WebSocket hatası: %s", e)

# ---------------------------------------------------------------------------
# Başlangıç
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup():
    """Uygulama başlangıcı."""
    # Log streamer'ı başlat
    await log_streamer.basla()
    
    # Log tarama görevi
    async def log_tarama_dongusu():
        while True:
            await log_streamer.tara()
            await asyncio.sleep(1)

    asyncio.create_task(log_tarama_dongusu())
    logger.info("ReYMeN Web UI başlatıldı")


@app.get("/api/health")
async def health():
    return {"durum": "ok", "zaman": datetime.now().isoformat()}


# ── Konusma Gecmisi ────────────────────────────────────────────────────────


@app.get("/konusmalar", response_class=HTMLResponse)
async def konusmalar_sayfasi(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return RedirectResponse(url="/login")
    konusmalar = _konusma_listele()
    return templates.TemplateResponse("conversations.html", {
        "request": request, "user": user, "konusmalar": konusmalar, "tema": request.cookies.get("tema", "dark"),
    })


@app.get("/api/konusmalar")
async def api_konusmalar(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"hata": "Yetkisiz"}, status_code=401)
    konusmalar = _konusma_listele()
    if not konusmalar:
        return HTMLResponse('<div class="gri">Henüz konuşma kaydı bulunamadı.</div>')
    html = ""
    for k in konusmalar[:50]:
        html += f'''<div class="conv-item" onclick="konusmaAc('{k.get("id","")}')">
            <div class="conv-title">💬 {k.get("baslik","") or k.get("hedef","İsimsiz")}</div>
            <div class="conv-meta">{k.get("tarih","") or k.get("zaman","")} · {k.get("mesaj_sayisi",0)} mesaj</div>
        </div>'''
    return HTMLResponse(html)


@app.get("/api/konusmalar/{konusma_id}/mesajlar")
async def api_konusma_mesajlar(konusma_id: str, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"hata": "Yetkisiz"}, status_code=401)
    mesajlar = _konusma_mesajlari_getir(konusma_id)
    return {"mesajlar": mesajlar}


# ── Toast Bildirim API ──────────────────────────────────────────────────────


@app.post("/api/toast/gonder")
async def api_toast_gonder(request: Request):
    """Harici bir servisten toast bildirimi gonder. (admin yetkisi)
    
    Kullanim: curl -X POST /api/toast/gonder -H "Cookie: ..." \\
              -d "mesaj=Islem tamam&tip=success"
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"hata": "Yetkisiz"}, status_code=401)
    data = await request.form()
    mesaj = data.get("mesaj", "")
    tip = data.get("tip", "info")
    return JSONResponse({"gonderildi": True, "mesaj": mesaj, "tip": tip})


@app.websocket("/ws/toast")
async def ws_toast(websocket: WebSocket):
    """WebSocket uzerinden anlik bildirim gonderimi.
    
    Kullanim (client): new WebSocket('ws://host:5000/ws/toast')
    Client'a gonderim: {"tip": "success", "mesaj": "Islem tamam"}
    """
    await websocket.accept()
    try:
        # Toast abonelerini izle
        _WS_TOAST_KLIENTLER.add(websocket)
        await websocket.send_json({"tip": "info", "mesaj": "Baglandi"})
        while True:
            data = await websocket.receive_text()
            # Gelen mesaji tum client'lara yayinla
            for ws in list(_WS_TOAST_KLIENTLER):
                try:
                    await ws.send_text(data)
                except Exception:
                    _WS_TOAST_KLIENTLER.discard(ws)
    except Exception:
        pass
    finally:
        _WS_TOAST_KLIENTLER.discard(websocket)


_WS_TOAST_KLIENTLER: set = set()


# ── Konusma Veri Kaynagi ───────────────────────────────────────────────────


def _konusma_listele() -> list[dict]:
    """Session DB'den son konusmalari listele."""
    import sqlite3
    # OnceHafiza / session DB
    db_yollari = [
        PROJE_KOK / ".ReYMeN" / "ogrenmeler.db",
        PROJE_KOK / "reymen" / "cereyan" / ".ReYMeN" / "session.db",
        Path.home() / ".hermes" / "state.db",
    ]
    for db_yol in db_yollari:
        if db_yol.exists():
            try:
                conn = sqlite3.connect(str(db_yol))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                # FTS5 session tablosu
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                if cur.fetchone():
                    cur.execute("SELECT id, title, created_at, message_count FROM sessions ORDER BY created_at DESC LIMIT 50")
                    rows = cur.fetchall()
                    conn.close()
                    if rows:
                        return [
                            {"id": r["id"], "baslik": r["title"] or "İsimsiz",
                             "tarih": str(r["created_at"])[:19] if r["created_at"] else "",
                             "mesaj_sayisi": r["message_count"] or 0}
                            for r in rows
                        ]
                # Ogrenmeler tablosu
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ogrenmeler'")
                if cur.fetchone():
                    cur.execute("SELECT hedef, cozum, kaynak, zaman FROM ogrenmeler ORDER BY zaman DESC LIMIT 50")
                    rows = cur.fetchall()
                    conn.close()
                    return [
                        {"id": r["hedef"], "baslik": r["hedef"],
                         "tarih": str(r["zaman"])[:19] if r["zaman"] else "",
                         "mesaj_sayisi": len(r["cozum"]) if r["cozum"] else 0}
                        for r in rows
                    ]
                conn.close()
            except Exception:
                pass
    # Son care: .ReYMeN/notes/ klasöründen .md dosyalari
    notes_dir = PROJE_KOK / ".ReYMeN" / "notes"
    if notes_dir.exists():
        konusmalar = []
        for f in sorted(notes_dir.glob("*.md"), reverse=True)[:50]:
            konusmalar.append({
                "id": f.stem, "baslik": f.stem.replace("-", " ").replace("_", " "),
                "tarih": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "mesaj_sayisi": len(f.read_text().splitlines()),
            })
        return konusmalar
    return []


def _konusma_mesajlari_getir(konusma_id: str) -> list[dict]:
    """Bir konusmanin mesajlarini getir."""
    import sqlite3
    db_yollari = [
        PROJE_KOK / ".ReYMeN" / "ogrenmeler.db",
        PROJE_KOK / "reymen" / "cereyan" / ".ReYMeN" / "session.db",
    ]
    for db_yol in db_yollari:
        if db_yol.exists():
            try:
                conn = sqlite3.connect(str(db_yol))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                # Session messages
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
                if cur.fetchone():
                    cur.execute(
                        "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id LIMIT 100",
                        (konusma_id,))
                    rows = cur.fetchall()
                    conn.close()
                    if rows:
                        return [
                            {"rol": r["role"], "icerik": r["content"] or "",
                             "zaman": str(r["created_at"])[:19] if r["created_at"] else ""}
                            for r in rows
                        ]
                conn.close()
            except Exception:
                pass
    # Notes fallback
    note_path = PROJE_KOK / ".ReYMeN" / "notes" / f"{konusma_id}.md"
    if note_path.exists():
        return [{"rol": "user", "icerik": note_path.read_text()[:2000], "zaman": ""}]
    return []

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def baslat(port: int = 5000, host: str = "0.0.0.0") -> None:
    """Web UI'yi başlat."""
    print(f"🌐 ReYMeN Web UI v2: http://{host}:{port}")
    print(f"   Giriş: admin / reymen (varsayılan)")
    print(f"   Canlı log: /logs")
    uvicorn.run(app, host=host, port=port, log_level="info")


def cli() -> None:
    """Komut satırından çalıştırma."""
    import argparse
    parser = argparse.ArgumentParser(description="ReYMeN Web UI v2")
    parser.add_argument("--port", type=int, default=5000, help="Port (varsayılan: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (varsayılan: 0.0.0.0)")
    args = parser.parse_args()
    baslat(args.port, args.host)


# ── Motor Entegrasyonu ──────────────────────────────────────────────────

_WEB_UI_MOTOR = None
_WEB_UI_THREAD = None


def motor_kaydet(motor) -> None:
    """Motor'a Web UI araçlarını kaydet."""
    global _WEB_UI_MOTOR
    _WEB_UI_MOTOR = motor
    motor._plugin_arac_kaydet(
        "WEB_UI_BASLAT", _web_ui_baslat,
        "Web UI'yi baslat (port 5000, FastAPI + HTMX). Parametre: port=5000 host=0.0.0.0"
    )
    motor._plugin_arac_kaydet(
        "WEB_UI_DURUM", _web_ui_durum,
        "Web UI durumunu goster: calisma, port, route sayisi"
    )
    motor._plugin_arac_kaydet(
        "WEB_UI_DURDUR", _web_ui_durdur,
        "Web UI'yi durdur."
    )
    logger.info("[WEB_UI] Motor'a 3 arac kaydedildi (BASLAT, DURUM, DURDUR)")


def _web_ui_baslat(**kw) -> str:
    """Web UI'yi ayri thread'de baslat."""
    global _WEB_UI_THREAD
    if _WEB_UI_THREAD and _WEB_UI_THREAD.is_alive():
        return "[WEB_UI] Zaten calisiyor (localhost:5000)"
    import threading
    port = int(kw.get("args", [5000])[0]) if kw.get("args") else 5000
    _WEB_UI_THREAD = threading.Thread(
        target=baslat,
        args=(port, "0.0.0.0"),
        daemon=True,
    )
    _WEB_UI_THREAD.start()
    return f"[WEB_UI] Baslatildi: http://localhost:{port}"


def _web_ui_durum(**kw) -> str:
    """Web UI durumu."""
    global _WEB_UI_THREAD
    aktif = _WEB_UI_THREAD is not None and _WEB_UI_THREAD.is_alive()
    routes = len([r for r in app.routes if hasattr(r, 'path')])
    if aktif:
        return f"  WEB_UI: AKTIF (localhost:5000)\n  Route: {routes}\n  Tool: 3"
    return "  WEB_UI: PASIF"


def _web_ui_durdur(**kw) -> str:
    """Web UI'yi durdur."""
    global _WEB_UI_THREAD
    if _WEB_UI_THREAD and _WEB_UI_THREAD.is_alive():
        import os
        os._exit(0)
        return "[WEB_UI] Durduruldu"
    return "[WEB_UI] Zaten kapali"


if __name__ == "__main__":
    cli()
