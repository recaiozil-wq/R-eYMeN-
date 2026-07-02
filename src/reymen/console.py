"""ReYMeN console CLI — ReYMeN'teki ``reymen_cli/`` paketinin ReYMeN karşılığı.

ReYMeN'te komutlar::

    reymen status         → hermes_cli/main.py → cmd_status()
    reymen model          → hermes_cli/model_cmd.py
    reymen cron list      → hermes_cli/cron_cmd.py

Bu modül, ``reymen_launcher.py``'deki argparse üzerinden çağrılır.
Kullanım::

    reymen status
    reymen model
    reymen cost summary
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Any

# Rules Engine CLI
try:
    from reymen.sistem.kurallar import cmd_kural
except ImportError:
    def cmd_kural(args) -> int:
        print("[HATA] Rules Engine modulu yuklenemedi (reymen.sistem.kurallar)")
        return 1


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Alt komutlar (hermes_cli/ cmd_* karşılığı)
# ---------------------------------------------------------------------------
def cmd_version(args: argparse.Namespace) -> int:
    """Versiyon bilgisi."""
    from reymen_launcher import _REYMEN_VERSION, _REYMEN_BUILD, _REYMEN_CONFIG, _KOK

    print(f"ReYMeN Agent v{_REYMEN_VERSION} ({_REYMEN_BUILD})")
    print(f"Proje: {_KOK}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Model: {_REYMEN_CONFIG['model']} ({_REYMEN_CONFIG['provider']})")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Genel durum raporu (ReYMeN'teki ``reymen status`` gibi)."""
    from reymen_launcher import _mevcut_model, _KOK, _REYMEN_VERSION, _g, _c, _d, _gb

    m, p = _mevcut_model()
    print(f"  {_gb('ReYMeN Agent Durumu')}")
    print(f"  {'─' * 50}")
    print(f"  Model:      {_g(m)}")
    print(f"  Provider:   {_c(p)}")
    print(f"  Versiyon:   {_d(_REYMEN_VERSION)}")
    print(f"  Çalışma:    {_KOK}")
    print(f"  Python:     {sys.executable}")
    return 0


def cmd_model(args: argparse.Namespace) -> int:
    """Model/Provider seçim ekranı (ReYMeN'teki ``reymen model`` gibi)."""
    from reymen_launcher import _api_kontrol_bekle, _model_sec

    api_sonuc = _api_kontrol_bekle(timeout=3)
    _model_sec(api_sonuc)
    return 0


def cmd_cost(args: argparse.Namespace) -> int:
    """API maliyet takibi (ReYMeN'teki ``reymen cost`` gibi)."""
    try:
        from reymen import cost_tracker
    except ImportError:
        print("[HATA] cost_tracker modülü bulunamadı.")
        return 1

    sub = getattr(args, "sub", None)
    if sub == "summary":
        print_json(cost_tracker.summary())
    elif sub == "log":
        print_json(cost_tracker.dump_log(limit=getattr(args, "limit", 20)))
    elif sub == "reset":
        count = cost_tracker.reset()
        print(f"{count} kayıt silindi.")
    else:
        print_json(cost_tracker.summary())
    return 0


def cmd_skill_shrink(args: argparse.Namespace) -> int:
    """Skill küçültme CLI komutu."""
    try:
        from reymen.scripts.skill_shrink import cmd_skill_shrink as _shrink_impl
        return _shrink_impl(args)
    except ImportError as e:
        print(f"[HATA] skill_shrink modülü bulunamadı: {e}")
        return 1
    except Exception as e:
        print(f"[HATA] {e}")
        return 1


def cmd_auth(args: argparse.Namespace) -> int:
    """🔐 Auth yönetimi CLI komutu.

    Kullanım:
        reymen auth status          → Auth sistemi durumu
        reymen auth list            → Token'ları listele
        reymen auth users           → Kullanıcıları listele
        reymen auth create <user>   → Kullanıcı/token oluştur
        reymen auth token <user>    → Token oluştur
        reymen auth revoke <token>  → Token iptal et
        reymen auth delete <user>   → Kullanıcı sil
        reymen auth role <user> <r> → Rol değiştir (admin/user/guest)
        reymen auth key <key>       → API key doğrula
    """
    try:
        from reymen.guvenlik.reymen_auth import auth_manager as _auth
    except ImportError as e:
        print(f"[HATA] auth modülü bulunamadı: {e}")
        return 1

    sub = getattr(args, "auth_sub", None)

    if sub == "status":
        durum = _auth.status()
        print_json(durum)
        return 0

    elif sub == "list":
        tokens = _auth.list_tokens()
        if not tokens:
            print("Henüz token bulunmuyor.")
            return 0
        print(f"{'KULLANICI':<20} {'ROL':<10} {'OLUŞTURULMA':<25} {'DURUM':<10}")
        print("-" * 65)
        for t in tokens:
            user = t.get("user_id", "")[:12]
            role = t.get("role", "?")
            created = datetime.fromtimestamp(
                t.get("created_at", 0)
            ).strftime("%Y-%m-%d %H:%M:%S")
            durum_str = "✓ AKTİF" if not t.get("revoked") else "✗ İPTAL"
            print(f"{user:<20} {role:<10} {created:<25} {durum_str:<10}")
        return 0

    elif sub == "users":
        users = _auth.list_users()
        if not users:
            print("Henüz kullanıcı bulunmuyor.")
            return 0
        print(f"{'KULLANICI':<20} {'ROL':<10} {'AKTİF':<8} {'EMAIL':<25}")
        print("-" * 63)
        for u in users:
            aktif = "✓" if u.is_active else "✗"
            print(f"{u.username:<20} {u.role:<10} {aktif:<8} {u.email:<25}")
        return 0

    elif sub == "create":
        username = getattr(args, "username", "kullanici")
        role = getattr(args, "role", "user")
        user = _auth.create_user(username, role=role)
        if user:
            print(f"✅ Kullanıcı oluşturuldu: {user.username} ({user.role})")
            # Token da oluştur
            token = _auth.create_token(username, role=role)
            if token:
                print(f"   Token     : {token.access_token[:50]}...")
                print(f"   Refresh   : {token.refresh_token[:50]}...")
                print(f"   Süre      : {token.expires_in}s")
        else:
            print(f"❌ Kullanıcı oluşturulamadı: {username}")
        return 0

    elif sub == "token":
        username = getattr(args, "username", "kullanici")
        role = getattr(args, "role", "user")
        token = _auth.create_token(username, role=role)
        if token:
            print(f"✅ Token oluşturuldu:")
            print(f"   Kullanıcı : {username}")
            print(f"   Rol       : {token.role}")
            print(f"   Token     : {token.access_token}")
            print(f"   Refresh   : {token.refresh_token}")
            print(f"   Süre      : {token.expires_in}s")
        else:
            print(f"❌ Token oluşturulamadı: {username}")
        return 0

    elif sub == "revoke":
        token_value = getattr(args, "token_value", "")
        if not token_value:
            print("❌ Token değeri gerekli")
            return 1
        if _auth.revoke_token(token_value):
            print("✅ Token iptal edildi")
        else:
            print("❌ Token bulunamadı veya zaten iptal edilmiş")
        return 0

    elif sub == "delete":
        username = getattr(args, "username", "")
        if not username:
            print("❌ Kullanıcı adı gerekli")
            return 1
        if _auth.delete_user(username):
            print(f"✅ Kullanıcı silindi: {username}")
        else:
            print(f"❌ Kullanıcı bulunamadı: {username}")
        return 0

    elif sub == "role":
        username = getattr(args, "username", "")
        role = getattr(args, "role", "")
        if not username or not role:
            print("❌ Kullanıcı adı ve rol gerekli (admin/user/guest)")
            return 1
        if role not in ("admin", "user", "guest"):
            print(f"❌ Geçersiz rol: {role} (admin/user/guest)")
            return 1
        if _auth.update_user_role(username, role):
            print(f"✅ {username} rolü → {role}")
        else:
            print(f"❌ Kullanıcı bulunamadı: {username}")
        return 0

    elif sub == "key":
        key_value = getattr(args, "key_value", "")
        if not key_value:
            print("❌ API anahtarı gerekli")
            return 1
        from reymen.guvenlik.reymen_auth import validate_api_key_format
        valid, provider, msg = validate_api_key_format(key_value)
        if valid:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
        return 0

    elif sub == "cleanup":
        count = _auth.cleanup()
        print(f"🧹 {count} süresi dolmuş token temizlendi")
        return 0

    else:
        print("🔐 ReYMeN Auth Sistemi")
        print()
        print("Kullanım: reymen auth <komut> [argümanlar]")
        print()
        print("Komutlar:")
        print("  status              Auth sistemi durumu")
        print("  list                Token'ları listele")
        print("  users               Kullanıcıları listele")
        print("  create <user>       Kullanıcı + token oluştur")
        print("  token <user>        Token oluştur")
        print("  revoke <token>      Token iptal et")
        print("  delete <user>       Kullanıcı sil")
        print("  role <user> <role>  Rol değiştir (admin/user/guest)")
        print("  key <api_key>       API key doğrula")
        print("  cleanup             Süresi dolmuş token'ları temizle")
        return 0


# ── A2A/ACP ────────────────────────────────────────────────────────────────────
def cmd_a2a(args: argparse.Namespace) -> int:
    """A2A/ACP protokol yönetimi.

    Kullanım:
        reymen a2a status         → A2A/ACP durumu
        reymen a2a start          → ACP sunucusunu başlat (stdio)
        reymen a2a stop           → ACP sunucusunu durdur
        reymen a2a card list      → Agent Card'ları listele
        reymen a2a card register  → Agent Card kaydet
        reymen a2a task list      → Devredilen görevleri listele
        reymen a2a task delegate  → Görev devret
        reymen a2a skill transfer → Beceri aktar
        reymen a2a stats          → İstatistikler
    """
    alt = getattr(args, "a2a_sub", None) or "status"

    # Önce ACP modülünü yükle
    try:
        from reymen.a2a_acp import (
            ACPServer, AgentCard, _ACP_SERVER_INSTANCE,
        )
        _acp_loaded = True
    except ImportError as e:
        print(f"[HATA] A2A/ACP modulu yuklenemedi: {e}")
        return 1

    if alt == "status":
        if _ACP_SERVER_INSTANCE and _ACP_SERVER_INSTANCE.running:
            s = _ACP_SERVER_INSTANCE
            print(f"  ACP Sunucu: 🟢 AKTIF")
            print(f"  Transport:  {s.transport}")
            print(f"  Agentler:   {s._card_registry.count()}")
            print(f"  Gorevler:   {s._delegation.stats()['total']}")
            print(f"  Calisma:    {time.time() - s._start_time:.0f}s")
        else:
            print(f"  ACP Sunucu: 🔴 KAPALI")
            print(f"  (ACP_BASLAT ile baslat veya 'reymen a2a start')")
        return 0

    if alt == "start":
        transport = getattr(args, "transport", "stdio")
        port = getattr(args, "port", 9200)
        try:
            server = ACPServer(transport=transport, host="127.0.0.1", port=port)
            server.start_threaded()
            time.sleep(0.2)
            print(f"  ✅ ACP sunucusu baslatildi ({transport})")
            return 0
        except Exception as e:
            print(f"  ❌ Baslatma hatasi: {e}")
            return 1

    if alt == "stop":
        if _ACP_SERVER_INSTANCE and _ACP_SERVER_INSTANCE.running:
            _ACP_SERVER_INSTANCE.stop()
            print("  ✅ ACP sunucusu durduruldu")
        else:
            print("  ℹ️  ACP sunucusu zaten kapali")
        return 0

    if alt in ("card",):
        card_sub = getattr(args, "card_sub", "list")
        if card_sub == "list":
            if not _ACP_SERVER_INSTANCE or not _ACP_SERVER_INSTANCE.running:
                print("  ℹ️  ACP sunucusu calismiyor")
                return 0
            cards = _ACP_SERVER_INSTANCE._card_registry.list()
            if not cards:
                print("  Kayitli agent yok.")
                return 0
            print(f"  Kayitli Agent'lar ({len(cards)}):")
            for c in cards:
                caps = ", ".join(c.capabilities[:4])
                print(f"    🆔 {c.agent_id}")
                print(f"       İsim: {c.name or '-'}")
                print(f"       Yetenek: {caps or '-'}")
                print(f"       Beceri: {len(c.skills)} adet")
            return 0
        elif card_sub == "register":
            agent_id = getattr(args, "agent_id", None)
            if not agent_id:
                print("  ❌ agent_id gerekli")
                return 1
            if not _ACP_SERVER_INSTANCE or not _ACP_SERVER_INSTANCE.running:
                print("  ❌ ACP sunucusu calismiyor. Once 'reymen a2a start'")
                return 1
            caps_str = getattr(args, "capabilities", "messaging")
            skills_str = getattr(args, "skills", "")
            card = AgentCard(
                agent_id=agent_id,
                name=getattr(args, "name", agent_id),
                capabilities=[c.strip() for c in caps_str.split(",") if c.strip()],
                skills=[s.strip() for s in skills_str.split(",") if s.strip()],
            )
            _ACP_SERVER_INSTANCE._card_registry.register(card)
            print(f"  ✅ Card kaydedildi: {agent_id}")
            return 0

    if alt == "task":
        task_sub = getattr(args, "task_sub", "list")
        if task_sub == "list":
            if not _ACP_SERVER_INSTANCE or not _ACP_SERVER_INSTANCE.running:
                print("  ℹ️  ACP sunucusu calismiyor")
                return 0
            tasks = _ACP_SERVER_INSTANCE._delegation.list_tasks(
                agent_id=getattr(args, "agent_id", None),
                status=getattr(args, "task_status", None),
            )
            if not tasks:
                print("  Gorev yok.")
                return 0
            print(f"  Gorevler ({len(tasks)}):")
            for t in tasks:
                print(f"    📋 {t.task_id[:12]} | {t.title[:40]:<42} | {t.status:<12}")
            return 0
        elif task_sub == "delegate":
            if not _ACP_SERVER_INSTANCE or not _ACP_SERVER_INSTANCE.running:
                print("  ❌ ACP sunucusu calismiyor")
                return 1
            source = getattr(args, "source", "reymen")
            target = getattr(args, "target", "")
            title = getattr(args, "title", "")
            if not target or not title:
                print("  ❌ target ve title gerekli")
                return 1
            task = _ACP_SERVER_INSTANCE._delegation.delegate(
                source=source, target=target, title=title,
                description=getattr(args, "description", ""),
            )
            print(f"  ✅ Gorev devredildi: {task.task_id}")
            print(f"     {source} -> {target}: {title}")
            return 0

    if alt == "stats":
        if not _ACP_SERVER_INSTANCE or not _ACP_SERVER_INSTANCE.running:
            print("  ℹ️  ACP sunucusu calismiyor")
            return 0
        s = _ACP_SERVER_INSTANCE
        del_stats = s._delegation.stats()
        print(f"  ACP Istatistikleri:")
        print(f"    Agent Sayisi:  {s._card_registry.count()}")
        print(f"    Toplam Gorev:  {del_stats['total']}")
        print(f"    Tamamlanan:    {del_stats['completed']}")
        print(f"    Bekleyen:      {del_stats['pending']}")
        print(f"    Basarisiz:     {del_stats['failed']}")
        print(f"    Reddedilen:    {del_stats['rejected']}")
        return 0

    print(f"  ❌ Bilinmeyen a2a alt komutu: {alt}")
    return 1


# ---------------------------------------------------------------------------
# Parser (ReYMeN'teki _parser.py karşılığı)
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Birleşik CLI parser."""
    parser = argparse.ArgumentParser(
        prog="reymen",
        description="ReYMeN Agent - AI assistant with tool-calling capabilities",
    )
    parser.set_defaults(func=None)

    sub = parser.add_subparsers(dest="command", required=True)

    # version
    p_ver = sub.add_parser("version", help="Versiyon bilgisi")
    p_ver.set_defaults(func=cmd_version)

    # status
    p_st = sub.add_parser("status", help="Genel durum raporu")
    p_st.set_defaults(func=cmd_status)

    # model
    p_mdl = sub.add_parser("model", help="Model/Provider seçimi")
    p_mdl.set_defaults(func=cmd_model)

    # cost
    p_cost = sub.add_parser("cost", help="API maliyet takibi")
    p_cost_sub = p_cost.add_subparsers(dest="sub")
    p_cost_sub.add_parser("summary", help="Maliyet özeti")
    p_log = p_cost_sub.add_parser("log", help="Ham kayıtlar")
    p_log.add_argument("--limit", type=int, default=20)
    p_cost_sub.add_parser("reset", help="Kayıtları temizle")
    p_cost.set_defaults(func=cmd_cost, sub="summary")

    # skill
    p_skill = sub.add_parser("skill", help="Skill yönetimi")
    p_skill_sub = p_skill.add_subparsers(dest="skill_sub")
    p_shrink = p_skill_sub.add_parser("shrink", help="Şişkin skill'leri tespit et/küçült")
    p_shrink.add_argument("--dry-run", action="store_true", default=True,
                          help="Sadece tespit et, değişiklik yapma (varsayılan)")
    p_shrink.add_argument("--apply", action="store_true", default=False,
                          help="Bulunan şişkinlikleri uygula")
    p_shrink.add_argument("--stats", action="store_true", default=False,
                          help="Skill deposu istatistikleri")
    p_shrink.set_defaults(func=cmd_skill_shrink)

    # auth 🔐
    p_auth = sub.add_parser("auth", help="🔐 Auth yönetimi (token, kullanıcı, API key)")
    p_auth_sub = p_auth.add_subparsers(dest="auth_sub")
    p_auth_sub.add_parser("status", help="Auth sistemi durumu")
    p_auth_sub.add_parser("list", help="Token'ları listele")
    p_auth_sub.add_parser("users", help="Kullanıcıları listele")
    p_auth_create = p_auth_sub.add_parser("create", help="Kullanıcı + token oluştur")
    p_auth_create.add_argument("username", nargs="?", default="kullanici")
    p_auth_create.add_argument("--role", "-r", default="user", choices=["admin", "user", "guest"])
    p_auth_token = p_auth_sub.add_parser("token", help="Token oluştur")
    p_auth_token.add_argument("username", nargs="?", default="kullanici")
    p_auth_token.add_argument("--role", "-r", default="user", choices=["admin", "user", "guest"])
    p_auth_revoke = p_auth_sub.add_parser("revoke", help="Token iptal et")
    p_auth_revoke.add_argument("token_value", help="İptal edilecek token")
    p_auth_delete = p_auth_sub.add_parser("delete", help="Kullanıcı sil")
    p_auth_delete.add_argument("username", help="Silinecek kullanıcı")
    p_auth_role = p_auth_sub.add_parser("role", help="Kullanıcı rolü değiştir")
    p_auth_role.add_argument("username", help="Kullanıcı adı")
    p_auth_role.add_argument("role", choices=["admin", "user", "guest"])
    p_auth_key = p_auth_sub.add_parser("key", help="API key doğrula")
    p_auth_key.add_argument("key_value", help="Doğrulanacak API anahtarı")
    p_auth_sub.add_parser("cleanup", help="Süresi dolmuş token'ları temizle")
    p_auth.set_defaults(func=cmd_auth)

    # a2a/ACP
    p_a2a = sub.add_parser("a2a", help="📡 A2A/ACP protokol yönetimi (Agent Card, görev devretme, beceri aktarımı)")

    # kural (Rules Engine)
    p_kural = sub.add_parser("kural", help="📋 Kural/izin yönetimi (Rules Engine)")
    p_kural_sub = p_kural.add_subparsers(dest="kural_sub")
    p_kural_list = p_kural_sub.add_parser("list", help="Kuralları listele")
    p_kural_list.add_argument("--kategori", choices=["dosya_erisim", "ag", "komut", "api_cagrisi", "guvenlik"],
                               help="Kategori filtresi")
    p_kural_list.add_argument("--tip", choices=["izin", "engel", "uyari"], help="Kural tipi filtresi")
    p_kural_list.add_argument("--aktif", action="store_true", help="Sadece aktif kurallar")
    p_kural_ekle = p_kural_sub.add_parser("ekle", help="Yeni kural ekle")
    p_kural_ekle.add_argument("kategori", choices=["dosya_erisim", "ag", "komut", "api_cagrisi", "guvenlik"],
                               help="Kural kategorisi")
    p_kural_ekle.add_argument("tip", choices=["izin", "engel", "uyari"], help="Kural tipi")
    p_kural_ekle.add_argument("desen", help="Eşleşme deseni (wildcard veya re: ile regex)")
    p_kural_ekle.add_argument("--sebep", "-s", default="", help="Kural açıklaması")
    p_kural_ekle.add_argument("--id", default=None, help="Kural ID'si (opsiyonel)")
    p_kural_sil = p_kural_sub.add_parser("sil", help="Kural sil")
    p_kural_sil.add_argument("kural_id", help="Silinecek kural ID'si")
    p_kural_kontrol = p_kural_sub.add_parser("kontrol", help="Bir hedefi kurallara göre kontrol et")
    p_kural_kontrol.add_argument("kategori", choices=["dosya_erisim", "ag", "komut", "api_cagrisi", "guvenlik"],
                                  help="Kontrol kategorisi")
    p_kural_kontrol.add_argument("hedef", help="Kontrol edilecek hedef (dosya yolu, komut, URL vb.)")
    p_kural.set_defaults(func=cmd_kural)
    p_a2a_sub = p_a2a.add_subparsers(dest="a2a_sub")
    p_a2a_sub.add_parser("status", help="A2A/ACP durumu")
    p_a2a_start = p_a2a_sub.add_parser("start", help="ACP sunucusunu başlat")
    p_a2a_start.add_argument("--transport", default="stdio", choices=["stdio", "socket"],
                             help="Taşıma protokolü (varsayılan: stdio)")
    p_a2a_start.add_argument("--port", type=int, default=9200,
                             help="Socket port (transport=socket ise, varsayılan: 9200)")
    p_a2a_sub.add_parser("stop", help="ACP sunucusunu durdur")

    # card alt komutları
    p_card = p_a2a_sub.add_parser("card", help="Agent Card yönetimi")
    p_card_sub = p_card.add_subparsers(dest="card_sub")
    p_card_sub.add_parser("list", help="Agent Card'ları listele")
    p_card_reg = p_card_sub.add_parser("register", help="Agent Card kaydet")
    p_card_reg.add_argument("agent_id", help="Benzersiz agent ID")
    p_card_reg.add_argument("--name", default="", help="Gösterim adı")
    p_card_reg.add_argument("--capabilities", default="messaging",
                            help="Yetenek listesi (virgülle ayrılmış)")
    p_card_reg.add_argument("--skills", default="", help="Beceri listesi (virgülle ayrılmış)")
    p_card.set_defaults(card_sub="list")

    # task alt komutları
    p_task = p_a2a_sub.add_parser("task", help="Görev devretme yönetimi")
    p_task_sub = p_task.add_subparsers(dest="task_sub")
    p_task_list = p_task_sub.add_parser("list", help="Devredilen görevleri listele")
    p_task_list.add_argument("--agent-id", help="Agent ID filtresi")
    p_task_list.add_argument("--status", dest="task_status",
                              help="Durum filtresi (pending/accepted/completed/failed)")
    p_task_del = p_task_sub.add_parser("delegate", help="Yeni görev devret")
    p_task_del.add_argument("target", help="Hedef agent ID")
    p_task_del.add_argument("title", help="Görev başlığı")
    p_task_del.add_argument("--source", default="reymen", help="Kaynak agent ID (varsayılan: reymen)")
    p_task_del.add_argument("--description", default="", help="Görev açıklaması")
    p_task.set_defaults(task_sub="list")

    p_a2a_sub.add_parser("stats", help="ACP istatistikleri")
    p_a2a.set_defaults(func=cmd_a2a)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.func:
        return args.func(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
