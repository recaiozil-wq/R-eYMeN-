# -*- coding: utf-8 -*-
"""conversation_compression.py — Konusma Sikistirma.

Uzun konusma gecmisini LLM ile ozetleyerek context'e sigdirir.
context_manager.py ile birlikte calisir.
"""

import json
import re
from pathlib import Path
from typing import Optional


class ConversationCompressor:
    """Sliding Window Memory — uzun konusmalari ozetleyerek context'e sigdirir.

    Yapılandırılabilir pencere boyutuyla son N tur korunur,
    daha eski turlar iteratif LLM ozeti olarak sıkıştırılır.
    """

    _OZET_BASLIGI = "[Önceki Konuşma Özeti]\n"

    def __init__(self, provider=None, pencere_boyutu: int = 6, esik_token: int = 3500):
        """
        Args:
            provider:       LLM provider (Beyin ornegi). Yoksa kural-tabanli ozet kullanilir.
            pencere_boyutu: Kac mesaj (user+assistant ciftleri * 2) ozetlenmeden tutulacak.
            esik_token:     Bu kadar token asiminda otomatik sikistirma baslangici.
        """
        self.provider = provider
        self.pencere_boyutu = max(pencere_boyutu, 2)
        self.esik_token = esik_token
        self._diyalog_ozeti = ""      # Iteratif ozet: her sikistirmada guncellenir
        self._sikistirma_sayisi = 0

    # ── Token tahmini ──────────────────────────────────────────────────

    @staticmethod
    def _token_tahmin(mesajlar: list) -> int:
        return sum(len(m.get("content", "")) // 4 for m in mesajlar)

    # ── Ozetleme ──────────────────────────────────────────────────────

    def _llm_ozetle(self, mesajlar: list) -> str:
        """LLM kullanarak anlamli, gorev-odakli ozet uret."""
        satirlar = []
        for m in mesajlar[-20:]:  # Son 20 mesajı al (sınırlı)
            rol = m.get("role", "?")
            icerik = m.get("content", "")[:300]
            satirlar.append(f"[{rol.upper()}]: {icerik}")

        # Onceki ozet varsa ekle
        onceki_bolum = ""
        if self._diyalog_ozeti:
            onceki_bolum = f"\n[ONCEKI OZET]:\n{self._diyalog_ozeti[:400]}\n\n"

        prompt = (
            "Bir otonom ajan konusmasini ozetliyorsun.\n"
            f"{onceki_bolum}"
            "Asagidaki ajan turlarini MAKSIMUM 5 cumlede ozetle.\n"
            "Odaklan: tamamlanan eylemler, ortaya cikan hatalar, kritik bulgular.\n"
            "KISA VE BILGI-YOGUN yaz — model duygusal anlati degil, eylem ozeti bekliyor.\n\n"
            + "\n".join(satirlar)
        )
        try:
            return self.provider.uret(
                prompt,
                [{"role": "user", "content": "Ozeti yaz."}]
            )
        except Exception:
            return self._basit_ozetle(mesajlar)

    def _basit_ozetle(self, mesajlar: list) -> str:
        """LLM olmadan kural-tabanli ozet."""
        eylemler = []
        hatalar  = []
        for m in mesajlar:
            icerik = m.get("content", "")
            # Eylem satırlarını yakala
            for satir in icerik.splitlines():
                satir = satir.strip()
                if "Eylem:" in satir or "ACTION:" in satir:
                    eylemler.append(satir[:80])
                if "[Hata]" in satir or "Error" in satir:
                    hatalar.append(satir[:80])

        parcalar = []
        if self._diyalog_ozeti:
            parcalar.append(f"[Önceki]: {self._diyalog_ozeti[:200]}")
        if eylemler:
            parcalar.append("Eylemler: " + "; ".join(eylemler[-5:]))
        if hatalar:
            parcalar.append("Hatalar: " + "; ".join(hatalar[-3:]))
        if not parcalar:
            parcalar.append(f"{len(mesajlar)} mesaj islendi.")
        return "\n".join(parcalar)

    # ── Ana sikistirma ─────────────────────────────────────────────────

    def sikistir(self, mesajlar: list, esik_token: int = None) -> list:
        """Mesaj listesini sliding window ile sıkıştırır.

        Son ``pencere_boyutu`` mesaj korunur, daha eskiler ozetlenir.
        Token esiginin altındaysa dokunulmaz.

        Args:
            mesajlar:   [{"role":..., "content":...}, ...] listesi.
            esik_token: Bu degerin ustundeyse sikistirma yapar.

        Returns:
            Sıkıştırılmış mesaj listesi.
        """
        esik = esik_token or self.esik_token
        if self._token_tahmin(mesajlar) <= esik:
            return mesajlar

        pencere = self.pencere_boyutu
        if len(mesajlar) <= pencere:
            return mesajlar

        eski = mesajlar[:-pencere]
        yeni = mesajlar[-pencere:]

        if self.provider:
            ozet = self._llm_ozetle(eski)
        else:
            ozet = self._basit_ozetle(eski)

        self._diyalog_ozeti = ozet
        self._sikistirma_sayisi += 1

        return [
            {"role": "system", "content": self._OZET_BASLIGI + ozet}
        ] + yeni

    # ── Yardimci ──────────────────────────────────────────────────────

    def ozeti_al(self) -> str:
        """Son ozet metnini donDur."""
        return self._diyalog_ozeti

    def sikistirma_sayisi(self) -> int:
        """Kac kez sikistirma yapildigini donDur."""
        return self._sikistirma_sayisi

    def sifirla(self):
        """Iteratif ozet bellegi temizle (yeni gorev icin)."""
        self._diyalog_ozeti = ""
        self._sikistirma_sayisi = 0


if __name__ == "__main__":
    c = ConversationCompressor()
    mesajlar = [
        {"role": "user", "content": "bir dosya olustur"},
        {"role": "assistant", "content": "DOSYA_YAZ(\"test.txt\", \"merhaba\")"},
        {"role": "user", "content": "simdi oku"},
        {"role": "assistant", "content": "DOSYA_OKU(\"test.txt\")"},
    ]
    sonuc = c.sikistir(mesajlar, esik_token=5)
    print(f"{len(mesajlar)} -> {len(sonuc)} mesaj")
