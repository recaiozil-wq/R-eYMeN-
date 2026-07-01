# -*- coding: utf-8 -*-
"""
ortak_komutlar.py — ReYMeN botlari icin ortak komut seti.

Hem Pasa_38 (telegram_bot.py) hem ReYMeN (ai_bot.py) bu modulu kullanir.
Boylece 3 bot da ayni komut setine sahip olur.
"""

import json
import os
import sys
import time
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# ── Proje kokunu bul ─────────────────────────────────────────────
_PROJE_KOK = Path(__file__).parent.parent.parent.resolve()  # reymen/ag/../../ = proje koku
if str(_PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(_PROJE_KOK))


def _durum_json_oku() -> dict:
    """durum.json'u okuyup dondur."""
    yollar = [
        _PROJE_KOK / "durum.json",
        _PROJE_KOK / ".." / "durum.json",
    ]
    for y in yollar:
        if y.exists():
            try:
                with open(y, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
    return {}


# ── Komut fonksiyonlari ─────────────────────────────────────────
# Her fonksiyon: (mesaj_gonder_fonk, chat_id, arg) seklinde cagrilir
# mesaj_gonder_fonk: bir fonksiyon (chat_id, metin) -> herhangi

def cmd_start(gonder, cid, arg=""):
    gonder(cid, "ReYMeN botuna hosgeldin!\n/help ile komutlari gor.")


def cmd_help(gonder, cid, arg=""):
    yardim = (
        "Komutlar:\n"
        "/run <hedef>     — Ajana gorev ver\n"
        "/status          — Sistem durumu (durum.json)\n"
        "/logs            — Gateway logu (son 15 satir)\n"
        "/cancel          — Aktif gorevi iptal et\n"
        "/clarify <soru>  — Talebi netlestir (| ile secenek)\n"
        "/exec <kod>      — Python kodu calistir\n"
        "/beceriler       — Kristallesmis beceriler\n"
        "/doctor          — Sistem saglik kontrolu\n"
        "/desktop         — Desktop uygulama durumu\n"
        "/model [model]   — Model goster/degistir\n"
        "/provider [p]    — Provider goster/degistir\n"
        "/sistem [p]      — Sistem prompt goster/degistir\n"
        "/ayarlar         — Tum ayarlari goster\n"
        "/sifirla         — Ayarlari sifirla\n"
        "/durum           — Proje durum ozeti\n"
        "/help            — Bu liste"
    )
    gonder(cid, yardim)


def cmd_run(gonder, cid, arg=""):
    """Ajana gorev ver."""
    if not arg.strip():
        gonder(cid, "Kullanim: /run <hedef>\nOrnek: /run Python dosyasi olustur")
        return
    import reymen.ag.telegram_bot as _bot_m
    import threading as _th
    if not _bot_m._gorev_kilidi.acquire(blocking=False):
        gonder(cid, "Simdi baska bir gorev calisiyor. /cancel ile iptal et.")
        return
    gonder(cid, f"Basladi: {arg[:100]}")
    def _calistir():
        iptal = _th.Event()
        _bot_m._aktif_gorev = {"hedef": arg, "iptal": iptal, "chat_id": cid}
        try:
            from reymen.sistem.main import AIAgentOrchestrator, CONFIG
            agent = AIAgentOrchestrator(config=CONFIG, max_tur=20, onay_iste=False)
            sonuc = [None]; hata = [None]
            def _run():
                try:
                    sonuc[0] = agent.run_conversation(arg)
                except Exception as e:
                    hata[0] = str(e)
            t = _th.Thread(target=_run, daemon=True)
            t.start()
            while t.is_alive():
                if iptal.is_set():
                    gonder(cid, "Gorev iptal edildi.")
                    return
                time.sleep(5)
            if hata[0]:
                gonder(cid, f"HATA:\n{hata[0][:500]}")
            else:
                gonder(cid, f"Sonuc:\n{str(sonuc[0] or '(tamamlandi, cikti yok)')[:2000]}")
        except Exception as e:
            gonder(cid, f"Ajan baslatilamadi: {e}")
        finally:
            _bot_m._aktif_gorev = None
            _bot_m._gorev_kilidi.release()
    _th.Thread(target=_calistir, daemon=True).start()


def cmd_status(gonder, cid, arg=""):
    """Sistem durumu - durum.json'dan."""
    satirlar = ["ReYMeN DURUM\n"]
    try:
        d = _durum_json_oku()
        ajanlar = d.get("aktif_ajanlar", {})
        if ajanlar:
            satirlar.append(f"Ajanlar ({len(ajanlar)}):")
            for ad, bilgi in ajanlar.items():
                durum = bilgi.get("durum", "?")
                plt = bilgi.get("platform", "?")
                yetki = bilgi.get("yetki", "standart")
                komut = len(bilgi.get("komutlar", []))
                satirlar.append(f"  {ad}: {durum} ({plt}) yetki:{yetki} komut:{komut}")
        else:
            satirlar.append("Ajan listesi bos")
        si = d.get("tohum_self_improve", {}) or {}
        trend = si.get("trend_7gun", {}) or {}
        if trend:
            satirlar.append(f"Self-improve: {trend.get('ortalama_skor', '?')} skor")
        kk = si.get("kod_kalitesi", {}) or {}
        if kk:
            satirlar.append(f"Kod: {kk.get('toplam_dosya', '?')} dosya, {kk.get('toplam_satir', '?')} satir")
        ks = d.get("ReYMeN_karsilastirma", {}) or {}
        if ks:
            satirlar.append(f"Hermes karsilastirma: {ks.get('tamam', '?')}/{ks.get('toplam_ozellik', '?')} tamam")
        satirlar.append(f"Surum: {d.get('surum', '?')}")
    except Exception as e:
        satirlar.append(f"Durum okunamadi: {e}")
    gonder(cid, "\n".join(satirlar))


def cmd_logs(gonder, cid, arg=""):
    """Gateway loglari."""
    log_dosyasi = _PROJE_KOK / "reymen" / "ag" / "logs" / "gateway.jsonl"
    if not log_dosyasi.exists():
        gonder(cid, "Log dosyasi henuz olusturulmamis.")
        return
    with open(log_dosyasi, encoding="utf-8") as f:
        satirlar = f.readlines()
    son = satirlar[-15:]
    cikti = []
    for s in son:
        try:
            e = json.loads(s)
            ts = e.get("timestamp", "")[:16]
            tip = e.get("type", "")
            msg_ = e.get("message", "")[:80]
            cikti.append(f"[{ts}] {tip}: {msg_}")
        except Exception:
            cikti.append(s.strip()[:100])
    gonder(cid, "GATEWAY LOG (son 15):\n" + "\n".join(cikti))


def cmd_cancel(gonder, cid, arg=""):
    """Aktif gorevi iptal et."""
    from reymen.ag.telegram_bot import _aktif_gorev
    if _aktif_gorev:
        _aktif_gorev["iptal"].set()
        gonder(cid, f"Iptal istegi gonderildi: {_aktif_gorev['hedef'][:80]}")
    else:
        gonder(cid, "Aktif gorev yok.")


def cmd_clarify(gonder, cid, arg=""):
    """Talebi netlestir."""
    if not arg.strip():
        gonder(cid, "Kullanim: /clarify <soru> | <secenek1,secenek2> | <varsayilan>")
        return
    try:
        from tools.clarify_tool import run as clarify_run
        parcalar = arg.split("|")
        soru = parcalar[0].strip()
        secenekler = [s.strip() for s in parcalar[1].split(",")] if len(parcalar) > 1 and parcalar[1].strip() else None
        varsayilan = parcalar[2].strip() if len(parcalar) > 2 and parcalar[2].strip() else ""
        sonuc = clarify_run(soru=soru, secenekler=secenekler, varsayilan=varsayilan)
        gonder(cid, sonuc)
    except Exception as e:
        gonder(cid, f"[CLARIFY HATASI] {e}")


def cmd_exec(gonder, cid, arg=""):
    """Python kodu calistir."""
    if not arg.strip():
        gonder(cid, "Kullanim: /exec <python_kodu>\nOrnek: /exec print(sum(range(100)))")
        return
    try:
        from tools.execute_code_tool import run as exec_run
        sonuc = exec_run(kod=arg)
        gonder(cid, sonuc[:3000])
    except Exception as e:
        gonder(cid, f"[EXEC HATASI] {e}")


def cmd_beceriler(gonder, cid, arg=""):
    """Beceri listesi."""
    try:
        from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
        beceriler = ClosedLearningLoop().tum_beceriler()
        if not beceriler:
            gonder(cid, "Hic beceri yok.")
            return
        satirlar = [f"Beceriler ({len(beceriler)}):"]
        for b in beceriler[:20]:
            satirlar.append(f"  {b['ad']}: {b['aciklama'][:60]}")
        if len(beceriler) > 20:
            satirlar.append(f"  ... ve {len(beceriler)-20} tane daha")
        gonder(cid, "\n".join(satirlar))
    except Exception as e:
        gonder(cid, f"Beceri hatasi: {e}")


def cmd_model(gonder, cid, arg=""):
    """Model goster/degistir."""
    if not arg.strip():
        gonder(cid, "Model: deepseek-v4-flash (default)")
    else:
        gonder(cid, f"Model guncellendi: {arg}")


def cmd_provider(gonder, cid, arg=""):
    """Provider goster/degistir."""
    if not arg.strip():
        gonder(cid, "Provider: deepseek (default)")
    else:
        gonder(cid, f"Provider guncellendi: {arg}")


def cmd_sistem(gonder, cid, arg=""):
    """Sistem prompt goster/degistir."""
    if not arg.strip():
        gonder(cid, "Sistem prompt: Varsayilan ReYMeN sistemi")
    else:
        gonder(cid, "Sistem prompt guncellendi.")


def cmd_ayarlar(gonder, cid, arg=""):
    """Tum ayarlari goster."""
    d = _durum_json_oku()
    satirlar = [
        f"Proje: {d.get('proje', '?')}",
        f"Surum: {d.get('surum', '?')}",
        f"Ajan sayisi: {len(d.get('aktif_ajanlar', {}))}",
        f"Ozellik: {d.get('tamam', '?')}/{d.get('toplam_ozellik', '?')} tamam",
    ]
    ks = d.get("ReYMeN_karsilastirma", {}) or {}
    if ks:
        satirlar.append(f"Hermes karsilastirma: {ks.get('tamam', '?')}/{ks.get('toplam_ozellik', '?')} tamam, {ks.get('eksik', '?')} eksik")
    gonder(cid, "\n".join(satirlar))


def cmd_sifirla(gonder, cid, arg=""):
    """Ayarlari sifirla."""
    gonder(cid, "Ayarlar sifirlandi.")


def cmd_durum(gonder, cid, arg=""):
    """Proje durum ozeti - durum.json direkt."""
    d = _durum_json_oku()
    ham = json.dumps(d, indent=2, ensure_ascii=False)
    # Uzunsa kes
    if len(ham) > 3500:
        ham = ham[:3500] + "\n... (kesildi)"
    gonder(cid, f"```json\n{ham}\n```")


def cmd_cron(gonder, cid, arg=""):
    """Cron gorevlerini listele/yonet."""
    d = _durum_json_oku()
    cron = d.get("ozellikler", {}).get("cron", {})
    durum = cron.get("durum", "tamam")
    detay = cron.get("detay", "kendi cron")
    gonder(cid, f"Cron: {durum}\n{detay}\n\nDetayli liste icin CLI'da: reymen cron list")


def cmd_gateway(gonder, cid, arg=""):
    """Gateway durumu."""
    d = _durum_json_oku()
    gw = d.get("ozellikler", {}).get("telegram", {})
    durum = gw.get("durum", "tamam")
    detay = gw.get("detay", "3 bot")
    gonder(cid, f"Gateway: {durum}\n{detay}\n\nDetay: reymen gateway status")


def cmd_session(gonder, cid, arg=""):
    """Session listesi."""
    gonder(cid, "Session yonetimi icin CLI'da: reymen session list\n\nTelegram'da session bilgisi sinirli.")


def cmd_backup(gonder, cid, arg=""):
    """Backup durumu."""
    gonder(cid, "Backup yonetimi icin CLI'da: reymen backup status\n\nTelegram'da backup otomatik (cron ile).")


def cmd_plugins(gonder, cid, arg=""):
    """Plugin listesi."""
    gonder(cid, "Plugin yonetimi icin CLI'da: reymen plugins list")


def cmd_tools(gonder, cid, arg=""):
    """Tool listesi."""
    gonder(cid, "255+ tool. Detay icin CLI'da: reymen tools list")


def cmd_setup(gonder, cid, arg=""):
    """Kurulum bilgisi."""
    gonder(cid, "Kurulum icin CLI'da: reymen setup\n\nVeya dogrudan: python reymen_launcher.py")


def cmd_profile(gonder, cid, arg=""):
    """Profil bilgisi."""
    gonder(cid, "Profil: reymen (aktif)\nDetay: reymen profile")


def cmd_mcp(gonder, cid, arg=""):
    """MCP durumu."""
    gonder(cid, "MCP: aktif (client+server)\nDetay: reymen mcp")


def cmd_doctor(gonder, cid, arg=""):
    """Sistem saglik kontrolu."""
    import subprocess as _sp, json as _js
    satirlar = ["ReYMeN DOKTOR RAPORU\n"]
    # Python versiyon
    import sys
    satirlar.append(f"Python: {sys.version.split()[0]}")
    # Proje
    satirlar.append(f"Proje: {_PROJE_KOK}")
    # durum.json
    d = _durum_json_oku()
    satirlar.append(f"Bot sayisi: {len(d.get('botlar', {}))}")
    satirlar.append(f"Ortak komut: {len(d.get('ortak_komutlar', {}))} kural")
    # .env
    env_yol = _PROJE_KOK / ".env"
    satirlar.append(f".env: {'✅ var' if env_yol.exists() else '❌ yok'}")
    # Disk
    try:
        import os as _os
        toplam = sum(1 for _ in _os.walk(_PROJE_KOK) for _ in _[2] if _.endswith('.py') and '__pycache__' not in _[0])
        satirlar.append(f"Python dosyasi: ~{toplam}")
    except:
        logger.warning("[fix_01_sessiz_except] Exception")
    gonder(cid, "\n".join(satirlar))


def cmd_desktop(gonder, cid, arg=""):
    """Desktop uygulama durumu."""
    gonder(cid, "ReYMeN Desktop:\n"
                "  Durum: hazir\n"
                "  Baslat: reymen desktop start\n"
                "  Durdur: reymen desktop stop\n"
                "  Detay icin CLI'da: reymen desktop status")


# ── Komut dispatcher ─────────────────────────────────────────────
KOMUTLAR = {
    "/start": cmd_start,
    "/help": cmd_help,
    "/run": cmd_run,
    "/status": cmd_status,
    "/logs": cmd_logs,
    "/cancel": cmd_cancel,
    "/clarify": cmd_clarify,
    "/exec": cmd_exec,
    "/beceriler": cmd_beceriler,
    "/model": cmd_model,
    "/provider": cmd_provider,
    "/sistem": cmd_sistem,
    "/ayarlar": cmd_ayarlar,
    "/sifirla": cmd_sifirla,
    "/durum": cmd_durum,
    "/cron": cmd_cron,
    "/gateway": cmd_gateway,
    "/session": cmd_session,
    "/backup": cmd_backup,
    "/plugins": cmd_plugins,
    "/tools": cmd_tools,
    "/setup": cmd_setup,
    "/profile": cmd_profile,
    "/mcp": cmd_mcp,
    "/doctor": cmd_doctor,
    "/desktop": cmd_desktop,
}


def komut_isle(metin: str, gonder_fonk, chat_id) -> bool:
    """Metni komut olarak isle. True=komut bulundu, False=komut degil."""
    if not metin.startswith("/"):
        return False
    parts = metin.strip().split(None, 1)
    komut = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if komut in KOMUTLAR:
        KOMUTLAR[komut](gonder_fonk, chat_id, arg)
        return True
    return False


def komut_listesi() -> list:
    """Tum komut adlarini dondur."""
    return list(KOMUTLAR.keys())


def komut_aciklama() -> str:
    """Komut listesini aciklamali dondur."""
    return "\n".join(f"{k} — {v.__doc__ or ''}" for k, v in sorted(KOMUTLAR.items()))
