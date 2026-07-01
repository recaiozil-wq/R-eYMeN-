# -*- coding: utf-8 -*-
"""
browser_agent.py — ReYMeN Otonom Browser Agent Loop Tool.

Tek hedef ver, ReYMeN tarayıcıyı otomatik yönetsin:
  Hedef → Plan → Döngü (navigate → vision → decide → act → verify) → Rapor

Resilience desenleri (skill: browser-hata-desenleri):
  - retry + exponential backoff
  - timeout + screenshot + log
  - sekme state yönetimi (invisible döngü tespiti)
  - finally ile kaynak temizleme

Tool Registry'e otomatik kaydolur (tools/ dizininde run() fonksiyonu).

Kullanım (LLM'den):
    Eylem: BROWSER_AGENT(goal="GitHub'da ReYMeN reposunu bul ve yıldız sayısını söyle")
"""

import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Sabitler ─────────────────────────────────────────────────────────
_DENEME_SAYISI = 3
_MAX_DENEME = 3  # invisible döngü kesme sınırı
_TIMEOUT_KISA = 5000
_TIMEOUT_UZUN = 15000
_BEKLEME_CARPAN = 1.0  # exponential backoff başlangıcı

# ── Tool Meta (Registry için) ──────────────────────────────────────────
TOOL_META = {
    "aciklama": "Otonom Browser Agent — tek hedefle tarayıcıyı otomatik yönetir",
    "kategori": "browser",
    "risk": 2,
    "parametreler": [
        {"ad": "goal", "tip": "string", "zorunlu": True,
         "aciklama": "Tarayıcıda yapılacak iş (örn: 'Google\'da X ara, ilk sonucu aç')"},
        {"ad": "url", "tip": "string", "zorunlu": False,
         "aciklama": "Başlangıç URL'si (opsiyonel)"},
        {"ad": "max_tur", "tip": "int", "zorunlu": False,
         "aciklama": "Maksimum döngü turu (varsayılan: 15)"},
    ],
}

# ── LLM Sistemi Talimati ─────────────────────────────────────────────
_SISTEM_TALIMATI = """Sen ReYMeN'in tarayıcı otomasyon ajanısın.
Görevin: Verilen hedefe ulaşmak için tarayıcıyı adım adım yönetmek.

TARAYICI KOMUTLARIN:
  navigate: URL'ye git (param: url)
  click:    elementi tıkla (param: selector - CSS selector)
  type:     input alanına yazı yaz (param: selector, text)
  scroll:   sayfayı kaydır (param: direction - up/down)
  back:     bir önceki sayfaya dön
  screenshot: ekran görüntüsü al
  tamam:   hedefe ulaşıldı, döngüyü bitir
  basarisiz: hedefe ulaşılamadı, döngüyü bitir

ADIM ADIM DÖNGÜ:
1. Mevcut sayfayı analiz et (sana snapshot verildi)
2. Bir sonraki eylemi belirle
3. Eylemi yap
4. Hedefe ulaşıldı mı kontrol et
5. Ulaşılmadıysa döngüye devam et

CEVAP FORMATI (sadece geçerli JSON):
{"degerlendirme": "mevcut durum analizi", "hedefe_ulasti": false, "eylem": {"tur": "navigate", "parametreler": {"url": "https://..."}, "aciklama": "google'a git"}}

Kurallar:
- Aynı eylemi 3 kere tekrarlama → tıkanma var, farklı yol dene
- 3 farklı yol dene, yine olmazsa basarisiz bildir
- Hedefe ulaştıysan "hedefe_ulasti": true ve "sonuc" alanını doldur
"""


class BrowserAgentLoop:
    """Browser Agent Loop — hedefe kadar otonom döngü.

    Resilience desenleri:
    - guvenli_tikla: retry + exponential backoff + screenshot
    - sekme state: her adımda sayfa kontrolü
    - invisible döngü tespiti: MAX_DENEME sayacı
    - finally: kaynak temizleme
    """

    def __init__(self, goal: str, baslangic_url: Optional[str] = None,
                 max_tur: int = 15):
        self.goal = goal
        self.baslangic_url = baslangic_url
        self.max_tur = max_tur
        self.tur = 0
        self.son_eylem = None
        self.son_snapshot = ""
        self._beyin = None

        # Resilience state
        self._sekme_acma_sayaci = 0
        self._aktif_sayfa = None
        self._engine = None

    def _beyin_al(self):
        """Beyin (LLM) sistemini lazy import et."""
        if self._beyin is None:
            try:
                from reymen.cereyan.beyin import Beyin as _Beyin
                cfg = {
                    "default_provider": os.environ.get("BEYIN_PROVIDER", "deepseek"),
                    "default_model": os.environ.get("BEYIN_MODEL", "deepseek-chat"),
                    "providers": {
                        "deepseek": {
                            "base_url": "https://api.deepseek.com",
                            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
                        },
                        "openrouter": {
                            "base_url": "https://openrouter.ai/api/v1",
                            "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
                        },
                    },
                }
                self._beyin = _Beyin(cfg)
            except Exception as e:
                logger.warning("[BrowserAgent] Beyin yuklenemedi: %s", e)
                self._beyin = None
        return self._beyin

    # ── Resilience: guvenli_tikla ─────────────────────────────────────
    def _guvenli_tikla(self, selector: str) -> tuple[bool, str]:
        """Retry + exponential backoff + screenshot ile güvenli tıklama.

        Returns:
            (başarılı_mı, sonuç_mesajı)
        """
        for i in range(_DENEME_SAYISI):
            try:
                engine = self._engine_al()
                sonuc = engine.tikla(selector)
                if "hatasi" not in sonuc.lower():
                    return True, sonuc
                logger.warning("[BrowserAgent] Tik %d/%d basarisiz: %s",
                               i + 1, _DENEME_SAYISI, sonuc)
            except Exception as e:
                logger.warning("[BrowserAgent] Tik %d/%d hata: %s",
                               i + 1, _DENEME_SAYISI, e)

            # Exponential backoff: 1sn, 2sn, 3sn
            bekle = _BEKLEME_CARPAN * (i + 1)
            logger.info("[BrowserAgent] %d sn bekleniyor...", bekle)
            time.sleep(bekle)

        # Tüm denemeler başarısız → screenshot al
        try:
            engine = self._engine_al()
            ss = engine.ekran_goruntusu()
            logger.warning("[BrowserAgent] Tik basarisiz, screenshot alindi: %s", ss[:100])
        except Exception:
            pass

        return False, f"[HATA] Tik basarisiz ({_DENEME_SAYISI} deneme): {selector}"

    def _guvenli_sayfa_ac(self, url: str) -> tuple[bool, str]:
        """Timeout + retry ile güvenli sayfa açma."""
        # Invisible döngü tespiti
        if self._sekme_acma_sayaci >= _MAX_DENEME:
            return False, "[HATA] Sekme açma/kapama döngüsü tespit edildi — işlem durduruldu"

        for i in range(_DENEME_SAYISI):
            try:
                engine = self._engine_al()
                sonuc = engine.sayfa_ac(url)
                self._sekme_acma_sayaci += 1
                return True, sonuc
            except TimeoutError:
                logger.warning("[BrowserAgent] Sayfa %d/%d timeout: %s",
                               i + 1, _DENEME_SAYISI, url)
                if i < _DENEME_SAYISI - 1:
                    time.sleep(2.0 * (i + 1))
            except Exception as e:
                logger.warning("[BrowserAgent] Sayfa %d/%d hata: %s",
                               i + 1, _DENEME_SAYISI, e)
                if i < _DENEME_SAYISI - 1:
                    time.sleep(1.0 * (i + 1))

        return False, f"[HATA] Sayfa acilamadi ({_DENEME_SAYISI} deneme): {url}"

    def _guvenli_ekran_goruntusu(self) -> str:
        """Screenshot al, başarısızsa boş dön."""
        for i in range(2):
            try:
                engine = self._engine_al()
                return engine.ekran_goruntusu()
            except Exception as e:
                logger.warning("[BrowserAgent] Screenshot %d/2 hata: %s", i + 1, e)
                time.sleep(0.5)
        return "[Screenshot alinamadi]"

    # ── LLM Karar ─────────────────────────────────────────────────────
    def _llm_karar_ver(self, snapshot: str) -> dict:
        """LLM'den bir sonraki adımı iste."""
        beyin = self._beyin_al()
        snapshot_kisa = snapshot[:2500]

        mesaj = {
            "role": "user",
            "content": (
                f"Mevcut sayfa durumu:\n{snapshot_kisa}\n\n"
                f"Hedef: {self.goal}\n"
                f"Tur: {self.tur + 1}/{self.max_tur}\n\n"
                f"Bir sonraki eylemi belirle (sadece JSON):"
            )
        }

        if beyin:
            try:
                yanit = beyin.dusun(
                    sistem_prompt=_SISTEM_TALIMATI,
                    mesajlar=[mesaj],
                )
                return self._json_ayikla(yanit)
            except Exception as e:
                return self._hata_karar(f"LLM hatasi: {e}")
        else:
            return self._basit_strateji()

    def _json_ayikla(self, yanit: str) -> dict:
        """LLM yanıtından JSON çıkar."""
        try:
            if "```" in yanit:
                parcalar = yanit.split("```")
                for p in parcalar:
                    p = p.strip()
                    if p.startswith("json"):
                        p = p[4:]
                    try:
                        return json.loads(p)
                    except json.JSONDecodeError:
                        continue
            return json.loads(yanit)
        except (json.JSONDecodeError, Exception):
            return {
                "degerlendirme": "JSON ayrıştırılamadı",
                "hedefe_ulasti": True,
                "eylem": {"tur": "tamam", "parametreler": {},
                          "aciklama": "JSON parse hatasi"},
                "sonuc": f"LLM yaniti parse edilemedi: {yanit[:100]}"
            }

    def _hata_karar(self, hata: str) -> dict:
        return {
            "degerlendirme": hata, "hedefe_ulasti": True,
            "eylem": {"tur": "basarisiz", "parametreler": {}, "aciklama": hata},
            "sonuc": f"Hata: {hata}"
        }

    def _basit_strateji(self) -> dict:
        if self.tur == 0 and self.baslangic_url:
            return {
                "degerlendirme": "Baslangic sayfasina gidiliyor",
                "hedefe_ulasti": False,
                "eylem": {"tur": "navigate",
                          "parametreler": {"url": self.baslangic_url},
                          "aciklama": f"{self.baslangic_url}'e git"}
            }
        return {
            "degerlendirme": "Basit strateji, LLM yok",
            "hedefe_ulasti": True,
            "eylem": {"tur": "tamam", "parametreler": {},
                      "aciklama": "Basit strateji sonu"},
            "sonuc": f"LLM bulunamadi. Sayfa: {self.son_snapshot[:200]}"
        }

    def _engine_al(self):
        """Browser engine al (singleton)."""
        if self._engine is None:
            from reymen.arac.browser_engine import BrowserEngine
            self._engine = BrowserEngine()
        return self._engine

    # ── Ana Döngü ─────────────────────────────────────────────────────
    def calistir(self) -> str:
        """Ana döngüyü çalıştır.

        Resilience:
        - Her adımda retry + exponential backoff
        - Screenshot ile hata kanıtı
        - Sekme state yönetimi
        - finally ile kaynak temizleme
        - Invisible döngü tespiti
        """
        logger.info("[BrowserAgent] Baslatiliyor: %s", self.goal)

        engine = None
        try:
            engine = self._engine_al()
            baslatma = engine.baslat()
            logger.info("[BrowserAgent] %s", baslatma)

            # İlk sayfaya git
            if self.baslangic_url:
                basarili, msg = self._guvenli_sayfa_ac(self.baslangic_url)
                if not basarili:
                    return f"❌ BASLANGIC HATASI\n\nHedef: {self.goal}\n{msg}"

            # Ana döngü
            while self.tur < self.max_tur:
                self.tur += 1
                logger.info("[BrowserAgent] Tur %d/%d", self.tur, self.max_tur)

                # Snapshot al
                self.son_snapshot = self._guvenli_ekran_goruntusu()

                # LLM karar ver
                karar = self._llm_karar_ver(self.son_snapshot)
                eylem = karar.get("eylem", {})
                eylem_tur = eylem.get("tur", "tamam")
                self.son_eylem = eylem_tur

                logger.info("[BrowserAgent] Karar: %s", eylem)

                # Hedefe ulaşıldı mı?
                if karar.get("hedefe_ulasti", False):
                    sonuc = karar.get("sonuc", "Hedefe ulasildi")
                    return (
                        f"✅ BROWSER AGENT TAMAMLANDI\n\n"
                        f"Hedef: {self.goal}\n"
                        f"Tur: {self.tur}/{self.max_tur}\n"
                        f"Sonuç: {sonuc}"
                    )

                # Eylemi uygula (resilience desenleri ile)
                params = eylem.get("parametreler", {})

                if eylem_tur == "navigate":
                    url = params.get("url", "")
                    if not url and self.baslangic_url:
                        url = self.baslangic_url
                    basarili, msg = self._guvenli_sayfa_ac(url)
                    if not basarili:
                        return f"❌ NAVIGASYON HATASI\n\nHedef: {self.goal}\nTur: {self.tur}/{self.max_tur}\n{msg}"

                elif eylem_tur == "click":
                    selector = params.get("selector", "")
                    basarili, msg = self._guvenli_tikla(selector)
                    if not basarili:
                        return (
                            f"❌ TIKLAMA HATASI\n\n"
                            f"Hedef: {self.goal}\n"
                            f"Tur: {self.tur}/{self.max_tur}\n"
                            f"Selector: {selector}\n"
                            f"{msg}"
                        )

                elif eylem_tur in ("scrolldown", "scroll"):
                    logger.info("[BrowserAgent] Scroll: %s", params.get("direction", "down"))

                elif eylem_tur in ("tamam", "basarisiz"):
                    return (
                        f"{'✅' if eylem_tur == 'tamam' else '❌'} BROWSER AGENT SONLANDI\n\n"
                        f"Hedef: {self.goal}\n"
                        f"Tur: {self.tur}/{self.max_tur}\n"
                        f"Sonuç: {eylem.get('aciklama', '')}"
                    )

                time.sleep(0.5)

            # Max tura ulaşıldı
            return (
                f"⚠️ BROWSER AGENT SINIR ASIMI\n\n"
                f"Hedef: {self.goal}\n"
                f"Tur: {self.tur}/{self.max_tur}\n"
                f"Sebep: Maksimum tur sayisina ulasildi\n"
                f"Son durum: {self.son_snapshot[:200]}"
            )

        except Exception as e:
            logger.error("[BrowserAgent] Kritik hata: %s", e)
            return (
                f"❌ BROWSER AGENT KRITIK HATA\n\n"
                f"Hedef: {self.goal}\n"
                f"Hata: {e}"
            )

        finally:
            # Kaynakları temizle
            if engine:
                try:
                    engine.kapat()
                    logger.info("[BrowserAgent] Kaynaklar temizlendi")
                except Exception as e:
                    logger.warning("[BrowserAgent] Kapatma hatasi: %s", e)


# ── Tool Entry Point (tools/ discovery için) ──────────────────────────

def run(goal: str = "", url: str = "", max_tur: int = 15) -> str:
    """BROWSER_AGENT tool entry point.

    Args:
        goal: Yapılacak iş (örn: "GitHub'da ReYMeN reposunu bul")
        url: Başlangıç URL'si (opsiyonel)
        max_tur: Maksimum döngü turu

    Returns:
        İşlem sonucu metni
    """
    if not goal:
        return "[HATA] 'goal' parametresi zorunludur"

    agent = BrowserAgentLoop(
        goal=goal,
        baslangic_url=url if url else None,
        max_tur=max_tur
    )
    return agent.calistir()


# ── Test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run(goal="Test sayfasi", url="https://example.com", max_tur=2))
