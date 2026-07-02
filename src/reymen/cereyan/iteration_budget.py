# -*- coding: utf-8 -*-
"""iteration_budget.py — ReYMeN thread-safe iterasyon butcesi.

ReYMeN Agent IterationBudget pattern'i ile ayni.
Her ajan (ana veya alt) kendi butcesine sahiptir.
Thread-safe consume/refund sayaci.

Kullanim:
    budget = IterationBudget(max_total=90)
    if budget.consume():
        # islem yap
        pass
    budget.refund()  # execute_code gibi durumlarda iade
"""

import threading


class IterationBudget:
    """Thread-safe iterasyon sayaci.

    Her ajan kendi butcesine sahip olur.
    Ana ajan: max_iterations (varsayilan 90)
    Alt ajan: delegation.max_iterations (varsayilan 50)

    Geriye uyumluluk: max_tur parametresi de calisir (max_total ile ayni).
    """

    def __init__(self, max_total: int = None, max_tur: int = None):
        # max_tur eski API uyumlulugu
        if max_total is None and max_tur is not None:
            max_total = max_tur
        if max_total is None:
            max_total = 90
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        """Bir iterasyon harca. True: izin var, False: butce doldu."""
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        """Bir iterasyonu iade et (ornek: execute_code icin)."""
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)

    def reset(self) -> None:
        """Butceyi sifirla."""
        with self._lock:
            self._used = 0

    def __repr__(self) -> str:
        return f"IterationBudget({self.used}/{self.max_total})"

    # ══════════════════════════════════════════════════════════════════
    # GERIYE UYUMLULUK — eski API
    # ══════════════════════════════════════════════════════════════════

    @property
    def tur(self) -> int:
        """Eski API: tur sayisi = used ile ayni."""
        return self._used

    @property
    def max_tur(self) -> int:
        """Eski API alias: max_total ile ayni."""
        return self.max_total

    def tur_basla(self) -> None:
        """Eski API: consume ile ayni."""
        self.consume()

    def tur_bitir(self, basarili: bool = True, sonuc: str = "",
                  hata_tipi: str = "") -> bool:
        """Eski API: tur sonu kontrolu. True = devam et, False = dur."""
        return self.remaining > 0

    def devam_etmeli_mi(self) -> bool:
        """Eski API: kalan butce var mi?"""
        return self.remaining > 0

    def durum_raporu(self) -> str:
        """Eski API: butce durumunu okunabilir string olarak dondur."""
        return f"Tur {self._used}/{self.max_total} (kalan: {self.remaining})"

    def gorev_tamamla(self) -> None:
        """Eski API: reset ile ayni."""
        self.reset()

    # Takma adlar
    gorev_tamami = gorev_tamamla

    def eylem_kaydet(self, eylem: str) -> None:
        """Eski API: eylem logla (no-op)."""
        pass

    def ozet_dict(self) -> dict:
        """Eski API: dict'e cevir."""
        return {"tur": self._used, "max_tur": self.max_total}

    def analiz_et(self, gorev: str) -> dict:
        """Gorev karmasikligini analiz et (1-5).

        Kategori bazli hesaplama:
          1 = selamlasma/sosyal/basit soru
          2 = tek kategorili basit islem
          3 = iki kategorili veya cok adimli islem
          4 = 3+ kategori veya toplu gorev (swarm esigi)
          5 = toplu + islem (swarm)
        """
        hedef = gorev.lower().strip()

        # ── 0. Selamlasma/sosyal/basit soru → direkt 1 ──────────────
        _selam = any(k in hedef for k in [
            "merhaba", "selam", "naber", "nasılsın", "nasilsin",
            "iyi misin", "teşekkür", "tesekkur", "sağol", "sagol",
            "günaydın", "gunaydin", "iyi günler", "iyi gunler",
            "iyi akşamlar", "iyi aksamlar", "iyi geceler",
            "ne yapıyorsun", "ne yapiyorsun", "napıyorsun", "napiyorsun",
            "kolay gelsin", "hayırlı", "hayirli",
        ])
        # Eger sadece selam kelimeleri varsa (ek istek yoksa)
        if _selam:
            # Icinde ek islem kelimesi yoksa direkt 1
            _ek_islem = any(k in hedef for k in [
                "yap", "ara", "oku", "yaz", "sil", "bul",
                "calistir", "çalıştır", "indir", "yukle", "yükle",
                "kur", "gönder", "gonder", "tara", "kontrol",
                "düzelt", "duzelt", "temizle", "düzenle", "duzenle",
                "raporla", "analiz", "incele", "güncelle", "guncelle",
                "aç", "ac", "kapat", "kes", "koştur", "kostur",
            ])
            if not _ek_islem:
                return {"karmasiklik": 1}

        # ── 1. Toplu gorev tespiti ─────────────────────────────────
        _toplu = any(k in hedef for k in [
            "hepsini", "hepsin", "hepsi",
            "tümünü", "tümü", "tüm", "tumu", "tumunu",
            "bütün", "butun", "toplu",
        ])
        _islem = any(k in hedef for k in [
            "kontrol", "gider", "düzelt", "duzelt", "onar", "temizle",
            "tara", "düzenle", "duzenle", "yap", "calistir", "çalıştır",
            "incele", "dönüştür", "donustur", "güncelle", "guncelle",
        ])
        if _toplu and _islem:
            return {"karmasiklik": 5}
        if _toplu:
            return {"karmasiklik": 4}

        # ── 2. Cok adimli gorev tespiti (baglac + virgul) ──────────
        _cok_adim_baglac = any(k in hedef for k in [
            "ve", "sonra", "ardindan", "ardından", "daha sonra",
            "once", "önce", "daha önce", "daha once",
        ])
        _cok_adim_virgul = hedef.count(",") >= 2
        _cok_adim = _cok_adim_baglac or _cok_adim_virgul

        # ── 3. Kategori bazinda keyword sayisi ──────────────────────
        # Her kategoriden ilk keyword sayilir, ayni kategoriden
        # birden fazla keyword extra puan vermez
        kategoriler = {
            "dosya_islem": ["dosya", "klasör", "klasor", "dizin", "belge", "uzanti"],
            "web_islem":   ["web", "internet", "url", "site", "sayfa", "link",
                           "indir", "yukle", "yükle", "gönder", "gonder"],
            "kod_islem":   ["kod", "python", "script", "calistir", "çalıştır",
                           "analiz", "derle", "debug", "test"],
            "sistem_islem":["sistem", "komut", "terminal", "powershell", "servis",
                           "port", "ağ", "ag", "islem", "işlem", "proses", "durdur"],
            "arama_islem": ["ara", "bul", "tara", "sorgula", "keşfet", "kesfet",
                           "listele", "getir"],
            "yazma_islem": ["yaz", "oluştur", "olustur", "kaydet", "ekle",
                           "güncelle", "guncelle", "sil", "düzenle", "duzenle",
                           "temizle", "dönüştür", "donustur", "düzelt", "duzelt",
                           "onar"],
            "guvenlik":    ["güvenlik", "guvenlik", "şifre", "sifre", "izin",
                           "yetki", "erişim", "erisim"],
            "github_islem":["git", "github", "repo", "commit", "push", "pull",
                           "clone", "branch", "merge"],
        }

        # Ekstra puan veren kelimeler (kategori disi kapsam artirici)
        _ekstra_kelimeler = ["raporla", "özet", "ozet", "karşılaştır", "karsilastir",
                            "birleştir", "birlestir", "görsel", "gorsel", "grafik"]

        # Kac farkli kategori bulundu
        _bulunan_kategori = 0
        for kategori, kw_list in kategoriler.items():
            if any(kw in hedef for kw in kw_list):
                _bulunan_kategori += 1

        # ── 4. Skor hesaplama ──────────────────────────────────────
        skor = _bulunan_kategori
        if _cok_adim:
            skor += 1

        # Ek keyword sayisi (kategori disi ekstra)
        _ek_kelimeler = ["raporla", "özet", "ozet", "karşılaştır", "karsilastir",
                        "donüştür", "donustur", "birleştir", "birlestir"]
        for k in _ek_kelimeler:
            if k in hedef:
                # Sadece yeni kategori eklemediysek bonus
                if not any(kw in hedef for kw in kategoriler.get("yazma_islem", [])):
                    skor += 1
                    break

        return {"karmasiklik": max(1, min(skor, 5))}
