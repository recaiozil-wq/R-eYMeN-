# -*- coding: utf-8 -*-
"""
📊 analitik.py — ReYMeN Kalite/Analitik Motoru.

SQLite tabanli metrik toplama, raporlama ve dashboard.
Her LLM cagrisi, tool kullanimi, hata ve maliyeti kaydeder.

Kullanim (motor):
    ANALITIK_KAYDET(tur="llm_cagri", detay={"model": "deepseek", "token": 1500})
    ANALITIK_RAPOR(gun=7)  → son 7 gun
    ANALITIK_PANEL()       → HTML dashboard
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Sabitler ────────────────────────────────────────────────────────────────

PROJE_KOK: Path = Path(__file__).resolve().parent.parent.parent
DB_DIZINI: Path = PROJE_KOK / "reymen" / "merkez_db"
DB_DIZINI.mkdir(parents=True, exist_ok=True)
VERITABANI: str = str(DB_DIZINI / "analitik.db")

# Olay turleri
TUR_LLM_CAGRI = "llm_cagri"
TUR_TOOL_KULLANIM = "tool_kullanim"
TUR_HATA = "hata"
TUR_MALIYET = "maliyet"
TUR_MESAJ = "mesaj"
TUR_SESSION = "session"

_local = threading.local()


def _baglan() -> sqlite3.Connection:
    """Thread-safe SQLite baglantisi."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(VERITABANI)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
    return _local.conn


def _tablolari_olustur():
    """Idempotent tablo olusturma."""
    conn = _baglan()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS olaylar (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            zaman       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            tur         TEXT NOT NULL,
            kaynak      TEXT DEFAULT '',
            sure_ms     INTEGER DEFAULT 0,
            token_giris INTEGER DEFAULT 0,
            token_cikis INTEGER DEFAULT 0,
            maliyet     REAL DEFAULT 0.0,
            basarili    INTEGER DEFAULT 1,
            hata_mesaji TEXT DEFAULT '',
            detay_json  TEXT DEFAULT '{}',
            bot_adi     TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_olay_zaman ON olaylar(zaman);
        CREATE INDEX IF NOT EXISTS idx_olay_tur ON olaylar(tur);
        CREATE INDEX IF NOT EXISTS idx_olay_bot ON olaylar(bot_adi);

        CREATE TABLE IF NOT EXISTS gunluk_ozet (
            tarih       TEXT PRIMARY KEY,
            toplam_soru INTEGER DEFAULT 0,
            basarili    INTEGER DEFAULT 0,
            hata        INTEGER DEFAULT 0,
            toplam_token INTEGER DEFAULT 0,
            toplam_maliyet REAL DEFAULT 0.0,
            ortalama_sure_ms REAL DEFAULT 0.0,
            bot_bazli   TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS provider_ozet (
            provider    TEXT NOT NULL,
            tarih       TEXT NOT NULL,
            cagri       INTEGER DEFAULT 0,
            token       INTEGER DEFAULT 0,
            maliyet     REAL DEFAULT 0.0,
            PRIMARY KEY (provider, tarih)
        );
    """)
    conn.commit()


# ── Kayit Fonksiyonlari ─────────────────────────────────────────────────────

def kaydet(
    tur: str,
    kaynak: str = "",
    sure_ms: int = 0,
    token_giris: int = 0,
    token_cikis: int = 0,
    maliyet: float = 0.0,
    basarili: bool = True,
    hata_mesaji: str = "",
    detay: Optional[dict] = None,
    bot_adi: str = "",
) -> int:
    """Bir olay/kayit ekler.

    Ornek:
        kaydet("llm_cagri", "deepseek", sure_ms=1500,
               token_giris=500, token_cikis=200, maliyet=0.002)
    """
    _tablolari_olustur()
    conn = _baglan()
    cur = conn.execute(
        """INSERT INTO olaylar
           (tur, kaynak, sure_ms, token_giris, token_cikis,
            maliyet, basarili, hata_mesaji, detay_json, bot_adi)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            tur, kaynak, sure_ms, token_giris, token_cikis,
            maliyet, 1 if basarili else 0, hata_mesaji,
            json.dumps(detay or {}, ensure_ascii=False),
            bot_adi,
        ),
    )
    conn.commit()
    return cur.lastrowid or 0


def llm_cagri_kaydet(
    model: str,
    sure_ms: int,
    token_giris: int,
    token_cikis: int,
    maliyet: float = 0.0,
    basarili: bool = True,
    hata: str = "",
    bot: str = "",
) -> int:
    """Kisa yol: LLM cagrisi kaydet."""
    return kaydet(
        tur=TUR_LLM_CAGRI,
        kaynak=model,
        sure_ms=sure_ms,
        token_giris=token_giris,
        token_cikis=token_cikis,
        maliyet=maliyet,
        basarili=basarili,
        hata_mesaji=hata,
        bot_adi=bot,
        detay={"model": model},
    )


def tool_kullanimi_kaydet(
    tool_adi: str,
    sure_ms: int,
    basarili: bool = True,
    hata: str = "",
    bot: str = "",
) -> int:
    """Kisa yol: tool kullanimi kaydet."""
    return kaydet(
        tur=TUR_TOOL_KULLANIM,
        kaynak=tool_adi,
        sure_ms=sure_ms,
        basarili=basarili,
        hata_mesaji=hata,
        bot_adi=bot,
    )


def hata_kaydet(
    kaynak: str,
    hata_mesaji: str,
    bot: str = "",
    detay: Optional[dict] = None,
) -> int:
    """Kisa yol: hata kaydet."""
    return kaydet(
        tur=TUR_HATA,
        kaynak=kaynak,
        basarili=False,
        hata_mesaji=hata_mesaji,
        bot_adi=bot,
        detay=detay,
    )


# ── Rapor Fonksiyonlari ─────────────────────────────────────────────────────

def ozet_son_n(gun: int = 7) -> dict[str, Any]:
    """Son N gunun ozet metrikleri."""
    _tablolari_olustur()
    conn = _baglan()
    kesim = (datetime.now(timezone.utc) - timedelta(days=gun)).isoformat()

    # Genel metrikler
    genel = conn.execute(
        """SELECT
            COUNT(*) as toplam,
            SUM(CASE WHEN basarili=1 THEN 1 ELSE 0 END) as basarili,
            SUM(CASE WHEN basarili=0 THEN 1 ELSE 0 END) as basarisiz,
            COALESCE(SUM(token_giris + token_cikis), 0) as toplam_token,
            COALESCE(SUM(maliyet), 0) as toplam_maliyet,
            COALESCE(AVG(sure_ms), 0) as ortalama_sure
         FROM olaylar WHERE zaman >= ?""",
        (kesim,),
    ).fetchone()

    # Tur bazli
    tur_bazli = {}
    for row in conn.execute(
        "SELECT tur, COUNT(*) as adet FROM olaylar WHERE zaman >= ? GROUP BY tur",
        (kesim,),
    ):
        tur_bazli[row["tur"]] = row["adet"]

    # Gunluk trend
    trend = []
    for row in conn.execute(
        """SELECT DATE(zaman) as gun, COUNT(*) as adet,
                  SUM(token_giris+token_cikis) as token
           FROM olaylar WHERE zaman >= ?
           GROUP BY gun ORDER BY gun""",
        (kesim,),
    ):
        trend.append({"gun": row["gun"], "adet": row["adet"], "token": row["token"]})

    # Bot bazli
    bot_bazli = {}
    for row in conn.execute(
        "SELECT bot_adi, COUNT(*) as adet FROM olaylar WHERE zaman>=? AND bot_adi!='' GROUP BY bot_adi",
        (kesim,),
    ):
        bot_bazli[row["bot_adi"]] = row["adet"]

    # Hata dagilimi
    hatalar = []
    for row in conn.execute(
        """SELECT kaynak, hata_mesaji, COUNT(*) as adet
           FROM olaylar WHERE zaman>=? AND basarili=0 AND hata_mesaji!=''
           GROUP BY hata_mesaji ORDER BY adet DESC LIMIT 10""",
        (kesim,),
    ):
        hatalar.append({
            "kaynak": row["kaynak"],
            "hata": row["hata_mesaji"][:100],
            "adet": row["adet"],
        })

    return {
        "donem_gun": gun,
        "toplam_olay": genel["toplam"] or 0,
        "basarili": genel["basarili"] or 0,
        "basarisiz": genel["basarisiz"] or 0,
        "basari_orani": round(
            (genel["basarili"] / genel["toplam"] * 100) if genel["toplam"] else 0, 1
        ),
        "toplam_token": genel["toplam_token"] or 0,
        "toplam_maliyet": round(genel["toplam_maliyet"] or 0, 6),
        "ortalama_sure_ms": round(genel["ortalama_sure"] or 0, 1),
        "tur_bazli": tur_bazli,
        "trend": trend,
        "bot_bazli": bot_bazli,
        "en_cok_hatalar": hatalar,
    }


def provider_raporu(gun: int = 7) -> list[dict]:
    """Provider bazli maliyet ve kullanim raporu."""
    _tablolari_olustur()
    conn = _baglan()
    kesim = (datetime.now(timezone.utc) - timedelta(days=gun)).isoformat()

    sonuc = []
    for row in conn.execute(
        """SELECT kaynak as provider,
                  COUNT(*) as cagri,
                  SUM(token_giris+token_cikis) as token,
                  SUM(maliyet) as maliyet,
                  AVG(sure_ms) as ortalama_sure
           FROM olaylar
           WHERE zaman>=? AND tur='llm_cagri' AND kaynak!=''
           GROUP BY kaynak ORDER BY cagri DESC""",
        (kesim,),
    ):
        sonuc.append({
            "provider": row["provider"],
            "cagri": row["cagri"],
            "token": row["token"] or 0,
            "maliyet": round(row["maliyet"] or 0, 6),
            "ortalama_sure_ms": round(row["ortalama_sure"] or 0, 1),
        })
    return sonuc


def canli_izle(son_n: int = 50) -> list[dict]:
    """Son N olay (canli izleme)."""
    _tablolari_olustur()
    conn = _baglan()
    rows = conn.execute(
        """SELECT id, zaman, tur, kaynak, sure_ms,
                  token_giris, token_cikis, maliyet,
                  basarili, hata_mesaji, bot_adi
           FROM olaylar ORDER BY id DESC LIMIT ?""",
        (son_n,),
    ).fetchall()
    return [dict(r) for r in rows]


def haftalik_ozet() -> str:
    """Insan okunabilir haftalik ozet metni."""
    o = ozet_son_n(7)
    satirlar = [
        "📊 **Haftalik Analitik Ozeti**",
        f"  Donem: son {o['donem_gun']} gun",
        f"  Toplam olay: {o['toplam_olay']}",
        f"  Basari: %{o['basari_orani']}",
        f"  Toplam token: {o['toplam_token']}",
        f"  Toplam maliyet: ${o['toplam_maliyet']}",
        f"  Ortalama sure: {o['ortalama_sure_ms']}ms",
        "",
    ]

    if o.get("trend"):
        satirlar.append("**Trend:**")
        for t in o["trend"][-5:]:
            satirlar.append(f"  {t['gun']}: {t['adet']} olay, {t['token']} token")

    if o.get("en_cok_hatalar"):
        satirlar.append("**En cok hata:**")
        for h in o["en_cok_hatalar"][:5]:
            satirlar.append(f"  ❌ {h['kaynak']}: {h['adet']}x - {h['hata']}")

    return "\n".join(satirlar)


# ── Temizlik ─────────────────────────────────────────────────────────────────

def eski_kayitlari_temizle(saklama_gunu: int = 90):
    """90 gunden eski kayitlari temizler."""
    _tablolari_olustur()
    conn = _baglan()
    kesim = (datetime.now(timezone.utc) - timedelta(days=saklama_gunu)).isoformat()
    silinen = conn.execute("DELETE FROM olaylar WHERE zaman < ?", (kesim,)).rowcount
    conn.commit()
    logger.info("Analitik: %s eski kayit temizlendi", silinen)
    conn.execute("VACUUM")
    return silinen


# ── Motor Tool'lari ─────────────────────────────────────────────────────────

def motor_analitik_kaydet(params: str = "") -> str:
    """ANALITIK_KAYDET(tur=\"llm_cagri\", kaynak=\"deepseek\", sure_ms=1500, ...)\n
    Bir analitik olayi kaydeder.\n
    Parametreler: tur (zorunlu), kaynak, sure_ms, token_giris, token_cikis,\n
                  maliyet, basarili, hata_mesaji, bot_adi
    """
    import ast
    try:
        # Parametreleri ayristir: tur="llm_cagri", sure_ms=1500, ...
        params_dict = {}
        for part in params.split(","):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"\'')
                # Sayisal donusum
                if v.replace(".", "", 1).replace("-", "", 1).isdigit():
                    v = float(v) if "." in v else int(v)
                params_dict[k] = v
        tur = params_dict.pop("tur", "bilinmiyor")
        basarili = params_dict.pop("basarili", True)
        if isinstance(basarili, str):
            basarili = basarili.lower() in ("true", "1", "yes")
    except Exception:
        tur = params.strip().split(",")[0].strip() if params else "bilinmiyor"
        params_dict = {}
        basarili = True

    _id = kaydet(tur=str(tur), basarili=bool(basarili), **params_dict)
    return f"✅ Analitik kaydedildi (ID: {_id}, tur: {tur})"


def motor_analitik_rapor(params: str = "") -> str:
    """ANALITIK_RAPOR(gun=7)\n
    Son N gunun analitik raporunu dondurur.
    """
    try:
        gun = int(params.split("=")[1].strip().rstrip(")")) if "=" in params else 7
    except (ValueError, IndexError):
        gun = 7
    return ozet_son_n(gun)["_raw"] if False else json.dumps(ozet_son_n(gun), indent=2, ensure_ascii=False)


def motor_analitik_panel(params: str = "") -> str:
    """ANALITIK_PANEL()\n
    HTML dashboard olusturur.
    """
    return _dashboard_html()


# ── HTML Dashboard ──────────────────────────────────────────────────────────

def _dashboard_html() -> str:
    """Kendi kendine yeten HTML dashboard sayfasi."""
    o = ozet_son_n(7)
    p = provider_raporu(7)
    trend = o.get("trend", [])

    trend_json = json.dumps(trend, ensure_ascii=False)
    hatalar_json = json.dumps(o.get("en_cok_hatalar", []), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="tr" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ReYMeN Analitik Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
h1,h2{{color:#58a6ff;margin:20px 0 10px}}
.kart{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.metrikler{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:15px 0}}
.metrik{{text-align:center;padding:15px;background:#0d1117;border-radius:8px}}
.metrik .deger{{font-size:2em;font-weight:700;color:#58a6ff}}
.metrik .etiket{{font-size:.85em;color:#8b949e;margin-top:5px}}
.hatalar{{list-style:none}}
.hatalar li{{padding:5px 10px;margin:3px 0;background:#2d1b1b;border-radius:4px;border-left:3px solid #f85149}}
.hatalar li span.adet{{float:right;background:#f85149;color:#fff;border-radius:10px;padding:0 8px;font-size:.8em}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d}}
th{{color:#8b949e;font-weight:600}}
.canvas-container{{max-height:300px;margin:20px 0}}
</style>
</head>
<body>
<h1>📊 ReYMeN Analitik</h1>
<p style="color:#8b949e;margin-bottom:20px">Son 7 gun • {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<div class="metrikler">
  <div class="metrik"><div class="deger">{o['toplam_olay']}</div><div class="etiket">Toplam Olay</div></div>
  <div class="metrik"><div class="deger">%{o['basari_orani']}</div><div class="etiket">Basari Orani</div></div>
  <div class="metrik"><div class="deger">{o['toplam_token']:,}</div><div class="etiket">Token</div></div>
  <div class="metrik"><div class="deger">${o['toplam_maliyet']}</div><div class="etiket">Maliyet</div></div>
  <div class="metrik"><div class="deger">{o['ortalama_sure_ms']}ms</div><div class="etiket">Ort. Sure</div></div>
</div>

<div class="kart">
<h2>📈 Trend</h2>
<div class="canvas-container"><canvas id="trendChart"></canvas></div>
</div>

<div class="kart">
<h2>🏢 Provider Bazli</h2>
<table><tr><th>Provider</th><th>Çağrı</th><th>Token</th><th>Maliyet</th><th>Ort. Süre</th></tr>
{''.join(f'<tr><td>{r["provider"]}</td><td>{r["cagri"]}</td><td>{r["token"]:,}</td><td>${r["maliyet"]}</td><td>{r["ortalama_sure_ms"]}ms</td></tr>' for r in p)}
</table>
</div>

<div class="kart">
<h2>❌ En Çok Hata</h2>
<ul class="hatalar">
{''.join(f'<li><strong>{h["kaynak"]}</strong>: {h["hata"]} <span class="adet">{h["adet"]}x</span></li>' for h in o.get('en_cok_hatalar',[]))}
</ul>
</div>

<script>
const trendData = {trend_json};
new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: trendData.map(t => t.gun.slice(5)),
    datasets: [
      {{label:'Olay',data:trendData.map(t=>t.adet),borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,0.1)',fill:true,tension:0.3}},
      {{label:'Token (bin)',data:trendData.map(t=>Math.round(t.token/1000)),borderColor:'#3fb950',backgroundColor:'rgba(63,185,80,0.1)',fill:true,tension:0.3,yAxisID:'y1'}}
    ]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#c9d1d9'}}}}}},
    scales:{{x:{{ticks:{{color:'#8b949e'}}}},y:{{ticks:{{color:'#8b949e'}}}},y1:{{position:'right',ticks:{{color:'#8b949e'}},grid:{{drawOnChartArea:false}}}}}}
  }}
}});
</script>
</body>
</html>"""


# ── Motor Kaydi ─────────────────────────────────────────────────────────────

def motor_kaydet(motor: Any) -> None:
    """Motor tarafindan cagrilir, ANALITIK tool'larini kaydeder."""
    from reymen.sistem.analitik import (
        motor_analitik_kaydet,
        motor_analitik_rapor,
        motor_analitik_panel,
    )
    motor._plugin_arac_kaydet(
        "ANALITIK_KAYDET",
        motor_analitik_kaydet,
        "Analitik olay kaydet: ANALITIK_KAYDET(tur='llm_cagri', kaynak='deepseek', sure_ms=1500)",
    )
    motor._plugin_arac_kaydet(
        "ANALITIK_RAPOR",
        motor_analitik_rapor,
        "Son N gun analitik raporu: ANALITIK_RAPOR(gun=7)",
    )
    motor._plugin_arac_kaydet(
        "ANALITIK_PANEL",
        motor_analitik_panel,
        "HTML analitik dashboard: ANALITIK_PANEL()",
    )
    logger.info("[Analitik] 3 tool motor'a kaydedildi")


# ── Baslangic ───────────────────────────────────────────────────────────────

_tablolari_olustur()
logger.info("Analitik motoru hazir -> %s", VERITABANI)
