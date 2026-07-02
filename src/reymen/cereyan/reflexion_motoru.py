# -*- coding: utf-8 -*-
"""
reflexion_motoru.py — Reflexion Pattern (Shinn et al. 2023).

Buyuk LLM sistemlerindeki ilke:
  "Basarisizliktan ogren: sozel yansima uret, hafizaya kaydet,
   benzer gorevi tekrarlarken onceki dersi getir."

Fark (klasik hata kaydindan):
  - Normal hata logu: "[Hata]: timeout" — ne oldu
  - Reflexion: "Web_Ara aracini kullanirken timeout aldim cunku sorgu
    cok genel ve 10+ saniye surdu. Gelecekte sorguyu daraltmaliyim
    ve PYTHON_CALISTIR ile dogrulama adimi eklemeliyim." — NE YAPMALI

Entegrasyon (main.py):
    from reflexion_motoru import ReflexionMotoru
    rm = ReflexionMotoru(provider=self.provider, hafiza=self.hafiza)
    # Hata/basarisizlik sonrasinda:
    rm.yansima_kaydet(hedef, adim_gecmisi, hata_mesaji)
    # Gorev basinda sistem prompt'a ekle:
    ders = rm.ilgili_dersleri_al(hedef)
    if ders: sistem_prompt += ders
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
YANSIMA_LOG = ROOT / ".ReYMeN" / "reflexion_log.jsonl"
MAKS_YANSIMA = 200  # Dosya satir siniri

# ── Prompt sablon ─────────────────────────────────────────────────────────────

_YANSIMA_SISTEM = """Sen deneyimli bir yapay zeka sistemi analisti ve ogretmenisin.
Sana basarisiz bir ajan gorevi sunulacak.
Gorevine gore NEDEN basarisiz oldugunu analiz et ve ne yapmasi gerektigini ac.

Yaniti TAM OLARAK su formatta ver (baska sey yazma):
NEDEN_BASARISIZ: [Tek cumle - kok neden]
KACINILACAK: [Tek cumle - tekrar yapilmamasi gereken eylem]
DAHA_IYI_YAKLASIM: [Tek cumle - bir dahaki seferde nasil yapilmali]
ANAHTAR_KELIMELER: [virgul,ile,ayrilmis,kelimeler]
"""

_DERS_ENJEKSIYON_SABLON = """\n== REFLEXION: ONCEKI DERSLER ==
{dersler}
== /REFLEXION ==
"""


class ReflexionMotoru:
    """Basarisizliklardan sozel yansima ureten ve hafizaya kaydeden sinif."""

    def __init__(self, provider=None, hafiza=None, log_yolu: str = None):
        self._provider = provider
        self._hafiza = hafiza
        self._log = Path(log_yolu) if log_yolu else YANSIMA_LOG
        self._log.parent.mkdir(parents=True, exist_ok=True)

    # ── Ana API ──────────────────────────────────────────────────────────────

    def yansima_kaydet(
        self,
        hedef: str,
        adim_gecmisi: list[str],
        hata_mesaji: str,
    ) -> Optional[dict]:
        """Basarisiz gorev icin LLM yansimasi uret ve kaydet.

        Args:
            hedef:         Basarisiz olan kullanici hedefi.
            adim_gecmisi:  Gerceklestirilen adimlar listesi.
            hata_mesaji:   Son hata veya basarisizlik ozeti.

        Returns:
            Yansima sozlugu veya None (LLM hatasinda).
        """
        if not self._provider:
            return self._kural_tabanli_yansima(hedef, adim_gecmisi, hata_mesaji)

        adimlar_str = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(adim_gecmisi))
        kullanici_msg = (
            f"Hedef: {hedef}\n\n"
            f"Yapilan adimlar:\n{adimlar_str}\n\n"
            f"Hata / Basarisizlik: {hata_mesaji[:300]}"
        )

        try:
            yanit = self._provider.uret(_YANSIMA_SISTEM, [{"role": "user", "content": kullanici_msg}])
            yansima = self._yanit_ayristir(yanit)
        except Exception as e:
            print(f"[Reflexion] LLM hatasi: {e}")
            yansima = self._kural_tabanli_yansima(hedef, adim_gecmisi, hata_mesaji)

        if not yansima:
            return None

        # Hafizaya kaydet
        yansima["hedef"] = hedef[:100]
        yansima["zaman"] = datetime.now().isoformat()
        yansima["hata"] = hata_mesaji[:200]

        self._dosyaya_kaydet(yansima)

        if self._hafiza:
            self._vektore_kaydet(hedef, yansima)

        print(f"[Reflexion] Yansima kaydedildi: {yansima.get('neden_basarisiz', '')[:80]}")
        return yansima

    def ilgili_dersleri_al(self, hedef: str, adet: int = 3) -> str:
        """Benzer gecmis basarisizliklarin derslerini getir.

        Once vektor hafizasindan dene, sonra JSONL dosyasindan anahtar kelime tarama.

        Returns:
            Sistem prompt'una enjekte edilecek formatlI string (bos olabilir).
        """
        # 1. Vektor hafizasi
        if self._hafiza:
            try:
                from reymen.hafiza.vektorel_hafiza import anlamsal_hafiza_ara
                vek_sonuc = anlamsal_hafiza_ara(self._hafiza, f"REFLEXION {hedef}", adet=adet)
                if vek_sonuc and "bulunamadi" not in vek_sonuc.lower():
                    return _DERS_ENJEKSIYON_SABLON.format(dersler=vek_sonuc[:600])
            except Exception as _e:
                logger.warning("[ReflexionMotoru] except Exception (L130): %s", Exception)
                pass

        # 2. JSONL anahtar kelime tarama
        dersler = self._dosyadan_benzer_bul(hedef, adet)
        if not dersler:
            return ""

        satirlar = []
        for d in dersler:
            satirlar.append(
                f"- Hedef: {d.get('hedef', '?')[:60]}\n"
                f"  Neden: {d.get('neden_basarisiz', '?')}\n"
                f"  Cozum: {d.get('daha_iyi_yaklasim', '?')}"
            )

        return _DERS_ENJEKSIYON_SABLON.format(dersler="\n".join(satirlar))

    # ── Ic yardimcilar ───────────────────────────────────────────────────────

    @staticmethod
    def _yanit_ayristir(yanit: str) -> Optional[dict]:
        """LLM ciktisini yapilandirilmis sozluge donustur."""
        satir_map = {
            "neden_basarisiz":    r"NEDEN_BASARISIZ:\s*(.+)",
            "kacinilacak":        r"KACINILACAK:\s*(.+)",
            "daha_iyi_yaklasim":  r"DAHA_IYI_YAKLASIM:\s*(.+)",
            "anahtar_kelimeler":  r"ANAHTAR_KELIMELER:\s*(.+)",
        }
        sonuc = {}
        for alan, kalip in satir_map.items():
            m = re.search(kalip, yanit, re.IGNORECASE)
            sonuc[alan] = m.group(1).strip() if m else ""

        return sonuc if any(sonuc.values()) else None

    @staticmethod
    def _kural_tabanli_yansima(hedef: str, adimlar: list, hata: str) -> dict:
        """LLM olmadan kural tabanli yansima."""
        neden = "Bilinmeyen hata"
        cozum = "Farkli bir yaklasim dene"
        kacinilacak = "Ayni adimi tekrarlama"

        hata_lower = hata.lower()
        if "timeout" in hata_lower or "zaman asimi" in hata_lower:
            neden = "Islem zaman asimina ugradi"
            cozum = "Daha kisa sorgu veya islem parcalara bol"
            kacinilacak = "Uzun sure bekleyen ayni araci tekrar cagirma"
        elif "modul" in hata_lower or "import" in hata_lower:
            neden = "Gerekli Python modulu yuklu degil"
            cozum = "try/except ile modulu kontrol et ve alternatif kullan"
            kacinilacak = "Yuklu olmayan modulu import etme"
        elif "izin" in hata_lower or "permission" in hata_lower:
            neden = "Dosya/sistem izin hatasi"
            cozum = "Farkli dizin veya kullanici izinlerini kontrol et"
            kacinilacak = "Kisitilanmis alanlara yazma deneme"
        elif "baglanti" in hata_lower or "connection" in hata_lower:
            neden = "Network baglantisi kurulamadi"
            cozum = "Internet baglantisin varsa tekrar dene, yoksa cevrimici arac kullanma"
            kacinilacak = "Cevrimdisi ortamda ag gerektiren arac cagirma"

        anahtar = " ".join(hedef.lower().split()[:4])
        return {
            "neden_basarisiz":   neden,
            "kacinilacak":       kacinilacak,
            "daha_iyi_yaklasim": cozum,
            "anahtar_kelimeler": anahtar,
        }

    def _dosyaya_kaydet(self, yansima: dict):
        """JSONL dosyasina satir olarak ekle; siniri asarsa en eskiyi sil."""
        try:
            # Mevcut satirlari oku
            satirlar = []
            if self._log.exists():
                satirlar = self._log.read_text(encoding="utf-8").splitlines()

            # Sinir kontrolu
            if len(satirlar) >= MAKS_YANSIMA:
                satirlar = satirlar[-(MAKS_YANSIMA - 1):]  # En eskiyi at

            satirlar.append(json.dumps(yansima, ensure_ascii=False))
            self._log.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        except OSError as e:
            print(f"[Reflexion] Dosya yazma hatasi: {e}")

    def _vektore_kaydet(self, hedef: str, yansima: dict):
        """ChromaDB hafizasina REFLEXION prefix ile kaydet."""
        try:
            from reymen.hafiza.vektorel_hafiza import tecrube_kaydet
            icerik = (
                f"REFLEXION: {hedef}\n"
                f"Neden: {yansima.get('neden_basarisiz', '')}\n"
                f"Kacinilacak: {yansima.get('kacinilacak', '')}\n"
                f"Cozum: {yansima.get('daha_iyi_yaklasim', '')}"
            )
            kayit_id = f"reflexion-{abs(hash(hedef + yansima.get('zaman', ''))) % 999999}"
            tecrube_kaydet(self._hafiza, kayit_id, icerik, {"tip": "reflexion"})
        except Exception as e:
            print(f"[Reflexion] Vektor kayit hatasi: {e}")

    def _dosyadan_benzer_bul(self, hedef: str, adet: int) -> list:
        """JSONL'den anahtar kelime ile benzer yansimalari bul."""
        if not self._log.exists():
            return []
        hedef_kelimeler = set(hedef.lower().split())
        sonuclar = []
        try:
            for satir in self._log.read_text(encoding="utf-8").splitlines():
                if not satir.strip():
                    continue
                try:
                    d = json.loads(satir)
                except json.JSONDecodeError:
                    continue
                anahtar = set((d.get("anahtar_kelimeler", "")).replace(",", " ").lower().split())
                eski_hedef = set(d.get("hedef", "").lower().split())
                toplam = anahtar | eski_hedef
                eslesme = len(hedef_kelimeler & toplam)
                if eslesme > 0:
                    sonuclar.append((eslesme, d))
            sonuclar.sort(key=lambda x: x[0], reverse=True)
            return [d for _, d in sonuclar[:adet]]
        except OSError:
            return []


# ── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("=== reflexion_motoru.py Test ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_yolu = os.path.join(tmpdir, "ref_log.jsonl")

        rm = ReflexionMotoru(provider=None, hafiza=None, log_yolu=log_yolu)

        # Test 1: Kural tabanli yansima (LLM yok)
        yansima = rm.yansima_kaydet(
            "Web'den haber cek",
            ["WEB_ARA(\"python news\")", "TARAYICI_AC(\"https://...\")"],
            "[Hata]: timeout — 30 saniyede yanit gelmedi",
        )
        print("[Test 1] Yansima:", json.dumps(yansima, ensure_ascii=False, indent=2)[:200])

        # Test 2: Ikinci yansima
        rm.yansima_kaydet(
            "Python dosyasini calistir",
            ["PYTHON_CALISTIR(\"import tensorflow\")"],
            "[Hata]: ModuleNotFoundError: tensorflow",
        )

        # Test 3: Ilgili ders getir
        dersler = rm.ilgili_dersleri_al("Internetten veri cek", adet=2)
        print(f"\n[Test 2] Dersler ({len(dersler)} karakter):")
        print(dersler[:300] if dersler else "(Ders bulunamadi)")

        # Test 4: Alakasiz sorgu - ders gelmemeli
        alakasiz = rm.ilgili_dersleri_al("PDF dosyasini oku ve ozet cikar")
        print(f"\n[Test 3] Alakasiz sorgu ders: {'(Bos - dogru)' if not alakasiz else alakasiz[:100]}")

        print("\n[Testler] Tamamlandi.")
