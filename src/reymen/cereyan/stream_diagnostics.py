# -*- coding: utf-8 -*-
"""Streaming API çağrısı sağlık takibi.

Her stream denemesi için first-token-time, token hızı, toplam süre ve
hata bilgisini kaydeder. conversation_loop.py'nin retry döngüsü bu
istatistikleri kullanarak yavaş/sıkışmış stream'leri erken keser.

ReYMeN'in stream_diagnostics.py'sinden adapte edilmiştir.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StreamDenemesi:
    """Tek bir stream girişiminin istatistikleri."""
    baslangic: float = field(default_factory=time.monotonic)
    ilk_token_zamani: Optional[float] = None
    bitis: Optional[float] = None
    token_sayisi: int = 0
    hata: Optional[str] = None
    provider: str = ""
    model: str = ""

    def ilk_token_kaydet(self) -> None:
        if self.ilk_token_zamani is None:
            self.ilk_token_zamani = time.monotonic()

    def token_ekle(self, sayi: int = 1) -> None:
        if self.ilk_token_zamani is None:
            self.ilk_token_zamani = time.monotonic()
        self.token_sayisi += sayi

    def bitir(self, hata: Optional[str] = None) -> None:
        self.bitis = time.monotonic()
        self.hata = hata

    @property
    def ilk_token_gecikme(self) -> Optional[float]:
        """İlk token'a kadar geçen süre (saniye)."""
        if self.ilk_token_zamani is None:
            return None
        return self.ilk_token_zamani - self.baslangic

    @property
    def toplam_sure(self) -> float:
        """Toplam geçen süre (saniye); bitmemişse şimdiye kadar."""
        bitis = self.bitis or time.monotonic()
        return bitis - self.baslangic

    @property
    def token_hizi(self) -> Optional[float]:
        """Token/saniye; yeterli veri yoksa None."""
        if self.token_sayisi == 0 or self.ilk_token_zamani is None:
            return None
        sure = (self.bitis or time.monotonic()) - self.ilk_token_zamani
        if sure <= 0:
            return None
        return self.token_sayisi / sure

    @property
    def basarili(self) -> bool:
        return self.hata is None and self.bitis is not None

    def ozet(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "ilk_token_gecikme_sn": round(self.ilk_token_gecikme or 0, 3),
            "toplam_sure_sn": round(self.toplam_sure, 3),
            "token_sayisi": self.token_sayisi,
            "token_hizi": round(self.token_hizi or 0, 1),
            "basarili": self.basarili,
            "hata": self.hata,
        }


class StreamSaglikTakibi:
    """Bir konuşma boyunca tüm stream denemelerini takip eder.

    Kullanım::

        takip = StreamSaglikTakibi(max_ilk_token_bekleme=15.0)
        deneme = takip.yeni_deneme(provider="deepseek", model="deepseek-chat")
        # ... stream loop ...
        for chunk in stream:
            deneme.token_ekle()
            if takip.ask_mi(deneme):
                break  # yavaş stream'i kes
        deneme.bitir()
    """

    def __init__(
        self,
        max_ilk_token_bekleme: float = 30.0,
        min_token_hizi: float = 0.5,
        yeniden_deneme_esigi: int = 3,
    ) -> None:
        self.max_ilk_token_bekleme = max_ilk_token_bekleme
        self.min_token_hizi = min_token_hizi
        self.yeniden_deneme_esigi = yeniden_deneme_esigi
        self._denemeler: List[StreamDenemesi] = []

    def yeni_deneme(self, provider: str = "", model: str = "") -> StreamDenemesi:
        deneme = StreamDenemesi(provider=provider, model=model)
        self._denemeler.append(deneme)
        return deneme

    def ask_mi(self, deneme: StreamDenemesi) -> bool:
        """Stream'i kesmek gerekiyor mu?

        İlk token çok geç geldiyse veya token hızı çok düştüyse True döner.
        """
        # İlk token henüz gelmedi ve bekleme süresi aşıldı
        if deneme.ilk_token_zamani is None:
            gecen = time.monotonic() - deneme.baslangic
            if gecen > self.max_ilk_token_bekleme:
                return True

        # Token hızı çok düşük
        hiz = deneme.token_hizi
        if hiz is not None and hiz < self.min_token_hizi:
            return True

        return False

    @property
    def toplam_deneme(self) -> int:
        return len(self._denemeler)

    @property
    def basarili_deneme(self) -> int:
        return sum(1 for d in self._denemeler if d.basarili)

    @property
    def son_deneme(self) -> Optional[StreamDenemesi]:
        return self._denemeler[-1] if self._denemeler else None

    def ortalama_ilk_token(self) -> Optional[float]:
        gecikme_ler = [
            d.ilk_token_gecikme
            for d in self._denemeler
            if d.ilk_token_gecikme is not None
        ]
        if not gecikme_ler:
            return None
        return sum(gecikme_ler) / len(gecikme_ler)

    def ozet(self) -> dict:
        return {
            "toplam_deneme": self.toplam_deneme,
            "basarili": self.basarili_deneme,
            "ortalama_ilk_token_sn": self.ortalama_ilk_token(),
            "denemeler": [d.ozet() for d in self._denemeler],
        }
