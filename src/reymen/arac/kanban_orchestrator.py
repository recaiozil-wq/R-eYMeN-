# -*- coding: utf-8 -*-
"""
kanban_orchestrator.py — ReYMeN Gelismis Kanban Gorev Tahtasi.

Ozellikler:
  - SQLite + FTS5 ile kalici depolama
  - Kolonlar: todo → ready → running → done | blocked | archived
  - Oncelik (1-yuksek, 2-orta, 3-dusuk), atanan kullanici, etiketler
  - Ajan tarafindan KANBAN_EKLE / KANBAN_GUNCELLE / KANBAN_LISTE araclari
  - CLI: python kanban_orchestrator.py [ekle|liste|guncelle|sil|ozet]
  - Dashboard entegrasyonu: JSON export

Kullanim (CLI):
    python kanban_orchestrator.py ekle "Rapor yaz" --oncelik 1
    python kanban_orchestrator.py liste --durum todo
    python kanban_orchestrator.py guncelle 3 --durum done
    python kanban_orchestrator.py ozet
"""
import argparse
import json
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.resolve()
DB_YOLU = ROOT / ".ReYMeN" / "kanban.db"

DURUMLAR = ("todo", "ready", "running", "done", "blocked", "archived")
DURUM_SIMGELERI = {
    "todo":     "◻",
    "ready":    "▶",
    "running":  "●",
    "done":     "✓",
    "blocked":  "⊘",
    "archived": "—",
}
ONCELIK_SIMGELERI = {1: "!!!", 2: "!! ", 3: "!  "}


# ── Veri Modeli ──────────────────────────────────────────────────────────────

@dataclass
class Gorev:
    id: int = 0
    baslik: str = ""
    govde: str = ""
    durum: str = "todo"
    oncelik: int = 2
    atanan: str = ""
    etiketler: str = ""
    olusturma: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    guncelleme: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    baslangic: str = ""
    bitis: str = ""
    hedef_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def satir(self) -> str:
        simge = DURUM_SIMGELERI.get(self.durum, "?")
        onc = ONCELIK_SIMGELERI.get(self.oncelik, "   ")
        atanan = f" @{self.atanan}" if self.atanan else ""
        etiket = f" [{self.etiketler}]" if self.etiketler else ""
        return f"{simge} {self.id:3d}  {onc}  {self.durum:8s}{atanan}{etiket}  {self.baslik}"


# ── Veritabani ───────────────────────────────────────────────────────────────

class KanbanDB:
    _kilit = threading.Lock()

    def __init__(self, db_yolu: Path = DB_YOLU):
        self.db_yolu = db_yolu
        self.db_yolu.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _baglanti(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_yolu), timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _init_db(self):
        with self._kilit:
            con = self._baglanti()
            try:
                con.executescript("""
                    CREATE TABLE IF NOT EXISTS gorevler (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        baslik      TEXT    NOT NULL,
                        govde       TEXT    DEFAULT '',
                        durum       TEXT    DEFAULT 'todo',
                        oncelik     INTEGER DEFAULT 2,
                        atanan      TEXT    DEFAULT '',
                        etiketler   TEXT    DEFAULT '',
                        olusturma   TEXT,
                        guncelleme  TEXT,
                        baslangic   TEXT    DEFAULT '',
                        bitis       TEXT    DEFAULT '',
                        hedef_id    TEXT    DEFAULT ''
                    );
                    CREATE INDEX IF NOT EXISTS idx_durum ON gorevler(durum);
                    CREATE INDEX IF NOT EXISTS idx_oncelik ON gorevler(oncelik);

                    CREATE VIRTUAL TABLE IF NOT EXISTS gorevler_fts
                        USING fts5(baslik, govde, content='gorevler', content_rowid='id');

                    CREATE TRIGGER IF NOT EXISTS gorevler_fts_ins
                        AFTER INSERT ON gorevler BEGIN
                            INSERT INTO gorevler_fts(rowid, baslik, govde)
                            VALUES (new.id, new.baslik, new.govde);
                        END;

                    CREATE TRIGGER IF NOT EXISTS gorevler_fts_del
                        AFTER DELETE ON gorevler BEGIN
                            INSERT INTO gorevler_fts(gorevler_fts, rowid, baslik, govde)
                            VALUES ('delete', old.id, old.baslik, old.govde);
                        END;
                """)
                con.commit()
            finally:
                con.close()

    def _satir_cevir(self, row: sqlite3.Row) -> Gorev:
        return Gorev(
            id=row["id"],
            baslik=row["baslik"],
            govde=row["govde"] or "",
            durum=row["durum"] or "todo",
            oncelik=row["oncelik"] or 2,
            atanan=row["atanan"] or "",
            etiketler=row["etiketler"] or "",
            olusturma=row["olusturma"] or "",
            guncelleme=row["guncelleme"] or "",
            baslangic=row["baslangic"] or "",
            bitis=row["bitis"] or "",
            hedef_id=row["hedef_id"] or "",
        )

    def ekle(self, baslik: str, govde: str = "", oncelik: int = 2,
             atanan: str = "", etiketler: str = "", hedef_id: str = "") -> Gorev:
        simdi = datetime.now(timezone.utc).isoformat()
        with self._kilit:
            con = self._baglanti()
            try:
                cur = con.execute(
                    "INSERT INTO gorevler (baslik, govde, durum, oncelik, atanan, "
                    "etiketler, olusturma, guncelleme, hedef_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (baslik, govde, "todo", oncelik, atanan, etiketler, simdi, simdi, hedef_id),
                )
                con.commit()
                row = con.execute("SELECT * FROM gorevler WHERE id=?", (cur.lastrowid,)).fetchone()
                return self._satir_cevir(row)
            finally:
                con.close()

    def guncelle(self, gorev_id: int, **alanlar) -> Optional[Gorev]:
        IZINLI_KOLONLAR = {"baslik", "govde", "durum", "oncelik", "atanan", "etiketler",
                           "baslangic", "bitis", "hedef_id"}
        alanlar = {k: v for k, v in alanlar.items() if k in IZINLI_KOLONLAR and v is not None}
        if not alanlar:
            return self.bul(gorev_id)

        alanlar["guncelleme"] = datetime.now(timezone.utc).isoformat()

        # Durum degisikliklerinde zaman damgasi
        if alanlar.get("durum") == "running" and not alanlar.get("baslangic"):
            alanlar["baslangic"] = alanlar["guncelleme"]
        if alanlar.get("durum") in ("done", "archived") and not alanlar.get("bitis"):
            alanlar["bitis"] = alanlar["guncelleme"]

        set_clause = ", ".join(f"{k}=?" for k in alanlar)
        degerler = list(alanlar.values()) + [gorev_id]

        with self._kilit:
            con = self._baglanti()
            try:
                con.execute(f"UPDATE gorevler SET {set_clause} WHERE id=?", degerler)  # nosec B608 — IZINLI_KOLONLAR whitelist'i ile filtreli (satir 165-167)
                con.commit()
                row = con.execute("SELECT * FROM gorevler WHERE id=?", (gorev_id,)).fetchone()
                return self._satir_cevir(row) if row else None
            finally:
                con.close()

    def sil(self, gorev_id: int) -> bool:
        with self._kilit:
            con = self._baglanti()
            try:
                cur = con.execute("DELETE FROM gorevler WHERE id=?", (gorev_id,))
                con.commit()
                return cur.rowcount > 0
            finally:
                con.close()

    def bul(self, gorev_id: int) -> Optional[Gorev]:
        con = self._baglanti()
        try:
            row = con.execute("SELECT * FROM gorevler WHERE id=?", (gorev_id,)).fetchone()
            return self._satir_cevir(row) if row else None
        finally:
            con.close()

    def listele(self, durum: str = "", oncelik: int = 0,
                atanan: str = "", limit: int = 100) -> list[Gorev]:
        filtreler = []
        degerler: list = []
        if durum:
            filtreler.append("durum=?")
            degerler.append(durum)
        if oncelik:
            filtreler.append("oncelik=?")
            degerler.append(oncelik)
        if atanan:
            filtreler.append("atanan=?")
            degerler.append(atanan)

        where = f"WHERE {' AND '.join(filtreler)}" if filtreler else ""
        con = self._baglanti()
        try:
            rows = con.execute(
                f"SELECT * FROM gorevler {where} ORDER BY oncelik ASC, id ASC LIMIT ?",  # nosec B608 — filtreler listesi fonksiyon parametrelerinden, kullanici inputu dogrudan gecmez
                degerler + [limit],
            ).fetchall()
            return [self._satir_cevir(r) for r in rows]
        finally:
            con.close()

    def ara(self, sorgu: str, limit: int = 20) -> list[Gorev]:
        con = self._baglanti()
        try:
            rows = con.execute(
                "SELECT g.* FROM gorevler g "
                "JOIN gorevler_fts f ON g.id = f.rowid "
                "WHERE gorevler_fts MATCH ? ORDER BY rank LIMIT ?",
                (sorgu, limit),
            ).fetchall()
            return [self._satir_cevir(r) for r in rows]
        except Exception:
            return []
        finally:
            con.close()

    def ozet(self) -> dict:
        con = self._baglanti()
        try:
            rows = con.execute(
                "SELECT durum, COUNT(*) as sayi FROM gorevler GROUP BY durum"
            ).fetchall()
            toplam = con.execute("SELECT COUNT(*) FROM gorevler").fetchone()[0]
            return {
                "toplam": toplam,
                "kolonlar": {r["durum"]: r["sayi"] for r in rows},
            }
        finally:
            con.close()

    def tamamla(self, gorev_id: int) -> Optional[Gorev]:
        return self.guncelle(gorev_id, durum="done")

    def engelle(self, gorev_id: int, neden: str = "") -> Optional[Gorev]:
        govde = self.bul(gorev_id)
        govde_metni = (govde.govde if govde else "") + (f"\n[ENGEL]: {neden}" if neden else "")
        return self.guncelle(gorev_id, durum="blocked", govde=govde_metni)


# ── Orkestrator ──────────────────────────────────────────────────────────────

class AdvancedKanbanOrchestrator:
    """ReYMeN ana arayuzu — ajan araclariyla dogrudan kullanilir."""

    def __init__(self, db_yolu: Path = DB_YOLU):
        self.db = KanbanDB(db_yolu)

    # Ajan araclari
    def ekle(self, baslik: str, govde: str = "", oncelik: int = 2,
             atanan: str = "", etiketler: str = "", hedef_id: str = "") -> dict:
        g = self.db.ekle(baslik, govde, oncelik, atanan, etiketler, hedef_id)
        return g.to_dict()

    def guncelle(self, gorev_id: int, **alanlar) -> dict:
        g = self.db.guncelle(gorev_id, **alanlar)
        return g.to_dict() if g else {}

    def liste(self, durum: str = "", oncelik: int = 0, limit: int = 50) -> list[dict]:
        return [g.to_dict() for g in self.db.listele(durum=durum, oncelik=oncelik, limit=limit)]

    def ara(self, sorgu: str) -> list[dict]:
        return [g.to_dict() for g in self.db.ara(sorgu)]

    def tamamla(self, gorev_id: int) -> dict:
        g = self.db.tamamla(gorev_id)
        return g.to_dict() if g else {}

    def engelle(self, gorev_id: int, neden: str = "") -> dict:
        g = self.db.engelle(gorev_id, neden)
        return g.to_dict() if g else {}

    def sil(self, gorev_id: int) -> bool:
        return self.db.sil(gorev_id)

    def ozet(self) -> dict:
        return self.db.ozet()

    def gorsel_tahta(self) -> str:
        """Terminal'de ASCII kanban tahtasi goster."""
        satirlar = ["═" * 70, "  ReYMeN KANBAN TAHTASI", "═" * 70]
        for durum in ("todo", "ready", "running", "done", "blocked"):
            gorevler = self.db.listele(durum=durum, limit=20)
            simge = DURUM_SIMGELERI.get(durum, "?")
            satirlar.append(f"\n{simge} {durum.upper()} ({len(gorevler)})")
            satirlar.append("─" * 60)
            if gorevler:
                for g in gorevler:
                    satirlar.append(f"  {g.satir()}")
            else:
                satirlar.append("  (bos)")
        satirlar.append("\n" + "═" * 70)
        return "\n".join(satirlar)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(description="ReYMeN Kanban CLI")
    sub = parser.add_subparsers(dest="komut")

    # ekle
    p_ekle = sub.add_parser("ekle", help="Yeni gorev ekle")
    p_ekle.add_argument("baslik")
    p_ekle.add_argument("--govde", default="")
    p_ekle.add_argument("--oncelik", type=int, choices=[1, 2, 3], default=2)
    p_ekle.add_argument("--atanan", default="")
    p_ekle.add_argument("--etiket", default="")

    # liste
    p_lst = sub.add_parser("liste", help="Gorevleri listele")
    p_lst.add_argument("--durum", choices=DURUMLAR, default="")
    p_lst.add_argument("--oncelik", type=int, choices=[1, 2, 3], default=0)
    p_lst.add_argument("--json", action="store_true")

    # guncelle
    p_gnc = sub.add_parser("guncelle", help="Gorevi guncelle")
    p_gnc.add_argument("id", type=int)
    p_gnc.add_argument("--durum", choices=DURUMLAR)
    p_gnc.add_argument("--baslik")
    p_gnc.add_argument("--oncelik", type=int, choices=[1, 2, 3])
    p_gnc.add_argument("--atanan")

    # sil
    p_sil = sub.add_parser("sil", help="Gorevi sil")
    p_sil.add_argument("id", type=int)

    # ara
    p_ara = sub.add_parser("ara", help="Full-text arama")
    p_ara.add_argument("sorgu")

    # ozet
    sub.add_parser("ozet", help="Tahta ozeti")

    # tahta
    sub.add_parser("tahta", help="Gorsel kanban tahtasi")

    args = parser.parse_args()
    k = AdvancedKanbanOrchestrator()

    if args.komut == "ekle":
        g = k.ekle(args.baslik, args.govde, args.oncelik, args.atanan, args.etiket)
        print(f"[Kanban] Gorev eklendi: #{g['id']} — {g['baslik']}")

    elif args.komut == "liste":
        gorevler = k.liste(durum=args.durum, oncelik=args.oncelik)
        if getattr(args, "json", False):
            print(json.dumps(gorevler, ensure_ascii=False, indent=2))
        else:
            if not gorevler:
                print("(bos)")
            for g in gorevler:
                gorv = Gorev(**g)
                print(gorv.satir())

    elif args.komut == "guncelle":
        alanlar = {k: v for k, v in vars(args).items()
                   if k not in ("komut", "id") and v is not None}
        g = k.guncelle(args.id, **alanlar)
        if g:
            print(f"[Kanban] Guncellendi: #{g['id']} → {g['durum']}")
        else:
            print(f"[Kanban] Gorev bulunamadi: #{args.id}")

    elif args.komut == "sil":
        ok = k.sil(args.id)
        print(f"[Kanban] {'Silindi' if ok else 'Bulunamadi'}: #{args.id}")

    elif args.komut == "ara":
        sonuclar = k.ara(args.sorgu)
        for g in sonuclar:
            print(Gorev(**g).satir())

    elif args.komut == "ozet":
        ozet = k.ozet()
        print(f"Toplam: {ozet['toplam']}")
        for durum, sayi in ozet.get("kolonlar", {}).items():
            simge = DURUM_SIMGELERI.get(durum, "?")
            print(f"  {simge} {durum:10s}: {sayi}")

    elif args.komut == "tahta":
        print(k.gorsel_tahta().encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))

    else:
        parser.print_help()


def motor_kaydet(motor):
    """Kanban araçlarını motora kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    _kb = KanbanDB()
    motor._plugin_arac_kaydet(
        "KANBAN_EKLE",
        lambda baslik="", govde="", oncelik="2": str(
            _kb.ekle(baslik, govde, int(oncelik) if str(oncelik).isdigit() else 2).satir()
        ),
        "Kanban tahtasına görev ekle (baslik, govde, oncelik:1-3)",
    )
    motor._plugin_arac_kaydet(
        "KANBAN_LISTE",
        lambda durum="": (
            "\n".join(g.satir() for g in _kb.listele(durum=durum)) or "[Kanban]: Görev yok"
        ),
        "Kanban görevlerini listele (durum: todo/running/done/boş=hepsi)",
    )
    motor._plugin_arac_kaydet(
        "KANBAN_GUNCELLE",
        lambda id="0", durum="done": (
            str(_kb.guncelle(int(id), durum=durum).satir()) if str(id).isdigit() else "[Kanban]: Geçersiz id"
        ),
        "Kanban görevi güncelle (id, durum: todo/ready/running/done/blocked)",
    )
    motor._plugin_arac_kaydet(
        "KANBAN_OZET",
        lambda: str(_kb.ozet()),
        "Kanban tahta özetini göster (kolon bazında görev sayıları)",
    )


if __name__ == "__main__":
    _cli()
