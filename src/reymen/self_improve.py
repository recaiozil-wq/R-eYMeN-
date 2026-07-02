"""
🔄 Self-improvement — Aktif kendini geliştirme döngüsü.

Kalite metrikleri toplar, SQLite ile kalıcı depolar, trend analizi yapar,
otomatik hedef belirler ve iyileştirme önerileri üretir.

Özellikler:
- SQLite kalıcı depolama (oturumlar arası veri korunur)
- Zaman bazlı trend/ilerleme takibi
- Otomatik hedef belirleme (en zayıf metrik hangisi?)
- Kod kalite analizi (projeyi tarar, metrik çıkarır)
- Aktif iyileştirme döngüsü (düşük kaliteli adımları otomatik analiz eder)
- conversation_loop entegrasyonu (her tur sonrası otomatik kayıt)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "QualityMetric", "QualityReport",
    "evaluate", "suggest_fix",
    "SelfImprover", "ImprovementGoal",
    "record_step", "record_step_with_cost",
    "report", "reset_history",
    "auto_improve_cycle", "kod_kalite_analizi",
    "kod_kalite_gecmisi", "conversation_loop_hook",
]

# ── SQLite yolu ─────────────────────────────────────────────────────────
_DB_DIR = Path(__file__).parent / "merkez_db"
_DB_PATH = _DB_DIR / "self_improve.db"


def _db_connection() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    return conn


def _db_init() -> None:
    """Tablo yapısını oluştur (idempotent)."""
    with _db_connection() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,
                step_name   TEXT DEFAULT '',
                success     INTEGER NOT NULL DEFAULT 1,
                errors      INTEGER DEFAULT 0,
                retries     INTEGER DEFAULT 0,
                duration    REAL DEFAULT 0.0,
                tokens_used INTEGER DEFAULT 0,
                score       REAL DEFAULT 0.0,
                grade       TEXT DEFAULT 'F',
                source      TEXT DEFAULT 'manual',
                metadata    TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_metrics_source ON metrics(source);

            CREATE TABLE IF NOT EXISTS improvement_goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  REAL NOT NULL,
                metric_name TEXT NOT NULL,
                current_val REAL DEFAULT 0.0,
                target_val  REAL DEFAULT 0.0,
                status      TEXT DEFAULT 'active',
                strategy    TEXT DEFAULT '',
                notes       TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_goals_status ON improvement_goals(status);

            CREATE TABLE IF NOT EXISTS code_quality_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,
                total_files INTEGER DEFAULT 0,
                total_lines INTEGER DEFAULT 0,
                test_count  INTEGER DEFAULT 0,
                test_pass   REAL DEFAULT 0.0,
                except_pass INTEGER DEFAULT 0,
                todo_count  INTEGER DEFAULT 0,
                fixme_count INTEGER DEFAULT 0,
                pylint_score REAL DEFAULT 0.0,
                details     TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_time ON code_quality_snapshots(timestamp);
        """)


# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class QualityMetric:
    """Tek bir çözüm adımının kalite metrikleri."""
    success: bool
    errors: int = 0
    retries: int = 0
    duration: float = 0.0
    tokens_used: int = 0
    step_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityReport:
    """Kalite değerlendirme raporu."""
    score: float
    grade: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.score >= 0.6

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "grade": self.grade,
            "passed": self.passed,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class ImprovementGoal:
    """İyileştirme hedefi."""
    metric_name: str
    current_val: float = 0.0
    target_val: float = 0.0
    status: str = "active"
    strategy: str = ""
    notes: str = ""
    created_at: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Değerlendirme ──────────────────────────────────────────────────────

def _grade_for(score: float) -> str:
    if score >= 0.9:
        return "A"
    if score >= 0.8:
        return "B"
    if score >= 0.7:
        return "C"
    if score >= 0.6:
        return "D"
    return "F"


def evaluate(metric: QualityMetric) -> QualityReport:
    """Kalite metriklerini değerlendirip rapor döndürür."""
    score = 0.0
    issues: list[str] = []

    if metric.success:
        score += 0.5
    else:
        issues.append("adım başarısız")

    if metric.errors == 0:
        score += 0.2
    else:
        penalty = min(0.2, metric.errors * 0.05)
        score += 0.2 - penalty
        if metric.errors >= 3:
            issues.append(f"yüksek hata sayısı ({metric.errors})")

    if metric.retries == 0:
        score += 0.15
    else:
        penalty = min(0.15, metric.retries * 0.05)
        score += 0.15 - penalty
        if metric.retries >= 3:
            issues.append(f"çok fazla yeniden deneme ({metric.retries})")

    if metric.duration <= 0:
        score += 0.0
    elif metric.duration < 5.0:
        score += 0.15
    elif metric.duration < 30.0:
        score += 0.10
    else:
        issues.append(f"uzun süre ({metric.duration:.1f}s)")

    score = max(0.0, min(1.0, score))
    return QualityReport(
        score=score,
        grade=_grade_for(score),
        issues=issues,
        suggestions=suggest_fix(metric),
    )


def suggest_fix(metric: QualityMetric) -> list[str]:
    """Düşük kaliteli adımlar için iyileştirme önerileri üretir."""
    suggestions: list[str] = []
    if not metric.success:
        suggestions.append("Adım başarısız — hata loglarını inceleyip kök nedeni bul.")
    if metric.errors >= 3:
        suggestions.append("Çok hata var — input validasyonu ve hata yakalama (try/except) ekle.")
    if metric.retries >= 3:
        suggestions.append("Çok yeniden deneme — backoff stratejisi veya farklı yaklaşım dene.")
    if metric.duration > 30.0:
        suggestions.append("Yavaş adım — paralelleştirme, önbellekleme veya batch işlem düşün.")
    if metric.tokens_used > 10_000:
        suggestions.append("Yüksek token kullanımı — prompt'u kısalt veya özetle.")
    if not suggestions:
        suggestions.append("İyi performans — iyileştirme gerekmiyor.")
    return suggestions


# ── SelfImprover (SQLite destekli) ──────────────────────────────────────

class SelfImprover:
    """Adım geçmişini SQLite'da tutar, trend analizi yapar, hedef belirler."""

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold
        _db_init()

    # -- Kayıt ----------------------------------------------------------------

    def record(self, metric: QualityMetric) -> QualityReport:
        """Adımı değerlendirir ve SQLite'a kaydeder."""
        report = evaluate(metric)
        if not report.passed:
            report.suggestions = suggest_fix(metric)

        with _db_connection() as db:
            db.execute(
                """INSERT INTO metrics (timestamp, step_name, success, errors,
                   retries, duration, tokens_used, score, grade, source, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.time(),
                    metric.step_name,
                    int(metric.success),
                    metric.errors,
                    metric.retries,
                    metric.duration,
                    metric.tokens_used,
                    report.score,
                    report.grade,
                    metric.source,
                    json.dumps(metric.metadata, ensure_ascii=False),
                ),
            )
        return report

    # -- Sorgulama ------------------------------------------------------------

    def history(self, limit: int = 100, source: str | None = None) -> list[dict]:
        """Son N kaydı döndür."""
        with _db_connection() as db:
            if source:
                rows = db.execute(
                    "SELECT * FROM metrics WHERE source=? ORDER BY timestamp DESC LIMIT ?",
                    (source, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def trend(self, days: int = 7) -> dict[str, Any]:
        """Kalite trend özeti (son N gün)."""
        cutoff = time.time() - days * 86400
        with _db_connection() as db:
            rows = db.execute(
                "SELECT score, grade, success FROM metrics WHERE timestamp >= ?",
                (cutoff,),
            ).fetchall()

        if not rows:
            return {
                "donem_gun": days,
                "toplam_adim": 0,
                "ortalama_skor": 0.0,
                "gecme_orani": 0.0,
                "dusuk_kalite": 0,
                "not_dagilimi": {},
            }

        scores = [r["score"] for r in rows]
        passed = sum(1 for r in rows if r["score"] >= self.threshold)
        grades: dict[str, int] = {}
        for r in rows:
            g = r["grade"]
            grades[g] = grades.get(g, 0) + 1

        return {
            "donem_gun": days,
            "toplam_adim": len(rows),
            "ortalama_skor": round(sum(scores) / len(scores), 3),
            "gecme_orani": round(passed / len(rows), 3),
            "dusuk_kalite": len(rows) - passed,
            "not_dagilimi": dict(sorted(grades.items())),
        }

    def haftalik_ilerleme(self) -> list[dict]:
        """Haftalık ortalama skorları döndür (son 8 hafta)."""
        sonuc = []
        for i in range(8):
            bas = time.time() - (i + 1) * 7 * 86400
            bit = time.time() - i * 7 * 86400
            with _db_connection() as db:
                rows = db.execute(
                    "SELECT score FROM metrics WHERE timestamp >= ? AND timestamp < ?",
                    (bas, bit),
                ).fetchall()
            ortalama = round(sum(r["score"] for r in rows) / len(rows), 3) if rows else 0.0
            hafta_adi = datetime.fromtimestamp(bas).strftime("%d.%m")
            sonuc.append({"hafta": hafta_adi, "ortalama": ortalama, "adim": len(rows)})
        return list(reversed(sonuc))

    # -- Hedef belirleme -----------------------------------------------------

    def hedef_belirle(self) -> ImprovementGoal | None:
        """En zayıf metriği tespit edip hedef oluşturur."""
        with _db_connection() as db:
            rows = db.execute(
                "SELECT * FROM metrics WHERE timestamp > ? ORDER BY score ASC LIMIT 10",
                (time.time() - 7 * 86400,),
            ).fetchall()

        if not rows:
            return None

        # En sık görülen sorun
        error_adimlari = [r for r in rows if r["errors"] > 2]
        retry_adimlari = [r for r in rows if r["retries"] > 2]
        sure_adimlari = [r for r in rows if r["duration"] > 30]

        hedef: ImprovementGoal | None = None
        if len(error_adimlari) >= 3:
            hedef = ImprovementGoal(
                metric_name="hata_sayisi",
                current_val=sum(r["errors"] for r in error_adimlari) / len(error_adimlari),
                target_val=1.0,
                strategy="try/except ekle, input dogrulamasi yap",
                notes=f"Son 7 günde {len(error_adimlari)} adım yüksek hatalı",
                created_at=time.time(),
            )
        elif len(retry_adimlari) >= 3:
            hedef = ImprovementGoal(
                metric_name="retry_sayisi",
                current_val=sum(r["retries"] for r in retry_adimlari) / len(retry_adimlari),
                target_val=1.0,
                strategy="backoff stratejisi ekle, alternatif cozum dene",
                notes=f"Son 7 günde {len(retry_adimlari)} adım yüksek retry'li",
                created_at=time.time(),
            )
        elif len(sure_adimlari) >= 2:
            hedef = ImprovementGoal(
                metric_name="sure",
                current_val=sum(r["duration"] for r in sure_adimlari) / len(sure_adimlari),
                target_val=15.0,
                strategy="paralellestir, cache ekle",
                notes=f"Son 7 günde {len(sure_adimlari)} adım yavaş",
                created_at=time.time(),
            )

        if hedef:
            with _db_connection() as db:
                db.execute(
                    """INSERT INTO improvement_goals
                       (created_at, metric_name, current_val, target_val, status, strategy, notes)
                       VALUES (?, ?, ?, ?, 'active', ?, ?)""",
                    (hedef.created_at, hedef.metric_name, hedef.current_val,
                     hedef.target_val, hedef.strategy, hedef.notes),
                )
        return hedef

    def aktif_hedefler(self) -> list[dict]:
        """Aktif iyileştirme hedeflerini döndür."""
        with _db_connection() as db:
            rows = db.execute(
                "SELECT * FROM improvement_goals WHERE status='active' ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def hedef_tamamla(self, goal_id: int) -> bool:
        """Hedefi tamamlandı olarak işaretle."""
        with _db_connection() as db:
            cur = db.execute(
                "UPDATE improvement_goals SET status='completed' WHERE id=?",
                (goal_id,),
            )
            return cur.rowcount > 0

    # -- İyileştirme döngüsü -------------------------------------------------

    def auto_improve(self) -> list[str]:
        """Düşük kaliteli adımlar için toplu öneri üretir + hedef belirler."""
        all_suggestions: list[str] = []

        with _db_connection() as db:
            rows = db.execute(
                "SELECT * FROM metrics WHERE score < ? ORDER BY timestamp DESC LIMIT 20",
                (self.threshold,),
            ).fetchall()

        for r in rows:
            metric = QualityMetric(
                success=bool(r["success"]),
                errors=r["errors"],
                retries=r["retries"],
                duration=r["duration"],
                tokens_used=r["tokens_used"],
                step_name=r["step_name"],
            )
            all_suggestions.extend(suggest_fix(metric))

        # Hedef belirle
        hedef = self.hedef_belirle()
        if hedef:
            all_suggestions.append(
                f"[HEDEF] {hedef.metric_name}: {hedef.current_val:.1f} → {hedef.target_val:.1f} "
                f"({hedef.strategy})"
            )

        seen: set[str] = set()
        unique: list[str] = []
        for s in all_suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique

    def auto_fix_script_uret(self) -> str | None:
        """En düşük kaliteli alan için otomatik fix script'i üret."""
        hedefler = self.aktif_hedefler()
        if not hedefler:
            return None

        h = hedefler[0]
        strategy = h.get("strategy", "")
        metric = h.get("metric_name", "")

        script = f"""# ReYMeN Self-Improve: Otomatik Fix
# Hedef: {metric} ({h.get('current_val', 0):.1f} → {h.get('target_val', 0):.1f})
# Strateji: {strategy}

import logging
logger = logging.getLogger(__name__)


def fix_uygula():
    \"\"\"{strategy}\"\"\"
    logger.info("[SELF_IMPROVE] Fix uygulaniyor: {metric}")
    # TODO: {strategy}
    return True


if __name__ == "__main__":
    fix_uygula()
"""
        return script

    def reset(self) -> None:
        """Tüm kayıtları temizle."""
        with _db_connection() as db:
            db.execute("DELETE FROM metrics")
            db.execute("DELETE FROM improvement_goals")
            db.execute("DELETE FROM code_quality_snapshots")


# ── Kod Kalite Analizi ──────────────────────────────────────────────────

def kod_kalite_analizi(proje_yolu: str | None = None) -> dict[str, Any]:
    """Proje kod tabanını tarar, kalite metriklerini çıkarır.

    Args:
        proje_yolu: Proje kök dizini (None = otomatik algıla).

    Returns:
        Kalite metrikleri sözlüğü.
    """
    if proje_yolu is None:
        proje_yolu = str(Path(__file__).parent.parent)

    kok = Path(proje_yolu)
    py_dosyalari = list(kok.rglob("*.py"))

    # Gizli, __pycache__, venv klasörlerini atla
    EXCLUDE = {".git", "__pycache__", ".venv", "venv", ".env",
               "node_modules", ".ReYMeN", ".cron_logs", ".alt_ajan_gozlem",
               "bot_venv", "reymen_venv", "ReYMeN_cli",
               "hermes-memory-backup", "ReYMeN-memory-backup",
               "_claude_multi_output", ".yedek", "Lib", "site-packages"}
    py_dosyalari = [
        p for p in py_dosyalari
        if not any(part.startswith(".") or part in EXCLUDE
                   for part in p.relative_to(kok).parts)
    ]

    toplam_satir = 0
    except_pass_sayisi = 0
    todo_sayisi = 0
    fixme_sayisi = 0
    sinif_sayisi = 0
    fonk_sayisi = 0
    import_hatalari = 0

    for dosya in py_dosyalari:
        try:
            icerik = dosya.read_text(encoding="utf-8", errors="replace")
            satirlar = icerik.splitlines()
            toplam_satir += len(satirlar)

            # except:pass
            except_pass_sayisi += len(re.findall(r"except\s*.*:\s*\n\s*pass", icerik, re.MULTILINE))

            # TODO / FIXME
            todo_sayisi += len(re.findall(r"#\s*TODO", icerik, re.IGNORECASE))
            fixme_sayisi += len(re.findall(r"#\s*FIXME", icerik, re.IGNORECASE))

            # class / def
            sinif_sayisi += len(re.findall(r"^\s*class\s+\w+", icerik, re.MULTILINE))
            fonk_sayisi += len(re.findall(r"^\s*(?:async\s+)?def\s+\w+", icerik, re.MULTILINE))

        except Exception:
            import_hatalari += 1

    # Test dosyaları
    test_dosyalari = [p for p in py_dosyalari if "test" in p.stem.lower()]
    test_satir = sum(
        len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        for p in test_dosyalari
    )

    sonuc = {
        "tarih": datetime.now().isoformat(),
        "timestamp": time.time(),
        "toplam_dosya": len(py_dosyalari),
        "toplam_satir": toplam_satir,
        "test_dosyasi": len(test_dosyalari),
        "test_satir": test_satir,
        "test_orani": round(test_satir / toplam_satir, 3) if toplam_satir else 0,
        "sinif_sayisi": sinif_sayisi,
        "fonk_sayisi": fonk_sayisi,
        "except_pass": except_pass_sayisi,
        "todo": todo_sayisi,
        "fixme": fixme_sayisi,
        "ortalama_dosya_boyut": round(toplam_satir / len(py_dosyalari), 1) if py_dosyalari else 0,
        "import_hatali": import_hatalari,
    }

    # SQLite'a kaydet
    try:
        _db_init()
        with _db_connection() as db:
            db.execute(
                """INSERT INTO code_quality_snapshots
                   (timestamp, total_files, total_lines, test_count, test_pass,
                    except_pass, todo_count, fixme_count, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.time(),
                    sonuc["toplam_dosya"],
                    sonuc["toplam_satir"],
                    sonuc["test_dosyasi"],
                    sonuc["test_orani"],
                    sonuc["except_pass"],
                    sonuc["todo"],
                    sonuc["fixme"],
                    json.dumps(sonuc, ensure_ascii=False),
                ),
            )
    except Exception as e:
        logger.warning("[SELF_IMPROVE] Kod kalite kayit hatasi: %s", e)

    return sonuc


def kod_kalite_gecmisi(limit: int = 10) -> list[dict]:
    """Geçmiş kod kalite snapshot'larını döndür."""
    _db_init()
    with _db_connection() as db:
        rows = db.execute(
            "SELECT * FROM code_quality_snapshots ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Aktif iyileştirme döngüsü ─────────────────────────────────────────

def auto_improve_cycle(proje_yolu: str | None = None) -> dict[str, Any]:
    """Tam iyileştirme döngüsü: kod tara → metrik çıkar → hedef belirle → öneri üret.

    Returns:
        Döngü sonucu sözlüğü.
    """
    improver = _singleton

    # 1. Kod kalite analizi
    kalite = kod_kalite_analizi(proje_yolu)

    # 2. Son 7 gün trendi
    trend = improver.trend(days=7)

    # 3. Hedef belirle
    hedef = improver.hedef_belirle()

    # 4. Öneriler
    oneriler = improver.auto_improve()

    # 5. Otomatik metrik kaydı (kod kalitesini metrik olarak kaydet)
    dosya_metric = QualityMetric(
        success=kalite["import_hatali"] == 0,
        errors=kalite["except_pass"] // 10,
        retries=kalite["fixme"],
        duration=0,
        tokens_used=kalite["toplam_satir"],
        step_name="kod_kalite_analizi",
        source="auto_improve_cycle",
    )
    improver.record(dosya_metric)

    return {
        "kod_kalitesi": kalite,
        "trend": trend,
        "hedef": hedef.as_dict() if hedef else None,
        "oneriler": oneriler,
        "aktif_hedefler": improver.aktif_hedefler(),
        "haftalik_ilerleme": improver.haftalik_ilerleme(),
    }


# ── conversation_loop entegrasyonu ─────────────────────────────────────

def conversation_loop_hook(**kwargs) -> None:
    """conversation_loop'dan çağrılacak hook.

    Her tur sonunda otomatik kalite metriklerini kaydeder.
    """
    improver = _singleton
    tur = kwargs.get("tur", 0)
    basarili = kwargs.get("basarili", False)
    task_id = kwargs.get("task_id", "")
    kaynak = kwargs.get("kaynak", "")

    metric = QualityMetric(
        success=basarili,
        step_name=f"tur_{tur}_{task_id[:8] if task_id else 'anon'}",
        source=f"conversation_loop_{kaynak}" if kaynak else "conversation_loop",
    )
    improver.record(metric)


# ── Singleton ───────────────────────────────────────────────────────────

_singleton = SelfImprover()


def record_step(metric: QualityMetric) -> QualityReport:
    return _singleton.record(metric)


def report() -> dict[str, Any]:
    trend = _singleton.trend(days=7)
    trend["aktif_hedefler"] = _singleton.aktif_hedefler()
    trend["haftalik_ilerleme"] = _singleton.haftalik_ilerleme()
    return trend


def reset_history() -> None:
    _singleton.reset()


def record_step_with_cost(
    *,
    success: bool,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    errors: int = 0,
    retries: int = 0,
    duration: float = 0.0,
    step_name: str = "",
) -> QualityReport:
    from . import cost_tracker
    cost_tracker.record_usage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        metadata={"step_name": step_name} if step_name else None,
    )
    metric = QualityMetric(
        success=success,
        errors=errors,
        retries=retries,
        duration=duration,
        tokens_used=prompt_tokens + completion_tokens,
        step_name=step_name,
    )
    return _singleton.record(metric)


# ── Motor Kaydı ────────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a self-improvement araçlarını kaydet."""
    motor._plugin_arac_kaydet("SELF_IMPROVE_REPORT", _tool_report,
                              "Self-improvement trend raporu (SQLite kalici).")
    motor._plugin_arac_kaydet("SELF_IMPROVE_SUGGEST", _tool_suggest,
                              "Dusuk kaliteli adimlar icin iyilestirme onerileri + hedef.")
    motor._plugin_arac_kaydet("SELF_IMPROVE_RECORD", _tool_record,
                              "Kalite metriklerini kaydet: success, step_name, errors, retries, duration, tokens_used")
    motor._plugin_arac_kaydet("SELF_IMPROVE_RESET", _tool_reset,
                              "Self-improvement gecmisini temizle.")
    motor._plugin_arac_kaydet("SELF_IMPROVE_CYCLE", _tool_cycle,
                              "Tam iyilestirme dongusu: kod tara + metrik + hedef + oneri.")
    motor._plugin_arac_kaydet("SELF_IMPROVE_GOALS", _tool_goals,
                              "Aktif iyilestirme hedeflerini listele.")
    motor._plugin_arac_kaydet("KOD_KALITE_ANALIZI", _tool_kalite,
                              "Proje kod tabanini tara, kalite metriklerini cikar.")
    logger.info("[SELF_IMPROVE] Motor'a 7 arac kaydedildi")


def _tool_report(**kw) -> str:
    trend = _singleton.trend(days=7)
    trend["aktif_hedefler"] = _singleton.aktif_hedefler()
    trend["haftalik_ilerleme"] = _singleton.haftalik_ilerleme()
    return json.dumps(trend, indent=2, ensure_ascii=False)


def _tool_suggest(**kw) -> str:
    oneriler = _singleton.auto_improve()
    if not oneriler:
        return "[SELF_IMPROVE] Iyilestirme gerektiren adim yok."
    return "[SELF_IMPROVE] Oneriler:\n" + "\n".join(f"  - {s}" for s in oneriler)


def _tool_record(success: bool = True, step_name: str = "",
                 errors: int = 0, retries: int = 0,
                 duration: float = 0.0, tokens_used: int = 0) -> str:
    metric = QualityMetric(
        success=success, step_name=step_name,
        errors=errors, retries=retries,
        duration=duration, tokens_used=tokens_used,
    )
    rapor = _singleton.record(metric)
    return (f"[SELF_IMPROVE] Kaydedildi: adim={step_name} "
            f"skor={rapor.score:.2f} not={rapor.grade} "
            f"{'✅' if rapor.passed else '⚠️'}")


def _tool_reset(**kw) -> str:
    _singleton.reset()
    return "[SELF_IMPROVE] Gecmis temizlendi."


def _tool_cycle(**kw) -> str:
    sonuc = auto_improve_cycle()
    return json.dumps(sonuc, indent=2, ensure_ascii=False)


def _tool_goals(**kw) -> str:
    hedefler = _singleton.aktif_hedefler()
    if not hedefler:
        return "[SELF_IMPROVE] Aktif hedef yok."
    return json.dumps(hedefler, indent=2, ensure_ascii=False)


def _tool_kalite(**kw) -> str:
    sonuc = kod_kalite_analizi()
    return json.dumps(sonuc, indent=2, ensure_ascii=False)
