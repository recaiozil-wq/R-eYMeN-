# -*- coding: utf-8 -*-
"""
self_improvement.py — ReYMeN Otonom Oz-Gelistirme Motoru.

Ne yapar:
  - Gecmis basarisiz gorevleri analiz eder
  - Hatali araclari tespit eder
  - Yeni beceri stratejileri olusturur
  - Sistem talimatina iyilestirme onerileri uretir
  - Yeni arac kombinasyonlari dener

Kullanim:
    python self_improvement.py              -- Analiz yap ve rapor goster
    python self_improvement.py --uygula    -- Onerileri uygula (SOUL.md guncelle)
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

ANALIZ_RAPOR = ROOT / ".ReYMeN" / "self_improvement.json"
SOUL_YOLU = ROOT / ".ReYMeN" / "SOUL.md"


class OzGelistirmeMotoru:
    def __init__(self, provider=None):
        self.provider = provider

    def hata_analizi_yap(self) -> dict:
        """SQLite oturum gunlugundan hatalari analiz et."""
        try:
            import sqlite3
            db = ROOT.parent / "merkez_db" / "session_cereyan.db"
            if not db.exists():
                return {"hata_sayisi": 0, "en_sik_hatalar": [], "basarisiz_araclar": []}
            con = sqlite3.connect(str(db))
            try:
                rows = con.execute(
                    "SELECT eylem, sonuc FROM ajan_gunlugu "
                    "WHERE sonuc LIKE '%[Hata]%' OR sonuc LIKE '%Hatasi]%' "
                    "ORDER BY rowid DESC LIMIT 200"
                ).fetchall()
            except Exception:
                rows = []
            finally:
                con.close()

            arac_hatalari: dict[str, int] = {}
            hata_mesajlari: list[str] = []
            for eylem, sonuc in rows:
                arac = eylem.split("(")[0] if "(" in eylem else eylem
                arac_hatalari[arac] = arac_hatalari.get(arac, 0) + 1
                hata_mesajlari.append(sonuc[:80])

            basarisiz = sorted(arac_hatalari.items(), key=lambda x: -x[1])
            return {
                "hata_sayisi": len(rows),
                "en_sik_hatalar": hata_mesajlari[:5],
                "basarisiz_araclar": basarisiz[:5],
            }
        except Exception as e:
            return {"hata": str(e)}

    def beceri_bosluk_analizi(self) -> list[str]:
        """Tamamlanan gorevleri analiz et, eksik beceri alanlari bul."""
        try:
            import sqlite3
            db = ROOT.parent / "merkez_db" / "session_cereyan.db"
            if not db.exists():
                return []
            con = sqlite3.connect(str(db))
            try:
                rows = con.execute(
                    "SELECT hedef FROM ajan_gunlugu "
                    "WHERE eylem LIKE '%GOREV_BITTI%' "
                    "ORDER BY rowid DESC LIMIT 50"
                ).fetchall()
            except Exception:
                rows = []
            finally:
                con.close()

            hedefler = [r[0] for r in rows if r[0]]
            return hedefler[:10]
        except Exception:
            return []

    def oneri_uret(self, hata_analizi: dict, provider=None) -> str:
        """LLM kullanarak iyilestirme onerileri uret."""
        prov = provider or self.provider
        if not prov:
            return self._kural_tabanli_oneri(hata_analizi)

        prompt = f"""ReYMeN ajaninin hata analizi:

Toplam hata: {hata_analizi.get('hata_sayisi', 0)}
En cok hata veren araclar: {hata_analizi.get('basarisiz_araclar', [])}
Ornek hata mesajlari: {hata_analizi.get('en_sik_hatalar', [])}

Bu verilere dayanarak ReYMeN icin 3 somut iyilestirme onerisi yaz.
Her oneri uygulanabilir ve teknik olmali.
Format:
1. [Oneri basligI]: aciklama
2. ...
3. ..."""
        try:
            return prov.uret(prompt, [{"role": "user", "content": "Oneri uret."}])
        except Exception as e:
            return self._kural_tabanli_oneri(hata_analizi)

    def _kural_tabanli_oneri(self, analiz: dict) -> str:
        oneriler = []
        basarisiz = dict(analiz.get("basarisiz_araclar", []))

        if basarisiz.get("KOMUT_CALISTIR", 0) > 3:
            oneriler.append("1. KOMUT_CALISTIR yerine PYTHON_CALISTIR tercih et — daha guvenilir sandbox")
        if basarisiz.get("TARAYICI_AC", 0) > 2:
            oneriler.append("2. TARAYICI_AC basarisizsa WEB_ARA'ya don — Playwright gerekmez")
        if basarisiz.get("EKRAN_TIKLA", 0) > 2:
            oneriler.append("3. EKRAN_TIKLA oncesi EKRAN_NISAN kullan — hedef noktayi dogrula")
        if not oneriler:
            oneriler = [
                "1. Her islemden once HAFIZA_ARA yap — benzer gecmis tecrubelerden yararlan",
                "2. Basarisiz eylem sonrasi IC_GOZLEM kullan — strateji degistir",
                "3. Uzun gorevleri GOREV_BITTI ile erken bitirme; plan bitene kadar devam et",
            ]
        return "\n".join(oneriler)

    def soul_guncelle(self, oneriler: str) -> bool:
        """Onerileri SOUL.md'e ek olarak kaydet."""
        if not SOUL_YOLU.exists():
            return False
        mevcut = SOUL_YOLU.read_text(encoding="utf-8")
        ek = f"\n\n## Oz-Gelistirme ({datetime.now().strftime('%Y-%m-%d')})\n{oneriler}\n"
        SOUL_YOLU.write_text(mevcut + ek, encoding="utf-8")
        print(f"[Self-Imp] SOUL.md guncellendi.")
        return True

    def rapor_kaydet(self, sonuc: dict):
        ANALIZ_RAPOR.parent.mkdir(parents=True, exist_ok=True)
        ANALIZ_RAPOR.write_text(
            json.dumps(sonuc, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def calistir(self, uygula: bool = False) -> dict:
        print("[Self-Imp] Hata analizi yapiliyor...")
        hata_analizi = self.hata_analizi_yap()
        print(f"  Toplam hata: {hata_analizi.get('hata_sayisi', 0)}")

        print("[Self-Imp] Oneri uretiliyor...")
        oneriler = self.oneri_uret(hata_analizi)
        print(f"\n--- ONERILER ---\n{oneriler}\n")

        beceriler = self.beceri_bosluk_analizi()

        sonuc = {
            "zaman": datetime.now(timezone.utc).isoformat(),
            "hata_analizi": hata_analizi,
            "oneriler": oneriler,
            "gecmis_gorevler": beceriler,
        }
        self.rapor_kaydet(sonuc)

        if uygula:
            self.soul_guncelle(oneriler)

        return sonuc


if __name__ == "__main__":
    uygula = "--uygula" in sys.argv
    try:
        from reymen.cereyan.beyin import Beyin
        from reymen.sistem.main import CONFIG
        prov = Beyin(CONFIG)
    except Exception:
        prov = None

    motor = OzGelistirmeMotoru(provider=prov)
    motor.calistir(uygula=uygula)
