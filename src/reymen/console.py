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
from datetime import datetime
from typing import Any


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
