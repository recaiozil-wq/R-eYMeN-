# -*- coding: utf-8 -*-
"""
context_manager.py — TrajectoryCompressor (ReYMeN Konusma Sikistirici).

Ozellikler:
  - LLM ile yapisal ozet (Cozumlendi / Devam Ediyor / Bekleyen)
  - Araç çıktısı budama (token tasarrufu)
  - Kuyruk koruma: son N mesaj dokunulmaz
  - Iteratif guncelleme: onceki ozet varsa birlestir
  - Provider verilmezse rule-based fallback
  - Ayni dosyada hem ContextCompressor hem AdvancedContextCompressor

ReYMeN context_compressor'dan ilham alindi, ReYMeN icin yeniden yazildi.
"""
import re
from typing import Optional

# Ozet mesajinin basi — LLM'e bu ozeti talimata degil referansa al der
OZET_BASLIGI = (
    "[BAGLAM SIKISTIRMASI — SADECE REFERANS]\n"
    "Asagidaki ozet onceki mesajlari temsil eder. "
    "Bu ozeti AKTIF TALIMAT olarak degil, GECMIS BILGI olarak kullan. "
    "Sondaki kullanici mesajina gore hareket et.\n\n"
)

OZET_SABLONU = """## Aktif Gorev
{aktif_gorev}

## Tamamlananlar
{tamamlananlar}

## Devam Eden
{devam_eden}

## Bekleyen / Engeller
{bekleyen}

## Onemli Bulgular
{bulgular}
"""

OZET_SISTEM_TALIMATI = (
    "Asagidaki konusma gecmisini analiz et ve structured bir ozet uret. "
    "Format kesinlikle asagidaki gibi olmali:\n\n"
    "## Aktif Gorev\n(su an ne uzerine calisiliyor)\n\n"
    "## Tamamlananlar\n(tamamlanan adimlar, maddeler halinde)\n\n"
    "## Devam Eden\n(henuz bitmemis isler)\n\n"
    "## Bekleyen / Engeller\n(hata, eksik bilgi, onay bekleme)\n\n"
    "## Onemli Bulgular\n(kritik kesfler, kod degisiklikleri, kararlar)\n\n"
    "Kisa ve odakli tut. Gereksiz tekrar yok."
)


class TrajectoryCompressor:
    """LLM destekli konusma gecmisi sikistirici."""

    def __init__(self, provider=None, esik_oran: float = 0.75,
                 korunan_son: int = 8, max_arac_cikti: int = 300):
        self.provider = provider          # RuntimeProviderEngine veya None
        self.esik_oran = esik_oran        # Bu orandan fazla dolunca sikistir
        self.korunan_son = korunan_son    # Son N mesaj korunur
        self.max_arac_cikti = max_arac_cikti  # Gozlem satirlari max uzunlugu
        self._onceki_ozet: str = ""       # Iteratif guncelleme icin

    # ── Token tahmini ─────────────────────────────────────────────────

    def _token_tahmin(self, mesajlar: list) -> int:
        return sum(len(m.get("content", "")) for m in mesajlar) // 4

    # ── Arac cikti budama ─────────────────────────────────────────────

    def _arac_ciktilarini_buda(self, mesajlar: list) -> list:
        """Uzun [Gozlem] ve [Tamam] satirlarini kisalt."""
        budanmis = []
        for m in mesajlar:
            icerik = m.get("content", "")
            if m.get("role") == "user" and len(icerik) > self.max_arac_cikti:
                # [Gozlem] ile baslayan uzun mesajlari kisalt
                if icerik.startswith("Gozlem:") or icerik.startswith("["):
                    icerik = icerik[:self.max_arac_cikti] + "\n... [budandi]"
            budanmis.append({**m, "content": icerik})
        return budanmis

    # ── Ozetleme ──────────────────────────────────────────────────────

    def _ozet_uret(self, mesajlar: list) -> str:
        """Verilen mesajlar listesini ozetle — LLM varsa LLM, yoksa kural."""
        if self.provider:
            return self._llm_ile_ozetle(mesajlar)
        return self._kural_ile_ozetle(mesajlar)

    def _llm_ile_ozetle(self, mesajlar: list) -> str:
        """LLM kullanarak yapisal ozet uret."""
        parcalar = []
        for m in mesajlar[-40:]:  # Son 40 mesaj — daha fazlasi cok token
            rol = m.get("role", "?")
            icerik = m.get("content", "")[:400]
            parcalar.append(f"[{rol}]: {icerik}")

        gecmis = "\n".join(parcalar)

        # Onceki ozet varsa birlestir
        if self._onceki_ozet:
            gecmis = (
                f"[ONCEKI OZET]\n{self._onceki_ozet}\n\n"
                f"[YENI MESAJLAR]\n{gecmis}"
            )

        try:
            ozet = self.provider.uret(
                OZET_SISTEM_TALIMATI,
                [{"role": "user", "content": gecmis}],
            )
            self._onceki_ozet = ozet
            return ozet
        except Exception:
            return self._kural_ile_ozetle(mesajlar)

    def _kural_ile_ozetle(self, mesajlar: list) -> str:
        """LLM olmadan kural-tabanli ozet."""
        satirlar = []
        eylemler = []
        gozlemler = []

        for m in mesajlar:
            icerik = m.get("content", "")
            if m.get("role") == "assistant":
                # Eylem satirini yakala
                e = re.search(r"Eylem:\s*(\w+)\((.{0,60})", icerik)
                if e:
                    eylemler.append(f"  - {e.group(1)}({e.group(2)}...")
            elif m.get("role") == "user" and icerik.startswith("Gozlem:"):
                gozlemler.append("  - " + icerik[8:60])

        if self._onceki_ozet:
            satirlar.append(f"[Onceki Ozet]\n{self._onceki_ozet[:500]}\n")

        satirlar.append("## Aktif Gorev\n(devam ediyor)\n")

        if eylemler:
            satirlar.append("## Tamamlananlar\n" + "\n".join(eylemler[-10:]))
        if gozlemler:
            satirlar.append("## Onemli Bulgular\n" + "\n".join(gozlemler[-5:]))

        ozet = "\n\n".join(satirlar) if satirlar else "[Ozet olusturulamadi]"
        self._onceki_ozet = ozet
        return ozet

    # ── Ana sikistirma ────────────────────────────────────────────────

    def compress(self, mesajlar: list, context_length: int = 8192) -> list:
        """
        Token bütçesi esigi asilinca sikistir.
        Son `korunan_son` mesaj her zaman korunur.
        """
        if len(mesajlar) <= self.korunan_son:
            return mesajlar

        # Arac ciktilarini once buda
        mesajlar = self._arac_ciktilarini_buda(mesajlar)

        if self._token_tahmin(mesajlar) < context_length * self.esik_oran:
            return mesajlar

        eski = mesajlar[:-self.korunan_son]
        son = mesajlar[-self.korunan_son:]

        # Eski ozet mesajini kaldır (tekrar ozetleme)
        eski = [m for m in eski
                if not m.get("content", "").startswith("[BAGLAM SIKISTIRMASI")]

        if not eski:
            return mesajlar

        ozet_metni = self._ozet_uret(eski)
        ozet_mesaj = {
            "role": "system",
            "content": OZET_BASLIGI + ozet_metni,
        }
        return [ozet_mesaj] + son

    def sifirla(self):
        """Iteratif ozet bellegi temizle (yeni gorev icin)."""
        self._onceki_ozet = ""


# Geriye donuk uyumluluk takma adlari
class AdvancedContextCompressor(TrajectoryCompressor):
    """Eski isim — TrajectoryCompressor'in takma adi."""
    pass


ContextCompressor = AdvancedContextCompressor


if __name__ == "__main__":
    comp = TrajectoryCompressor()
    msgs = []
    for i in range(50):
        msgs.append({"role": "user", "content": f"Gozlem: Adim {i} tamamlandi."})
        msgs.append({"role": "assistant", "content": f"Eylem: DOSYA_YAZ(\"dosya{i}.txt\", \"icerik\")"})

    sonuc = comp.compress(msgs, context_length=8192)
    print(f"Onceki: {len(msgs)} mesaj → Sonraki: {len(sonuc)} mesaj")
    print(sonuc[0]["content"][:300])
